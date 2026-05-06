from datetime import datetime, timezone
from app.extensions import db


class WorkoutTemplate(db.Model):
    """model for workout templates created by users. Each template includes a name and a list of exercises."""
    __tablename__ = "workout_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    exercises = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """returns template data for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "exercises": self.exercises or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<WorkoutTemplate {self.name} for user_id={self.user_id}>"