import json
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


uri = f"mongodb+srv://{os.environ.get('DB_USERNAME')}:{os.environ.get('DB_PASSWORD')}@px-test.amaelqi.mongodb.net/?appName=px-test"
print(uri)
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!\n\n")
except Exception as e:
    print(e)


db = client.test
recipe = db['recipe']

event_collection = db['events']
processed_messages_collection = db['processed_messages']

def get_events_for_chat(preprocessed_message):
    return list(
        event_collection.find(
            {
                "location": {
                    "$regex": preprocessed_message['location'],
                    "$options": "i"   # case-insensitive
                },
            },
            {"_id": 0}
        )
    )

def save_processed_messages(preprocessed_message):
    try:
        result = processed_messages_collection.insert_many(preprocessed_message)
        return result
    except Exception as e:
        raise e

def save_event(analysed_events):
    try:
        result = event_collection.insert_many(analysed_events['events'])

        return result
    except Exception as e:
        raise e
   

from datetime import UTC, datetime, timedelta

def query_events_by_location(location):
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    return list(
        event_collection.find(
            {
                "location": {
                    "$regex": location,
                    "$options": "i"   # case-insensitive
                },
                # "timestamp_start": {"$gte": cutoff}
            },
            {"_id": 0}
        ).sort("timestamp_start", -1)
    )

def query_events(mode="limit", limit=50):
    if mode == "latest":
        return event_collection.find_one(
            {}, {"_id":0},
            sort=[("timestamp_start", -1)]
        )
    
    if mode == "limit":
        return list(
            event_collection.find(
                {}, {"_id":0}
            )
            .sort("timestamp_start", -1)
            .limit(limit)
        )

    if mode == "last_24h":
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        print(cutoff)
        return list(
            event_collection.find({
                "timestamp_start": {"$gte": cutoff}
            },
            {"_id":0}).sort("timestamp_start", -1)
        )


    return []

