from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import Workout, WorkoutSet
from app.utils.auth_decorator import require_auth


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