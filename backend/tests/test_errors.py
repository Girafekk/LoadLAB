from app.core.config import get_settings
from app.main import app


def test_unknown_route_returns_unified_error(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"]


def test_wrong_method_returns_unified_error(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_unexpected_error_is_hidden_from_client(client):
    def broken_dependency():
        raise RuntimeError("секретные подробности")

    app.dependency_overrides[get_settings] = broken_dependency

    response = client.get("/api/v1/health")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert "секретные" not in error["message"]
