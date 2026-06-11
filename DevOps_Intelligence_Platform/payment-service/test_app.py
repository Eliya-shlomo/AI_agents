from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_process_payment():
    response = client.post("/payment", json={
        "card_number": "1234567890123456",
        "amount": 100.0
    })
    assert response.status_code == 200
    assert "transaction_id" in response.json()

def test_payment_db_connection():
    # באג בכוונה! DB_URL לא מוגדר
    import os
    db_url = os.environ["DB_URL"]  # יזרוק KeyError!
    assert db_url is not None



