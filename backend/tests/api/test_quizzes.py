"""Квизы: выдача вопросов, проверка ответов и история попыток."""

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.demo_lesson import publish_demo_lesson
from app.db.demo_quiz import DEMO_QUIZ_QUESTIONS, publish_demo_quiz
from app.db.seed import seed_curriculum
from app.models import (
    Lesson,
    Module,
    Quiz,
    QuizAttempt,
    QuizAttemptAnswer,
    QuizOption,
    QuizQuestion,
    User,
    quiz_attempt_selected_options,
)
from app.services import quiz_service
from tests.api.helpers import register


def _prepare(db_session) -> int:
    """Структура курса, опубликованный демо-урок и квиз. Возвращает id урока."""
    seed_curriculum(db_session)
    publish_demo_lesson(db_session)
    publish_demo_quiz(db_session)
    return db_session.scalar(select(Lesson.id).order_by(Lesson.id))


def _login(client, email: str = "student@example.com") -> int:
    response = register(client, email=email)
    assert response.status_code == 201
    return response.json()["id"]


def _questions(db_session) -> list[QuizQuestion]:
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    quiz = db_session.scalar(select(Quiz).where(Quiz.lesson_id == lesson_id))
    return list(
        db_session.scalars(
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz.id)
            .order_by(QuizQuestion.position)
            .options(selectinload(QuizQuestion.options))
        )
    )


def _correct_answers(db_session) -> list[dict[str, object]]:
    return [
        {
            "question_id": question.id,
            "option_ids": [option.id for option in question.options if option.is_correct],
        }
        for question in _questions(db_session)
    ]


# --- Выдача квиза ----------------------------------------------------------------


def test_guest_cannot_open_quiz(api_client, db_session):
    _prepare(db_session)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))

    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").status_code == 401
    assert api_client.post(f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={}).status_code == 401


def test_student_sees_questions_without_correct_flags(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))

    response = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz")

    assert response.status_code == 200
    body = response.json()
    assert len(body["quiz"]["questions"]) == 10 == len(DEMO_QUIZ_QUESTIONS)
    assert body["attempts"] == []
    assert body["best_percent"] is None
    kinds = {question["kind"] for question in body["quiz"]["questions"]}
    assert kinds == {"theory", "situation", "analysis", "error", "decision"}
    for question in body["quiz"]["questions"]:
        assert question["options"]
        for option in question["options"]:
            assert set(option) == {"id", "text", "position"}
            assert "is_correct" not in option


def test_quiz_requires_published_lesson_and_quiz(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))

    db_session.execute(update(Quiz).values(is_published=False))
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").status_code == 404

    db_session.execute(update(Quiz).values(is_published=True))
    db_session.execute(update(Lesson).where(Lesson.id == lesson_id).values(is_published=False))
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").status_code == 404


# --- Отправка ответов ------------------------------------------------------------


def test_all_correct_answers_give_full_score(api_client, db_session):
    lesson_id = _prepare(db_session)
    user_id = _login(api_client)

    response = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == body["max_score"] == 10
    assert body["percent"] == 100
    assert all(item["is_correct"] for item in body["questions"])
    assert all(item["explanation"] for item in body["questions"])
    assert db_session.scalar(select(QuizAttempt.score).where(QuizAttempt.user_id == user_id)) == 10
    assert db_session.scalar(select(QuizAttemptAnswer.id)) is not None


def test_wrong_answer_is_explained_and_counted(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    answers = _correct_answers(db_session)
    # Портим первый вопрос: выбираем заведомо неверный вариант.
    question = _questions(db_session)[0]
    wrong = next(option.id for option in question.options if not option.is_correct)
    answers[0]["option_ids"] = [wrong]

    body = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    ).json()

    assert body["score"] == 9
    assert body["percent"] == 90
    assert body["questions"][0]["is_correct"] is False
    assert wrong in body["questions"][0]["selected_option_ids"]
    assert set(body["questions"][0]["correct_option_ids"]) == {
        option.id for option in question.options if option.is_correct
    }
    assert body["questions"][0]["explanation"] == question.explanation


def test_partial_multiple_choice_answer_is_wrong(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    answers = _correct_answers(db_session)
    multiple = next(
        item
        for item in answers
        if len(item["option_ids"]) > 1  # type: ignore[arg-type]
    )
    multiple["option_ids"] = multiple["option_ids"][:1]  # type: ignore[index]

    body = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    ).json()

    assert body["score"] == 9
    failed = next(item for item in body["questions"] if not item["is_correct"])
    assert failed["question_id"] == multiple["question_id"]


def test_incomplete_or_foreign_answers_are_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    answers = _correct_answers(db_session)
    wrong_question = _questions(db_session)[1]

    missing = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers[:-1]}
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "validation_error"

    foreign_option = answers[0]["option_ids"][0]  # type: ignore[index]
    answers[0]["option_ids"] = [foreign_option + 100000]
    unknown_option = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    )
    assert unknown_option.status_code == 422

    answers[0]["option_ids"] = [option.id for option in wrong_question.options][:1]  # type: ignore[index]
    # Вариант существует, но принадлежит другому вопросу.
    body = api_client.post(f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers})
    assert body.status_code == 422


def test_duplicate_question_answer_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    answers = _correct_answers(db_session)
    answers.append(answers[0])

    response = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    )

    assert response.status_code == 422


def test_guest_cannot_submit_and_foreign_origin_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    answers = _correct_answers(db_session)

    api_client.cookies.clear()
    assert (
        api_client.post(
            f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
        ).status_code
        == 401
    )

    _login(api_client)
    foreign = {"Origin": "https://evil.example"}
    assert (
        api_client.post(
            f"/api/v1/lessons/{lesson_id}/quiz/attempts",
            json={"answers": answers},
            headers=foreign,
        ).status_code
        == 403
    )


# --- История попыток -------------------------------------------------------------


def test_attempts_are_saved_and_best_score_is_shown(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    full = _correct_answers(db_session)
    partial = _correct_answers(db_session)
    partial[0]["option_ids"] = [
        option.id for option in _questions(db_session)[0].options if not option.is_correct
    ][:1]

    api_client.post(f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": full})
    api_client.post(f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": partial})

    body = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").json()
    assert len(body["attempts"]) == 2
    assert body["attempts_total"] == 2
    assert body["best_percent"] == 100
    assert body["attempts"][0]["percent"] == 90  # последняя попытка первой
    assert body["attempts"][1]["percent"] == 100


def test_attempts_of_one_student_are_invisible_to_another(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )
    api_client.cookies.clear()

    _login(api_client, email="second@example.com")
    body = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").json()

    assert body["attempts"] == []
    assert body["best_percent"] is None
    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz/attempts").json() == []


def test_attempt_history_requires_quiz(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    db_session.execute(update(Quiz).values(is_published=False))

    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz/attempts").status_code == 404


def test_quiz_seed_is_idempotent(db_session):
    _prepare(db_session)

    assert publish_demo_quiz(db_session) == 0
    assert (
        db_session.scalar(select(QuizOption.id).where(QuizOption.is_correct.is_(True))) is not None
    )


# --- Сохранность и «битый» контент ------------------------------------------------


def test_selected_options_are_stored(db_session, api_client):
    lesson_id = _prepare(db_session)
    _login(api_client)
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )

    stored = db_session.scalar(select(func.count()).select_from(quiz_attempt_selected_options))
    expected = sum(len(item["option_ids"]) for item in _correct_answers(db_session))  # type: ignore[arg-type]
    assert stored == expected


def test_lesson_deletion_removes_quiz_data(db_session, api_client):
    lesson_id = _prepare(db_session)
    _login(api_client)
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )

    db_session.execute(delete(Lesson).where(Lesson.id == lesson_id))
    db_session.flush()

    assert db_session.scalar(select(func.count()).select_from(QuizAttempt)) == 0
    assert db_session.scalar(select(func.count()).select_from(QuizAttemptAnswer)) == 0
    assert db_session.scalar(select(func.count()).select_from(quiz_attempt_selected_options)) == 0


def test_user_deletion_removes_attempts_only_of_that_user(db_session, api_client):
    lesson_id = _prepare(db_session)
    first_id = _login(api_client)
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )
    api_client.cookies.clear()
    second_id = _login(api_client, email="second@example.com")
    api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts",
        json={"answers": _correct_answers(db_session)},
    )

    db_session.execute(delete(User).where(User.id == first_id))
    db_session.flush()

    remaining = list(db_session.scalars(select(QuizAttempt.user_id)))
    assert remaining == [second_id]


def test_empty_answers_and_empty_options_are_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)

    empty = api_client.post(f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": []})
    assert empty.status_code == 422

    answers = _correct_answers(db_session)
    answers[0]["option_ids"] = []
    no_options = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    )
    assert no_options.status_code == 422


def test_duplicate_option_ids_are_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    answers = _correct_answers(db_session)
    answers[0]["option_ids"] = answers[0]["option_ids"] * 2  # type: ignore[operator]

    response = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    )

    assert response.status_code == 422


def test_question_from_another_quiz_is_rejected(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    other_quiz = Quiz(module_id=module_id, title="Другой квиз", is_published=True)
    other_question = QuizQuestion(
        kind="theory", text="Вопрос другого квиза", explanation="Нет", position=1
    )
    other_question.options = [
        QuizOption(text="Верно", is_correct=True, position=1),
        QuizOption(text="Неверно", is_correct=False, position=2),
    ]
    other_quiz.questions = [other_question]
    db_session.add(other_quiz)
    db_session.flush()

    answers = _correct_answers(db_session)
    answers[0]["question_id"] = other_question.id
    response = api_client.post(
        f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
    )

    assert response.status_code == 422


def test_quiz_with_question_without_correct_option_is_unavailable(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    first_question = _questions(db_session)[0]
    db_session.execute(
        update(QuizOption)
        .where(QuizOption.question_id == first_question.id)
        .values(is_correct=False)
    )

    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").status_code == 503
    # Для запроса нужен хотя бы один вариант: пустой список отклонила бы схема.
    answers = _correct_answers(db_session)
    answers[0]["option_ids"] = [first_question.options[0].id]
    assert (
        api_client.post(
            f"/api/v1/lessons/{lesson_id}/quiz/attempts",
            json={"answers": answers},
        ).status_code
        == 503
    )


def test_empty_quiz_is_unavailable(api_client, db_session):
    _prepare(db_session)
    _login(api_client)
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    db_session.execute(delete(QuizQuestion))
    db_session.flush()

    assert api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").status_code == 503


def test_module_can_have_only_one_quiz(db_session):
    _prepare(db_session)
    module_id = db_session.scalar(select(Module.id).order_by(Module.id))
    db_session.add(Quiz(module_id=module_id, title="Первый квиз модуля"))
    db_session.flush()

    db_session.add(Quiz(module_id=module_id, title="Второй квиз модуля"))
    with pytest.raises(IntegrityError, match="uq_quizzes_module_id"):
        db_session.flush()


def test_multiple_flag_matches_number_of_correct_options(api_client, db_session):
    lesson_id = _prepare(db_session)
    _login(api_client)
    correct_counts = {
        question.id: sum(1 for option in question.options if option.is_correct)
        for question in _questions(db_session)
    }

    body = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").json()

    for question in body["quiz"]["questions"]:
        assert question["multiple"] is (correct_counts[question["id"]] > 1)


def test_history_is_limited_but_total_and_best_use_all_attempts(
    api_client, db_session, monkeypatch
):
    monkeypatch.setattr(quiz_service, "HISTORY_LIMIT", 2)
    lesson_id = _prepare(db_session)
    _login(api_client)
    full = _correct_answers(db_session)
    partial = _correct_answers(db_session)
    partial[0]["option_ids"] = [
        option.id for option in _questions(db_session)[0].options if not option.is_correct
    ][:1]

    for answers in (full, partial, full):
        assert (
            api_client.post(
                f"/api/v1/lessons/{lesson_id}/quiz/attempts", json={"answers": answers}
            ).status_code
            == 201
        )

    body = api_client.get(f"/api/v1/lessons/{lesson_id}/quiz").json()
    assert len(body["attempts"]) == 2
    assert body["attempts_total"] == 3
    assert body["best_percent"] == 100
