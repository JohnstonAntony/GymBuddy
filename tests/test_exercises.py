import pytest
from app.extensions import db
from app.models import Exercise


@pytest.fixture
def seeded_exercises(app):
    """small set of exercises inserted into the database for testing list and filter functionality."""
    with app.app_context():
        db.session.add_all([
            Exercise(name="Bench Press", category="push",
                     muscle_groups="chest,triceps", equipment_required="barbell"),
            Exercise(name="Squat", category="legs",
                     muscle_groups="quads,glutes", equipment_required="barbell"),
            Exercise(name="Pull-Up", category="pull",
                     muscle_groups="lats,biceps", equipment_required="bodyweight"),
        ])
        db.session.commit()


def test_list_exercises_empty(client):
    """tests if the list is empty that it returns count 0 and empty list, rather than erroring."""
    response = client.get("/api/exercises")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
    assert data["exercises"] == []


def test_list_exercises_returns_all(client, seeded_exercises):
    """returns all exercises when no filters are applied, sorted alphabetically by name."""
    response = client.get("/api/exercises")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 3
    names = [e["name"] for e in data["exercises"]]
    assert names == sorted(names)


def test_filter_by_category(client, seeded_exercises):
    """filters exercises by category. this one tests for legs"""
    response = client.get("/api/exercises?category=legs")
    data = response.get_json()
    assert data["count"] == 1
    assert data["exercises"][0]["name"] == "Squat"


def test_filter_by_invalid_category(client):
    """invlaid category returns 400 with error message."""
    response = client.get("/api/exercises?category=banana")
    assert response.status_code == 400


def test_filter_by_muscle(client, seeded_exercises):
    """filters exercises by muscle group. this one tests forchest"""
    response = client.get("/api/exercises?muscle=chest")
    data = response.get_json()
    assert data["count"] == 1
    assert data["exercises"][0]["name"] == "Bench Press"


def test_get_single_exercise(client, seeded_exercises):
    """retrieves details of a single exercise by ID. This test gets an ID from the list endpoint first to avoid hardcoding an ID."""
    #get an ID from the list endpoint first
    list_response = client.get("/api/exercises")
    exercise_id = list_response.get_json()["exercises"][0]["id"]

    response = client.get(f"/api/exercises/{exercise_id}")
    assert response.status_code == 200
    assert response.get_json()["exercise"]["id"] == exercise_id


def test_get_exercise_not_found(client):
    """checks that requesting a non-existent exercise ID returns a 404 with an error message."""
    response = client.get("/api/exercises/9999")
    assert response.status_code == 404


def test_no_auth_required(client, seeded_exercises):
    """tests that the exercise endpoints can be accessed without authentication. If authentication was required, this would return a 401 error instead."""
    response = client.get("/api/exercises")
    assert response.status_code == 200  # NOT 401