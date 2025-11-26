import json
import os
from flask import abort
from openai import OpenAI
from utils import strip_markdown_fences
PREPROCESS_PROMPT = f"""

You are ChatGPT-5.1, an advanced AI specialized in deep message analysis with full adaptation to the Haitian context.
You understand local cultural norms, linguistic patterns (Kreyòl, French, English, mixed), 
and real-world constraints in Haiti such as electricity instability, connectivity issues, transportation risks, 
MonCash usage, local business etiquette, and the indirect communication style common among Haitians.

For each message provided, perform a complete analysis and return a JSON object with two keys:
1. "messages_analysis": an array containing detailed analysis per message
2. "etat_des_lieux": a high-level synthesis summarizing the global situation, trends, risks, and priorities

Each item in "messages_analysis" MUST include:

1. "message": the original text
2. "language": detected language ["kreyol","french","english","mixed"]
3. "category": inferred domain
     ["personal","business","payment","technology","support",
      "logistics","security","urgent_request","social","other"]
4. "relevance": ["Not Relevant","Relevant","Urgent"]
5. "priority_rank": integer from 1 (highest priority) to 5 (lowest priority)
      Priority is based on:
        - urgency
        - potential risk (security, deadlines, transport issues)
        - cultural/business importance
        - emotional or relational weight
6. "confidence": float between 0 and 1
7. "summary": a concise interpretation adapted to Haitian context
8. "recommendation": the best next action considering local realities
      Examples:
        - unstable electricity/internet
        - MonCash or local payment constraints
        - local working hours
        - transport/security concerns
        - business etiquette in Haiti
        - WhatsApp-style informal communication

After analyzing all messages, produce a global section:

"etat_des_lieux": 
    A structured synthesis that includes:
    - overall tone (positive, neutral, tense, urgent)
    - general themes (business, personal, logistics, etc.)
    - risks or constraints specific to Haiti (security, transport, power, delays)
    - the global priority actions
    - the general state of the situation ("où en sommes-nous?")
    - clarity on what should be done next

Your reasoning must be:
- precise
- context-aware
- culturally coherent with Haiti
- aligned with ChatGPT-5.1 reasoning quality
- concise but actionable

Messages to analyze:

"""
                         

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

DEEP_SYSTEM_PROMPT = "prompts/system/deepseek_pretriage.txt"
GPT_SYSTEM_PROMPT = "prompts/system/gpt_analysis.txt"

# USER_PROMPT   = load_prompt("prompts/user/chatbot_query.md")



def preprocess_msg(messages: list):
    os.system("cls")
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
                {"role": "system", "content": system_prompt},
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


