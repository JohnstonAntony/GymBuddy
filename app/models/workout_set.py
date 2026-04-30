from app.extensions import db


class WorkoutSet(db.Model):
    """single set within a workout: one exercise, reps, weight, optional RPE."""
    __tablename__ = "workout_sets"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id"), nullable=False, index=True
    )
    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercises.id"), nullable=False, index=True
    )
    set_number = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    rpe = db.Column(db.Float)  # 1-10 effort scale, optional

    exercise = db.relationship("Exercise", lazy=True)

    def to_dict(self):
        """returns set data for API responses."""
        return {
            "id": self.id,
            "workout_id": self.workout_id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name if self.exercise else None,
            "set_number": self.set_number,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "rpe": self.rpe,
        }

    def __repr__(self):
        return f"<WorkoutSet #{self.set_number} of workout {self.workout_id}>"