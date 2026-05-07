from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import WorkoutTemplate, Workout, WorkoutSet
from app.utils.auth_decorator import require_auth
from app.utils.template_validation import validate_template_exercises


templates_blueprint = Blueprint("templates", __name__, url_prefix="/api/templates")


def _get_template_or_404(template_id):
    """looks up a template by ID and verifies it belongs to the current user."""
    template = db.session.get(WorkoutTemplate, template_id)
    if not template or template.user_id != g.current_user.id:
        return None, (jsonify({"error": "Template not found"}), 404)
    return template, None


@templates_blueprint.route("", methods=["GET"])
@require_auth
def list_templates():
    """list all of the current user's templates."""
    templates = (
        WorkoutTemplate.query
        .filter_by(user_id=g.current_user.id)
        .order_by(WorkoutTemplate.created_at.desc())
        .all()
    )
    return jsonify({
        "templates": [t.to_dict() for t in templates],
    }), 200


@templates_blueprint.route("", methods=["POST"])
@require_auth
def create_template():
    """a new template creator"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    name = data.get("name")
    if not isinstance(name, str) or not name:
        return jsonify({"error": "name is required"}), 400

    exercises = data.get("exercises", [])
    validated, error = validate_template_exercises(exercises)
    if error:
        return jsonify({"error": error}), 400

    template = WorkoutTemplate(
        user_id=g.current_user.id,
        name=name,
        exercises=validated,
    )
    db.session.add(template)
    db.session.commit()

    return jsonify({"template": template.to_dict()}), 201


@templates_blueprint.route("/<int:template_id>", methods=["GET"])
@require_auth
def get_template(template_id):
    """get details about a specific template with exercises."""
    template, error = _get_template_or_404(template_id)
    if error:
        return error
    return jsonify({"template": template.to_dict()}), 200


@templates_blueprint.route("/<int:template_id>", methods=["PATCH"])
@require_auth
def update_template(template_id):
    """update the name or exercises of a template. PATCH"""
    template, error = _get_template_or_404(template_id)
    if error:
        return error

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"]:
            return jsonify({"error": "name must be a non-empty string"}), 400
        template.name = data["name"]

    if "exercises" in data:
        validated, validation_error = validate_template_exercises(data["exercises"])
        if validation_error:
            return jsonify({"error": validation_error}), 400
        template.exercises = validated

    db.session.commit()
    return jsonify({"template": template.to_dict()}), 200

@templates_blueprint.route("/<int:template_id>", methods=["DELETE"])
@require_auth
def delete_template(template_id):
    """deletes a template, existing workouts based on the template are not affected."""
    template, error = _get_template_or_404(template_id)
    if error:
        return error
    db.session.delete(template)
    db.session.commit()
    return "", 204

@templates_blueprint.route("/<int:template_id>/start", methods=["POST"])
@require_auth
def start_workout_from_template(template_id):
    """creates a new workout based on the template with placeholder reps and weight which the user fills in when completing the workout."""
    template, error = _get_template_or_404(template_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}

    # workout name defaults to template name unless overridden
    workout_name = data.get("name") or template.name

    workout = Workout(
        user_id=g.current_user.id,
        name=workout_name,
        notes=data.get("notes"),
    )
    db.session.add(workout)
    db.session.flush()  # assigns workout.id without committing

    set_number = 1
    for entry in template.exercises:
        for _ in range(entry["target_sets"]):
            workout_set = WorkoutSet(
                workout_id=workout.id,
                exercise_id=entry["exercise_id"],
                set_number=set_number,
                reps=0,           
                weight_kg=0.0,    # placeholder values to be filled in when completing the workout
            )
            db.session.add(workout_set)
            set_number += 1

    db.session.commit()

    return jsonify({"workout": workout.to_dict(include_sets=True)}), 201