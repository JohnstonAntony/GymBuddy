from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import Exercise


exercises_blueprint = Blueprint("exercises", __name__, url_prefix="/api/exercises")


ALLOWED_CATEGORIES = {"push", "pull", "legs", "cardio", "core"}


@exercises_blueprint.route("", methods=["GET"])
def list_exercises():
    """list of exercises, with optional filtering by category and muscle group. Results are sorted alphabetically by name"""
    query = Exercise.query

    category = request.args.get("category")
    if category:
        if category not in ALLOWED_CATEGORIES:
            return jsonify({
                "error": f"category must be one of: {sorted(ALLOWED_CATEGORIES)}"
            }), 400
        query = query.filter_by(category=category)

    muscle = request.args.get("muscle")
    if muscle:
        # muscle group is filtered using comma separated string LIKE query searches handles the search 
        query = query.filter(Exercise.muscle_groups.contains(muscle))

    exercises = query.order_by(Exercise.name).all()

    return jsonify({
        "count": len(exercises),
        "exercises": [e.to_dict() for e in exercises],
    }), 200


@exercises_blueprint.route("/<int:exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    """returns details of a single exercise by ID. 404 if not found."""
    exercise = db.session.get(Exercise, exercise_id)
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    return jsonify({"exercise": exercise.to_dict()}), 200