import os
import json
from pyexpat.errors import messages
from flask import Flask, abort, request
from openai import OpenAI

app = Flask(__name__)
POST = 'POST'
GET = 'GET'
PROMPT = f"""

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
model_list = ['openai/gpt-oss-120b','deepseek-ai/DeepSeek-V3']


client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

# messages = [
#     "Kidnaping au niveau de Siloe",
#     # "Bòn fèt jodi a frè m nan!",
#     # "Dlo ap monte anpil bò Gonaïves yo.",
# ]




# for model in model_list:
#   completion = client.chat.completions.create(
#       model=model,
#       response_format={"type": "json_object"},
#       messages=[{"role": "user", "content": prompt}]
#   )

@app.route('/')
def home():
    return "<h1>Welcome To Patrol-X</h1>"



@app.route('/chat', methods=[POST])
def execute():
    if request.method == POST:
        try:
            
            messages = list(request.json['prompt'])
            prompt = f"{PROMPT}\n{messages}"
            print("Thinking.........")
            completion = client.chat.completions.create(
                model=model_list[1],
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}]
            )

            answer = completion.choices[0].message.content
            print("Answer sent to the client")
            return answer
        except Exception as e:
            print(e)
           
    else:
        return str(os.environ['HF_TOKEN'])

# print(execute(messages))