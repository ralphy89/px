import json
from flask import Flask, abort, request
from flask_cors import CORS
from .services import *
from .db.models import *

app = Flask(__name__)
CORS(app, origins=["*"])

POST = 'POST'
GET = 'GET'

@app.route('/')
def home():
    return "<h1>Welcome To Patrol-X</h1>"


@app.route('/chat', methods=['POST'])
def chat():
    if request.method == POST:
        if not request.is_json:
            abort(400, description="Expected JSON body")
        try:
            messages = request.json['prompt']
            return chat_with_gpt(messages)
        except Exception as e:
            print(e)
            abort(400, description=str(e))
    else:
        abort(404, description="Expected POST request")


@app.route('/events/latest', methods=['POST', 'GET'])
def get_events():
    if request.method == GET:
        events_list = query_events()
        return {"status": "ok", "Events": events_list}, 200
    else:
        abort(404, description="Expected GET request")

@app.route('/events/location/<location>', methods=['GET'])
def get_events_by_location(location):
    print(f"\nRequest for location: {location}")

    # 1. Query MongoDB (last 24h + partial match)
    events_list = query_events_by_location(location)
    print(f"Events found: {len(events_list)}")

    # 2. Generate RAG summary
    summary = generate_summary(events_list, location)
    return {"status": "ok", "summary": summary}, 200



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

        
