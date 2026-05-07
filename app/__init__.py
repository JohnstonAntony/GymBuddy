from flask import Flask, app
from config import config_by_name
from app.extensions import db, migrate



def create_app(config_name="development"): # creates folder if it doesn't exist so it doesn't throw an error when initzialising run.py
    app = Flask(__name__, instance_relative_config=True)

    import os
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(config_by_name[config_name])

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)

    #import models so alembic can detect them
    from app import models # noqa: F401

    #register CLI commands
    from app.cli import register_commands
    register_commands(app)

   #registered blueprints
    from app.api.auth import auth_blueprint
    from app.api.users import users_blueprint
    from app.api.exercises import exercises_blueprint
    from app.api.workouts import workouts_blueprint
    from app.api.sets import sets_blueprint
    from app.api.templates import templates_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(users_blueprint)
    app.register_blueprint(exercises_blueprint)
    app.register_blueprint(workouts_blueprint)
    app.register_blueprint(sets_blueprint)
    app.register_blueprint(templates_blueprint)


    # Health check route
    @app.route("/health")
    def health_check():
        return {"status": "ok", "message": "GymBuddy is running"}

    return app