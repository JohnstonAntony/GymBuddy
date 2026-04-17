from datetime import datetime, timezone
from app.extensions import db


class User(db.Model): #user model to store basic user info with auth for unique columns, string limit and required feilds.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Store hashed passwords, not plaintext will implement hashing in a later session.
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc) # Store timestamps in UTC to avoid timezone issues
    )

    profile = db.relationship(
        "UserProfile", backref="user", uselist=False, lazy=True
    )

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

    def __repr__(self):
        return f"<UserProfile for user_id={self.user_id}>"