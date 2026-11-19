"""AI Teacher: ответы, история, рекомендации и шпаргалка."""

from sqlalchemy import select

from app.db.content_loader import seed_content
from app.db.seed import seed_curriculum
from app.models import Lesson, Module
from tests.api.helpers import register


def _prepare(api_client, db_session) -> int:
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.flush()
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    register(api_client)
    return int(lesson_id)


def test_ai_requires_login(api_client):
    assert (
        api_client.post(
            "/api/v1/ai/teacher/ask", json={"lesson_id": 1, "question": "?"}
        ).status_code
        == 401
    )


def test_ai_answers_from_lesson_and_stores_history(api_client, db_session):
    lesson_id = _prepare(api_client, db_session)

    response = api_client.post(
        "/api/v1/ai/teacher/ask",
        json={"lesson_id": lesson_id, "question": "Что такое нагрузочное тестирование?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local"
    assert body["mode"] == "answer"
    assert body["lesson_id"] == lesson_id
    assert "Проще" in body["answer"]
    assert "Шаги" in body["answer"]

    repeat = api_client.post(
        "/api/v1/ai/teacher/ask",
        json={"lesson_id": lesson_id, "question": "Что такое нагрузочное тестирование?"},
    )
    assert repeat.json()["mode"] == "simpler"
    assert repeat.json()["answer"] != body["answer"]

    history = api_client.get("/api/v1/ai/teacher/history", params={"lesson_id": lesson_id})
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_ai_recommendations_and_cheatsheet(api_client, db_session):
    _prepare(api_client, db_session)

    recommendations = api_client.get("/api/v1/ai/teacher/recommendations")
    assert recommendations.status_code == 200
    assert recommendations.json() == []

    cheatsheet = api_client.get("/api/v1/ai/teacher/cheatsheet")
    assert cheatsheet.status_code == 200
    assert cheatsheet.json()["title"]
    assert cheatsheet.json()["lesson_ids"]


def test_ai_hides_draft_lesson(api_client, db_session):
    _prepare(api_client, db_session)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    draft = Lesson(module_id=module_id, title="Черновик", position=99, is_published=False)
    db_session.add(draft)
    db_session.flush()

    response = api_client.post(
        "/api/v1/ai/teacher/ask",
        json={"lesson_id": draft.id, "question": "Что здесь?"},
    )
    assert response.status_code == 404


def test_ai_rate_limit_and_history_isolated(api_client, db_session):
    lesson_id = _prepare(api_client, db_session)
    statuses = []
    for _ in range(16):
        response = api_client.post(
            "/api/v1/ai/teacher/ask",
            json={"lesson_id": lesson_id, "question": "Что такое RPS?"},
        )
        statuses.append(response.status_code)
    assert statuses[-1] == 429
    assert api_client.get("/api/v1/ai/teacher/history", params={"lesson_id": lesson_id}).json()

    register(api_client, email="second-ai@example.com")
    assert (
        api_client.get("/api/v1/ai/teacher/history", params={"lesson_id": lesson_id}).json() == []
    )
