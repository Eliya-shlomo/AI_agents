from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_authenticate_success():
    response = client.post("/auth?username=admin&password=1234")
    assert response.status_code == 200
    assert response.json()["status"] == "authenticated"