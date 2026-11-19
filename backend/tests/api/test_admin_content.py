"""Административное управление программой и прогрессом учеников."""

from sqlalchemy import select, update

from app.db.seed import seed_curriculum
from app.models import (
    Course,
    Lesson,
    LessonProgress,
    Module,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    User,
)
from tests.api.helpers import register


def _admin(api_client, db_session) -> None:
    response = register(api_client, email="admin@example.com")
    assert response.status_code == 201
    db_session.execute(update(User).where(User.email == "admin@example.com").values(role="admin"))


def _course_id(db_session) -> int:
    return db_session.scalar(select(Course.id).where(Course.slug == "load-testing"))


def test_admin_routes_require_admin(api_client):
    assert api_client.get("/api/v1/admin/courses").status_code == 401

    register(api_client)
    assert api_client.get("/api/v1/admin/courses").status_code == 403
    assert api_client.get("/api/v1/admin/students").status_code == 403


def test_admin_creates_course_module_and_lesson(api_client, db_session):
    _admin(api_client, db_session)

    course = api_client.post(
        "/api/v1/admin/courses",
        json={"slug": "new-course", "title": "Новый курс", "description": "Описание"},
    )
    assert course.status_code == 201
    course_id = course.json()["id"]

    module = api_client.post(
        f"/api/v1/admin/courses/{course_id}/modules",
        json={"title": "Модуль 1", "summary": "Кратко"},
    )
    assert module.status_code == 201
    assert module.json()["position"] == 1

    lesson = api_client.post(
        f"/api/v1/admin/modules/{module.json()['id']}/lessons",
        json={"title": "Урок 1", "estimated_minutes": 45},
    )
    assert lesson.status_code == 201
    assert lesson.json()["position"] == 1
    assert lesson.json()["is_published"] is False

    tree = api_client.get(f"/api/v1/admin/courses/{course_id}").json()
    assert tree["module_count"] == 1
    assert tree["lesson_count"] == 1
    assert tree["modules"][0]["lessons"][0]["title"] == "Урок 1"


def test_admin_publishes_lesson_blocks_and_quiz(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    course_id = _course_id(db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))

    assert (
        api_client.patch(
            f"/api/v1/admin/courses/{course_id}", json={"is_published": True}
        ).status_code
        == 200
    )
    published = api_client.patch(f"/api/v1/admin/lessons/{lesson_id}", json={"is_published": True})
    assert published.status_code == 200
    assert published.json()["is_published"] is True

    blocks = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/blocks",
        json={
            "blocks": [
                {"type": "heading", "content": {"text": "Заголовок"}},
                {"type": "text", "content": {"text": "Текст урока"}},
            ]
        },
    )
    assert blocks.status_code == 200
    assert [block["type"] for block in blocks.json()["blocks"]] == ["heading", "text"]

    quiz = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/quiz",
        json={
            "title": "Проверка",
            "description": "Один вопрос",
            "is_published": True,
            "questions": [
                {
                    "kind": "theory",
                    "text": "Вопрос?",
                    "explanation": "Потому что так.",
                    "options": [
                        {"text": "Верно", "is_correct": True},
                        {"text": "Неверно", "is_correct": False},
                    ],
                }
            ],
        },
    )
    assert quiz.status_code == 200
    assert quiz.json()["questions"][0]["options"][0]["is_correct"] is True

    # Публичный урок и квиз видны ученику (в тесте роль администратора тоже подходит).
    public_lesson = api_client.get(f"/api/v1/lessons/{lesson_id}")
    assert public_lesson.status_code == 200
    assert public_lesson.json()["title"]
    public_quiz = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz")
    assert public_quiz.status_code == 200


def test_admin_rejects_invalid_blocks_and_quiz(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))

    bad_block = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/blocks",
        json={"blocks": [{"type": "video", "content": {}}]},
    )
    assert bad_block.status_code == 422

    no_correct = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/quiz",
        json={
            "title": "Плохой квиз",
            "questions": [
                {
                    "kind": "theory",
                    "text": "Вопрос?",
                    "explanation": "Нет верного",
                    "options": [
                        {"text": "А", "is_correct": False},
                        {"text": "Б", "is_correct": False},
                    ],
                }
            ],
        },
    )
    assert no_correct.status_code == 422

    one_option = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/quiz",
        json={
            "title": "Плохой квиз",
            "questions": [
                {
                    "kind": "theory",
                    "text": "Вопрос?",
                    "explanation": "Один вариант",
                    "options": [{"text": "А", "is_correct": True}],
                }
            ],
        },
    )
    assert one_option.status_code == 422


def test_admin_position_conflict(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))

    created = api_client.post(
        f"/api/v1/admin/modules/{module_id}/lessons", json={"title": "Ещё урок"}
    )
    assert created.status_code == 201
    lesson_id = created.json()["id"]

    conflict = api_client.patch(f"/api/v1/admin/lessons/{lesson_id}", json={"position": 1})
    assert conflict.status_code == 409


def test_admin_sees_student_progress(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    course_id = _course_id(db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    db_session.execute(update(Course).where(Course.id == course_id).values(is_published=True))
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=True))

    student = User(email="student-progress@example.com", password_hash="hash")
    db_session.add(student)
    db_session.flush()
    db_session.add(LessonProgress(user_id=student.id, lesson_id=lesson_id))
    db_session.flush()

    listing = api_client.get("/api/v1/admin/students")
    assert listing.status_code == 200
    row = next(item for item in listing.json() if item["email"] == student.email)
    assert row["completed_lessons"] == 1
    assert row["total_lessons"] == 1
    assert row["percent"] == 100

    detail = api_client.get(f"/api/v1/admin/students/{student.id}")
    assert detail.status_code == 200
    assert detail.json()["modules"][0]["completed"] == 1


def test_admin_quiz_save_requires_confirmation_when_attempts_exist(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    payload = {
        "title": "Квиз",
        "is_published": True,
        "questions": [
            {
                "kind": "theory",
                "text": "Вопрос?",
                "explanation": "Потому что так.",
                "options": [
                    {"text": "Верно", "is_correct": True},
                    {"text": "Неверно", "is_correct": False},
                ],
            }
        ],
    }
    assert (
        api_client.put(f"/api/v1/admin/lessons/{lesson_id}/quiz", json=payload).status_code == 200
    )

    question_id = db_session.scalar(select(QuizQuestion.id))
    option_id = db_session.scalar(
        select(QuizOption.id).where(
            QuizOption.question_id == question_id, QuizOption.is_correct.is_(True)
        )
    )
    db_session.execute(
        update(Course).where(Course.id == _course_id(db_session)).values(is_published=True)
    )
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=True))
    attempt = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": [{"question_id": question_id, "option_ids": [option_id]}]},
    )
    assert attempt.status_code == 201
    assert db_session.scalar(select(QuizAttempt.id)) is not None

    blocked = api_client.put(f"/api/v1/admin/lessons/{lesson_id}/quiz", json=payload)
    assert blocked.status_code == 409
    assert "попыток" in blocked.json()["error"]["message"]

    confirmed = api_client.put(
        f"/api/v1/admin/lessons/{lesson_id}/quiz",
        json={**payload, "confirm_attempts_loss": True},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["attempts_count"] == 0
    db_session.expire_all()
    assert db_session.scalar(select(QuizAttempt.id)) is None


def test_admin_can_clear_description_and_summary(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    course_id = _course_id(db_session)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    db_session.execute(update(Course).where(Course.id == course_id).values(description="Старое"))
    db_session.execute(update(Module).where(Module.id == module_id).values(summary="Старое"))
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(summary="Старое"))

    course = api_client.patch(f"/api/v1/admin/courses/{course_id}", json={"description": None})
    assert course.status_code == 200
    assert course.json()["description"] is None

    module = api_client.patch(f"/api/v1/admin/modules/{module_id}", json={"summary": None})
    assert module.status_code == 200
    assert module.json()["summary"] is None

    lesson = api_client.patch(f"/api/v1/admin/lessons/{lesson_id}", json={"summary": None})
    assert lesson.status_code == 200
    assert lesson.json()["summary"] is None


def test_admin_moves_lesson_and_handles_edge(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    lessons = list(
        db_session.scalars(
            select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.position)
        )
    )
    first, second = lessons[0], lessons[1]
    first_position = first.position
    second_position = second.position

    moved = api_client.post(f"/api/v1/admin/lessons/{second.id}/move", json={"direction": "up"})
    assert moved.status_code == 200
    assert moved.json()["position"] == first_position

    db_session.expire_all()
    first_after = db_session.get(Lesson, first.id)
    second_after = db_session.get(Lesson, second.id)
    assert second_after is not None and first_after is not None
    assert second_after.position == first_position
    assert first_after.position == second_position

    edge = api_client.post(f"/api/v1/admin/lessons/{second.id}/move", json={"direction": "up"})
    assert edge.status_code == 409


def test_admin_delete_quiz_requires_confirmation(api_client, db_session):
    seed_curriculum(db_session)
    _admin(api_client, db_session)
    course_id = _course_id(db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    payload = {
        "title": "Квиз",
        "is_published": True,
        "questions": [
            {
                "kind": "theory",
                "text": "Вопрос?",
                "explanation": "Потому что так.",
                "options": [
                    {"text": "Верно", "is_correct": True},
                    {"text": "Неверно", "is_correct": False},
                ],
            }
        ],
    }
    assert (
        api_client.put(f"/api/v1/admin/lessons/{lesson_id}/quiz", json=payload).status_code == 200
    )
    db_session.execute(update(Course).where(Course.id == course_id).values(is_published=True))
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=True))
    question_id = db_session.scalar(select(QuizQuestion.id))
    option_id = db_session.scalar(
        select(QuizOption.id).where(
            QuizOption.question_id == question_id, QuizOption.is_correct.is_(True)
        )
    )
    assert (
        api_client.post(
            f"/api/v1/lessons/{lesson_id}/quiz/attempts",
            json={"answers": [{"question_id": question_id, "option_ids": [option_id]}]},
        ).status_code
        == 201
    )

    assert api_client.delete(f"/api/v1/admin/lessons/{lesson_id}/quiz").status_code == 409
    assert (
        api_client.delete(
            f"/api/v1/admin/lessons/{lesson_id}/quiz?confirm_attempts_loss=true"
        ).status_code
        == 204
    )
    assert api_client.get(f"/api/v1/admin/lessons/{lesson_id}/quiz").json() is None


def test_admin_deletes_course_and_children(api_client, db_session):
    _admin(api_client, db_session)
    course = api_client.post(
        "/api/v1/admin/courses", json={"slug": "delete-me", "title": "Удалить"}
    ).json()
    module = api_client.post(
        f"/api/v1/admin/courses/{course['id']}/modules", json={"title": "Модуль"}
    ).json()
    api_client.post(f"/api/v1/admin/modules/{module['id']}/lessons", json={"title": "Урок"})

    assert api_client.delete(f"/api/v1/admin/courses/{course['id']}").status_code == 204
    assert db_session.scalar(select(Course.id).where(Course.slug == "delete-me")) is None
    assert api_client.get(f"/api/v1/admin/courses/{course['id']}").status_code == 404
