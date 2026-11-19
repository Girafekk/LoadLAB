"""Проверка учебного контента 8 недель."""

import pytest
from sqlalchemy import func, select

from app.db.content import WEEKS
from app.db.content.builder import build_blocks
from app.db.content_loader import seed_content
from app.db.curriculum_data import COURSE
from app.db.seed import seed_curriculum
from app.models import Course, Lesson, LessonBlock, Quiz, QuizQuestion


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
