import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Course, Lesson, LessonBlock, Module, User


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def _create_course_tree(session: Session) -> Course:
    """Курс с одним модулем, одним уроком и двумя блоками."""
    course = Course(slug="test-course", title="Тестовый курс")
    module = Module(title="Модуль 1", position=1)
    lesson = Lesson(title="Урок 1", position=1)
    lesson.blocks = [
        LessonBlock(type="heading", content={"text": "Заголовок"}, position=1),
        LessonBlock(type="text", content={"text": "Текст урока"}, position=2),
    ]
    module.lessons = [lesson]
    course.modules = [module]
    session.add(course)
    session.flush()
    return course


def test_course_tree_is_readable_through_relationships(db_session):
    course_id = _create_course_tree(db_session).id
    # Сбрасываем кэш сессии, чтобы данные заново читались из базы.
    db_session.expire_all()

    course = db_session.get(Course, course_id)
    module = course.modules[0]
    lesson = module.lessons[0]

    assert module.course is course
    assert lesson.module is module
    assert [block.type for block in lesson.blocks] == ["heading", "text"]
    assert lesson.blocks[1].content == {"text": "Текст урока"}
    assert lesson.blocks[0].lesson is lesson


def test_database_defaults_are_applied(db_session):
    course = _create_course_tree(db_session)
    user = User(email="student@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    db_session.expire_all()

    lesson = course.modules[0].lessons[0]
    assert course.is_published is False
    assert lesson.is_published is False
    assert lesson.estimated_minutes == 90
    assert user.role == "student"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


def test_deleting_course_cascades_to_children(db_session):
    course = _create_course_tree(db_session)

    db_session.delete(course)
    db_session.flush()

    assert _count(db_session, Course) == 0
    assert _count(db_session, Module) == 0
    assert _count(db_session, Lesson) == 0
    assert _count(db_session, LessonBlock) == 0


def test_duplicate_email_is_rejected(db_session):
    db_session.add(User(email="same@example.com", password_hash="hash"))
    db_session.flush()

    db_session.add(User(email="same@example.com", password_hash="other"))
    with pytest.raises(IntegrityError, match="uq_users_email"):
        db_session.flush()


def test_unknown_user_role_is_rejected(db_session):
    db_session.add(User(email="boss@example.com", password_hash="hash", role="superuser"))
    with pytest.raises(IntegrityError, match="ck_users_role"):
        db_session.flush()


def test_duplicate_lesson_position_in_module_is_rejected(db_session):
    module = _create_course_tree(db_session).modules[0]

    db_session.add(Lesson(module_id=module.id, title="Второй урок на том же месте", position=1))
    with pytest.raises(IntegrityError, match="uq_lessons_module_id_position"):
        db_session.flush()


def test_unknown_block_type_is_rejected(db_session):
    lesson = _create_course_tree(db_session).modules[0].lessons[0]

    db_session.add(LessonBlock(lesson_id=lesson.id, type="video", content={}, position=3))
    with pytest.raises(IntegrityError, match="ck_lesson_blocks_type"):
        db_session.flush()
