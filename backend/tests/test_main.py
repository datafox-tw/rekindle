from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_planned_routes_are_stubbed():
    assert client.post("/api/lab/runs").status_code == 501
    assert client.post("/api/uploads").status_code == 501
    assert client.get("/api/metrics").status_code == 501
