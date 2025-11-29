import json
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import UTC, datetime, timedelta

uri = f"mongodb+srv://{os.environ.get('DB_USERNAME')}:{os.environ.get('DB_PASSWORD')}@px-prod.amaelqi.mongodb.net/?appName=px-test"
print(uri)
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!\n\n")
except Exception as e:
    print(e)


db = client.production

event_collection = db['events']
processed_messages_collection = db['processed_messages']
users_collection = db['users']
sessions_collection = db['sessions']
notifications_collection = db['notifications']


def get_time_cutoff(time_range):
    """Convert time_range string to datetime cutoff."""
    now = datetime.now(UTC)
    
    if time_range == "today":
        # Start of today in UTC
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "yesterday":
        # Start of yesterday in UTC
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "last_24h":
        return now - timedelta(hours=24)
    elif time_range == "last_week":
        return now - timedelta(days=7)
    else:  # "any"
        return None


def build_location_query(location, location_is_general):
    """Build MongoDB query for location filtering, respecting hierarchy."""
    if not location:
        return {}
    
    # Hierarchical zones that support parent → subzone
    hierarchical_zones = {
        "Delmas": ["Delmas"],
        "Tabarre": ["Tabarre", "Clercine", "Klèsin"],
        "Pétion-Ville": ["Pétion-Ville", "Petionville", "Petyonvil", "PV"],
        "Croix-des-Bouquets": ["Croix-des-Bouquets", "Kwadebouke", "Bon Repos"],
        "Pèlerin": ["Pèlerin", "Pelerin"],
        "Thomassin": ["Thomassin"],
        "Canapé-Vert": ["Canapé-Vert", "Kanapevè"],
        "Laboule": ["Laboule", "Laboul"]
    }
    
    # Normalize location name
    location_normalized = location.strip()
    
    # Check if this is a hierarchical parent
    if location_is_general:
        # Find matching parent zone
        for parent, variants in hierarchical_zones.items():
            if any(location_normalized.lower() == v.lower() for v in variants):
                # Build regex to match parent and all subzones
                # e.g., "Delmas" should match "Delmas", "Delmas 19", "Delmas 33", etc.
                # Pattern: ^Delmas($|\s|\s\d+)
                parent_pattern = parent.replace("-", "\\-")  # Escape hyphens
                regex_pattern = f"^{parent_pattern}($|\\s|\\s\\d+)"
                return {"location": {"$regex": regex_pattern, "$options": "i"}}
        
        # If not found in hierarchical list, treat as exact match
        return {"location": {"$regex": f"^{location_normalized.replace('-', '\\-')}$", "$options": "i"}}
    else:
        # Specific subzone or non-hierarchical zone - exact match
        # Escape special regex characters
        escaped_location = location_normalized.replace("-", "\\-")
        return {"location": {"$regex": f"^{escaped_location}$", "$options": "i"}}


def get_events_for_chat(query_params):
    """
    Flexible query function that supports multiple filters.
    
    Args:
        query_params (dict): Contains:
            - location (str or None): Location to filter by
            - location_is_general (bool): Whether location is a parent zone
            - event_types (list): List of event types to filter by
            - severity (str or None): Severity level to filter by
            - time_range (str): "today", "yesterday", "last_24h", "last_week", "any"
            - query_type (str): Type of query for logging
    
    Returns:
        list: List of matching events
    """
    try:
        # Build MongoDB query
        query = {}
        
        # Location filter (normalize empty strings to None)
        location = query_params.get('location')
        if location and location.strip():
            location_query = build_location_query(
                location,
                query_params.get('location_is_general', False)
            )
            query.update(location_query)
        
        # Event type filter
        event_types = query_params.get('event_types', [])
        if event_types and len(event_types) > 0:
            query['event_type'] = {"$in": event_types}
        
        # Severity filter (include the specified severity and higher)
        severity = query_params.get('severity')
        if severity:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            severity_level = severity_order.get(severity.lower(), 3)
            # Include all severities at or above the requested level
            allowed_severities = [
                s for s, level in severity_order.items() 
                if level <= severity_level
            ]
            query['severity'] = {"$in": allowed_severities}
        
        # Time range filter
        time_range = query_params.get('time_range', 'any')
        cutoff = get_time_cutoff(time_range)
        if cutoff:
            # MongoDB can compare ISO strings directly, but we'll use string format for consistency
            cutoff_str = cutoff.isoformat()
            query['timestamp_start'] = {"$gte": cutoff_str}
        
        print(f"Query params: {query_params}")
        print(f"MongoDB query: {query}")
        
        # Execute query
        results = list(
            event_collection.find(query, {"_id": 0})
            .sort("timestamp_start", -1)
            .limit(100)  # Limit to prevent huge responses
        )
        
        print(f"Found {len(results)} events")
        return results
        
    except Exception as e:
        print(f"Error querying events: {e}")
        return []


def save_processed_messages(preprocessed_message):
    try:
        result = processed_messages_collection.insert_many(preprocessed_message)
        return result
    except Exception as e:
        raise e


def save_event(analysed_events):
    """
    Save events to database and return the saved events with their IDs.
    
    Args:
        analysed_events (dict): Dictionary with 'events' list
    
    Returns:
        dict: Dictionary with 'result' (InsertManyResult) and 'events' (with _id added)
    """
    try:
        result = event_collection.insert_many(analysed_events['events'])
        
        # Add _id to events for notification creation
        for i, event in enumerate(analysed_events['events']):
            event['_id'] = str(result.inserted_ids[i])
        
        return {
            'result': result,
            'events': analysed_events['events']
        }
    except Exception as e:
        raise e


def query_events_by_location(location):
    """
    Legacy function for backward compatibility.
    Queries events by location (last 24h).
    """
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    return list(
        event_collection.find(
            {
                "location": {
                    "$regex": location,
                    "$options": "i"   # case-insensitive
                },
            },
            {"_id": 0}
        ).sort("timestamp_start", -1)
    )


def query_events(mode="limit", limit=10):
    """
    Query events with different modes.
    
    Args:
        mode: "latest", "limit", or "last_24h"
        limit: Maximum number of events to return (for "limit" mode)
    
    Returns:
        Event(s) matching the query
    """
    if mode == "latest":
        return event_collection.find_one(
            {}, {"_id": 0},
            sort=[("timestamp_start", -1)]
        )
    
    if mode == "limit":
        return list(
            event_collection.find(
                {}, {"_id": 0}
            )
            .sort("timestamp_start", -1)
            .limit(limit)
        )

    if mode == "last_24h":
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        cutoff_str = cutoff.isoformat()
        print(cutoff_str)
        return list(
            event_collection.find({
                "timestamp_start": {"$gte": cutoff_str}
            },
            {"_id": 0}).sort("timestamp_start", -1)
        )

    return []


# ============================================================================
# USER AUTHENTICATION FUNCTIONS
# ============================================================================

def create_user(username, email, password_hash):
    """
    Create a new user in the database.
    
    Args:
        username (str): Username
        email (str): Email address
        password_hash (str): Hashed password
    
    Returns:
        dict: Created user document (without password) or None if user exists
    """
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({
            "$or": [
                {"username": username},
                {"email": email}
            ]
        })
        
        if existing_user:
            return None  # User already exists
        
        # Create new user
        user = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "is_active": True
        }
        
        result = users_collection.insert_one(user)
        user['_id'] = str(result.inserted_id)
        # Remove password hash from return
        user.pop('password_hash', None)
        return user
        
    except Exception as e:
        print(f"Error creating user: {e}")
        raise e


def get_user_by_username(username):
    """
    Get user by username.
    
    Args:
        username (str): Username
    
    Returns:
        dict: User document or None
    """
    try:
        user = users_collection.find_one({"username": username})
        if user:
            user['_id'] = str(user['_id'])
        return user
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None


def get_user_by_email(email):
    """
    Get user by email.
    
    Args:
        email (str): Email address
    
    Returns:
        dict: User document or None
    """
    try:
        user = users_collection.find_one({"email": email})
        if user:
            user['_id'] = str(user['_id'])
        return user
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None


def get_user_by_id(user_id):
    """
    Get user by ID.
    
    Args:
        user_id (str): User ID
    
    Returns:
        dict: User document (without password) or None
    """
    try:
        from bson import ObjectId
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user['_id'] = str(user['_id'])
            user.pop('password_hash', None)  # Remove password hash
        return user
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None


def save_session(user_id, token, expires_at):
    """
    Save a user session (token) in the database.
    
    Args:
        user_id (str): User ID
        token (str): JWT token
        expires_at (str): Expiration timestamp (ISO format)
    
    Returns:
        bool: True if successful
    """
    try:
        session = {
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "created_at": datetime.now(UTC).isoformat(),
            "is_active": True
        }
        sessions_collection.insert_one(session)
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False


def get_session(token):
    """
    Get session by token.
    
    Args:
        token (str): JWT token
    
    Returns:
        dict: Session document or None
    """
    try:
        session = sessions_collection.find_one({
            "token": token,
            "is_active": True
        })
        if session:
            # Check if session is expired
            expires_at = datetime.fromisoformat(session['expires_at'].replace('Z', '+00:00'))
            if datetime.now(UTC) > expires_at:
                # Deactivate expired session
                sessions_collection.update_one(
                    {"token": token},
                    {"$set": {"is_active": False}}
                )
                return None
            session['_id'] = str(session['_id'])
        return session
    except Exception as e:
        print(f"Error getting session: {e}")
        return None


def deactivate_session(token):
    """
    Deactivate a session (logout).
    
    Args:
        token (str): JWT token
    
    Returns:
        bool: True if successful
    """
    try:
        result = sessions_collection.update_one(
            {"token": token},
            {"$set": {"is_active": False, "logged_out_at": datetime.now(UTC).isoformat()}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error deactivating session: {e}")
        return False


# ============================================================================
# NOTIFICATION FUNCTIONS (SIMPLIFIED)
# ============================================================================

def create_notification(user_id, event):
    """
    Create a notification for a user from an event.
    
    Args:
        user_id (str): User ID
        event (dict): Event document
    
    Returns:
        dict: Created notification document
    """
    try:
        event_type = event.get('event_type', 'event')
        location = event.get('location', 'Unknown')
        severity = event.get('severity', 'unknown')
        summary = event.get('summary', 'New event')
        
        notification = {
            "user_id": user_id,
            "event_id": str(event.get('_id', '')),
            "title": f"{event_type.title()} in {location}",
            "message": summary,
            "location": location,
            "event_type": event_type,
            "severity": severity,
            "is_read": False,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        result = notifications_collection.insert_one(notification)
        notification['_id'] = str(result.inserted_id)
        return notification
        
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None


def get_user_notifications(user_id, limit=50, unread_only=False):
    """
    Get notifications for a user.
    
    Args:
        user_id (str): User ID
        limit (int): Maximum number of notifications to return
        unread_only (bool): If True, only return unread notifications
    
    Returns:
        list: List of notification documents
    """
    try:
        query = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        
        notifications = list(
            notifications_collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
        
        return notifications
        
    except Exception as e:
        print(f"Error getting user notifications: {e}")
        return []


def mark_notification_read(notification_id, user_id):
    """
    Mark a notification as read.
    
    Args:
        notification_id (str): Notification ID
        user_id (str): User ID (for security)
    
    Returns:
        bool: True if successful
    """
    try:
        from bson import ObjectId
        
        result = notifications_collection.update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": user_id
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.now(UTC).isoformat()
                }
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error marking notification as read: {e}")
        return False


def mark_all_notifications_read(user_id):
    """
    Mark all notifications as read for a user.
    
    Args:
        user_id (str): User ID
    
    Returns:
        int: Number of notifications marked as read
    """
    try:
        result = notifications_collection.update_many(
            {
                "user_id": user_id,
                "is_read": False
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.now(UTC).isoformat()
                }
            }
        )
        
        return result.modified_count
        
    except Exception as e:
        print(f"Error marking all notifications as read: {e}")
        return 0


def delete_notification(notification_id, user_id):
    """
    Delete a notification.
    
    Args:
        notification_id (str): Notification ID
        user_id (str): User ID (for security)
    
    Returns:
        bool: True if successful
    """
    try:
        from bson import ObjectId
        
        result = notifications_collection.delete_one({
            "_id": ObjectId(notification_id),
            "user_id": user_id
        })
        
        return result.deleted_count > 0
        
    except Exception as e:
        print(f"Error deleting notification: {e}")
        return False


def get_unread_count(user_id):
    """
    Get count of unread notifications for a user.
    
    Args:
        user_id (str): User ID
    
    Returns:
        int: Number of unread notifications
    """
    try:
        count = notifications_collection.count_documents({
            "user_id": user_id,
            "is_read": False
        })
        return count
        
    except Exception as e:
        print(f"Error getting unread count: {e}")
        return 0




def get_all_active_users():
    """
    Get all active user IDs for notifications.
    Simple version - notify all active users.
    
    Returns:
        list: List of active user IDs
    """
    try:
        users = users_collection.find({"is_active": True}, {"_id": 1})
        return [str(user['_id']) for user in users]
    except Exception as e:
        print(f"Error getting active users: {e}")
        return []
