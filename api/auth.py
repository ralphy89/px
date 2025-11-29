import os
import jwt
import bcrypt
from datetime import datetime, UTC, timedelta
from flask import jsonify
from .db.models import create_user, get_user_by_username, get_user_by_email, save_session, get_session, deactivate_session, get_user_by_id

# JWT Secret Key - MUST be set as environment variable in production
JWT_SECRET = os.environ.get("JWT_SECRET")

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


def hash_password(password):
    """
    Hash a password using bcrypt.
    
    Args:
        password (str): Plain text password
    
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password, password_hash):
    """
    Verify a password against its hash.
    
    Args:
        password (str): Plain text password
        password_hash (str): Hashed password
    
    Returns:
        bool: True if password matches
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def generate_token(user_id, username):
    """
    Generate a JWT token for a user.
    
    Args:
        user_id (str): User ID
        username (str): Username
    
    Returns:
        str: JWT token
    """
    expires_at = datetime.now(UTC) + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expires_at,
        "iat": datetime.now(UTC)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at.isoformat()


def verify_token(token):
    """
    Verify and decode a JWT token.
    
    Args:
        token (str): JWT token
    
    Returns:
        dict: Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None


def sign_up(username, email, password):
    """
    Sign up a new user.
    
    Args:
        username (str): Username
        email (str): Email address
        password (str): Plain text password
    
    Returns:
        dict: Response with status and user data or error message
    """
    try:
        # Validate input
        if not username or not email or not password:
            return {
                "status": "error",
                "message": "Username, email, and password are required"
            }, 400
        
        if len(password) < 6:
            return {
                "status": "error",
                "message": "Password must be at least 6 characters long"
            }, 400
        
        # Check if user already exists
        if get_user_by_username(username):
            return {
                "status": "error",
                "message": "Username already exists"
            }, 400
        
        if get_user_by_email(email):
            return {
                "status": "error",
                "message": "Email already exists"
            }, 400
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user = create_user(username, email, password_hash)
        
        if not user:
            return {
                "status": "error",
                "message": "Failed to create user"
            }, 500
        
        # Generate token
        token, expires_at = generate_token(user['_id'], username)
        
        # Save session
        save_session(user['_id'], token, expires_at)
        
        return {
            "status": "ok",
            "message": "User created successfully",
            "user": {
                "id": user['_id'],
                "username": user['username'],
                "email": user['email'],
                "created_at": user['created_at']
            },
            "token": token,
            "expires_at": expires_at
        }, 201
        
    except Exception as e:
        print(f"Error in sign_up: {e}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }, 500


def sign_in(username_or_email, password):
    """
    Sign in a user.
    
    Args:
        username_or_email (str): Username or email
        password (str): Plain text password
    
    Returns:
        dict: Response with status and user data or error message
    """
    try:
        # Validate input
        if not username_or_email or not password:
            return {
                "status": "error",
                "message": "Username/email and password are required"
            }, 400
        
        # Get user by username or email
        user = get_user_by_username(username_or_email)
        if not user:
            user = get_user_by_email(username_or_email)
        
        if not user:
            return {
                "status": "error",
                "message": "Invalid username/email or password"
            }, 401
        
        # Check if user is active
        if not user.get('is_active', True):
            return {
                "status": "error",
                "message": "Account is deactivated"
            }, 403
        
        # Verify password
        if not verify_password(password, user.get('password_hash', '')):
            return {
                "status": "error",
                "message": "Invalid username/email or password"
            }, 401
        
        # Generate token
        token, expires_at = generate_token(user['_id'], user['username'])
        
        # Save session
        save_session(user['_id'], token, expires_at)
        
        return {
            "status": "ok",
            "message": "Sign in successful",
            "user": {
                "id": user['_id'],
                "username": user['username'],
                "email": user['email']
            },
            "token": token,
            "expires_at": expires_at
        }, 200
        
    except Exception as e:
        print(f"Error in sign_in: {e}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }, 500


def logout(token):
    """
    Logout a user by deactivating their session.
    
    Args:
        token (str): JWT token
    
    Returns:
        dict: Response with status
    """
    try:
        if not token:
            return {
                "status": "error",
                "message": "Token is required"
            }, 400
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return {
                "status": "error",
                "message": "Invalid or expired token"
            }, 401
        
        # Deactivate session
        success = deactivate_session(token)
        
        if success:
            return {
                "status": "ok",
                "message": "Logged out successfully"
            }, 200
        else:
            return {
                "status": "error",
                "message": "Failed to logout"
            }, 500
        
    except Exception as e:
        print(f"Error in logout: {e}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }, 500


def get_current_user(token):
    """
    Get current user from token.
    
    Args:
        token (str): JWT token
    
    Returns:
        dict: User data or None
    """
    try:
        if not token:
            return None
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return None
        
        # Check session in database
        session = get_session(token)
        if not session:
            return None
        
        # Get user
        user = get_user_by_id(payload['user_id'])
        return user
        
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        return None

