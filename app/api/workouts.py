from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import Workout, WorkoutSet, Exercise
from app.utils.auth_decorator import require_auth
from app.utils.ownership import get_workout_or_404


workouts_blueprint = Blueprint("workouts", __name__, url_prefix="/api/workouts")


@workouts_blueprint.route("", methods=["GET"])
@require_auth
def list_workouts():
    """lists workouts belonging to the current user, with optional filters and pagination. parameters: from (yyyy-mm-dd), to (yyyy-mm-dd), exercise_id, page, per_page."""
    query = Workout.query.filter_by(user_id=g.current_user.id)

    #optional date-range filter
    date_from = request.args.get("from")
    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "from must be YYYY-MM-DD"}), 400
        query = query.filter(Workout.started_at >= d)

    date_to = request.args.get("to")
    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "to must be YYYY-MM-DD"}), 400
        #added one day to include the entire end date (up to 23:59:59)
        query = query.filter(Workout.started_at < d.replace(hour=23, minute=59, second=59))

    #optional exercise_id filter (workouts that include this exercise)
    exercise_id = request.args.get("exercise_id", type=int)
    if exercise_id:
        query = query.join(WorkoutSet).filter(
            WorkoutSet.exercise_id == exercise_id
        ).distinct()

    #default sorting is newest to oldest
    query = query.order_by(Workout.started_at.desc())

    #pagination
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "workouts": [w.to_dict(include_sets=False) for w in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "total_pages": pagination.pages,
    }), 200


@workouts_blueprint.route("", methods=["POST"])
@require_auth
def create_workout():
    """creates a new workout for the current user. Returns the created workout."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    name = data.get("name")
    if not name or not isinstance(name, str):
        return jsonify({"error": "name is required"}), 400

    workout = Workout(
        user_id=g.current_user.id,
        name=name,
        notes=data.get("notes"),
    )
    db.session.add(workout)
    db.session.commit()

    return jsonify({"workout": workout.to_dict()}), 201


@workouts_blueprint.route("/<int:workout_id>", methods=["GET"])
@require_auth
def get_workout(workout_id):
    """retrieves details of a single workout by ID, including its sets and exercises. 404 if not found or doesn't belong to user."""
    workout, error = get_workout_or_404(workout_id)
    if error:
        return error
    return jsonify({"workout": workout.to_dict(include_sets=True)}), 200


@workouts_blueprint.route("/<int:workout_id>", methods=["PATCH"])
@require_auth
def update_workout(workout_id):
    """updates a workout's name, notes, or completed_at timestamp using patch."""
    workout, error = get_workout_or_404(workout_id)
    if error:
        return error

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"]:
            return jsonify({"error": "name must be a non-empty string"}), 400
        workout.name = data["name"]

    if "notes" in data:
        workout.notes = data["notes"]  #nullable, any string

    if "completed_at" in data:
        try:
            workout.completed_at = datetime.fromisoformat(data["completed_at"])
        except (ValueError, TypeError):
            return jsonify({"error": "completed_at must be an ISO datetime"}), 400

    db.session.commit()
    return jsonify({"workout": workout.to_dict(include_sets=True)}), 200


@workouts_blueprint.route("/<int:workout_id>", methods=["DELETE"])
@require_auth
def delete_workout(workout_id):
    """deletes a workout and its sets, cascades parent-child."""
    workout, error = get_workout_or_404(workout_id)
    if error:
        return error

    db.session.delete(workout)
    db.session.commit()
    return "", 204


@workouts_blueprint.route("/<int:workout_id>/sets", methods=["POST"])
@require_auth
def add_set_to_workout(workout_id):
    """adds a set to workout."""
    workout, error = get_workout_or_404(workout_id)
    if error:
        return error

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Required fields
    exercise_id = data.get("exercise_id")
    reps = data.get("reps")
    weight_kg = data.get("weight_kg")

    if not isinstance(exercise_id, int):
        return jsonify({"error": "exercise_id must be an integer"}), 400
    if not isinstance(reps, int) or reps <= 0:
        return jsonify({"error": "reps must be a positive integer"}), 400
    if not isinstance(weight_kg, (int, float)) or weight_kg < 0:
        return jsonify({"error": "weight_kg must be a non-negative number"}), 400

    # verifies if the exercise exists
    if not db.session.get(Exercise, exercise_id):
        return jsonify({"error": "exercise_id does not match a known exercise"}), 400

    # optional RPE
    rpe = data.get("rpe")
    if rpe is not None and (not isinstance(rpe, (int, float)) or rpe < 1 or rpe > 10):
        return jsonify({"error": "rpe must be a number between 1 and 10"}), 400

    #determines the next set_number for this workout
    next_number = (
        db.session.query(db.func.coalesce(db.func.max(WorkoutSet.set_number), 0))
        .filter_by(workout_id=workout.id)
        .scalar()
    ) + 1

    workout_set = WorkoutSet(
        workout_id=workout.id,
        exercise_id=exercise_id,
        set_number=next_number,
        reps=reps,
        weight_kg=float(weight_kg),
        rpe=float(rpe) if rpe is not None else None,
    )
    db.session.add(workout_set)
    db.session.commit()

    return jsonify({"set": workout_set.to_dict()}), 201