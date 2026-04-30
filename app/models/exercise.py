from app.extensions import db


class Exercise(db.Model):
    """exercise catalogue. Shared across all users."""
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    muscle_groups = db.Column(db.String(200))
    equipment_required = db.Column(db.String(120))
    description = db.Column(db.Text)

    def to_dict(self):
        """returns exercise data for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "muscle_groups": self.muscle_groups.split(",") if self.muscle_groups else [],
            "equipment_required": self.equipment_required,
            "description": self.description,
        }

    def __repr__(self):
        return f"<Exercise {self.name}>"