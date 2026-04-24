from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash #password hashing
from app.extensions import db


class User(db.Model):  #user model to store basic user info with auth for unique columns, string limit and required feilds.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Store hashed passwords, not plaintext will implement hashing in a later session.
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc) # Store timestamps in UTC, used a lambda to ensure the default is evaluated at runtime, not at import time.
    )

    profile = db.relationship(
        "UserProfile", backref="user", uselist=False, lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password) #Hashes the password and store the hash.

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) #Checks if the provided password matches the stored hash, returns True or False.

    def to_dict(self, include_profile=False):
        """Return user data safe for API responses, no password hash."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_profile:
            data["profile"] = self.profile.to_dict() if self.profile else None
        return data
    
    def __repr__(self):
        return f"<User {self.username}>"


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    full_name = db.Column(db.String(120))
    date_of_birth = db.Column(db.Date)
    weight_kg = db.Column(db.Float)
    height_cm = db.Column(db.Float)
    fitness_goal = db.Column(db.String(30))
    experience_level = db.Column(db.String(20))

    def to_dict(self):
        """Return profile data safe for API responses."""
        return {
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "fitness_goal": self.fitness_goal,
            "experience_level": self.experience_level,
        }


    def __repr__(self):
        return f"<UserProfile for user_id={self.user_id}>"