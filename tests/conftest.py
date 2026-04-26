import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    """creates a fresh Flask app configured for testing. Each test gets its own app and empty in-memory database."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """return a Flask test client for making fake HTTP requests."""
    return app.test_client()


@pytest.fixture
def registered_user(client):
    """registers a default user and return their credentials. Used as a starting state for tests that need an existing user."""
    credentials = {
        "username": "john",
        "email": "john@example.com",
        "password": "password1",
    }
    client.post("/api/auth/register", json=credentials)
    return credentials


@pytest.fixture
def auth_token(client, registered_user):
    """logs in the default user and returns their JWT token."""
    response = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    return response.get_json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """returns headers ready to send authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}