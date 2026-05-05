import pytest
from app.extensions import db
from app.models import Exercise


@pytest.fixture
def seeded_exercise(app):
    with app.app_context():
        exercise = Exercise(
            name="Bench Press", category="push",
            muscle_groups="chest,triceps", equipment_required="barbell"
        )
        db.session.add(exercise)
        db.session.commit()
        return exercise.id


@pytest.fixture
def workout_with_set(client, auth_headers, seeded_exercise):
    """creates a workout and adds a set to it, returns both IDs for use in set tests."""
    workout_response = client.post("/api/workouts", headers=auth_headers, json={"name": "Push"})
    workout_id = workout_response.get_json()["workout"]["id"]

    set_response = client.post(
        f"/api/workouts/{workout_id}/sets",
        headers=auth_headers,
        json={"exercise_id": seeded_exercise, "reps": 8, "weight_kg": 80},
    )
    set_id = set_response.get_json()["set"]["id"]
    return workout_id, set_id


def test_patch_set(client, auth_headers, workout_with_set):
    """checks if patch updates only the provided fields and leaves the others unchanged."""
    _, set_id = workout_with_set
    response = client.patch(f"/api/sets/{set_id}",
                            headers=auth_headers, json={"weight_kg": 85})
    assert response.status_code == 200
    data = response.get_json()["set"]
    assert data["weight_kg"] == 85.0
    assert data["reps"] == 8  #checks that reps is unchanged


def test_patch_set_invalid_rpe(client, auth_headers, workout_with_set):
    """checks if rpe is between 1 and 10"""
    _, set_id = workout_with_set
    response = client.patch(f"/api/sets/{set_id}",
                            headers=auth_headers, json={"rpe": 11})
    assert response.status_code == 400


def test_delete_set(client, auth_headers, workout_with_set):
    """checks if DELETE removes the set."""
    _, set_id = workout_with_set
    response = client.delete(f"/api/sets/{set_id}", headers=auth_headers)
    assert response.status_code == 204


def test_delete_set_not_owned(client, auth_headers, seeded_exercise):
    """checks that a user cannot delete another user's set, returns 404."""
    # registers Carl
    client.post("/api/auth/register", json={
        "username": "carl", "email": "carl@example.com", "password": "password2",
    })
    carl_login = client.post("/api/auth/login", json={
        "email": "carl@example.com", "password": "password2",
    })
    carl_headers = {"Authorization": f"Bearer {carl_login.get_json()['token']}"}

    # Carl creates a workout and a set
    carl_workout = client.post("/api/workouts", headers=carl_headers, json={"name": "Carl's"})
    carl_workout_id = carl_workout.get_json()["workout"]["id"]
    carl_set = client.post(
        f"/api/workouts/{carl_workout_id}/sets",
        headers=carl_headers,
        json={"exercise_id": seeded_exercise, "reps": 5, "weight_kg": 100},
    )
    carl_set_id = carl_set.get_json()["set"]["id"]

    # John tries to delete Carl's set
    response = client.delete(f"/api/sets/{carl_set_id}", headers=auth_headers)
    assert response.status_code == 404


def test_workout_delete_cascades_to_sets(client, auth_headers, workout_with_set):
    """workout deletion cascades to its sets"""
    workout_id, set_id = workout_with_set

    client.delete(f"/api/workouts/{workout_id}", headers=auth_headers)

    
    response = client.patch(f"/api/sets/{set_id}", headers=auth_headers, json={"reps": 10})
    assert response.status_code == 404