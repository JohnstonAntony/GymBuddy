from flask import Blueprint, request, jsonify, g # Tripped up here didn't import g from flask.
from app.extensions import db
from app.models import User
from app.utils.jwt_helper import generate_token
from app.utils.auth_decorator import require_auth


auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_blueprint.route("/register", methods=["POST"])
def register():
    """register a new user account.
    ---
    tags:
      - Auth
    responses:
      '201':
        description: User created
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                user:
                  type: object
      '400':
        description: Invalid input (e.g. missing fields, short password)
      '409':
        description: Email or username already in use"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    #basic validation - might add more checks later - password strength, email format, email and password double entry 
    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # uniqueness validation
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken, please use a different username"}), 409

    #create user
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({ #Return the created user data and a success message
        "message": "User account created successfully",
        "user": user.to_dict(),
    }), 201




@auth_blueprint.route("/login", methods=["POST"]) #Login route to authenticate users and return a JWT token
def login():
    """authenticate user and return a JWT token.
    ---
    tags:
    - Auth
    responses:
    '200':
        description: Authenticated, JWT returned
        content:
        application/json:
            schema:
            type: object
            properties:
                token:
                type: string
                user:
                type: object
    '401':
        description: Invalid credentials"""
   
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password): #If the user doesn't exist or the password is incorrect, return an error message left deliberately vague.
        return jsonify({"error": "Invalid credentials"}), 401 

    token = generate_token(user.id)

    return jsonify({
        "token": token,
        "user": user.to_dict(),
    }), 200

@auth_blueprint.route("/me", methods=["GET"])
@require_auth
def get_me():
    """return the currently authenticated user's info.
    ---
    tags:
    - Auth
    security:
    - BearerAuth: []
    responses:
    '200':
        description: Current user
    '401':
        description: Missing or invalid token"""
    
    return jsonify({"user": g.current_user.to_dict()}), 200 