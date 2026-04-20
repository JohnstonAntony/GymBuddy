from datetime import datetime, timedelta, timezone
import jwt
from flask import current_app #built in flask object that imports the current app config without the app itself.


def generate_token(user_id): #Generate a JWT for the given user_id signed with JWT_SECRET_KEY
   
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256", #HS256 is a simple signing algorthim that uses a shared key.
    )


def decode_token(token): #Decode and validate a JWT. Returns the payload dict or raises jwt Error.

    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=["HS256"], 
    )