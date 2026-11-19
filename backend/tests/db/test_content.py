"""Проверка учебного контента 8 недель."""

import pytest
from sqlalchemy import func, select

from app.db.content import WEEKS
from app.db.content.builder import build_blocks
from app.db.content_loader import seed_content
from app.db.curriculum_data import COURSE
from app.db.seed import seed_curriculum
from app.models import Course, Lesson, LessonBlock, Module, Quiz, QuizQuestion


def test_content_covers_all_lessons_and_quizzes():
    assert sum(len(week) for week in WEEKS.values()) == 60
    assert sum(len(module.lessons) for module in COURSE.modules) == 60

    for module, week in zip(COURSE.modules, WEEKS.values(), strict=True):
        assert len(week) == len(module.lessons)
        for data, title in zip(week, module.lessons, strict=True):
            assert data["title"] == title
            blocks = build_blocks(data)
            assert len(blocks) == 14
            assert all(block_type for block_type, _ in blocks)
            assert all(content for _, content in blocks)
            for block_type, content in blocks:
                if block_type == "table":
                    headers = content.get("headers")
                    rows = content.get("rows")
                    assert isinstance(headers, list) and headers
                    assert isinstance(rows, list) and rows
                    assert all(len(row) == len(headers) for row in rows)
                if block_type == "code":
                    assert str(content.get("code", "")).strip()
                if block_type == "list":
                    assert content.get("items")
                if block_type == "image":
                    assert str(content.get("src", "")).startswith("/lessons/")

            questions = data["questions"]
            assert len(questions) == 10
            assert {question["kind"] for question in questions} == {
                "theory",
                "situation",
                "analysis",
                "error",
                "decision",
            }
            for question in questions:
                assert question["text"].strip()
                assert question["explanation"].strip()
                options = question["options"]
                assert 4 <= len(options) <= 5
                assert len({text for text, _ in options}) == len(options)
                assert any(is_correct for _, is_correct in options)
                assert sum(1 for _, is_correct in options if is_correct) <= 3
                assert all(text.strip() and len(text) <= 500 for text, _ in options)
            positions = [
                index
                for question in questions
                for index, (_, is_correct) in enumerate(question["options"])
                if is_correct
            ]
            assert set(positions) != {0}

            text = " ".join(
                [data["theory"], data["practice"]]
                + [question["text"] for question in questions]
                + [option for question in questions for option, _ in question["options"]]
            ).lower()
            for banned in (
                "цвет кнопки",
                "погода за окном",
                "скриншот",
                "настроение",
                "расписание отпусков",
            ):
                assert banned not in text


def test_quiz_options_do_not_always_make_correct_answer_longest():
    single = [
        question
        for week in WEEKS.values()
        for lesson_data in week
        for question in lesson_data["questions"]
        if sum(1 for _, is_correct in question["options"] if is_correct) == 1
    ]
    longest_correct = sum(
        1 for question in single if max(question["options"], key=lambda option: len(option[0]))[1]
    )
    assert longest_correct / len(single) < 0.9


def test_seed_content_publishes_lessons_and_quizzes(db_session):
    seed_curriculum(db_session)
    result = seed_content(db_session)
    db_session.commit()

    assert result.lessons_filled == 60
    assert result.quizzes_created == 60
    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 60
    assert db_session.scalar(select(func.count()).select_from(LessonBlock)) == 60 * 14
    assert db_session.scalar(select(func.count()).select_from(Quiz)) == 60
    assert db_session.scalar(select(func.count()).select_from(QuizQuestion)) == 600

    course = db_session.scalar(select(Course).where(Course.slug == COURSE.slug))
    assert course is not None and course.is_published
    assert (
        db_session.scalar(
            select(func.count()).select_from(Lesson).where(Lesson.is_published.is_(False))
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Quiz).where(Quiz.is_published.is_(False))
        )
        == 0
    )


def test_seed_content_is_idempotent(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()

    second = seed_content(db_session)
    db_session.commit()

    assert second.lessons_filled == 0
    assert second.quizzes_created == 0
    assert db_session.scalar(select(func.count()).select_from(LessonBlock)) == 840


def test_loader_backfills_keys_by_title_after_reorder(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    lessons = list(
        db_session.scalars(
            select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.position)
        )
    )
    first, second = lessons[0], lessons[1]
    first_position, second_position = first.position, second.position
    first_title, second_title = first.title, second.title
    for lesson in lessons:
        lesson.content_key = None
    first.position = 0
    db_session.flush()
    second.position = first_position
    db_session.flush()
    first.position = second_position
    db_session.commit()

    seed_content(db_session)
    db_session.commit()
    db_session.expire_all()

    first_after = db_session.get(Lesson, first.id)
    second_after = db_session.get(Lesson, second.id)
    assert first_after is not None and second_after is not None
    assert first_after.title == first_title
    assert second_after.title == second_title
    assert first_after.content_key == "w1-l1"
    assert second_after.content_key == "w1-l2"


def test_refresh_keeps_quiz_publication_flag(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()
    quiz = db_session.scalar(select(Quiz).order_by(Quiz.id))
    assert quiz is not None
    quiz_id = quiz.id
    lesson_id = quiz.lesson_id
    quiz.is_published = False
    db_session.commit()

    seed_content(db_session, refresh=True, confirm_refresh=True)
    db_session.commit()
    db_session.expire_all()
    recreated = db_session.scalar(select(Quiz).where(Quiz.lesson_id == lesson_id))
    assert recreated is not None
    assert recreated.id != quiz_id
    assert recreated.is_published is False


def test_seed_content_keeps_lesson_when_moved_to_another_module(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()
    lessons = list(db_session.scalars(select(Lesson).order_by(Lesson.id)))
    first = lessons[0]
    original_title = first.title
    original_key = first.content_key
    modules = list(db_session.scalars(select(Module).order_by(Module.id)))
    destination = modules[1]
    new_position = (
        db_session.scalar(
            select(func.max(Lesson.position)).where(Lesson.module_id == destination.id)
        )
        or 0
    ) + 1
    first.module_id = destination.id
    first.position = new_position
    db_session.commit()

    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()
    db_session.expire_all()

    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 60
    moved = db_session.get(Lesson, first.id)
    assert moved is not None
    assert moved.module_id == destination.id
    assert moved.content_key == original_key
    assert moved.title == original_title
    assert moved.blocks
    assert moved.quiz is not None


def test_refresh_requires_explicit_confirmation(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()

    with pytest.raises(RuntimeError, match="--confirm"):
        seed_content(db_session, refresh=True)

    refreshed = seed_content(db_session, refresh=True, confirm_refresh=True)
    db_session.commit()
    assert refreshed.lessons_filled == 60
    assert refreshed.quizzes_created == 60


def test_seed_content_keeps_reordered_lessons_paired_and_hidden(db_session):
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()

    module = db_session.scalars(select(Lesson).order_by(Lesson.id)).first()
    assert module is not None
    first, second = list(
        db_session.scalars(
            select(Lesson).where(Lesson.module_id == module.module_id).order_by(Lesson.position)
        )
    )[:2]
    first_title = first.title
    first_position = first.position
    second_position = second.position

    first.position = 0
    db_session.flush()
    second.position = first_position
    db_session.flush()
    first.position = second_position
    first.is_published = False
    first.title = "Переименованный урок"
    db_session.flush()
    first_key = first.content_key
    quiz = db_session.scalar(select(Quiz).where(Quiz.lesson_id == first.id))
    assert quiz is not None
    quiz.is_published = False
    db_session.commit()

    blocks_before = db_session.scalar(select(func.count()).select_from(LessonBlock))
    seed_curriculum(db_session)
    result = seed_content(db_session)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(Lesson)) == 60
    assert result.lessons_filled == 0
    assert result.quizzes_created == 0
    assert db_session.scalar(select(func.count()).select_from(LessonBlock)) == blocks_before
    db_session.expire_all()
    reloaded = db_session.get(Lesson, first.id)
    assert reloaded is not None
    assert reloaded.title == "Переименованный урок"
    assert reloaded.content_key == first_key
    assert reloaded.is_published is False
    heading = next(block for block in reloaded.blocks if block.type == "heading")
    assert heading.content["text"] == first_title
    reloaded_quiz = db_session.scalar(select(Quiz).where(Quiz.lesson_id == first.id))
    assert reloaded_quiz is not None
    assert reloaded_quiz.is_published is False
    assert first_title in reloaded_quiz.title
