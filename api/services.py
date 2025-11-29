import json
import os
from flask import abort
from openai import OpenAI
from pydantic.types import T
from .utils import strip_markdown_fences
from .db.models import *
from datetime import datetime, UTC, timedelta                   

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("Missing HF_TOKEN environment variable")



client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)
model_list = ['openai/gpt-oss-120b','deepseek-ai/DeepSeek-V3']

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
            model=model_list[1],  # DeepSeek-V3
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


def analyse_chat_prompt(preprocessed_message):
    """
    Analyze user query and generate response using GPT-OSS-120B.
    
    Args:
        preprocessed_message (dict): Query parameters from preprocessing
    
    Returns:
        str: Generated response in the detected language
    """
    try:
        system_prompt = load_prompt(GPT_CHAT_SYSTEM_PROMPT)
        
        # Query events based on extracted parameters
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
            model=model_list[0],  # GPT-OSS-120B
            messages=[
                {"role": "system", "content": system_prompt}, 
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
    Main chat function that processes user messages.
    
    Args:
        message (str): User's question/prompt
    
    Returns:
        dict: Response with status and answer
    """
    print(f"Chat with GPT: {message}")
    
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
        model=model_list[1],
        messages=[{"role": "user", "content": prompt}],
    )

    return result.choices[0].message.content


def preprocess_msg(messages: list):
    
    """
    Preprocess incoming messages using DeepSeek-V3.
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
            model=model_list[1],          # DeepSeek-V3 index
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
    Final deep analysis using GPT-OSS-120B.
    Takes preprocessed messages (dict/json) and returns a structured event.
    """
    try:
        # Load system prompt (Haiti-optimized GPT analysis)
        system_prompt = load_prompt(GPT_SYSTEM_PROMPT)

        # Build user prompt - ALWAYS JSON-encode the data
        user_prompt = (
            "You will receive preprocessed messages from Haiti. "
            "Perform deep analysis and return ONE event object.\n\n"
            f"PREPROCESSED_MESSAGES = {json.dumps(preprocessed_msg, ensure_ascii=False, indent=2)}"
        )

        print("Analysing...")

        completion = client.chat.completions.create(
            model=model_list[0],  # GPT-OSS-120B MUST be here, not DeepSeek
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

