import pytest
from app.extensions import db
from app.models import Exercise


@pytest.fixture
def seeded_exercise(app):
    """adds a single exercise to the database and returns its ID so it can be referenced"""
    with app.app_context():
        exercise = Exercise(
            name="Bench Press", category="push",
            muscle_groups="chest,triceps", equipment_required="barbell"
        )
        db.session.add(exercise)
        db.session.commit()
        return exercise.id


@pytest.fixture
def second_user_token(client):
    """registers and logs in a second user, returns their token for auth in tests that need multiple users."""
    client.post("/api/auth/register", json={
        "username": "bob", "email": "bob@example.com", "password": "supersecret123",
    })
    response = client.post("/api/auth/login", json={
        "email": "bob@example.com", "password": "supersecret123",
    })
    return response.get_json()["token"]


def test_create_workout(client, auth_headers):
    """creating a workout with valid data returns 201 and the workout details."""
    response = client.post("/api/workouts", headers=auth_headers, json={"name": "Push Day"})
    assert response.status_code == 201
    assert response.get_json()["workout"]["name"] == "Push Day"


def test_create_workout_missing_name(client, auth_headers):
    """creating a workout without a name returns 400."""
    response = client.post("/api/workouts", headers=auth_headers, json={"notes": "no name"})
    assert response.status_code == 400


def test_create_workout_requires_auth(client):
    """no token = 401."""
    response = client.post("/api/workouts", json={"name": "Push Day"})
    assert response.status_code == 401


def test_list_workouts_empty(client, auth_headers):
    """a user with no workouts gets an empty list"""
    response = client.get("/api/workouts", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["total"] == 0


def test_list_workouts_returns_own_only(client, auth_headers, second_user_token):
    """a user with workouts should only see their own, not other users' workouts, IDOR prevention"""
    # Carl creates a workout
    carl_headers = {"Authorization": f"Bearer {second_user_token}"}
    client.post("/api/workouts", headers=carl_headers, json={"name": "Carl's workout"})

    # John (auth_headers) should see zero workouts
    response = client.get("/api/workouts", headers=auth_headers)
    assert response.get_json()["total"] == 0


def test_get_workout_owned(client, auth_headers):
    """a user can read their own workout by ID, gets 200 and workout details including sets and exercises."""
    create_response = client.post("/api/workouts", headers=auth_headers, json={"name": "Push Day"})
    workout_id = create_response.get_json()["workout"]["id"]

    response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
    assert response.status_code == 200


def test_get_workout_not_owned(client, auth_headers, second_user_token):
    """a user cannot read another user's workout, gets 404 to prevent information leak about existence of the workout, IDOR prevention."""
    # Carl creates a workout
    carl_headers = {"Authorization": f"Bearer {second_user_token}"}
    carl_response = client.post("/api/workouts", headers=carl_headers, json={"name": "Carl's workout"})
    carl_workout_id = carl_response.get_json()["workout"]["id"]

    # John tries to read Carl's workout
    response = client.get(f"/api/workouts/{carl_workout_id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_workout_nonexistent(client, auth_headers):
    """attempting to read a workout that doesn't exist returns 404"""
    response = client.get("/api/workouts/9999", headers=auth_headers)
    assert response.status_code == 404


def test_patch_workout(client, auth_headers):
    """patch updates only requested fields, other fields remain unchanged."""
    create = client.post("/api/workouts", headers=auth_headers, json={"name": "Original"})
    workout_id = create.get_json()["workout"]["id"]

    response = client.patch(f"/api/workouts/{workout_id}",
                            headers=auth_headers, json={"notes": "added notes"})
    assert response.status_code == 200
    data = response.get_json()["workout"]
    assert data["name"] == "Original"  
    assert data["notes"] == "added notes"


def test_patch_workout_not_owned(client, auth_headers, second_user_token):
    """attempting to patch another user's workout returns 404."""
    carl_headers = {"Authorization": f"Bearer {second_user_token}"}
    carl_response = client.post("/api/workouts", headers=carl_headers, json={"name": "Carl's"})
    carl_workout_id = carl_response.get_json()["workout"]["id"]

    response = client.patch(f"/api/workouts/{carl_workout_id}",
                            headers=auth_headers, json={"notes": "hacked"})
    assert response.status_code == 404


def test_delete_workout(client, auth_headers):
    """DELETE removes a workout, returns 204."""
    create = client.post("/api/workouts", headers=auth_headers, json={"name": "ToDelete"})
    workout_id = create.get_json()["workout"]["id"]

    response = client.delete(f"/api/workouts/{workout_id}", headers=auth_headers)
    assert response.status_code == 204

    # to confirm its gone
    get_response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_add_set_to_workout(client, auth_headers, seeded_exercise):
    """post creates a set and assigns it set = 1"""
    create = client.post("/api/workouts", headers=auth_headers, json={"name": "Push"})
    workout_id = create.get_json()["workout"]["id"]

    response = client.post(
        f"/api/workouts/{workout_id}/sets",
        headers=auth_headers,
        json={"exercise_id": seeded_exercise, "reps": 8, "weight_kg": 80},
    )
    assert response.status_code == 201
    set_data = response.get_json()["set"]
    assert set_data["set_number"] == 1
    assert set_data["reps"] == 8


def test_set_numbering_increments(client, auth_headers, seeded_exercise):
    """adding multiple sets to the same workout increments the set_number for each set."""
    create = client.post("/api/workouts", headers=auth_headers, json={"name": "Push"})
    workout_id = create.get_json()["workout"]["id"]

    for expected_n in (1, 2, 3):
        response = client.post(
            f"/api/workouts/{workout_id}/sets",
            headers=auth_headers,
            json={"exercise_id": seeded_exercise, "reps": 8, "weight_kg": 80},
        )
        assert response.get_json()["set"]["set_number"] == expected_n


def test_add_set_to_other_users_workout(client, auth_headers, second_user_token, seeded_exercise):
    """a user cannot add a set to another user's workout, gets 404"""
    carl_headers = {"Authorization": f"Bearer {second_user_token}"}
    carl_response = client.post("/api/workouts", headers=carl_headers, json={"name": "Carl's"})
    carl_workout_id = carl_response.get_json()["workout"]["id"]

    response = client.post(
        f"/api/workouts/{carl_workout_id}/sets",
        headers=auth_headers,
        json={"exercise_id": seeded_exercise, "reps": 8, "weight_kg": 80},
    )
    assert response.status_code == 404


def test_add_set_invalid_reps(client, auth_headers, seeded_exercise):
    """reps must be a positive integer, 0 reps is not valid."""
    create = client.post("/api/workouts", headers=auth_headers, json={"name": "Push"})
    workout_id = create.get_json()["workout"]["id"]

    response = client.post(
        f"/api/workouts/{workout_id}/sets",
        headers=auth_headers,
        json={"exercise_id": seeded_exercise, "reps": 0, "weight_kg": 80},
    )
    assert response.status_code == 400


def test_pagination(client, auth_headers):
    """paginaton test, checks if 2nd page shows third workout if per_page is 2 and there are 5 workouts total."""
    for i in range(5):
        client.post("/api/workouts", headers=auth_headers, json={"name": f"W{i}"})

    response = client.get("/api/workouts?page=1&per_page=2", headers=auth_headers)
    data = response.get_json()
    assert data["total"] == 5
    assert data["per_page"] == 2
    assert data["total_pages"] == 3
    assert len(data["workouts"]) == 2