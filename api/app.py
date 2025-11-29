import json
from flask import Flask, abort, request
from flask_cors import CORS
from .services import *
from .db.models import *
from .auth import sign_up, sign_in, logout, get_current_user

app = Flask(__name__)
CORS(app, origins=["*"])

POST = 'POST'
GET = 'GET'

@app.route('/')
def home():
    return "<h1>Welcome To Patrol-X</h1>"


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/auth/signup', methods=['POST'])
def signup():
    """Sign up a new user."""
    if request.method != POST:
        abort(404, description="Expected POST request")
    
    if not request.is_json:
        abort(400, description="Expected JSON body")
    
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        response, status_code = sign_up(username, email, password)
        return response, status_code
        
    except Exception as e:
        print(f"Signup error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


@app.route('/auth/signin', methods=['POST'])
def signin():
    """Sign in an existing user."""
    if request.method != POST:
        abort(404, description="Expected POST request")
    
    if not request.is_json:
        abort(400, description="Expected JSON body")
    
    try:
        data = request.get_json()
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        response, status_code = sign_in(username_or_email, password)
        return response, status_code
        
    except Exception as e:
        print(f"Signin error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


@app.route('/auth/logout', methods=['POST'])
def logout_endpoint():
    """Logout a user."""
    if request.method != POST:
        abort(404, description="Expected POST request")
    
    try:
        # Get token from Authorization header or request body
        token = None
        
        # Try Authorization header first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Fallback to request body
        if not token and request.is_json:
            data = request.get_json()
            token = data.get('token')
        
        if not token:
            return {
                "status": "error",
                "message": "Token is required"
            }, 400
        
        response, status_code = logout(token)
        return response, status_code
        
    except Exception as e:
        print(f"Logout error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


@app.route('/auth/me', methods=['GET'])
def get_me():
    """Get current user information."""
    if request.method != GET:
        abort(404, description="Expected GET request")
    
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {
                "status": "error",
                "message": "Authorization token required"
            }, 401
        
        token = auth_header.split(' ')[1]
        user = get_current_user(token)
        
        if not user:
            return {
                "status": "error",
                "message": "Invalid or expired token"
            }, 401
        
        return {
            "status": "ok",
            "user": {
                "id": user['_id'],
                "username": user['username'],
                "email": user['email'],
                "created_at": user.get('created_at'),
                "is_active": user.get('is_active', True)
            }
        }, 200
        
    except Exception as e:
        print(f"Get me error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


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

        
        preprocessed_messages = preprocess_msg(raw_messages)
        analysed_events = analyse_msg(preprocessed_messages)
        save_result = save_event(analysed_events)

        if save_result and save_result.get('result'):
            # Create notifications for all active users
            from .db.models import get_all_active_users, create_notification
            
            saved_events = save_result.get('events', [])
            active_users = get_all_active_users()
            
            for event in saved_events:
                # Only notify for critical or high severity events
                if event.get('severity') in ['critical', 'high']:
                    for user_id in active_users:
                        create_notification(user_id, event)
            
            return {"status": "ok", "Message": "Event save successfully"}, 200
        else:
            abort(500, description="Event not saved")

    except Exception as e:
        print("Error:", e)
        abort(500, description=str(e))


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

def get_authenticated_user():
    """Helper to get authenticated user from token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, {"status": "error", "message": "Authorization token required"}, 401
    
    token = auth_header.split(' ')[1]
    user = get_current_user(token)
    
    if not user:
        return None, {"status": "error", "message": "Invalid or expired token"}, 401
    
    return user, None, None


@app.route('/notifications', methods=['GET'])
def get_notifications():
    """Get notifications for the current user."""
    if request.method != GET:
        abort(404, description="Expected GET request")
    
    try:
        user, error, status = get_authenticated_user()
        if error:
            return error, status
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        
        notifications = get_user_notifications(user['_id'], limit=limit, unread_only=unread_only)
        unread_count = get_unread_count(user['_id'])
        
        return {
            "status": "ok",
            "notifications": notifications,
            "unread_count": unread_count
        }, 200
        
    except Exception as e:
        print(f"Get notifications error: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route('/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read_endpoint(notification_id):
    """Mark a notification as read."""
    if request.method != POST:
        abort(404, description="Expected POST request")
    
    try:
        user, error, status = get_authenticated_user()
        if error:
            return error, status
        
        success = mark_notification_read(notification_id, user['_id'])
        
        if success:
            return {"status": "ok", "message": "Notification marked as read"}, 200
        else:
            return {"status": "error", "message": "Notification not found"}, 404
        
    except Exception as e:
        print(f"Mark notification read error: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route('/notifications/read-all', methods=['POST'])
def mark_all_notifications_read_endpoint():
    """Mark all notifications as read."""
    if request.method != POST:
        abort(404, description="Expected POST request")
    
    try:
        user, error, status = get_authenticated_user()
        if error:
            return error, status
        
        count = mark_all_notifications_read(user['_id'])
        return {"status": "ok", "message": f"Marked {count} notifications as read"}, 200
        
    except Exception as e:
        print(f"Mark all notifications read error: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route('/notifications/<notification_id>', methods=['DELETE'])
def delete_notification_endpoint(notification_id):
    """Delete a notification."""
    if request.method != 'DELETE':
        abort(404, description="Expected DELETE request")
    
    try:
        user, error, status = get_authenticated_user()
        if error:
            return error, status
        
        success = delete_notification(notification_id, user['_id'])
        
        if success:
            return {"status": "ok", "message": "Notification deleted"}, 200
        else:
            return {"status": "error", "message": "Notification not found"}, 404
        
    except Exception as e:
        print(f"Delete notification error: {e}")
        return {"status": "error", "message": str(e)}, 500



        
