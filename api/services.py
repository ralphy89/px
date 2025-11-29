import json
import os
import numpy as np
from flask import abort
from openai import OpenAI
from pydantic.types import T
from .utils import strip_markdown_fences
from .db.models import *
from datetime import datetime, UTC, timedelta                   



GROK_TOKEN = os.environ.get("GROK_TOKEN")
if not GROK_TOKEN:
    raise RuntimeError(
        "Missing GROK_API_KEY or XAI_API_KEY environment variable.\n"
        "Get your API key from https://console.x.ai/\n"
        "Then set it: export GROK_API_KEY='your-api-key-here'"
    )

# Grok AI uses OpenAI-compatible API
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=GROK_TOKEN,
)


model_list = ['grok-4-1-fast-reasoning', 'grok-4-fast-reasoning']  # [analysis_model, preprocessing_model] 

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEEP_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts/system/deepseek_pretriage.txt")
GPT_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts/system/gpt_analysis.txt")
DEEPSEEK_CHAT_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts/system/deepseek_for_chat.txt")
GPT_CHAT_SYSTEM_PROMPT = os.path.join(BASE_DIR, "prompts/system/gpt_for_chat.txt")
# USER_PROMPT   = load_prompt("prompts/user/chatbot_query.md")


def preprocess_chat_prompt(message):
    """
    Preprocess user message to extract query parameters.
    
    Args:
        message (str): User's question/prompt
    
    Returns:
        dict: Extracted query parameters including:
            - query_type: Type of query (location, event_type, severity, general, etc.)
            - location: Location string or null
            - location_is_general: Whether location is a parent zone
            - event_types: List of event types or empty list
            - severity: Severity level or null
            - time_range: Time range filter
            - language: Detected language (ht, fr, en)
            - original_question: Original user question
    """
    try:
        system_prompt = load_prompt(DEEPSEEK_CHAT_SYSTEM_PROMPT)
        user_prompt = f"User question: {message}"
        print(f"Preprocessing User prompt: {user_prompt}")
        
        completion = client.chat.completions.create(
            response_format={"type": "json_object"},
            model=model_list[1], 
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_prompt}
            ]
        )
        
        preprocessed_msg = strip_markdown_fences(completion.choices[0].message.content)
        print(f"Preprocessed message: {preprocessed_msg}")
        
        query_params = json.loads(preprocessed_msg)
        
        # Ensure all required fields exist with defaults
        query_params.setdefault('query_type', 'general')
        query_params.setdefault('location', None)
        query_params.setdefault('location_is_general', False)
        query_params.setdefault('event_types', [])
        query_params.setdefault('severity', None)
        query_params.setdefault('time_range', 'any')
        query_params.setdefault('language', 'ht')
        query_params.setdefault('original_question', message)
        
        return query_params
        
    except Exception as e:
        print(f"Error preprocessing chat prompt: {e}")
        # Return default query params on error
        return {
            'query_type': 'general',
            'location': None,
            'location_is_general': False,
            'event_types': [],
            'severity': None,
            'time_range': 'any',
            'language': 'ht',
            'original_question': message
        }


def format_events_for_rag(events):
    """
    Format events list into readable RAG context string.
    
    Args:
        events (list): List of event dictionaries
    
    Returns:
        str: Formatted events string or "NO_EVENTS"
    """
    if not events or len(events) == 0:
        return "NO_EVENTS"
    
    formatted_events = []
    for e in events:
        event_str = f"- [{e.get('timestamp_start', 'Unknown time')}] {e.get('summary', 'No summary')} "
        event_str += f"(Type: {e.get('event_type', 'unknown')}, "
        event_str += f"Severity: {e.get('severity', 'unknown')}, "
        event_str += f"Location: {e.get('location', 'unknown')}"
        
        if e.get('sources'):
            event_str += f", Sources: {e.get('sources')}"
        
        if e.get('recommended_action'):
            event_str += f", Action: {e.get('recommended_action')}"
        
        event_str += ")"
        formatted_events.append(event_str)
    
    return "\n".join(formatted_events)


def create_event_searchable_text(event):
    """
    Create a searchable text representation of an event for embedding.
    
    Args:
        event (dict): Event dictionary
    
    Returns:
        str: Searchable text combining summary, location, event_type, etc.
    """
    parts = []
    
    # Add summary (most important)
    if event.get('summary'):
        parts.append(event['summary'])
    
    # Add event type
    if event.get('event_type'):
        parts.append(f"Event type: {event['event_type']}")
    
    # Add location
    if event.get('location'):
        parts.append(f"Location: {event['location']}")
    
    # Add severity if high/critical
    if event.get('severity') in ['critical', 'high']:
        parts.append(f"Severity: {event['severity']}")
    
    # Add recommended action if available
    if event.get('recommended_action'):
        parts.append(event['recommended_action'])
    
    return " ".join(parts)


def get_query_embedding_grok(query_text):
    """
    Generate embedding for user query using Grok AI embeddings API.
    
    Args:
        query_text (str): User query text
    
    Returns:
        numpy.ndarray: Query embedding vector or None
    """
    try:
        # Try different Grok embedding models
        # Note: Grok may use different model names for embeddings
        embedding_models = ["grok-2-1212", "grok-2", "grok-beta"]
        
        for model_name in embedding_models:
            try:
                response = client.embeddings.create(
                    model=model_name,
                    input=query_text
                )
                
                embedding = np.array(response.data[0].embedding)
                print(f"Successfully generated embedding using {model_name}")
                return embedding
            except Exception as model_error:
                print(f"Model {model_name} failed: {model_error}, trying next...")
                continue
        
        print("All Grok embedding models failed")
        return None
    except Exception as e:
        print(f"Error generating query embedding with Grok: {e}")
        return None


def get_event_embeddings_grok(events):
    """
    Generate embeddings for a list of events using Grok AI.
    
    Args:
        events (list): List of event dictionaries
    
    Returns:
        dict: Dictionary mapping event index to embedding
    """
    if not events:
        return {}
    
    try:
        # Create searchable texts
        searchable_texts = [create_event_searchable_text(e) for e in events]
        
        # Try different Grok embedding models
        embedding_models = ["grok-code-fast-1"]
        
        for model_name in embedding_models:
            try:
                # Batch embed using Grok API
                response = client.embeddings.create(
                    model=model_name,
                    input=searchable_texts
                )
                
                event_embeddings = {}
                for i, embedding_data in enumerate(response.data):
                    if i < len(events):
                        event_embeddings[i] = np.array(embedding_data.embedding)
                
                print(f"Successfully generated {len(event_embeddings)} embeddings using {model_name}")
                return event_embeddings
            except Exception as model_error:
                print(f"Model {model_name} failed: {model_error}, trying next...")
                continue
        
        print("All Grok embedding models failed")
        return {}
        
    except Exception as e:
        print(f"Error generating event embeddings with Grok: {e}")
        return {}


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    try:
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    except Exception as e:
        print(f"Error calculating cosine similarity: {e}")
        return 0.0


def vector_search_events_grok(query_text, events, top_k=10):
    """
    Perform vector search using Grok embeddings to find most relevant events.
    
    Args:
        query_text (str): User query
        events (list): List of candidate events
        top_k (int): Number of top results to return
    
    Returns:
        list: Top K most relevant events sorted by relevance
    """
    if not events or len(events) == 0:
        return []
    
    try:
        # Generate query embedding
        query_embedding = get_query_embedding_grok(query_text)
        if query_embedding is None:
            print("Query embedding failed, returning recent events")
            return events[:top_k] if len(events) > top_k else events
        
        # Generate event embeddings
        event_embeddings = get_event_embeddings_grok(events)
        if not event_embeddings:
            print("Event embedding failed, returning recent events")
            return events[:top_k] if len(events) > top_k else events
        
        # Calculate similarities
        similarities = []
        for i, event in enumerate(events):
            if i in event_embeddings:
                similarity = cosine_similarity(query_embedding, event_embeddings[i])
                similarities.append((similarity, event))
            else:
                # If embedding failed for this event, give it low priority
                similarities.append((0.0, event))
        
        # Sort by similarity (descending) and return top K
        similarities.sort(key=lambda x: x[0], reverse=True)
        top_events = [event for _, event in similarities[:top_k]]
        
        print(f"Grok vector search: Found {len(top_events)} most relevant events")
        return top_events
        
    except Exception as e:
        print(f"Vector search error: {e}, returning recent events")
        return events[:top_k] if len(events) > top_k else events


def get_events_with_vector_search(query_params, original_question):
    """
    Get events using Grok vector search when no location is specified.
    This prevents loading all events and instead finds semantically relevant ones.
    
    Args:
        query_params (dict): Query parameters
        original_question (str): Original user question for semantic search
    
    Returns:
        list: Most relevant events
    """
    # First, get candidate events with filters (but no location)
    candidate_params = query_params.copy()
    candidate_params['location'] = None
    
    # Apply time filter - default to last 24h for general queries to limit candidates
    # This prevents loading too many old events
    if candidate_params.get('time_range') == 'any':
        candidate_params['time_range'] = 'last_24h'
        print("No time range specified for general query - defaulting to last_24h")
    
    # Get candidate events (limited by time and other filters)
    candidate_events = get_events_for_chat(candidate_params)
    
    if not candidate_events:
        print("No candidate events found for vector search")
        return []
    
    print(f"Found {len(candidate_events)} candidate events for Grok vector search")
    
    # Build enhanced search query from original question and extracted filters
    # This helps the vector search understand the user's intent better
    search_query = original_question
    
    # Enhance search query with extracted filters for better semantic matching
    if query_params.get('event_types'):
        search_query += " " + " ".join(query_params['event_types'])
    if query_params.get('severity'):
        search_query += " " + query_params['severity'] + " severity urgent"
    
    # Perform vector search using Grok embeddings to get top relevant events
    # Limit to top 15 most relevant to keep response focused
    try:
        top_events = vector_search_events_grok(search_query, candidate_events, top_k=15)
        return top_events
    except Exception as e:
        print(f"Grok vector search failed: {e}, falling back to recent events")
        # Fallback: return most recent events if vector search fails
        return candidate_events[:15] if len(candidate_events) > 15 else candidate_events


def is_patrolx_related(query_params, original_question):
    """
    Determine if the user's question is related to Patrol-X (events, locations, security, etc.).
    
    Args:
        query_params (dict): Extracted query parameters
        original_question (str): Original user question
    
    Returns:
        bool: True if question is Patrol-X related, False otherwise
    """
    # Check if any Patrol-X specific parameters were extracted
    has_location = query_params.get('location') and query_params.get('location').strip()
    has_event_types = query_params.get('event_types') and len(query_params.get('event_types', [])) > 0
    has_severity = query_params.get('severity') and query_params.get('severity').strip()
    
    # Check query type - if it's explicitly about location, event_type, severity, it's Patrol-X related
    query_type = query_params.get('query_type', 'general')
    if query_type in ['location', 'event_type', 'severity', 'combined']:
        return True
    
    # Check if question contains Patrol-X related keywords
    question_lower = original_question.lower()
    patrolx_keywords = [
        # Locations (Haitian zones)
        'delmas', 'pétion-ville', 'petionville', 'tabarre', 'cité soleil', 'site solèy',
        'carrefour', 'martissant', 'croix-des-bouquets', 'pèlerin', 'thomassin',
        'canapé-vert', 'laboule', 'kenscoff', 'bel-air', 'la saline', 'fontamara',
        # Event types
        'barikad', 'barricade', 'tire', 'shooting', 'kidnapping', 'enlèvement',
        'manifestation', 'protest', 'accident', 'aksidan', 'roadblock', 'blokaj',
        # Security/events related
        'kisa k ap pase', 'what happened', 'quoi de neuf', 'événement', 'event',
        'sécurité', 'security', 'danger', 'dangerous', 'insecurity', 'ensekirite',
        'situation', 'alert', 'alerte', 'crisis', 'crise'
    ]
    
    # If question contains any Patrol-X keywords, it's related
    if any(keyword in question_lower for keyword in patrolx_keywords):
        return True
    
    # If user explicitly asks about location, events, or security, it's related
    if has_location or has_event_types or has_severity:
        return True
    
    # If query type is general but contains location/event hints, check more carefully
    if query_type == 'general':
        # Very general questions like "what's the weather" or "tell me a joke" are not Patrol-X related
        general_questions = [
            'weather', 'météo', 'tan', 'joke', 'blague', 'joke', 'funny',
            'recipe', 'recette', 'cooking', 'cuisine', 'how to', 'comment faire',
            'what is', 'qu\'est-ce que', 'kisa se', 'definition', 'définition'
        ]
        if any(gq in question_lower for gq in general_questions):
            # Check if it's also about Haiti/Patrol-X context
            if not any(pk in question_lower for pk in ['haiti', 'haitian', 'ayiti', 'haitien']):
                return False
    
    # Default: if we extracted any Patrol-X parameters, assume it's related
    # Otherwise, it's likely a general question
    return has_location or has_event_types or has_severity


def answer_general_question(original_question, language='ht'):
    """
    Answer general questions using Grok's knowledge (not Patrol-X related).
    
    Args:
        original_question (str): User's question
        language (str): Detected language (ht, fr, en)
    
    Returns:
        str: Grok's answer to the general question
    """
    try:
        # Use Grok directly for general knowledge questions
        system_prompt = f"""You are a helpful AI assistant. Answer the user's question clearly and accurately using your knowledge.
        
Respond in {language} language if the question is in that language, otherwise respond in the same language as the question."""
        
        completion = client.chat.completions.create(
            model=model_list[0],  # grok-4-1-fast-reasoning for general knowledge
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_question}
            ]
        )
        
        answer = completion.choices[0].message.content
        print(f"Answered general question using Grok knowledge")
        return answer
        
    except Exception as e:
        print(f"Error answering general question: {e}")
        lang = language
        if lang == 'ht':
            return "Désolé, mwen pa ka reponn kèksyon ou a kounye a. Tanpri eseye ankò."
        elif lang == 'fr':
            return "Désolé, je n'ai pas pu traiter votre question. Veuillez réessayer."
        else:
            return "Sorry, I couldn't process your question. Please try again."


def analyse_chat_prompt(preprocessed_message):
    """
    Analyze user query and generate response using Grok.
    Routes to Patrol-X event search or general knowledge based on question type.
    
    Args:
        preprocessed_message (dict): Query parameters from preprocessing
    
    Returns:
        str: Generated response in the detected language
    """
    try:
        original_question = preprocessed_message.get('original_question', '')
        language = preprocessed_message.get('language', 'ht')
        
        # Check if question is Patrol-X related
        is_related = is_patrolx_related(preprocessed_message, original_question)
        
        if not is_related:
            # Not Patrol-X related: use Grok's general knowledge
            print("Question is not Patrol-X related - using Grok general knowledge")
            return answer_general_question(original_question, language)
        
        # Patrol-X related: use event-based search
        print("Question is Patrol-X related - using event search")
        system_prompt = load_prompt(GPT_CHAT_SYSTEM_PROMPT)
        
        # Determine if we should use vector search (no location specified)
        location = preprocessed_message.get('location')
        query_type = preprocessed_message.get('query_type', 'general')
        
        # For general situation questions, ensure we use last_24h events
        if query_type == 'general':
            # Check if it's a general situation question (safety, can I go out, etc.)
            situation_keywords = ['koman laria', 'eske m ka soti', 'how is the area', 'can i go out', 
                                 'is it safe', 'kijan sitiyasyon', 'eske li an sekirite', 'should i go out']
            question_lower = original_question.lower()
            is_situation_question = any(keyword in question_lower for keyword in situation_keywords)
            
            if is_situation_question:
                # Force last_24h for situation questions
                preprocessed_message['time_range'] = 'last_24h'
                print("General situation question detected - using last_24h events")
        
        if not location or not location.strip():
            # No location: use Grok vector search to find semantically relevant events
            print("No location specified - using Grok vector search")
            events = get_events_with_vector_search(preprocessed_message, original_question)
        else:
            # Location specified: use traditional filtered query
            print("Location specified - using filtered query")
            events = get_events_for_chat(preprocessed_message)
        
        events_context = format_events_for_rag(events)
        
        # Build user prompt with context
        user_prompt = f"""
                    User question context (extracted parameters):
                    {json.dumps(preprocessed_message, ensure_ascii=False, indent=2)}

                    Database events (RAG context):
                    {events_context}

                    Original user question: "{preprocessed_message.get('original_question', '')}"

                    Respond in {preprocessed_message.get('language', 'ht')} language.
                    """
        
        print(f"Query type: {preprocessed_message.get('query_type')}")
        print(f"Events found: {len(events)}")
        
        completion = client.chat.completions.create(
            model=model_list[0],  
            messages=[
                {"role": "system", "content": system_prompt + "\n\nToday's date: " + datetime.now(UTC).strftime("%Y-%m-%d")}, 
                {"role": "user", "content": user_prompt}
            ]
        )

        analysed_msg = completion.choices[0].message.content
        return analysed_msg
       
    except Exception as e:
        print(f"Error analysing chat prompt: {e}")
        # Return helpful error message in detected language
        lang = preprocessed_message.get('language', 'ht')
        if lang == 'ht':
            return "Désolé, mwen pa ka reponn kèksyon ou a kounye a. Tanpri eseye ankò."
        elif lang == 'fr':
            return "Désolé, je n'ai pas pu traiter votre question. Veuillez réessayer."
        else:
            return "Sorry, I couldn't process your question. Please try again."


def chat_with_gpt(message):
    """
    Main chat function that processes user messages using Grok AI.
    
    Args:
        message (str): User's question/prompt
    
    Returns:
        dict: Response with status and answer
    """
    print(f"Chat with Grok: {message}")
    
    # Step 1: Preprocess to extract query parameters
    preprocessed_msg = preprocess_chat_prompt(message)
    
    if not preprocessed_msg:
        return {
            "status": "error",
            "answer": "Error preprocessing your question. Please try again."
        }
    
    # Step 2: Analyze and generate response
    analysed_msg = analyse_chat_prompt(preprocessed_msg)
    
    if not analysed_msg:
        return {
            "status": "error",
            "answer": "Error generating response. Please try again."
        }
    
    return {
        "status": "ok",
        "answer": analysed_msg
    }

def get_summary_prompt(events_list, location):
    # Build RAG context from events
    context = "\n".join([
    f"- [{e.get('timestamp_start')}] {e.get('summary')} "
    f"(Type: {e.get('event_type')}, Severity: {e.get('severity')}, "
    f"Location: {e.get('location')}, Sources: {e.get('sources')})"
    for e in events_list
    ])

    print(context)
    prompt = f"""
    You are Patrol-X, an AI system summarizing verified public safety and mobility alerts 
    for Haitian cities.

    INTERPRETATION RULES BASED ON HAITIAN GEOGRAPHY (critical):

    1. The user selected: "{location}". This is the main area of interest.

    2. Haitian locations follow different naming conventions. 
    Apply these rules to interpret event locations correctly:

    • **Delmas, Pelerin, Martissant and Tabarre rule**  
        - Locations like "Delmas 19", "Delmas 33", "Delmas 75", "Pelerin 19", "Pelerin 33", "Pelerin 75", "Martissant 19", "Martissant 33", "Martissant 75", "Tabarre 19", "Tabarre 33", "Tabarre 75", etc. 
        ARE official subdivisions of Delmas, Pelerin, Martissant and Tabarre.  
        - When the selected location is "Delmas", "Pelerin", "Martissant" or "Tabarre", include and summarize 
        all events from "Delmas X", "Pelerin X", "Martissant X" or "Tabarre X" zones together.

    • **Non-numbered commune rule (e.g., Carrefour, Pétion-Ville)**  
        - Locations such as "Carrefour Drouillard", "Carrefour Feuilles", 
        "Carrefour Vincent", etc. are NOT subdivisions of Carrefour.  
        - They are separate zones that merely share a name root.  
        - When the selected location is "Carrefour", DO NOT merge or treat 
        these other zones as Carrefour.  
        - Report them separately and clearly as distinct areas.

        IMPORTANT GEOGRAPHIC RULES (HAITI):

        1. "Carrefour" is a standalone commune. 
        It does NOT contain: 
        - Carrefour Feuilles
        - Carrefour Drouillard
        - Carrefour Vincent

        2. Any location that STARTS WITH "Carrefour " is NOT a subzone of the commune “Carrefour”.
        Example:
        - "Carrefour Feuilles" ≠ "Carrefour"
        - "Carrefour Drouillard" ≠ "Carrefour"
        - "Carrefour Vincent" ≠ "Carrefour"
        Treat them as completely independent locations.
        - If user ask about "Carrefour", you should not include "Carrefour Feuilles", 
        "Carrefour Drouillard", "Carrefour Vincent" in the result. Keep it simple and clear.

        3. Only Delmas is hierarchical:
        - Delmas 19, Delmas 40B, Delmas 75 → subzones of Delmas.
        But "Carrefour X" does NOT follow this rule.

        You MUST respect these rules. Never merge, relate, or assume hierarchy between them.


    3. NEVER invent locations, subdivisions, or relations between zones.  
    Use ONLY what is explicitly found in the event list.

    EVENTS DETECTED (last 24h):
    {context}

    YOUR TASKS:
    1. Summarize the situation clearly based ONLY on the provided events.
    2. Respect the rules above when grouping or separating zones.
    3. Identify risks strictly based on the data.
    4. Provide a short and structured “état des lieux”.
    5. Mention sources exactly as provided.
    6. Keep the summary concise (1 short paragraphs).

    Use familiar Haitian alert language such as:
    - "État des lieux :"
    - "Voici ce qu’il faut retenir :"
    - "Selon les informations disponibles…"
    - "Zones concernées :"
    - "Sources mentionnées : …"

    Produce ONLY the final summary.
    """

    return prompt

def generate_summary(events_list, location):
    if not events_list:
        return f"No events detected in the last 24 hours for {location}. The area appears calm."
    prompt = get_summary_prompt(events_list, location)
    result = client.chat.completions.create(
        model=model_list[1],  # grok-2 for summarization
        messages=[{"role": "user", "content": prompt}],
    )

    return result.choices[0].message.content


def preprocess_msg(messages: list):
    
    """
    Preprocess incoming messages using Grok AI.
    - Filters irrelevant messages
    - Normalizes text
    - Extracts early tags
    - Outputs structured JSON
    """
    try:
        # Load system prompt
        system_prompt = load_prompt(DEEP_SYSTEM_PROMPT)

        # Build user prompt cleanly
        user_prompt = (
            "Here is a list of messages. Analyze each message independently.\n"
            "Return JSON ONLY.\n\n"
            f"{messages}"
        )

        print("Preprocessing...")

        completion = client.chat.completions.create(
            model=model_list[1],          # grok-2 for preprocessing
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        # Extract content
        content = strip_markdown_fences(completion.choices[0].message.content)
        print("Preprocessing DONE")
        return content

    except Exception as e:
        print("Preprocess Error:", e)
        return None



def analyse_msg(preprocessed_msg: dict):
    """
    Final deep analysis using Grok-2.
    Takes preprocessed messages (dict/json) and returns a structured event.
    """
    try:
        # Load system prompt (Haiti-optimized analysis)
        system_prompt = load_prompt(GPT_SYSTEM_PROMPT)

        # Build user prompt - ALWAYS JSON-encode the data
        user_prompt = (
            "You will receive preprocessed messages from Haiti. "
            "Perform deep analysis and return ONE event object.\n\n"
            f"PREPROCESSED_MESSAGES = {json.dumps(preprocessed_msg, ensure_ascii=False, indent=2)}"
        )

        print("Analysing...")

        completion = client.chat.completions.create(
            model=model_list[0],  # grok-2 for deep analysis
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt },
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract content and parse JSON
        content = completion.choices[0].message.content
        event = json.loads(content)

        print("Analysing DONE")
        return event

    except Exception as e:
        print("Analysis error:", e)
        raise e

