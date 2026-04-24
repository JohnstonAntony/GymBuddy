from flask import Flask
from config import config_by_name
from app.extensions import db



def create_app(config_name="development"): # creates folder if it doesn't exist so it doesn't throw an error when initzialising run.py
    app = Flask(__name__, instance_relative_config=True)

    import os
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(config_by_name[config_name])

  
    db.init_app(app)

    # Register blueprints
    from app.api.auth import auth_blueprint
    from app.api.users import users_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(users_blueprint)

    # Creates database tables
    with app.app_context():
        from app.models import User, UserProfile  # noqa: F401
        db.create_all()

    # Health check route
    @app.route("/health")
    def health_check():
        return {"status": "ok", "message": "GymBuddy is running"}

    return app