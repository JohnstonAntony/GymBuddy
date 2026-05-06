from app.extensions import db
from app.models import Exercise


def validate_template_exercises(exercises_data):
    """Validate the exercises data for a workout template. Error message on failure, validated list on success."""

    if not isinstance(exercises_data, list):
        return None, "exercises must be a list"

    validated = []
    seen_exercise_ids = set()

    for index, item in enumerate(exercises_data):
        prefix = f"exercises[{index}]"

        if not isinstance(item, dict):
            return None, f"{prefix} must be an object"

        exercise_id = item.get("exercise_id")
        target_sets = item.get("target_sets")
        target_reps = item.get("target_reps")

        if not isinstance(exercise_id, int):
            return None, f"{prefix}.exercise_id must be an number"
        if not isinstance(target_sets, int) or target_sets <= 0:
            return None, f"{prefix}.target_sets must be a positive number"
        if not isinstance(target_reps, int) or target_reps <= 0:
            return None, f"{prefix}.target_reps must be a positive number"

        # verifies the exercise exists
        if not db.session.get(Exercise, exercise_id):
            return None, f"{prefix}.exercise_id {exercise_id} does not match a known exercise"

        seen_exercise_ids.add(exercise_id)

        validated.append({
            "exercise_id": exercise_id,
            "target_sets": target_sets,
            "target_reps": target_reps,
        })

    return validated, None