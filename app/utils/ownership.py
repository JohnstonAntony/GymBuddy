from flask import jsonify, g
from app.extensions import db
from app.models import Workout, WorkoutSet


def get_workout_or_404(workout_id):
    """looks up a workout by ID, ensuring it belongs to the current user. 404 if not found or doesn't belong to user."""
    workout = db.session.get(Workout, workout_id)
    if not workout or workout.user_id != g.current_user.id:
        return None, (jsonify({"error": "Workout not found"}), 404)
    return workout, None


def get_set_or_404(set_id):
    """looks up a workout set by ID, ensuring it belongs to the current user through its workout. 404 if not found or doesn't belong to user."""
    workout_set = db.session.get(WorkoutSet, set_id)
    if not workout_set or workout_set.workout.user_id != g.current_user.id:
        return None, (jsonify({"error": "Set not found"}), 404)
    return workout_set, None