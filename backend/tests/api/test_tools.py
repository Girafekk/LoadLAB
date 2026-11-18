"""Конспект, выделения, вопросы, повторение, шпаргалки и слабые темы."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload

from app.db.demo_lesson import publish_demo_lesson
from app.db.demo_quiz import publish_demo_quiz
from app.db.seed import seed_curriculum
from app.models import (
    Cheatsheet,
    Lesson,
    LessonHighlight,
    LessonNote,
    Quiz,
    QuizQuestion,
    ReviewItem,
    SavedQuestion,
    User,
)
from tests.api.helpers import login, register


def _prepare(db_session, *, with_quiz: bool = False) -> int:
    seed_curriculum(db_session)
    publish_demo_lesson(db_session)
    if with_quiz:
        publish_demo_quiz(db_session)
    return db_session.scalar(select(Lesson.id).order_by(Lesson.id))


def _login(client, email: str = "student@example.com") -> int:
    response = register(client, email=email)
    if response.status_code == 409:
        response = login(client, email=email)
    assert response.status_code in (200, 201)
    return response.json()["id"]


def _quiz_questions(db_session) -> list[QuizQuestion]:
    return list(
        db_session.scalars(
            select(QuizQuestion)
            .order_by(QuizQuestion.position)
            .options(selectinload(QuizQuestion.options))
        )
    )


def _answers(db_session, *, wrong_first: int = 0) -> list[dict[str, object]]:
    answers = []
    for index, question in enumerate(_quiz_questions(db_session)):
        if index < wrong_first:
            option = next(item for item in question.options if not item.is_correct)
            answers.append({"question_id": question.id, "option_ids": [option.id]})
        else:
            answers.append(
                {
                    "question_id": question.id,
                    "option_ids": [item.id for item in question.options if item.is_correct],
                }
            )
    return answers


# --- Конспект --------------------------------------------------------------------


def test_note_can_be_empty_saved_and_updated(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    empty = api_client.get(f"/api/v1/lessons/{lesson_id}/note")
    assert empty.status_code == 200
    assert empty.json() == {"lesson_id": lesson_id, "content": "", "updated_at": None}

    saved = api_client.put(
        f"/api/v1/lessons/{lesson_id}/note", json={"content": "Команда — это роли."}
    )
    assert saved.status_code == 200
    assert saved.json()["content"] == "Команда — это роли."
    assert saved.json()["updated_at"] is not None

    cleared = api_client.put(f"/api/v1/lessons/{lesson_id}/note", json={"content": ""})
    assert cleared.json()["content"] == ""
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/note").json()["content"] == ""


def test_note_is_private_and_requires_published_lesson(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    api_client.put(f"/api/v1/lessons/{lesson_id}/note", json={"content": "Моё"})
    api_client.cookies.clear()

    _login(api_client, email="second@example.com")
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/note").json()["content"] == ""

    draft_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id.desc()))
    assert api_client.get(f"/api/v1/lessons/{draft_id}/note").status_code == 404
    assert (
        api_client.put(f"/api/v1/lessons/{draft_id}/note", json={"content": "Нельзя"}).status_code
        == 404
    )


def test_note_too_long_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    response = api_client.put(f"/api/v1/lessons/{lesson_id}/note", json={"content": "x" * 20_001})

    assert response.status_code == 422


# --- Выделения -------------------------------------------------------------------


def test_highlights_are_added_listed_and_deleted(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    created = api_client.post(
        f"/api/v1/lessons/{lesson_id}/highlights", json={"text": "Команда — это роли"}
    )
    assert created.status_code == 201
    highlight_id = created.json()["id"]

    listed = api_client.get(f"/api/v1/lessons/{lesson_id}/highlights").json()
    assert [item["text"] for item in listed] == ["Команда — это роли"]

    api_client.cookies.clear()
    _login(api_client, email="second@example.com")
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/highlights").json() == []
    assert api_client.delete(f"/api/v1/highlights/{highlight_id}").status_code == 404

    api_client.cookies.clear()
    _login(api_client)
    assert api_client.delete(f"/api/v1/highlights/{highlight_id}").status_code == 204
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/highlights").json() == []


def test_blank_highlight_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    response = api_client.post(f"/api/v1/lessons/{lesson_id}/highlights", json={"text": "   "})

    assert response.status_code == 422


# --- Сложные вопросы -------------------------------------------------------------


def test_saved_questions_crud_and_privacy(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    created = api_client.post(
        "/api/v1/saved-questions",
        json={"text": "Чем нагрузочное отличается от функционального?", "lesson_id": lesson_id},
    )
    assert created.status_code == 201
    question_id = created.json()["id"]
    assert created.json()["is_resolved"] is False

    resolved = api_client.patch(
        f"/api/v1/saved-questions/{question_id}", json={"is_resolved": True}
    )
    assert resolved.json()["is_resolved"] is True
    assert [item["id"] for item in api_client.get("/api/v1/saved-questions").json()] == [
        question_id
    ]

    api_client.cookies.clear()
    _login(api_client, email="second@example.com")
    assert api_client.get("/api/v1/saved-questions").json() == []
    assert (
        api_client.patch(
            f"/api/v1/saved-questions/{question_id}", json={"is_resolved": False}
        ).status_code
        == 404
    )
    assert api_client.delete(f"/api/v1/saved-questions/{question_id}").status_code == 404

    api_client.cookies.clear()
    _login(api_client)
    assert api_client.delete(f"/api/v1/saved-questions/{question_id}").status_code == 204


def test_saved_question_with_draft_lesson_is_rejected(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    draft_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id.desc()))

    response = api_client.post(
        "/api/v1/saved-questions", json={"text": "Вопрос", "lesson_id": draft_id}
    )

    assert response.status_code == 404


# --- Список повторения -----------------------------------------------------------


def test_review_items_crud_and_privacy(api_client, db_session):
    _prepare(db_session)
    _login(api_client)

    created = api_client.post("/api/v1/review-items", json={"title": "Повторить роли в команде"})
    assert created.status_code == 201
    item_id = created.json()["id"]

    done = api_client.patch(f"/api/v1/review-items/{item_id}", json={"is_done": True})
    assert done.json()["is_done"] is True
    assert len(api_client.get("/api/v1/review-items").json()) == 1

    api_client.cookies.clear()
    _login(api_client, email="second@example.com")
    assert api_client.get("/api/v1/review-items").json() == []
    assert (
        api_client.patch(f"/api/v1/review-items/{item_id}", json={"is_done": False}).status_code
        == 404
    )
    assert api_client.delete(f"/api/v1/review-items/{item_id}").status_code == 404


# --- Шпаргалки -------------------------------------------------------------------


def test_cheatsheets_crud_and_privacy(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    created = api_client.post(
        "/api/v1/cheatsheets",
        json={
            "title": "Роли команды",
            "content": "Аналитик — требования, разработчик — код.",
            "lesson_id": lesson_id,
        },
    )
    assert created.status_code == 201
    cheatsheet_id = created.json()["id"]

    updated = api_client.patch(
        f"/api/v1/cheatsheets/{cheatsheet_id}",
        json={"title": "Роли", "content": "Коротко."},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Роли"

    api_client.cookies.clear()
    _login(api_client, email="second@example.com")
    assert api_client.get("/api/v1/cheatsheets").json() == []
    assert (
        api_client.patch(
            f"/api/v1/cheatsheets/{cheatsheet_id}", json={"title": "Чужая"}
        ).status_code
        == 404
    )
    assert api_client.delete(f"/api/v1/cheatsheets/{cheatsheet_id}").status_code == 404


# --- Слабые темы -----------------------------------------------------------------


def test_weak_topics_appear_and_disappear_after_retry(api_client, db_session):
    lesson_id = _prepare(db_session, with_quiz=True)
    _login(api_client)

    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _answers(db_session, wrong_first=10)},
    )
    weak = api_client.get("/api/v1/users/me/weak-topics").json()
    assert len(weak) == 1
    assert weak[0]["lesson_id"] == lesson_id
    assert weak[0]["best_percent"] == 0
    assert weak[0]["attempts"] == 1

    # Вторая попытка 9 из 10 поднимает лучший результат до 90 — тема не слабая.
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _answers(db_session, wrong_first=1)},
    )
    assert api_client.get("/api/v1/users/me/weak-topics").json() == []


def test_weak_topics_are_empty_without_attempts(api_client, db_session):
    _prepare(db_session, with_quiz=True)
    _login(api_client)

    assert api_client.get("/api/v1/users/me/weak-topics").json() == []


def test_tools_require_login(api_client, db_session):
    lesson_id = _prepare(db_session)
    api_client.cookies.clear()

    assert api_client.get(f"/api/v1/lessons/{lesson_id}/note").status_code == 401
    assert api_client.get("/api/v1/saved-questions").status_code == 401
    assert api_client.get("/api/v1/review-items").status_code == 401
    assert api_client.get("/api/v1/cheatsheets").status_code == 401
    assert api_client.get("/api/v1/users/me/weak-topics").status_code == 401


def test_tools_guest_cannot_change_data_and_foreign_origin_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    api_client.cookies.clear()

    # Без входа, но с разрешённым Origin: CSRF проходит, прав нет.
    assert (
        api_client.put(f"/api/v1/lessons/{lesson_id}/note", json={"content": "нельзя"}).status_code
        == 401
    )
    assert api_client.post("/api/v1/review-items", json={"title": "нельзя"}).status_code == 401

    _login(api_client)
    foreign = {"Origin": "https://evil.example"}
    assert (
        api_client.put(
            f"/api/v1/lessons/{lesson_id}/note",
            json={"content": "нельзя"},
            headers=foreign,
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            "/api/v1/cheatsheets",
            json={"title": "Чужая", "content": "Текст"},
            headers=foreign,
        ).status_code
        == 403
    )


def test_empty_and_invalid_values_are_rejected(api_client, db_session):
    _prepare(db_session)
    _login(api_client)

    assert api_client.post("/api/v1/review-items", json={"title": "   "}).status_code == 422
    assert api_client.post("/api/v1/saved-questions", json={"text": "x" * 2_001}).status_code == 422
    assert (
        api_client.post(
            "/api/v1/cheatsheets", json={"title": "   ", "content": "Текст"}
        ).status_code
        == 422
    )
    created = api_client.post(
        "/api/v1/cheatsheets", json={"title": "Тема", "content": "Текст"}
    ).json()
    assert (
        api_client.patch(f"/api/v1/cheatsheets/{created['id']}", json={"title": "   "}).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/v1/saved-questions", json={"text": "Вопрос", "lesson_id": "abc"}
        ).status_code
        == 422
    )
    assert (
        api_client.post("/api/v1/review-items", json={"title": "Тема", "lesson_id": 0}).status_code
        == 404
    )


def test_partial_cheatsheet_update_and_owner_delete(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    created = api_client.post(
        "/api/v1/cheatsheets", json={"title": "Тема", "content": "Полный текст"}
    ).json()

    only_title = api_client.patch(
        f"/api/v1/cheatsheets/{created['id']}", json={"title": "Новое название"}
    ).json()
    assert only_title["title"] == "Новое название"
    assert only_title["content"] == "Полный текст"

    only_content = api_client.patch(
        f"/api/v1/cheatsheets/{created['id']}", json={"content": "Новый текст"}
    ).json()
    assert only_content["content"] == "Новый текст"

    assert api_client.delete(f"/api/v1/cheatsheets/{created['id']}").status_code == 204
    assert api_client.get("/api/v1/cheatsheets").json() == []


def test_lesson_deletion_keeps_personal_items_but_removes_notes(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    api_client.put(f"/api/v1/lessons/{lesson_id}/note", json={"content": "Конспект"})
    api_client.post(f"/api/v1/lessons/{lesson_id}/highlights", json={"text": "Фраза"})
    api_client.post("/api/v1/saved-questions", json={"text": "Вопрос", "lesson_id": lesson_id})
    api_client.post("/api/v1/review-items", json={"title": "Повторить", "lesson_id": lesson_id})
    api_client.post(
        "/api/v1/cheatsheets",
        json={"title": "Шпаргалка", "content": "Текст", "lesson_id": lesson_id},
    )

    db_session.execute(delete(Lesson).where(Lesson.id == lesson_id))
    db_session.flush()

    assert db_session.scalar(select(func.count()).select_from(LessonNote)) == 0
    assert db_session.scalar(select(func.count()).select_from(LessonHighlight)) == 0
    # Вопросы, повторение и шпаргалки остаются, но без ссылки на урок.
    for model in (SavedQuestion, ReviewItem, Cheatsheet):
        item = db_session.scalar(select(model))
        assert item is not None
        assert item.lesson_id is None


def test_user_deletion_removes_all_personal_items(db_session):
    _prepare(db_session)
    user = User(email="delete-me@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    db_session.add_all(
        [
            LessonNote(user_id=user.id, lesson_id=db_session.scalar(select(Lesson.id))),
            LessonHighlight(
                user_id=user.id, lesson_id=db_session.scalar(select(Lesson.id)), text="x"
            ),
            SavedQuestion(user_id=user.id, text="Вопрос"),
            ReviewItem(user_id=user.id, title="Тема"),
            Cheatsheet(user_id=user.id, title="Шпаргалка", content="Текст"),
        ]
    )
    db_session.flush()

    db_session.execute(delete(User).where(User.id == user.id))
    db_session.flush()

    for model in (LessonNote, LessonHighlight, SavedQuestion, ReviewItem, Cheatsheet):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0


def test_weak_topics_are_private_and_ignore_drafts(api_client, db_session):
    lesson_id = _prepare(db_session, with_quiz=True)
    _login(api_client)
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _answers(db_session, wrong_first=10)},
    )
    assert len(api_client.get("/api/v1/users/me/weak-topics").json()) == 1

    api_client.cookies.clear()
    _login(api_client, email="second@example.com")
    assert api_client.get("/api/v1/users/me/weak-topics").json() == []

    api_client.cookies.clear()
    _login(api_client)
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=False))
    assert api_client.get("/api/v1/users/me/weak-topics").json() == []

    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=True))
    db_session.execute(update(Quiz).values(is_published=False))
    assert api_client.get("/api/v1/users/me/weak-topics").json() == []
