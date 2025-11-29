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

def query_events(mode="limit", limit=10):
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


recipe_documents = [{ "name": "elotes", "ingredients": ["corn", "mayonnaise", "cotija cheese", "sour cream", "lime"], "prep_time": 35 },
                    { "name": "loco moco", "ingredients": ["ground beef", "butter", "onion", "egg", "bread bun", "mushrooms"], "prep_time": 54 },
                    { "name": "patatas bravas", "ingredients": ["potato", "tomato", "olive oil", "onion", "garlic", "paprika"], "prep_time": 80 },
                    { "name": "fried rice", "ingredients": ["rice", "soy sauce", "egg", "onion", "pea", "carrot", "sesame oil"], "prep_time": 40 }]

sample_events = [
  {
    "event": {
      "event_type": "roadblock",
      "severity": "high",
      "priority": "urgent",
      "timestamp_start_start": "2025-01-12T17:30:00",
      "timestamp_start_end": None,
      "probability": 0.92,
      "location": "Delmas 33",
      "summary": "Barikad ak kawotchou boule rapòte nan Delmas 33. Wout la enpratikab.",
      "recommended_action": "Evite zòn nan.",
      "sources_count": 2,
      "messages_used": ["m1", "m2"],
      "cluster_id": "delmas33_block"
    }
  },
  {
    "event": {
      "event_type": "gunshots",
      "severity": "critical",
      "priority": "urgent",
      "timestamp_start_start": "2025-01-12T20:15:00",
      "timestamp_start_end": None,
      "probability": 0.97,
      "location": "Martissant",
      "summary": "Plizyè kout zam lou tande nan Martissant. Sitiyasyon an danjere.",
      "recommended_action": "Evite Martissant imedyatman.",
      "sources_count": 1,
      "messages_used": ["m3"],
      "cluster_id": "martissant_shooting"
    }
  },
  {
    "event": {
      "event_type": "traffic",
      "severity": "medium",
      "priority": "medium",
      "timestamp_start_start": "2025-01-12T14:20:00",
      "timestamp_start_end": None,
      "probability": 0.75,
      "location": "Pétion-Ville",
      "summary": "Gwo trafik sou Rout Frère nan Petyonvil akoz yon kamyon pann.",
      "recommended_action": "Pran yon lòt trajè.",
      "sources_count": 1,
      "messages_used": ["m4"],
      "cluster_id": "petionville_traffic"
    }
  },
  {
    "event": {
      "event_type": "roadblock",
      "severity": "medium",
      "priority": "high",
      "timestamp_start_start": "2025-01-11T09:45:00",
      "timestamp_start_end": "2025-01-11T12:00:00",
      "probability": 0.82,
      "location": "Carrefour-Feuilles",
      "summary": "Barikad ak fatra sou wout Kafou Fèy, deplasman difisil.",
      "recommended_action": "Evite zòn nan si posib.",
      "sources_count": 2,
      "messages_used": ["m5", "m6"],
      "cluster_id": "carrefour_feuilles_block"
    }
  },
  {
    "event": {
      "event_type": "kidnapping",
      "severity": "critical",
      "priority": "urgent",
      "timestamp_start_start": "2025-01-10T18:10:00",
      "timestamp_start_end": None,
      "probability": 0.89,
      "location": "Delmas 19",
      "summary": "Yon ka kidnapin rapòte nan Delmas 19.",
      "recommended_action": "Evite Delmas 19 pou kounya.",
      "sources_count": 1,
      "messages_used": ["m7"],
      "cluster_id": "delmas19_kidnapping"
    }
  },
  {
    "event": {
      "event_type": "weather",
      "severity": "medium",
      "priority": "medium",
      "timestamp_start_start": "2025-01-12T13:00:00",
      "timestamp_start_end": None,
      "probability": 0.70,
      "location": "Tabarre",
      "summary": "Gwo lapli ap tonbe nan Tabarre, dlo koule nan kèk lari.",
      "recommended_action": "Kondwi ak prekosyon.",
      "sources_count": 1,
      "messages_used": ["m8"],
      "cluster_id": "tabarre_rain"
    }
  },
  {
    "event": {
      "event_type": "protest",
      "severity": "high",
      "priority": "high",
      "timestamp_start_start": "2025-01-11T15:00:00",
      "timestamp_start_end": "2025-01-11T17:30:00",
      "probability": 0.85,
      "location": "Route de l'Aéroport",
      "summary": "Manifestasyon sou Rout Ayewopò, foul ap mache ak bandwòl.",
      "recommended_action": "Evite zòn nan jiska sitiyasyon an kalme.",
      "sources_count": 1,
      "messages_used": ["m9"],
      "cluster_id": "airport_road_protest"
    }
  },
  {
    "event": {
      "event_type": "insecurity",
      "severity": "high",
      "priority": "urgent",
      "timestamp_start_start": "2025-01-12T08:45:00",
      "timestamp_start_end": None,
      "probability": 0.90,
      "location": "Croix-des-Bouquets",
      "summary": "Rapò sou mouvman gang ak vol machin nan Kwadèboukè.",
      "recommended_action": "Evite deplase nan zòn nan pou kounya.",
      "sources_count": 1,
      "messages_used": ["m10"],
      "cluster_id": "croix_des_bouquets_insecurity"
    }
  },
  {
    "event": {
      "event_type": "accident",
      "severity": "medium",
      "priority": "medium",
      "timestamp_start_start": "2025-01-12T10:10:00",
      "timestamp_start_end": None,
      "probability": 0.78,
      "location": "Cap-Haïtien",
      "summary": "Aksidan ant yon moto ak yon machin nan Okap.",
      "recommended_action": "Pran prekosyon nan trajè a.",
      "sources_count": 1,
      "messages_used": ["m11"],
      "cluster_id": "cap_haitian_accident"
    }
  },
  {
    "event": {
      "event_type": "fire",
      "severity": "high",
      "priority": "urgent",
      "timestamp_start_start": "2025-01-13T01:00:00",
      "timestamp_start_end": None,
      "probability": 0.87,
      "location": "Delmas 2",
      "summary": "Dife pran nan yon kay nan Delmas 2.",
      "recommended_action": "Evite zòn nan.",
      "sources_count": 1,
      "messages_used": ["m12"],
      "cluster_id": "delmas2_fire"
    }
  }
]

#save_events_to_db(sample_events[0])
# for q in query_events():
#     print(q)