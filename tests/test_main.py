import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["application"] == "NEXO AI"

def test_get_ollama_models():
    response = client.get("/api/v1/requests/models")
    assert response.status_code == 200
    assert "models" in response.json()

def test_auth_login_invalid():
    response = client.post("/api/v1/auth/login", json={
        "username": "usuario_falso_inexistente",
        "password": "wrongpassword"
    })
    assert response.status_code == 401