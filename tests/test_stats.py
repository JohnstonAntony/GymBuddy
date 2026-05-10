import pytest
from datetime import datetime, timezone
from app.extensions import db
from app.models import Exercise, Workout, WorkoutSet


@pytest.fixture
def seeded_exercise(app):
    """adds a single exercise"""
    with app.app_context():
        exercise = Exercise(
            name="Bench Press", category="push",
            muscle_groups="chest,triceps", equipment_required="barbell"
        )
        db.session.add(exercise)
        db.session.commit()
        return exercise.id


@pytest.fixture
def carl_token(client):
    """register and log in a second user, returning their token for auth in tests."""
    client.post("/api/auth/register", json={
        "username": "carl", "email": "carl@example.com", "password": "password2",
    })
    response = client.post("/api/auth/login", json={
        "email": "carl@example.com", "password": "password2",
    })
    return response.get_json()["token"]


def _create_workout_with_sets(client, headers, exercise_id, sets_data):
    """helper to create a workout with sets via the API. Returns the workout ID."""
    workout_response = client.post("/api/workouts", headers=headers, json={"name": "Test"})
    workout_id = workout_response.get_json()["workout"]["id"]
    for reps, weight in sets_data:
        client.post(
            f"/api/workouts/{workout_id}/sets",
            headers=headers,
            json={"exercise_id": exercise_id, "reps": reps, "weight_kg": weight},
        )
    return workout_id


def test_volume_empty(client, auth_headers):
    """tests that a user with no workouts returns empty data_points and zero total."""
    response = client.get("/api/stats/volume", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["data_points"] == []
    assert data["total_volume"] == 0


def test_volume_single_day(client, auth_headers, seeded_exercise):
    """tests that one workout with two sets sums to reps*weight per set."""
    _create_workout_with_sets(client, auth_headers, seeded_exercise,
                             [(8, 80), (8, 85)])

    response = client.get("/api/stats/volume", headers=auth_headers)
    data = response.get_json()
    assert len(data["data_points"]) == 1
    assert data["data_points"][0]["volume"] == 8 * 80 + 8 * 85  # 1320
    assert data["total_volume"] == 1320


def test_volume_groups_by_date(app, client, auth_headers, seeded_exercise):
    """tests that sets logged on two different dates produce two data points."""
    
    with app.app_context():
        user_id = 1  

        old_workout = Workout(
            user_id=user_id, name="Old",
            started_at=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
        )
        db.session.add(old_workout)
        db.session.flush()
        db.session.add(WorkoutSet(
            workout_id=old_workout.id, exercise_id=seeded_exercise,
            set_number=1, reps=10, weight_kg=50.0,
        ))

        new_workout = Workout(
            user_id=user_id, name="New",
            started_at=datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc),
        )
        db.session.add(new_workout)
        db.session.flush()
        db.session.add(WorkoutSet(
            workout_id=new_workout.id, exercise_id=seeded_exercise,
            set_number=1, reps=5, weight_kg=100.0,
        ))
        db.session.commit()

    response = client.get("/api/stats/volume", headers=auth_headers)
    data = response.get_json()
    assert len(data["data_points"]) == 2

    # ordered chronologically
    assert data["data_points"][0]["date"] == "2026-01-05"
    assert data["data_points"][0]["volume"] == 500   
    assert data["data_points"][1]["date"] == "2026-04-05"
    assert data["data_points"][1]["volume"] == 500   
    assert data["total_volume"] == 1000


def test_volume_filter_by_date_range(app, client, auth_headers, seeded_exercise):
    """tests that from= and to= filter the results by workout date. Inclusive end."""
    with app.app_context():
        user_id = 1

        # one workout in January, one in April
        for date in [datetime(2026, 1, 5, tzinfo=timezone.utc),
                     datetime(2026, 4, 5, tzinfo=timezone.utc)]:
            workout = Workout(user_id=user_id, name="W", started_at=date)
            db.session.add(workout)
            db.session.flush()
            db.session.add(WorkoutSet(
                workout_id=workout.id, exercise_id=seeded_exercise,
                set_number=1, reps=10, weight_kg=50.0,
            ))
        db.session.commit()

    # restricted to March-May
    response = client.get(
        "/api/stats/volume?from=2026-03-01&to=2026-05-31",
        headers=auth_headers,
    )
    data = response.get_json()
    assert len(data["data_points"]) == 1
    assert data["data_points"][0]["date"] == "2026-04-05"


def test_volume_excludes_other_users(client, auth_headers, carl_token, seeded_exercise):
    """tests that only the authenticated user's workouts are included in the results."""
    
    carl_headers = {"Authorization": f"Bearer {carl_token}"}
    _create_workout_with_sets(client, carl_headers, seeded_exercise, [(10, 50)])

    
    response = client.get("/api/stats/volume", headers=auth_headers)
    data = response.get_json()
    assert data["data_points"] == []
    assert data["total_volume"] == 0


def test_volume_bodyweight_exercise(client, auth_headers, seeded_exercise):
    """makes sure excerises with kg=0 are included with zero volume and not excluded or causing errors."""
    _create_workout_with_sets(client, auth_headers, seeded_exercise,
                              [(20, 0)])

    response = client.get("/api/stats/volume", headers=auth_headers)
    data = response.get_json()
    assert len(data["data_points"]) == 1
    assert data["data_points"][0]["volume"] == 0


def test_volume_invalid_from_date(client, auth_headers):
    """an invalid from= date returns a 400 with an error message."""
    response = client.get("/api/stats/volume?from=not-a-date", headers=auth_headers)
    assert response.status_code == 400


def test_volume_requires_auth(client):
    """no token = 401."""
    response = client.get("/api/stats/volume")
    assert response.status_code == 401

def test_prs_empty(client, auth_headers):
    """tests that a user with no workouts returns an empty PR list and zero count."""
    response = client.get("/api/stats/prs", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["personal_records"] == []
    assert data["count"] == 0


def test_prs_single_exercise_max(client, auth_headers, seeded_exercise):
    """only the heaviest set for the exercise is returned, even if there are multiple sets."""
    workout_id = _create_workout_with_sets(
        client, auth_headers, seeded_exercise,
        [(8, 60), (5, 80), (3, 100), (5, 90)],
    )

    response = client.get("/api/stats/prs", headers=auth_headers)
    data = response.get_json()
    assert data["count"] == 1
    pr = data["personal_records"][0]
    assert pr["weight_kg"] == 100
    assert pr["reps"] == 3


def test_prs_multiple_exercises(app, client, auth_headers):
    """different exercises get their own PR row."""
    with app.app_context():
        bench = Exercise(name="Bench", category="push",
                         muscle_groups="chest", equipment_required="barbell")
        squat = Exercise(name="Squat", category="legs",
                         muscle_groups="quads", equipment_required="barbell")
        db.session.add_all([bench, squat])
        db.session.commit()
        bench_id, squat_id = bench.id, squat.id

    _create_workout_with_sets(client, auth_headers, bench_id, [(5, 100)])
    _create_workout_with_sets(client, auth_headers, squat_id, [(5, 140)])

    response = client.get("/api/stats/prs", headers=auth_headers)
    data = response.get_json()
    assert data["count"] == 2
    # alphabetically sorted by exercise name
    assert data["personal_records"][0]["exercise_name"] == "Bench"
    assert data["personal_records"][0]["weight_kg"] == 100
    assert data["personal_records"][1]["exercise_name"] == "Squat"
    assert data["personal_records"][1]["weight_kg"] == 140


def test_prs_excludes_other_users(client, auth_headers, carl_token, seeded_exercise):
    """IDOR test for PR endpoint"""
    carl_headers = {"Authorization": f"Bearer {carl_token}"}
    _create_workout_with_sets(client, carl_headers, seeded_exercise, [(5, 200)])

    response = client.get("/api/stats/prs", headers=auth_headers)
    data = response.get_json()
    assert data["personal_records"] == []


def test_prs_dedupe_on_tied_weight(app, client, auth_headers, seeded_exercise):
    """returns most recent set if there are multiple with the same max weight for an exercise."""
    with app.app_context():
        user_id = 1
        # old PR
        old_workout = Workout(
            user_id=user_id, name="Old",
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.session.add(old_workout)
        db.session.flush()
        db.session.add(WorkoutSet(
            workout_id=old_workout.id, exercise_id=seeded_exercise,
            set_number=1, reps=5, weight_kg=100.0,
        ))
        # tied PR, more recent
        new_workout = Workout(
            user_id=user_id, name="New",
            started_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        db.session.add(new_workout)
        db.session.flush()
        db.session.add(WorkoutSet(
            workout_id=new_workout.id, exercise_id=seeded_exercise,
            set_number=1, reps=8, weight_kg=100.0,
        ))
        db.session.commit()

    response = client.get("/api/stats/prs", headers=auth_headers)
    data = response.get_json()
    assert data["count"] == 1
    pr = data["personal_records"][0]
    assert pr["weight_kg"] == 100
    assert pr["reps"] == 8
    assert pr["achieved_on"].startswith("2026-06-01")


def test_prs_requires_auth(client):
    response = client.get("/api/stats/prs")
    assert response.status_code == 401