from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import Workout, WorkoutSet
from app.utils.auth_decorator import require_auth
from app.models import Workout, WorkoutSet, Exercise


stats_blueprint = Blueprint("stats", __name__, url_prefix="/api/stats")


def _parse_date(value, field_name):
    """validator to parse a date string in YYYY-MM-DD format. Returns (datetime, error_message)."""
    if value is None:
        return None, None
    try:
        return datetime.strptime(value, "%Y-%m-%d"), None
    except (ValueError, TypeError):
        return None, f"{field_name} must be YYYY-MM-DD"


@stats_blueprint.route("/volume", methods=["GET"])
@require_auth
def get_volume():
    """endpoint to get total workout volume per day for the authenticated user, with optional date range filtering."""

    # parse and validate date parameters
    date_from, error = _parse_date(request.args.get("from"), "from")
    if error:
        return jsonify({"error": error}), 400

    date_to, error = _parse_date(request.args.get("to"), "to")
    if error:
        return jsonify({"error": error}), 400

    # build query to calculate total volume (reps * weight) per day (aggregation)
    date_expr = db.func.date(Workout.started_at).label("date")
    volume_expr = db.func.sum(WorkoutSet.reps * WorkoutSet.weight_kg).label("volume")

    query = (
        db.session.query(date_expr, volume_expr)
        .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
        .filter(Workout.user_id == g.current_user.id)
    )

    if date_from:
        query = query.filter(Workout.started_at >= date_from)
    if date_to:
        # anything before 23:59:59 of that day
        query = query.filter(
            Workout.started_at < date_to.replace(hour=23, minute=59, second=59)
        )

    query = query.group_by(date_expr).order_by(date_expr)
    results = query.all()

    data_points = [
        {"date": str(row.date), "volume": float(row.volume or 0)}
        for row in results
    ]
    total_volume = sum(p["volume"] for p in data_points)

    return jsonify({
        "data_points": data_points,
        "total_volume": total_volume,
        "from": date_from.date().isoformat() if date_from else None,
        "to": date_to.date().isoformat() if date_to else None,
    }), 200

@stats_blueprint.route("/prs", methods=["GET"])
@require_auth
def get_personal_records():
    """gets the heaviest set for each exercise for the authenticated user. If there are ties, returns the most recent one."""

    user_id = g.current_user.id

    # subquery: max weight per exercise for this user
    max_weights_subq = (
        db.session.query(
            WorkoutSet.exercise_id.label("exercise_id"),
            db.func.max(WorkoutSet.weight_kg).label("max_weight"),
        )
        .join(Workout, WorkoutSet.workout_id == Workout.id)
        .filter(Workout.user_id == user_id)
        .group_by(WorkoutSet.exercise_id)
        .subquery()
    )

    # outer query: find the actual sets matching those max weights
    rows = (
        db.session.query(WorkoutSet, Workout, Exercise)
        .join(Workout, WorkoutSet.workout_id == Workout.id)
        .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
        .join(
            max_weights_subq,
            db.and_(
                WorkoutSet.exercise_id == max_weights_subq.c.exercise_id,
                WorkoutSet.weight_kg == max_weights_subq.c.max_weight,
            ),
        )
        .filter(Workout.user_id == user_id)
        .order_by(Workout.started_at.desc())
        .all()
    )

    # if there are multiple keep the most recent one
    seen_exercises = set()
    prs = []
    for workout_set, workout, exercise in rows:
        if exercise.id in seen_exercises:
            continue
        seen_exercises.add(exercise.id)
        prs.append({
            "exercise_id": exercise.id,
            "exercise_name": exercise.name,
            "exercise_category": exercise.category,
            "weight_kg": workout_set.weight_kg,
            "reps": workout_set.reps,
            "set_id": workout_set.id,
            "workout_id": workout.id,
            "achieved_on": workout.started_at.isoformat() if workout.started_at else None,
        })

    # sort by exercise name for consistent ordering
    prs.sort(key=lambda p: p["exercise_name"])

    return jsonify({
        "personal_records": prs,
        "count": len(prs),
    }), 200