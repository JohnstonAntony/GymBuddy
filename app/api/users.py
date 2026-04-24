from datetime import date, datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import UserProfile
from app.utils.auth_decorator import require_auth


users_blueprint = Blueprint("users", __name__, url_prefix="/api/users")


ALLOWED_GOALS = {"strength", "hypertrophy", "endurance", "general_fitness", "weight_loss", "calisthenics"} 
ALLOWED_LEVELS = {"beginner", "intermediate", "advanced", "expert"}


@users_blueprint.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Return the authenticated user's data, including profile details if set."""
    return jsonify({"user": g.current_user.to_dict(include_profile=True)}), 200


@users_blueprint.route("/me", methods=["PATCH"])
@require_auth
def update_current_user():
    """Update fields on the authenticated user's profile, only fields updated by user request are updated."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    user = g.current_user

    # makes sure the user has a profile to update, create one if it doesn't exist
    if not user.profile:
        user.profile = UserProfile(user_id=user.id)
        db.session.add(user.profile)

    profile = user.profile

    # Validation fields, applies if added.
    if "full_name" in data:
        if not isinstance(data["full_name"], str) or len(data["full_name"]) > 120:
            return jsonify({"error": "full name must be alphabetical, max 120 characters"}), 400
        profile.full_name = data["full_name"]

    if "date_of_birth" in data:
        try:
            dob = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return jsonify({"error": "date of birth must be in the format YYYY-MM-DD"}), 400
        if dob > date.today():
            return jsonify({"error": "date of birth cannot be in the future"}), 400
        profile.date_of_birth = dob

    if "weight_kg" in data:
        if not isinstance(data["weight_kg"], (int, float)) or data["weight_kg"] <= 0:
            return jsonify({"error": "weight in kg must be a positive number"}), 400
        profile.weight_kg = float(data["weight_kg"])

    if "height_cm" in data:
        if not isinstance(data["height_cm"], (int, float)) or data["height_cm"] <= 0:
            return jsonify({"error": "height in cm must be a positive number"}), 400
        profile.height_cm = float(data["height_cm"])

    if "fitness_goal" in data:
        if data["fitness_goal"] not in ALLOWED_GOALS:
            return jsonify({
                "error": f"fitness goal must be one of: {sorted(ALLOWED_GOALS)}"
            }), 400
        profile.fitness_goal = data["fitness_goal"]

    if "experience_level" in data:
        if data["experience_level"] not in ALLOWED_LEVELS:
            return jsonify({
                "error": f"experience level must be one of: {sorted(ALLOWED_LEVELS)}"
            }), 400
        profile.experience_level = data["experience_level"]

    db.session.commit()

    return jsonify({"user": user.to_dict(include_profile=True)}), 200