import json
from flask import Flask, abort, request
from .services import *
from db.models import *

app = Flask(__name__)
POST = 'POST'
GET = 'GET'


@app.route('/')
def home():
    return "<h1>Welcome To Patrol-X</h1>"


@app.route('/events/latest', methods=['POST', 'GET'])
def get_events():
    if request.method == GET:
        events_list = query_events()
        return {"status": "ok", "Events": events_list}, 200
    else:
        abort(404, description="Expected GET request")

@app.route(f'/events/<location>', methods=['POST', 'GET'])
def get_events_by_location(location):
    if request.method == GET:
        print(location)


@app.route('/messages', methods=['POST'])
def receive_messages():
    if request.method != 'POST':
        abort(404)

    # Vérifier si JSON
    if not request.is_json:
        abort(400, description="Expected JSON body")

    try:
        payload = request.get_json()
        raw_messages = payload.get("messages", [])

        if not isinstance(raw_messages, list):
            abort(400, description="'messages' must be a list")

        # 1. Pré-traitement avec DeepSeek-V3
        preprocessed_messages = preprocess_msg(raw_messages)
        # 2. Analyse profonde avec GPT-OSS-120B
        analysed_events = analyse_msg(preprocessed_messages)
        
        # 3. Stockage dans la DB
        
        save_status = save_event(analysed_events)

        if save_status:
            return {"status": "ok", "Message": "Event save successfully"}, 200
        else:
            abort(500, description="Event not saved")

    except Exception as e:
        print("Error:", e)
        abort(500, description=str(e))

        




# @app.route('/chat', methods=[POST])
# def execute():
    # if request.method == POST:
    #     if not request.is_json:
    #             abort(400, description="Expected JSON body")
    #     try:
    #         messages = list(request.json['prompt'])
    #         prompt = f"{PROMPT}\n{messages}"
    #         print("Thinking.........")
    #         completion = client.chat.completions.create(
    #             model=model_list[1],
    #             response_format={"type": "json_object"},
    #             messages=[{"role": "user", "content": prompt}]
    #         )

    #         answer = completion.choices[0].message.content
    #         print("Answer sent to the client")
    #         return answer
    #     except Exception as e:
    #         print(e)
    #         abort(400)
           
    # else:
    #     abort(404)

# print(execute(messages))