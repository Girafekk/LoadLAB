import pytest
from sqlalchemy import func, select

from app.db.curriculum_data import COURSE
from app.db.demo_lesson import DEMO_LESSON_BLOCKS, publish_demo_lesson
from app.db.demo_quiz import DEMO_QUIZ_QUESTIONS, publish_demo_quiz
from app.db.seed import (
    clear_demo_content,
    demo_publication_state,
    demo_quiz_publication_state,
    restore_demo_publication,
    restore_quiz_publication,
    seed_curriculum,
)
from app.models import Course, Lesson, LessonBlock, Module, Quiz


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_curriculum_data_matches_the_programme():
    assert len(COURSE.modules) == 9
    assert [len(module.lessons) for module in COURSE.modules] == [7, 8, 8, 7, 8, 8, 8, 6, 11]


def test_seed_creates_course_structure(db_session):
    result = seed_curriculum(db_session)

    assert (result.courses_created, result.modules_created, result.lessons_created) == (1, 9, 71)

    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    assert course.title == "Нагрузочное тестирование с нуля"
    assert course.is_published is False
    assert [module.position for module in course.modules] == list(range(1, 10))
    assert course.modules[0].lessons[0].title == (
        "Как делают программы: команда, роли, место тестировщика"
    )
    assert [lesson.position for lesson in course.modules[7].lessons] == list(range(1, 7))
    assert [lesson.position for lesson in course.modules[8].lessons] == list(range(1, 12))
    # Уроки создаются пустыми: контент — отдельный этап.
    assert _count(db_session, LessonBlock) == 0


def test_seed_twice_creates_no_duplicates(db_session):
    seed_curriculum(db_session)
    second = seed_curriculum(db_session)

    assert (second.courses_created, second.modules_created, second.lessons_created) == (0, 0, 0)
    assert _count(db_session, Course) == 1
    assert _count(db_session, Module) == 9
    assert _count(db_session, Lesson) == 71


def test_seed_restores_only_missing_rows(db_session):
    seed_curriculum(db_session)
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    db_session.delete(course.modules[2].lessons[4])
    db_session.flush()
    db_session.expire_all()

    result = seed_curriculum(db_session)

    assert (result.courses_created, result.modules_created, result.lessons_created) == (0, 0, 1)
    assert _count(db_session, Lesson) == 71


def test_demo_lesson_publishes_the_course_and_first_lesson(db_session):
    seed_curriculum(db_session)

    created = publish_demo_lesson(db_session)

    assert created == len(DEMO_LESSON_BLOCKS) == 14
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    assert course.is_published is True
    first_lesson = course.modules[0].lessons[0]
    assert first_lesson.is_published is True
    # Остальные уроки остаются черновиками: контент для них — этап 9.
    assert _count(db_session, LessonBlock) == 14
    assert [block.position for block in first_lesson.blocks] == list(range(1, 15))


def test_demo_lesson_is_not_duplicated_on_repeat(db_session):
    seed_curriculum(db_session)
    publish_demo_lesson(db_session)

    assert publish_demo_lesson(db_session) == 0
    assert _count(db_session, LessonBlock) == 14


def test_demo_lesson_does_not_republish_an_unpublished_lesson(db_session):
    """Повторный сид не возвращает в публикацию то, что сняли вручную."""
    seed_curriculum(db_session)
    publish_demo_lesson(db_session)
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    first_lesson = course.modules[0].lessons[0]
    course.is_published = False
    first_lesson.is_published = False
    db_session.flush()

    assert publish_demo_lesson(db_session) == 0

    db_session.expire_all()
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    assert course.is_published is False
    assert course.modules[0].lessons[0].is_published is False
    assert _count(db_session, LessonBlock) == 14


def test_demo_lesson_requires_the_course_structure(db_session):
    with pytest.raises(RuntimeError, match="Сначала загрузите структуру курса"):
        publish_demo_lesson(db_session)


def test_refresh_demo_recreates_content_and_keeps_publication(db_session):
    seed_curriculum(db_session)
    publish_demo_lesson(db_session)
    publish_demo_quiz(db_session)
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    lesson = course.modules[0].lessons[0]
    lesson.is_published = False
    db_session.flush()

    state = demo_publication_state(db_session)
    assert state == (True, False)
    quiz_state = demo_quiz_publication_state(db_session)
    assert quiz_state is True
    quiz = db_session.scalar(select(Quiz))
    quiz.is_published = False
    db_session.flush()
    quiz_state = demo_quiz_publication_state(db_session)
    assert quiz_state is False

    clear_demo_content(db_session)
    assert publish_demo_lesson(db_session) == len(DEMO_LESSON_BLOCKS)
    assert publish_demo_quiz(db_session) == len(DEMO_QUIZ_QUESTIONS)
    restore_demo_publication(db_session, state)
    restore_quiz_publication(db_session, quiz_state)
    db_session.flush()
    db_session.expire_all()

    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    lesson = course.modules[0].lessons[0]
    # Контент пересобран, но скрытые урок и квиз не опубликованы заново.
    assert lesson.is_published is False
    assert len(lesson.blocks) == len(DEMO_LESSON_BLOCKS)
    quiz = db_session.scalar(select(Quiz))
    assert quiz is not None
    assert quiz.is_published is False
