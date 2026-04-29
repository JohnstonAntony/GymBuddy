import os

def _resolve_database_url():
    """Read DATABASE_URL from env and normalise it for SQLAlchemy + psycopg3."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required in production")
    # Render/Heroku give postgres://, SQLAlchemy 2.x wants postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # use psycopg3 (newer driver with Python 3.14 support)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    """base configuration. Shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"
    SQLALCHEMY_TRACK_MODIFICATIONS = False # disabled to save memory and improve perf

    # JWT settings
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "jwt-dev-secret-change-me"
    JWT_EXPIRY_HOURS = 24

    #reads from env in production, fall back to SQLite locally
    DATABASE_URL = os.environ.get("DATABASE_URL")


class DevelopmentConfig(Config):
    """configuration for local dev"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///gymbuddy_dev.db" #file pathing for db inside instance folder


class TestingConfig(Config):
    """configuration for running tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_EXPIRY_HOURS = 1


class ProductionConfig(Config):
    """configuration for production deployment. All secrets must come from environment variables \u2014 no defaults."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _resolve_database_url() if os.environ.get("FLASK_ENV") == "production" else None


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}