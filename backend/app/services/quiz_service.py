"""Прохождение квизов: выдача вопросов, проверка ответов, история попыток.

Сервер никогда не отдаёт признак правильности варианта до отправки: иначе
ответ можно было бы узнать из ответа API. Проверка и подсчёт баллов — только здесь.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Quiz, QuizAttempt, QuizAttemptAnswer, QuizOption, QuizQuestion, User
from app.schemas.quiz import (
    QuizAnswerInput,
    QuizAttemptCreate,
    QuizAttemptResult,
    QuizAttemptSummary,
    QuizOptionRead,
    QuizQuestionRead,
    QuizQuestionResult,
    QuizRead,
    QuizWithHistory,
)
from app.services import course_service

# Сколько последних попыток показывать в истории.
HISTORY_LIMIT = 50


class QuizNotFoundError(Exception):
    """Урока нет, он не опубликован или у урока ещё нет опубликованного квиза."""


class QuizValidationError(Exception):
    """Ответы не соответствуют вопросам квиза."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class QuizContentError(Exception):
    """Квиз настроен неверно: вопрос без верного варианта или без вопросов."""


def _percent(score: int, max_score: int) -> int:
    # Округляем вниз: 79,9 % не должно выглядеть как 80 % и одновременно
    # считаться слабой темой. Тот же принцип использует weak_topics_service.
    return (100 * score) // max_score if max_score else 0


def _ensure_valid_content(quiz: Quiz) -> None:
    if not quiz.questions:
        raise QuizContentError
    for question in quiz.questions:
        if not any(option.is_correct for option in question.options):
            raise QuizContentError


def _load_quiz(db: Session, lesson_id: int) -> Quiz | None:
    """Опубликованный квиз опубликованного урока вместе с вопросами и вариантами."""
    lesson = course_service.published_lesson(db, lesson_id)
    if lesson is None:
        return None
    return db.scalar(
        select(Quiz)
        .where(Quiz.lesson_id == lesson.id, Quiz.is_published.is_(True))
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options),
        )
    )


def _to_quiz_read(quiz: Quiz) -> QuizRead:
    questions = []
    for question in quiz.questions:
        correct_count = sum(1 for option in question.options if option.is_correct)
        questions.append(
            QuizQuestionRead(
                id=question.id,
                kind=question.kind,
                text=question.text,
                position=question.position,
                multiple=correct_count > 1,
                options=[QuizOptionRead.model_validate(option) for option in question.options],
            )
        )
    return QuizRead(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        questions=questions,
    )


def _attempts(db: Session, quiz_id: int, user_id: int) -> list[QuizAttempt]:
    return list(
        db.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.created_at.desc(), QuizAttempt.id.desc())
            .limit(HISTORY_LIMIT)
        )
    )


def _best_percent(db: Session, quiz_id: int, user_id: int) -> int | None:
    """Лучший результат по всем попыткам, а не только по показанным в истории."""
    best = db.scalar(
        select(func.max(QuizAttempt.score * 100.0 / QuizAttempt.max_score)).where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id,
            QuizAttempt.max_score > 0,
        )
    )
    return round(best) if best is not None else None


def _attempts_total(db: Session, quiz_id: int, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        )
        or 0
    )


def _summary(attempt: QuizAttempt) -> QuizAttemptSummary:
    return QuizAttemptSummary(
        id=attempt.id,
        score=attempt.score,
        max_score=attempt.max_score,
        percent=_percent(attempt.score, attempt.max_score),
        created_at=attempt.created_at,
    )


def get_lesson_quiz(db: Session, lesson_id: int, user_id: int) -> QuizWithHistory | None:
    """Квиз урока с историей попыток текущего ученика."""
    quiz = _load_quiz(db, lesson_id)
    if quiz is None:
        return None
    _ensure_valid_content(quiz)

    attempts = _attempts(db, quiz.id, user_id)
    return QuizWithHistory(
        quiz=_to_quiz_read(quiz),
        attempts=[_summary(item) for item in attempts],
        attempts_total=_attempts_total(db, quiz.id, user_id),
        best_percent=_best_percent(db, quiz.id, user_id),
    )


def list_attempts(db: Session, lesson_id: int, user_id: int) -> list[QuizAttemptSummary] | None:
    """История попыток по квизу урока или None, если квиза нет."""
    quiz = _load_quiz(db, lesson_id)
    if quiz is None:
        return None
    _ensure_valid_content(quiz)
    return [_summary(item) for item in _attempts(db, quiz.id, user_id)]


def _options_by_id(question: QuizQuestion) -> dict[int, QuizOption]:
    return {option.id: option for option in question.options}


def _validate_answers(
    questions: Sequence[QuizQuestion], answers: Sequence[QuizAnswerInput]
) -> dict[int, set[int]]:
    """Проверяет полноту и целостность ответов и возвращает выбранные варианты."""
    question_ids = {question.id for question in questions}
    seen: set[int] = set()
    selected: dict[int, set[int]] = {}

    for answer in answers:
        if answer.question_id not in question_ids:
            raise QuizValidationError("Ответ содержит вопрос из другого квиза")
        if answer.question_id in seen:
            raise QuizValidationError("На один вопрос можно ответить только один раз")
        seen.add(answer.question_id)

        question = next(item for item in questions if item.id == answer.question_id)
        options = _options_by_id(question)
        if len(set(answer.option_ids)) != len(answer.option_ids):
            raise QuizValidationError("Один вариант нельзя выбрать дважды")
        option_ids = set(answer.option_ids)
        unknown = option_ids - options.keys()
        if unknown:
            raise QuizValidationError("Выбран вариант, которого нет у этого вопроса")
        selected[answer.question_id] = option_ids

    missing = question_ids - seen
    if missing:
        raise QuizValidationError("Ответьте на все вопросы квиза")
    return selected


def submit_attempt(
    db: Session, lesson_id: int, user: User, data: QuizAttemptCreate
) -> QuizAttemptResult:
    """Проверяет ответы, сохраняет попытку и возвращает разбор."""
    quiz = _load_quiz(db, lesson_id)
    if quiz is None:
        raise QuizNotFoundError
    _ensure_valid_content(quiz)

    selected = _validate_answers(quiz.questions, data.answers)
    score = 0
    results: list[QuizQuestionResult] = []
    answers_to_store: list[tuple[QuizQuestion, bool, list[QuizOption]]] = []

    for question in quiz.questions:
        chosen_ids = selected[question.id]
        correct_ids = {option.id for option in question.options if option.is_correct}
        is_correct = chosen_ids == correct_ids
        score += int(is_correct)

        answers_to_store.append(
            (
                question,
                is_correct,
                [option for option in question.options if option.id in chosen_ids],
            )
        )
        results.append(
            QuizQuestionResult(
                question_id=question.id,
                is_correct=is_correct,
                selected_option_ids=[
                    option.id for option in question.options if option.id in chosen_ids
                ],
                correct_option_ids=[
                    option.id for option in question.options if option.id in correct_ids
                ],
                explanation=question.explanation,
            )
        )

    max_score = len(quiz.questions)
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=score,
        max_score=max_score,
    )
    db.add(attempt)
    db.flush()

    for question, is_correct, chosen_options in answers_to_store:
        db.add(
            QuizAttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                is_correct=is_correct,
                selected_options=chosen_options,
            )
        )
    db.commit()
    db.refresh(attempt)

    return QuizAttemptResult(
        id=attempt.id,
        score=score,
        max_score=max_score,
        percent=_percent(score, max_score),
        created_at=attempt.created_at,
        questions=results,
    )
