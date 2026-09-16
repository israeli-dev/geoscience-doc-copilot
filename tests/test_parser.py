from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_report_empty_payload():
    response = client.post("/api/v1/analyze-report", json={"report_text": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "Report text cannot be empty."