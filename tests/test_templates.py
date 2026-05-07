import pytest
from app.extensions import db
from app.models import Exercise


@pytest.fixture
def seeded_exercises(app):
    """adds two exercises to the database and returns their IDs for use in tests."""
    with app.app_context():
        bench = Exercise(name="Bench Press", category="push",
                         muscle_groups="chest,triceps", equipment_required="barbell")
        squat = Exercise(name="Squat", category="legs",
                         muscle_groups="quads,glutes", equipment_required="barbell")
        db.session.add_all([bench, squat])
        db.session.commit()
        return {"bench_id": bench.id, "squat_id": squat.id}


@pytest.fixture
def carl_token(client):
    """registers and logs in a user named Carl, returns his auth token."""
    client.post("/api/auth/register", json={
        "username": "carl", "email": "carl@example.com", "password": "password2",
    })
    response = client.post("/api/auth/login", json={
        "email": "carl@example.com", "password": "password2",
    })
    return response.get_json()["token"]


def test_create_template(client, auth_headers, seeded_exercises):
    """Creating a template with valid data returns 201 and the created template. POST"""
    response = client.post("/api/templates", headers=auth_headers, json={
        "name": "Push Day",
        "exercises": [
            {"exercise_id": seeded_exercises["bench_id"], "target_sets": 3, "target_reps": 8},
        ],
    })
    assert response.status_code == 201
    assert len(response.get_json()["template"]["exercises"]) == 1


def test_create_template_missing_name(client, auth_headers):
    """missing name returns 400."""
    response = client.post("/api/templates", headers=auth_headers, json={
        "exercises": [],
    })
    assert response.status_code == 400


def test_create_template_invalid_exercise_id(client, auth_headers):
    """an exercise_id that doesn't exist returns 400."""
    response = client.post("/api/templates", headers=auth_headers, json={
        "name": "Bad",
        "exercises": [{"exercise_id": 9999, "target_sets": 3, "target_reps": 8}],
    })
    assert response.status_code == 400


def test_create_template_invalid_target_sets(client, auth_headers, seeded_exercises):
    """a negative target_sets value returns 400."""
    response = client.post("/api/templates", headers=auth_headers, json={
        "name": "Bad",
        "exercises": [
            {"exercise_id": seeded_exercises["bench_id"], "target_sets": -1, "target_reps": 8},
        ],
    })
    assert response.status_code == 400


def test_create_template_strips_extra_keys(client, auth_headers, seeded_exercises):
    """Extra keys in an exercise entry are stripped — only known keys persist."""
    response = client.post("/api/templates", headers=auth_headers, json={
        "name": "With Extras",
        "exercises": [
            {
                "exercise_id": seeded_exercises["bench_id"],
                "target_sets": 3,
                "target_reps": 8,
                "extra_key": "should be stripped",
            },
        ],
    })
    assert response.status_code == 201
    entry = response.get_json()["template"]["exercises"][0]
    assert "extra_key" not in entry


def test_list_templates_returns_own_only(client, auth_headers, carl_token, seeded_exercises):
    """users see only their own templates in the list endpoint."""
    carl_headers = {"Authorization": f"Bearer {carl_token}"}
    client.post("/api/templates", headers=carl_headers, json={
        "name": "Carl's Template", "exercises": [],
    })

    response = client.get("/api/templates", headers=auth_headers)
    assert len(response.get_json()["templates"]) == 0


def test_get_template_not_owned(client, auth_headers, carl_token):
    """users cannot access a template they don't own, even if they know the ID."""
    carl_headers = {"Authorization": f"Bearer {carl_token}"}
    create = client.post("/api/templates", headers=carl_headers, json={
        "name": "Carl's", "exercises": [],
    })
    carl_template_id = create.get_json()["template"]["id"]

    response = client.get(f"/api/templates/{carl_template_id}", headers=auth_headers)
    assert response.status_code == 404


def test_patch_template(client, auth_headers, seeded_exercises):
    """PATCH updates only the targeted fields."""
    create = client.post("/api/templates", headers=auth_headers, json={
        "name": "Original",
        "exercises": [
            {"exercise_id": seeded_exercises["bench_id"], "target_sets": 3, "target_reps": 8},
        ],
    })
    template_id = create.get_json()["template"]["id"]

    response = client.patch(f"/api/templates/{template_id}",
                            headers=auth_headers, json={"name": "Renamed"})
    assert response.status_code == 200
    data = response.get_json()["template"]
    assert data["name"] == "Renamed"
    assert len(data["exercises"]) == 1  


def test_delete_template(client, auth_headers, seeded_exercises):
    """deleting a template returns 204 and removes it from the database. Existing workouts based on the template are not affected."""
    create = client.post("/api/templates", headers=auth_headers, json={
        "name": "ToDelete", "exercises": [],
    })
    template_id = create.get_json()["template"]["id"]

    response = client.delete(f"/api/templates/{template_id}", headers=auth_headers)
    assert response.status_code == 204

    # to confirm it is gone
    get_response = client.get(f"/api/templates/{template_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_start_workout_from_template(client, auth_headers, seeded_exercises):
    """starting a workout from a template creates a workout with the same exercises and placeholder values for reps and weight."""
    create = client.post("/api/templates", headers=auth_headers, json={
        "name": "Push",
        "exercises": [
            {"exercise_id": seeded_exercises["bench_id"], "target_sets": 3, "target_reps": 8},
            {"exercise_id": seeded_exercises["squat_id"], "target_sets": 2, "target_reps": 5},
        ],
    })
    template_id = create.get_json()["template"]["id"]

    response = client.post(f"/api/templates/{template_id}/start", headers=auth_headers)
    assert response.status_code == 201
    workout = response.get_json()["workout"]
    assert workout["name"] == "Push"
    assert len(workout["sets"]) == 5  
    #placeholder values
    assert all(s["reps"] == 0 and s["weight_kg"] == 0.0 for s in workout["sets"])
    # set_number is sequential
    assert [s["set_number"] for s in workout["sets"]] == [1, 2, 3, 4, 5]


def test_start_workout_with_custom_name(client, auth_headers, seeded_exercises):
    """testing that you can override the default workout name when starting from a template."""
    create = client.post("/api/templates", headers=auth_headers, json={
        "name": "Default Name", "exercises": [],
    })
    template_id = create.get_json()["template"]["id"]

    response = client.post(f"/api/templates/{template_id}/start",
                           headers=auth_headers, json={"name": "Custom Name"})
    assert response.get_json()["workout"]["name"] == "Custom Name"


def test_start_workout_from_other_users_template(client, auth_headers, carl_token):
    """users cannot start workouts from templates they don't own, even if they know the template ID."""
    carl_headers = {"Authorization": f"Bearer {carl_token}"}
    create = client.post("/api/templates", headers=carl_headers, json={
        "name": "Carl's", "exercises": [],
    })
    carl_template_id = create.get_json()["template"]["id"]

    response = client.post(f"/api/templates/{carl_template_id}/start", headers=auth_headers)
    assert response.status_code == 404


def test_create_template_requires_auth(client):
    """Token catch"""
    response = client.post("/api/templates", json={"name": "x", "exercises": []})
    assert response.status_code == 401