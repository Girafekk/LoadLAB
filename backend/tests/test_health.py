from app.db.session import is_database_available
from app.main import app


def test_health_reports_backend_state(client):
    app.dependency_overrides[is_database_available] = lambda: True

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "LoadLab API"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "test"
    assert body["database"] == "ok"
    assert "timestamp" in body


def test_health_works_when_database_is_down(client):
    app.dependency_overrides[is_database_available] = lambda: False

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["database"] == "unavailable"


def test_openapi_schema_describes_health(client):
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
