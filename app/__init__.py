from flask import Flask, app
from config import config_by_name
from app.extensions import db, migrate
from flasgger import Swagger



def create_app(config_name="development"): # creates folder if it doesn't exist so it doesn't throw an error when initzialising run.py
    app = Flask(__name__, instance_relative_config=True)

    import os
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_object(config_by_name[config_name])

     # swagger configuration
    app.config["SWAGGER"] = {
        "title": "GymBuddy API",
        "uiversion": 3,
        "openapi": "3.0.2",
        "specs_route": "/api/docs/",
    }
    swagger_template = {
        "openapi": "3.0.2",
        "info": {
            "title": "GymBuddy API",
            "description": "REST API for the GymBuddy workout tracking app.",
            "version": "1.0.0",
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    }
    
    Swagger(app, template=swagger_template)


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
    from app.api.stats import stats_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(users_blueprint)
    app.register_blueprint(exercises_blueprint)
    app.register_blueprint(workouts_blueprint)
    app.register_blueprint(sets_blueprint)
    app.register_blueprint(templates_blueprint)
    app.register_blueprint(stats_blueprint)


    # Health check route
    @app.route("/health")
    def health_check():
        return {"status": "ok", "message": "GymBuddy is running"}

    return app