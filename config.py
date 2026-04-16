import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration. Shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}