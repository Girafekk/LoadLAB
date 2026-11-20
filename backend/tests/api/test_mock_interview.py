"""Пробное собеседование."""

from app.models import InterviewQuestion
from tests.api.helpers import register


def _questions(db_session, count: int = 5) -> None:
    for index in range(count):
        db_session.add(
            InterviewQuestion(
                fingerprint=f"mock-{index}",
                text=f"Что такое метрика {index}?",
                topic="Метрики",
                status="approved",
                occurrences=1,
            )
        )
    db_session.flush()


def test_mock_interview_requires_auth(api_client):
    assert api_client.post("/api/v1/mock-interviews").status_code == 401


def test_mock_interview_needs_approved_questions(api_client):
    register(api_client)
    response = api_client.post("/api/v1/mock-interviews")
    assert response.status_code == 422


def test_mock_interview_flow(api_client, db_session):
    register(api_client, email="mock-student@example.com")
    _questions(db_session)
    started = api_client.post("/api/v1/mock-interviews")
    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "active"
    assert body["total"] == 5
    assert body["current"]["text"]

    current = body["current"]
    for index in range(5):
        response = api_client.post(
            f"/api/v1/mock-interviews/{body['id']}/answers",
            json={
                "answer": (f"Ответ {index}: называю главное, привожу пример и границу."),
                "answer_id": current["answer_id"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        if index < 4:
            assert payload["completed"] is False
            current = payload["next_question"]
            assert current
        else:
            assert payload["completed"] is True

    repeated = api_client.post(
        f"/api/v1/mock-interviews/{body['id']}/answers",
        json={"answer": "Повтор", "answer_id": current["answer_id"]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["completed"] is True

    report = api_client.get(f"/api/v1/mock-interviews/{body['id']}")
    assert report.status_code == 200
    assert report.json()["status"] == "completed"
    assert len(report.json()["answers"]) == 5


def test_mock_interview_is_private(api_client, db_session):
    register(api_client, email="mock-owner@example.com")
    _questions(db_session)
    started = api_client.post("/api/v1/mock-interviews").json()

    other = api_client.__class__(api_client.app)
    other.headers.update({"Origin": "http://localhost:3000"})
    register(other, email="mock-other@example.com")
    assert other.get(f"/api/v1/mock-interviews/{started['id']}").status_code == 404


def test_mock_answer_rejects_empty(api_client, db_session):
    register(api_client, email="mock-empty@example.com")
    _questions(db_session)
    started = api_client.post("/api/v1/mock-interviews").json()
    response = api_client.post(
        f"/api/v1/mock-interviews/{started['id']}/answers",
        json={"answer": "", "answer_id": started["current"]["answer_id"]},
    )
    assert response.status_code == 422
    whitespace = api_client.post(
        f"/api/v1/mock-interviews/{started['id']}/answers",
        json={"answer": "   ", "answer_id": started["current"]["answer_id"]},
    )
    assert whitespace.status_code == 422


def test_mock_answer_returns_retry_after(api_client, db_session):
    from app.core.rate_limit import ai_teacher_rate_limiter

    register(api_client, email="mock-limit@example.com")
    _questions(db_session)
    started = api_client.post("/api/v1/mock-interviews").json()
    user_id = api_client.get("/api/v1/auth/me").json()["id"]
    key = f"mock-interview:{user_id}"
    for _ in range(15):
        assert ai_teacher_rate_limiter.reserve_attempt(key) == 0
    response = api_client.post(
        f"/api/v1/mock-interviews/{started['id']}/answers",
        json={
            "answer": "Ответ достаточной длины для проверки.",
            "answer_id": started["current"]["answer_id"],
        },
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"]
