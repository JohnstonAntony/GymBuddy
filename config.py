import os
from dotenv import load_dotenv

load_dotenv()

base_directory = os.path.abspath(os.path.dirname(__file__)) # absolute path to directory


class Config:
    """Base configuration. Shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"
    SQLALCHEMY_TRACK_MODIFICATIONS = False # disabled to save memory and improve perf

     # JSON Web Token (JWT) settings
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "jwt-dev-secret-change-me"
    JWT_EXPIRY_HOURS = 24



class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{os.path.join(base_directory, 'instance', 'gymbuddy_dev.db')}" #file pathing for db inside instance folder
    )


class TestingConfig(Config): # testing cofig to see if SQalchemy is working correctly
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" 


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}