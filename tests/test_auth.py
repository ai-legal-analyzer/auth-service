import pytest
import httpx
import random

BASE_URL = "http://127.0.0.1:8001"


def generate_random_user_data():
    user_id = random.randint(100_000, 1_000_000)
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "username": f"testuser_{user_id}",
        "email": f"testuser_{user_id}@example.com",
        "password": "password123",
    }
    return user_data


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL) as c:
        yield c


def test_app_health(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_create_user(client):
    user_data = generate_random_user_data()
    response = client.post("/auth/", json=user_data)
    assert response.status_code == 201
    body = response.json()
    assert body["transaction"] == "Successful"


def test_login(client):
    user_data = {
        "first_name": "Login",
        "last_name": "Test",
        "username": "logintest",
        "email": "login@example.com",
        "password": "password123",
    }
    client.post("/auth/", json=user_data)

    login_response = client.post("/auth/token", data={
        "username": "logintest",
        "password": "password123",
    })

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_protected_endpoint(client):
    user = {
        "first_name": "Protected",
        "last_name": "User",
        "username": "protectedtest",
        "email": "protected@example.com",
        "password": "password123",
    }
    client.post("/auth/", json=user)

    login = client.post("/auth/token", data={
        "username": "protectedtest",
        "password": "password123",
    })
    token = login.json()["access_token"]

    response = client.get(
        "/auth/read_current_user",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["User"]["username"] == "protectedtest"


def test_unauthorized_access(client):
    response = client.get("/auth/read_current_user")
    assert response.status_code == 401


def test_duplicate_username(client):
    user_data = generate_random_user_data()

    r1 = client.post("/auth/", json=user_data)
    assert r1.status_code == 201

    user_data["email"] = "second@example.com"
    r2 = client.post("/auth/", json=user_data)

    assert r2.status_code in {400, 409, 422}
