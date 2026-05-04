from flask import Blueprint, request, jsonify
from app.extensions import db
from app.utils.auth_decorator import require_auth
from app.utils.ownership import get_set_or_404


sets_blueprint = Blueprint("sets", __name__, url_prefix="/api/sets")


@sets_blueprint.route("/<int:set_id>", methods=["PATCH"])
@require_auth
def update_set(set_id):
    """Updates a set's reps, weight_kg, or rpe using patch."""
    workout_set, error = get_set_or_404(set_id)
    if error:
        return error

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    if "reps" in data:
        if not isinstance(data["reps"], int) or data["reps"] <= 0:
            return jsonify({"error": "reps must be a positive integer"}), 400
        workout_set.reps = data["reps"]

    if "weight_kg" in data:
        if not isinstance(data["weight_kg"], (int, float)) or data["weight_kg"] < 0:
            return jsonify({"error": "weight_kg must be a non-negative number"}), 400
        workout_set.weight_kg = float(data["weight_kg"])

    if "rpe" in data:
        rpe = data["rpe"]
        if rpe is not None and (not isinstance(rpe, (int, float)) or rpe < 1 or rpe > 10):
            return jsonify({"error": "rpe must be a number between 1 and 10"}), 400
        workout_set.rpe = float(rpe) if rpe is not None else None

    db.session.commit()
    return jsonify({"set": workout_set.to_dict()}), 200


@sets_blueprint.route("/<int:set_id>", methods=["DELETE"])
@require_auth
def delete_set(set_id):
    """single set delete"""
    workout_set, error = get_set_or_404(set_id)
    if error:
        return error

    db.session.delete(workout_set)
    db.session.commit()
    return "", 204