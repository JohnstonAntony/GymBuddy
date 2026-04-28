import os


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

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is required in production")
        
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}