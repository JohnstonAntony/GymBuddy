from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import Workout, WorkoutSet
from app.utils.auth_decorator import require_auth
from app.models import Workout, WorkoutSet, Exercise
from datetime import datetime, date, timedelta


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

@stats_blueprint.route("/frequency", methods=["GET"])
@require_auth
def get_frequency():
    """Gets the number of workouts per day for the user, with optional date range filtering with limits. Returns zero for days with no workouts."""

    MAX_RANGE_DAYS = 730
    DEFAULT_RANGE_DAYS = 365

    user_id = g.current_user.id

    # date range parsing and validation, falls back to defaults if not provided
    date_to_arg = request.args.get("to")
    if date_to_arg:
        date_to_dt, error = _parse_date(date_to_arg, "to")
        if error:
            return jsonify({"error": error}), 400
        date_to = date_to_dt.date()
    else:
        date_to = date.today()

    date_from_arg = request.args.get("from")
    if date_from_arg:
        date_from_dt, error = _parse_date(date_from_arg, "from")
        if error:
            return jsonify({"error": error}), 400
        date_from = date_from_dt.date()
    else:
        date_from = date_to - timedelta(days=DEFAULT_RANGE_DAYS)

    if date_from > date_to:
        return jsonify({"error": "from must not be after to"}), 400

    range_days = (date_to - date_from).days
    if range_days > MAX_RANGE_DAYS:
        return jsonify({
            "error": f"date range cannot exceed {MAX_RANGE_DAYS} days"
        }), 400

    # query to count workouts per day in the range, returns only days with workouts
    date_expr = db.func.date(Workout.started_at).label("date")
    count_expr = db.func.count(Workout.id).label("count")

    rows = (
        db.session.query(date_expr, count_expr)
        .filter(Workout.user_id == user_id)
        .filter(Workout.started_at >= datetime.combine(date_from, datetime.min.time()))
        .filter(Workout.started_at < datetime.combine(
            date_to + timedelta(days=1), datetime.min.time()
        ))
        .group_by(date_expr)
        .all()
    )

    
    counts_by_date = {str(row.date): row.count for row in rows}

    # fill every day in the range, zero for empty days
    frequency = []
    current = date_from
    while current <= date_to:
        iso = current.isoformat()
        frequency.append({"date": iso, "count": counts_by_date.get(iso, 0)})
        current += timedelta(days=1)

    return jsonify({
        "frequency": frequency,
        "total_workouts": sum(item["count"] for item in frequency),
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
    }), 200