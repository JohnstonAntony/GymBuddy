from datetime import datetime, timezone
from app.extensions import db


class Workout(db.Model):
    """workout session belonging to one user. Contains many sets."""
    __tablename__ = "workouts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    sets = db.relationship(
        "WorkoutSet",
        backref="workout",
        cascade="all, delete-orphan", #ensures sets are deleted if workout is deleted
        lazy=True,
        order_by="WorkoutSet.set_number", #currently orders sets by set_number, might change it later to allow custom ordering
    )

    def to_dict(self, include_sets=True):
        """returns workout data for API responses."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
        }
        if include_sets:
            data["sets"] = [s.to_dict() for s in self.sets]
        return data

    def __repr__(self):
        return f"<Workout {self.name} for user_id={self.user_id}>"