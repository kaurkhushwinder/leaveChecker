"""Pytest-based end-to-end tests for the leaf disease FastAPI project."""

import io
from pathlib import Path

from fastapi.testclient import TestClient

import main
from database import SessionLocal
from models import LeafScan, User


def reset_database():
    """Clear database rows so each test starts from a clean state."""

    db = SessionLocal()
    try:
        db.query(LeafScan).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def clear_uploaded_files():
    """Delete uploaded files created during tests."""

    uploads_dir = Path("static/uploads")
    for item in uploads_dir.iterdir():
        if item.name != ".gitkeep" and item.is_file():
            item.unlink()


def setup_function():
    """Run before each test function."""

    reset_database()
    clear_uploaded_files()


def test_protected_routes_redirect_when_not_logged_in():
    client = TestClient(main.app)

    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

    response = client.get("/upload", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

    response = client.get("/history", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_registration_login_upload_prediction_history_and_logout():
    client = TestClient(main.app)

    response = client.post(
        "/register",
        data={
            "name": "Farmer One",
            "email": "farmer@example.com",
            "password": "12345",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "farmer@example.com").first()
        assert user is not None
    finally:
        db.close()

    response = client.post(
        "/login",
        data={"email": "farmer@example.com", "password": "12345"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Welcome, Farmer One!" in response.text

    response = client.post(
        "/upload",
        files={"leaf_image": ("leaf.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith("/predict/")

    predict_url = response.headers["location"]
    response = client.get(predict_url, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith("/result/")

    result_url = response.headers["location"]
    response = client.get(result_url)
    assert response.status_code == 200
    assert "Prediction Result" in response.text

    db = SessionLocal()
    try:
        scan = db.query(LeafScan).first()
        assert scan is not None
        assert scan.disease_result in {"Leaf Blight", "Powdery Mildew", "Healthy Leaf"}
        assert scan.treatment in {
            "Use copper-based fungicide.",
            "Apply sulfur spray.",
            "No treatment required.",
        }
        assert Path("static", scan.image_path).exists()
        disease_name = scan.disease_result
    finally:
        db.close()

    response = client.get("/history")
    assert response.status_code == 200
    assert disease_name in response.text

    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"

    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_invalid_login_shows_message():
    db = SessionLocal()
    try:
        db.add(User(name="Farmer Two", email="user2@example.com", password="pass"))
        db.commit()
    finally:
        db.close()

    client = TestClient(main.app)
    response = client.post(
        "/login",
        data={"email": "user2@example.com", "password": "wrong-pass"},
    )
    assert response.status_code == 200
    assert "Invalid email or password." in response.text


def test_duplicate_registration_shows_message():
    db = SessionLocal()
    try:
        db.add(User(name="Farmer Three", email="user3@example.com", password="pass"))
        db.commit()
    finally:
        db.close()

    client = TestClient(main.app)
    response = client.post(
        "/register",
        data={
            "name": "Farmer Three",
            "email": "user3@example.com",
            "password": "pass",
        },
    )
    assert response.status_code == 200
    assert "Email already registered." in response.text
