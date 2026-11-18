from sqlalchemy import update

from app.models import User
from tests.api.helpers import register

# --- Роли ------------------------------------------------------------------------


def test_admin_ping_requires_login(api_client):
    response = api_client.get("/api/v1/admin/ping")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_student_cannot_reach_admin_ping(api_client):
    register(api_client)

    response = api_client.get("/api/v1/admin/ping")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_reach_admin_ping(api_client, db_session):
    register(api_client)
    db_session.execute(update(User).values(role="admin"))

    response = api_client.get("/api/v1/admin/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_role_cannot_be_chosen_at_registration(api_client):
    response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "sly@example.com", "password": "correct-horse-42", "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "student"


# --- CSRF: проверка заголовка Origin -----------------------------------------------

CREDENTIALS = {"email": "student@example.com", "password": "correct-horse-42"}


def test_post_from_foreign_origin_is_rejected(api_client):
    response = api_client.post(
        "/api/v1/auth/register", json=CREDENTIALS, headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_post_without_origin_is_rejected(api_client):
    del api_client.headers["Origin"]

    response = api_client.post("/api/v1/auth/register", json=CREDENTIALS)

    assert response.status_code == 403


def test_post_from_api_own_origin_is_allowed(api_client):
    # Так отправляет запросы страница документации /api/v1/docs.
    response = api_client.post(
        "/api/v1/auth/register", json=CREDENTIALS, headers={"Origin": "http://testserver"}
    )

    assert response.status_code == 201


def test_get_does_not_need_origin(api_client):
    del api_client.headers["Origin"]

    assert api_client.get("/api/v1/health").status_code == 200


def test_logout_from_foreign_origin_is_rejected(api_client):
    register(api_client)

    response = api_client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    # Сессия осталась: подделанный запрос ничего не сломал.
    assert api_client.get("/api/v1/auth/me").status_code == 200


def test_logout_without_origin_is_rejected(api_client):
    register(api_client)
    del api_client.headers["Origin"]

    assert api_client.post("/api/v1/auth/logout").status_code == 403
    assert api_client.get("/api/v1/auth/me").status_code == 200
