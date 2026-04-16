from flask import Flask
from config import config_by_name


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Temporary health-check route to verify the app runs.
    @app.route("/health")
    def health_check():
        return {"status": "ok", "message": "GymBuddy is running"}
    # Will move routes into blueprints in a later lesson.

    return app