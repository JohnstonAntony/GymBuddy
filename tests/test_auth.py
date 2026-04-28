def test_register_success(client):
    """registration sucess test""" # valid registration returns 201 and the user
    response = client.post("/api/auth/register", json={
        "username": "carl",
        "email": "carl@example.com",
        "password": "passwordTest",
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["email"] == "carl@example.com"
    assert "password_hash" not in data["user"]  


def test_register_short_password(client):
    """password length checker test""" # short password is rejected with 400 and error message
    response = client.post("/api/auth/register", json={
        "username": "carl",
        "email": "carl@example.com",
        "password": "short",
    })
    assert response.status_code == 400
    assert "Password" in response.get_json()["error"]


def test_register_duplicate_email(client, registered_user):
    """Same email registration test""" # registering with an email that already exists returns 409
    response = client.post("/api/auth/register", json={
        "username": "randomUser",
        "email": registered_user["email"],
        "password": "passwordTest",
    })
    assert response.status_code == 409


def test_login_success(client, registered_user):
    """successful login test""" # valid login returns 200 with token and user info 
    response = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert response.status_code == 200
    data = response.get_json()
    assert "token" in data
    assert data["user"]["email"] == registered_user["email"]


def test_login_wrong_password(client, registered_user):
    """wrong password login test""" # invalid login returns 401 with error message
    response = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": "wrongPassword",
    })
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"


def test_me_without_token(client):
    """JWT token required test""" # hitting /me without a token returns 401
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_token(client, auth_headers):
    """valid token test""" # hitting /me with a valid token returns 200 and the user info
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "john@example.com"


def test_me_with_garbage_token(client):
    """incorrect token test""" # hitting /me with an invalid token returns 401
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401