"""Каталог курса, урок и прогресс ученика."""

from sqlalchemy import delete, event, func, select, update

from app.db.demo_lesson import DEMO_LESSON_BLOCKS, publish_demo_lesson
from app.db.seed import seed_curriculum
from app.models import Course, Lesson, LessonProgress, Module, User
from app.services import course_service
from tests.api.helpers import register


def _prepare_course(db_session, *, published: bool = True) -> None:
    """Структура курса и, по умолчанию, опубликованный демонстрационный урок."""
    seed_curriculum(db_session)
    if published:
        publish_demo_lesson(db_session)


def _demo_lesson_id(db_session) -> int:
    return db_session.scalar(select(Lesson.id).order_by(Lesson.id))


def _publish_first_lessons(db_session, count: int) -> list[int]:
    """Публикует первые уроки программы и возвращает их id по порядку."""
    ids = list(
        db_session.scalars(
            select(Lesson.id).join(Module).order_by(Module.position, Lesson.position).limit(count)
        )
    )
    db_session.execute(update(Lesson).where(Lesson.id.in_(ids)).values(is_published=True))
    return ids


def _login(client, email: str = "student@example.com") -> int:
    response = register(client, email=email)
    assert response.status_code == 201
    return response.json()["id"]


def _progress_count(db_session, user_id: int, lesson_id: int) -> int:
    return db_session.scalar(
        select(func.count())
        .select_from(LessonProgress)
        .where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id)
    )


# --- Каталог курса ---------------------------------------------------------------


def test_guest_sees_the_published_program_without_progress(api_client, db_session):
    _prepare_course(db_session)

    response = api_client.get("/api/v1/courses/current")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "load-testing"
    assert len(body["modules"]) == 9
    # Гость видит программу, но не личный прогресс.
    assert body["progress"] is None
    lessons = [lesson for module in body["modules"] for lesson in module["lessons"]]
    # Опубликован только демонстрационный урок: черновики не утекают.
    assert len(lessons) == 1
    assert lessons[0]["is_completed"] is False


def test_unpublished_course_is_not_shown(api_client, db_session):
    _prepare_course(db_session, published=False)

    assert api_client.get("/api/v1/courses/current").status_code == 404


def test_signed_in_student_sees_empty_progress(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    body = api_client.get("/api/v1/courses/current").json()

    assert body["progress"] == {
        "completed_lessons": 0,
        "total_lessons": 1,
        "percent": 0,
        "next_lesson_id": lesson_id,
        "last_completed_lesson_id": None,
    }


# --- Урок ------------------------------------------------------------------------


def test_guest_cannot_open_a_lesson(api_client, db_session):
    _prepare_course(db_session)
    lesson_id = _demo_lesson_id(db_session)

    assert api_client.get(f"/api/v1/lessons/{lesson_id}").status_code == 401


def test_student_opens_the_lesson_with_all_methodology_sections(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    response = api_client.get(f"/api/v1/lessons/{lesson_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["is_completed"] is False
    assert len(body["blocks"]) == len(DEMO_LESSON_BLOCKS) == 14
    # В уроке использованы все семь типов блоков.
    assert {block["type"] for block in body["blocks"]} == {
        "heading",
        "text",
        "code",
        "callout",
        "image",
        "table",
        "list",
    }
    assert body["blocks"][0]["position"] == 1
    # Заголовок первого блока — подзаголовок темы, а не повтор названия урока.
    assert body["blocks"][0]["content"]["text"]
    assert body["blocks"][0]["content"]["text"] != body["title"]


def test_unknown_and_draft_lessons_are_hidden(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    draft_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id.desc()))

    assert api_client.get("/api/v1/lessons/999999").status_code == 404
    assert api_client.get(f"/api/v1/lessons/{draft_id}").status_code == 404
    assert api_client.post(f"/api/v1/lessons/{draft_id}/complete").status_code == 404


# --- Отметка «пройден» -----------------------------------------------------------


def test_marking_lesson_completed_changes_progress(api_client, db_session):
    _prepare_course(db_session)
    user_id = _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 204

    lesson = api_client.get(f"/api/v1/lessons/{lesson_id}").json()
    assert lesson["is_completed"] is True
    progress = api_client.get("/api/v1/courses/current").json()["progress"]
    assert progress["completed_lessons"] == 1
    assert progress["percent"] == 100
    assert progress["next_lesson_id"] is None
    assert progress["last_completed_lesson_id"] == lesson_id
    assert _progress_count(db_session, user_id, lesson_id) == 1


def test_mark_is_idempotent_and_can_be_undone(api_client, db_session):
    _prepare_course(db_session)
    user_id = _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 204
    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 204
    assert _progress_count(db_session, user_id, lesson_id) == 1

    assert api_client.delete(f"/api/v1/lessons/{lesson_id}/complete").status_code == 204
    assert _progress_count(db_session, user_id, lesson_id) == 0
    # Повторное снятие отметки — тоже успешный, но ничего не меняющий запрос.
    assert api_client.delete(f"/api/v1/lessons/{lesson_id}/complete").status_code == 204
    assert api_client.get("/api/v1/courses/current").json()["progress"]["completed_lessons"] == 0


def test_progress_of_one_student_is_invisible_to_another(api_client, db_session):
    _prepare_course(db_session)
    first_user_id = _login(api_client)
    lesson_id = _demo_lesson_id(db_session)
    api_client.post(f"/api/v1/lessons/{lesson_id}/complete")
    api_client.cookies.clear()

    second_user_id = _login(api_client, email="second@example.com")

    assert second_user_id != first_user_id
    progress = api_client.get("/api/v1/courses/current").json()["progress"]
    assert progress["completed_lessons"] == 0
    assert api_client.get(f"/api/v1/lessons/{lesson_id}").json()["is_completed"] is False
    assert _progress_count(db_session, first_user_id, lesson_id) == 1


def test_completion_is_rejected_for_a_draft_lesson(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    lesson_id = _demo_lesson_id(db_session)
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=False))

    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 404


def test_guest_cannot_change_progress(api_client, db_session):
    _prepare_course(db_session)
    lesson_id = _demo_lesson_id(db_session)
    api_client.cookies.clear()

    # Origin разрешён, поэтому проверка CSRF проходит, а вход — нет.
    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 401
    assert api_client.delete(f"/api/v1/lessons/{lesson_id}/complete").status_code == 401


def test_completion_requires_allowed_origin(api_client, db_session):
    _prepare_course(db_session)
    user_id = _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    # Чужой Origin подделывает запрос с постороннего сайта — 403.
    foreign = {"Origin": "https://evil.example"}
    assert (
        api_client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=foreign).status_code == 403
    )
    assert (
        api_client.delete(f"/api/v1/lessons/{lesson_id}/complete", headers=foreign).status_code
        == 403
    )
    assert _progress_count(db_session, user_id, lesson_id) == 0


def test_lesson_of_unpublished_course_is_hidden(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    lesson_id = _demo_lesson_id(db_session)
    db_session.execute(update(Course).values(is_published=False))

    assert api_client.get(f"/api/v1/lessons/{lesson_id}").status_code == 404
    assert api_client.post(f"/api/v1/lessons/{lesson_id}/complete").status_code == 404


def test_invalid_lesson_id_is_rejected(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)

    # Не число — ошибка формы запроса, а не поиск урока.
    assert api_client.get("/api/v1/lessons/abc").status_code == 422
    assert api_client.get("/api/v1/lessons/0").status_code == 404
    assert api_client.get("/api/v1/lessons/-5").status_code == 404


def test_published_lesson_without_blocks_is_returned_empty(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    draft_id = db_session.scalar(
        select(Lesson.id).join(Module).where(Module.position == 2, Lesson.position == 1)
    )
    db_session.execute(update(Lesson).where(Lesson.id == draft_id).values(is_published=True))

    body = api_client.get(f"/api/v1/lessons/{draft_id}").json()

    assert body["blocks"] == []


def test_percent_and_next_lesson_are_counted_across_several_lessons(api_client, db_session):
    _prepare_course(db_session)
    _login(api_client)
    lesson_ids = _publish_first_lessons(db_session, count=3)

    assert api_client.post(f"/api/v1/lessons/{lesson_ids[0]}/complete").status_code == 204

    progress = api_client.get("/api/v1/courses/current").json()["progress"]
    # 1 из 3 — 33 % после округления.
    assert progress["completed_lessons"] == 1
    assert progress["total_lessons"] == 3
    assert progress["percent"] == 33
    assert progress["next_lesson_id"] == lesson_ids[1]
    assert progress["last_completed_lesson_id"] == lesson_ids[0]


def test_overview_uses_a_fixed_number_of_queries(api_client, db_session):
    """Каталог не должен делать запрос на каждый урок (проблема N+1)."""
    _prepare_course(db_session)
    _publish_first_lessons(db_session, count=8)
    user = User(email="queries@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()

    statements: list[str] = []

    def before_cursor_execute(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", before_cursor_execute)
    try:
        course_service.get_course_overview(db_session, user.id)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", before_cursor_execute)

    selects = [
        statement for statement in statements if statement.lstrip().upper().startswith("SELECT")
    ]
    # Курс, модули, уроки, прогресс — независимо от числа уроков.
    assert len(selects) <= 4


def test_two_simultaneous_marks_create_one_row(test_engine):
    """Два перекрывающихся запроса не создают дубль и не падают.

    Первое соединение вставляет отметку и держит транзакцию открытой, второе
    в это время пытается вставить ту же пару и ждёт на уникальном индексе.
    После коммита первого второй получает «конфликт — ничего не делать».
    Проверяется именно ожидание: второй поток обязан быть жив до коммита.
    """
    import time
    from threading import Event, Thread

    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.orm import Session

    course = Course(slug="concurrency-test", title="Проверка гонки")
    module = Module(title="Модуль", position=1)
    lesson = Lesson(title="Урок", position=1)
    module.lessons = [lesson]
    course.modules = [module]
    user = User(email="race@example.com", password_hash="hash")

    with Session(test_engine, expire_on_commit=False) as setup:
        setup.add_all([course, user])
        setup.commit()
        course_id, lesson_id, user_id = course.id, lesson.id, user.id

    def statement():
        return (
            insert(LessonProgress)
            .values(user_id=user_id, lesson_id=lesson_id)
            .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
        )

    first_inserted = Event()
    allow_commit = Event()
    errors: list[BaseException] = []

    def first_writer() -> None:
        try:
            with Session(test_engine) as session:
                session.execute(statement())
                first_inserted.set()
                if not allow_commit.wait(10):
                    raise RuntimeError("первое соединение не дождалось коммита")
                session.commit()
        except BaseException as error:  # noqa: BLE001 — ошибку проверяем в основном потоке
            errors.append(error)
            first_inserted.set()

    def second_writer() -> None:
        try:
            with Session(test_engine) as session:
                session.execute(statement())
                session.commit()
        except BaseException as error:  # noqa: BLE001
            errors.append(error)

    try:
        first = Thread(target=first_writer)
        first.start()
        assert first_inserted.wait(10)

        second = Thread(target=second_writer)
        second.start()
        # Второй поток должен упереться в незакоммиченную строку и ждать.
        time.sleep(0.5)
        assert second.is_alive(), "второй запрос не столкнулся с блокировкой"

        allow_commit.set()
        first.join(10)
        second.join(10)
        assert not first.is_alive() and not second.is_alive()
        assert errors == []

        with Session(test_engine) as check:
            assert (
                check.scalar(
                    select(func.count())
                    .select_from(LessonProgress)
                    .where(
                        LessonProgress.user_id == user_id,
                        LessonProgress.lesson_id == lesson_id,
                    )
                )
                == 1
            )
    finally:
        allow_commit.set()
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Course).where(Course.id == course_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()


def test_stale_client_session_is_rejected(api_client, db_session):
    """Старый экран не должен писать в аккаунт, в который уже вошли в другой вкладке."""
    _prepare_course(db_session)
    user_id = _login(api_client)
    lesson_id = _demo_lesson_id(db_session)

    stale = {"X-LoadLab-User": str(user_id + 1)}
    response = api_client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=stale)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

    current = {"X-LoadLab-User": str(user_id)}
    assert (
        api_client.post(f"/api/v1/lessons/{lesson_id}/complete", headers=current).status_code == 204
    )


def test_progress_is_removed_with_the_user(db_session):
    """При удалении ученика удаляются только его отметки, чужие остаются."""
    _prepare_course(db_session)
    lesson_id = _demo_lesson_id(db_session)
    removed = User(email="cascade-user@example.com", password_hash="hash")
    kept = User(email="kept-user@example.com", password_hash="hash")
    db_session.add_all([removed, kept])
    db_session.flush()
    db_session.add_all(
        [
            LessonProgress(user_id=removed.id, lesson_id=lesson_id),
            LessonProgress(user_id=kept.id, lesson_id=lesson_id),
        ]
    )
    db_session.flush()

    db_session.execute(delete(User).where(User.id == removed.id))
    db_session.flush()

    remaining = list(db_session.scalars(select(LessonProgress.user_id)))
    assert remaining == [kept.id]


def test_progress_is_removed_with_the_course(db_session):
    """Удаление курса убирает только его отметки.

    Удаление идёт средствами SQL, минуя ORM, — так проверяется ON DELETE CASCADE
    в самой базе, а не поведение Python-сессий. Отметка другого курса остаётся.
    """
    _prepare_course(db_session)
    lesson_id = _demo_lesson_id(db_session)
    other_course = Course(slug="other-course", title="Другой курс")
    other_lesson = Lesson(title="Чужой урок", position=1)
    other_course.modules = [Module(title="Модуль", position=1, lessons=[other_lesson])]
    user = User(email="cascade@example.com", password_hash="hash")
    db_session.add_all([other_course, user])
    db_session.flush()
    db_session.add_all(
        [
            LessonProgress(user_id=user.id, lesson_id=lesson_id),
            LessonProgress(user_id=user.id, lesson_id=other_lesson.id),
        ]
    )
    db_session.flush()

    db_session.execute(delete(Course).where(Course.slug == "load-testing"))
    db_session.flush()

    remaining = list(db_session.scalars(select(LessonProgress.lesson_id)))
    assert remaining == [other_lesson.id]
    assert db_session.get(Lesson, lesson_id) is None
    assert db_session.get(Lesson, other_lesson.id) is not None
