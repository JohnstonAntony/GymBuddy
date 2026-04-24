from functools import wraps
import jwt
from flask import request, jsonify, g
from app.models import User
from app.utils.jwt_helper import decode_token
from app.extensions import db


def require_auth(func):#Decorator to protect routes that need authentication, checks for JWT token and attaches the user to flask.g if valid.
    @wraps(func)
    def wrapper(*args, **kwargs): 
        """Decorator that protects a route by requiring a valid JWT in the
         Auth header. Attaches the user to flask.g after validation."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401

        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer": #format checker
            return jsonify({"error": "Invalid authorization header format"}), 401
        token = parts[1]

        
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        
        user_id = payload.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if not user:
            return jsonify({"error": "User no longer exists"}), 401 #final catch incase user was deleted after token was issued.

        
        g.current_user = user

       
        return func(*args, **kwargs)

    return wrapper