from sqlalchemy import func, select

from app.db.curriculum_data import COURSE
from app.db.seed import seed_curriculum
from app.models import Course, Lesson, LessonBlock, Module


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_curriculum_data_matches_the_programme():
    assert len(COURSE.modules) == 8
    assert [len(module.lessons) for module in COURSE.modules] == [7, 8, 8, 7, 8, 8, 8, 6]


def test_seed_creates_course_structure(db_session):
    result = seed_curriculum(db_session)

    assert (result.courses_created, result.modules_created, result.lessons_created) == (1, 8, 60)

    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    assert course.title == "Нагрузочное тестирование с нуля"
    assert course.is_published is False
    assert [module.position for module in course.modules] == list(range(1, 9))
    assert course.modules[0].lessons[0].title == (
        "Как делают программы: команда, роли, место тестировщика"
    )
    assert [lesson.position for lesson in course.modules[7].lessons] == list(range(1, 7))
    # Уроки создаются пустыми: контент — отдельный этап.
    assert _count(db_session, LessonBlock) == 0


def test_seed_twice_creates_no_duplicates(db_session):
    seed_curriculum(db_session)
    second = seed_curriculum(db_session)

    assert (second.courses_created, second.modules_created, second.lessons_created) == (0, 0, 0)
    assert _count(db_session, Course) == 1
    assert _count(db_session, Module) == 8
    assert _count(db_session, Lesson) == 60


def test_seed_restores_only_missing_rows(db_session):
    seed_curriculum(db_session)
    course = db_session.scalar(select(Course).where(Course.slug == "load-testing"))
    db_session.delete(course.modules[2].lessons[4])
    db_session.flush()
    db_session.expire_all()

    result = seed_curriculum(db_session)

    assert (result.courses_created, result.modules_created, result.lessons_created) == (0, 0, 1)
    assert _count(db_session, Lesson) == 60
