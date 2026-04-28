def test_get_me_no_profile(client, auth_headers):
    """before any changes to the profile, /me should return user info with profile as none"""
    response = client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["profile"] is None


def test_patch_creates_profile_lazily(client, auth_headers):
    """first PATCH creates the profile row and applies the field."""
    response = client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"weight_kg": 80},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["profile"]["weight_kg"] == 80.0


def test_patch_only_updates_sent_fields(client, auth_headers):
    """Checks if PATCHing one field doesn't wipe out the other fields in the profile."""
    # set weight first
    client.patch("/api/users/me", headers=auth_headers, json={"weight_kg": 80})
    # then, set height — weight should not be wiped
    client.patch("/api/users/me", headers=auth_headers, json={"height_cm": 170})

    response = client.get("/api/users/me", headers=auth_headers)
    profile = response.get_json()["user"]["profile"]
    assert profile["weight_kg"] == 80.0
    assert profile["height_cm"] == 170.0


def test_patch_rejects_invalid_goal(client, auth_headers):
    """fitness_goal not in ALLOWED_GOALS is rejected with 400."""
    response = client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"fitness_goal": "getting_huge"},
    )
    assert response.status_code == 400


def test_patch_rejects_negative_weight(client, auth_headers):
    """negative weight is rejected with 400."""
    response = client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"weight_kg": -50},
    )
    assert response.status_code == 400


def test_patch_rejects_future_dob(client, auth_headers):
    """date of birth in the future is rejected with 400."""
    response = client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"date_of_birth": "2099-01-01"},
    )
    assert response.status_code == 400


def test_patch_rejects_malformed_date(client, auth_headers):
    """date in the wrong format is rejected with 400."""
    response = client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"date_of_birth": "15/06/1995"},
    )
    assert response.status_code == 400


def test_patch_requires_auth(client):
    """No token = 401."""
    response = client.patch("/api/users/me", json={"weight_kg": 80})
    assert response.status_code == 401