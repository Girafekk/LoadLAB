"""Пробное собеседование: вопросы, ответы и разбор."""

from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import (
    InterviewQuestion,
    MockInterview,
    MockInterviewAnswer,
    User,
)
from app.schemas.mock_interview import (
    MockAnswerRead,
    MockAnswerResult,
    MockQuestion,
    MockReport,
    MockSession,
)
from app.services import ai_teacher_service, privacy


class MockInterviewError(Exception):
    """Ошибка сценария собеседования."""


class MockInterviewValidationError(MockInterviewError):
    """Некорректный ответ или параметры, а не отсутствие ресурса."""


def _question(answer: MockInterviewAnswer) -> MockQuestion | None:
    if not answer.question_text:
        return None
    return MockQuestion(
        answer_id=answer.id,
        question_id=answer.question_id,
        text=answer.question_text,
        topic=answer.question_topic,
        position=answer.position,
    )


def _current(interview: MockInterview) -> MockQuestion | None:
    for answer in interview.answers:
        if answer.answer is None:
            return _question(answer)
    return None


def session_view(interview: MockInterview) -> MockSession:
    return MockSession(
        id=interview.id,
        status=interview.status,
        score=interview.score,
        total=interview.total,
        current=_current(interview),
    )


def start(db: Session, user: User, count: int = 5) -> MockSession:
    questions = list(
        db.scalars(
            select(InterviewQuestion)
            .where(InterviewQuestion.status == "approved")
            .order_by(func.random())
            .limit(count)
        )
    )
    if not questions:
        raise MockInterviewError("Сначала подтвердите вопросы в банке")
    if len(questions) < count:
        raise MockInterviewError(f"Нужно минимум {count} подтверждённых вопросов")
    interview = MockInterview(user_id=user.id, total=len(questions), status="active")
    db.add(interview)
    db.flush()
    for position, question in enumerate(questions, start=1):
        db.add(
            MockInterviewAnswer(
                interview_id=interview.id,
                question_id=question.id,
                position=position,
                question_text=question.text,
                question_topic=question.topic,
                reference_answer=question.reference_answer,
                answer_criteria=question.answer_criteria,
            )
        )
    db.commit()
    db.refresh(interview)
    return session_view(interview)


def _fallback_feedback(
    answer: str, criteria: str | None = None, reference: str | None = None
) -> tuple[int, str]:
    """Локальная оценка по критериям и эталону, а не только по длине."""
    lowered = answer.casefold()
    score = 2
    if len(answer.split()) < 5:
        return 0, "Слишком короткий ответ. Назовите главное и приведите пример."
    if "пример" in lowered:
        score += 1
    if "границ" in lowered or "ограничен" in lowered:
        score += 1
    source = f"{criteria or ''} {reference or ''}"
    if source:
        keywords = [word.casefold() for word in re.findall(r"[A-Za-zА-Яа-яЁё]{5,}", source)]
        hits = sum(1 for word in set(keywords) if word in lowered)
        if hits >= 2:
            score += 1
    return min(score, 5), ("Разбор локальный: проверьте, что названы главное, пример и граница.")


def evaluate(
    question: str, answer: str, reference: str | None = None, criteria: str | None = None
) -> tuple[int, str]:
    system = (
        "Ты интервьюер Junior Load Tester. Оцени ответ по шкале 0–5, сверяясь "
        "с эталоном, если он дан. Поощряй простое объяснение своими словами, "
        "бытовой пример и честную границу; не требуй заученных определений. "
        "Пиши разбор простым русским языком, короткими предложениями. "
        "Верни только JSON без Markdown: "
        '{"score": число, "feedback": "2–3 предложения"}. '
        "Не раскрывай персональные данные."
    )
    user = (
        f"Вопрос: {privacy.anonymize(question)}\n\n"
        f"Ответ кандидата:\n{privacy.anonymize(answer)[:6_000]}"
    )
    if reference:
        user += f"\n\nЭталонный ответ:\n{privacy.anonymize(reference)[:3_000]}"
    if criteria:
        user += f"\n\nКритерии оценки:\n{privacy.anonymize(criteria)[:2_000]}"
    raw = ai_teacher_service.complete_external(system, user, timeout=35)
    if raw:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                score = int(data.get("score", 0))
                feedback = str(data.get("feedback", "")).strip()
                if 0 <= score <= 5 and feedback:
                    return score, feedback.replace("\x00", "")[:2_000]
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
    return _fallback_feedback(answer, criteria, reference)


_locks_guard = threading.Lock()
_interview_locks: dict[int, threading.Lock] = {}


def _lock_for(interview_id: int) -> threading.Lock:
    with _locks_guard:
        return _interview_locks.setdefault(interview_id, threading.Lock())


def submit(
    db: Session,
    user: User,
    interview_id: int,
    text: str,
    answer_id: int,
    allow_external: bool = False,
) -> MockAnswerResult:
    text = text.replace("\x00", "").strip()[:6_000]
    if not text:
        raise MockInterviewValidationError("Ответ пустой")
    # Один ответ на конкретное собеседование за раз. Разные интервью
    # не блокируют друг друга.
    with _lock_for(interview_id):
        interview = db.scalar(
            select(MockInterview).where(
                MockInterview.id == interview_id, MockInterview.user_id == user.id
            )
        )
        if interview is None:
            raise MockInterviewError("Собеседование не найдено")
        if answer_id is not None:
            answer = next((item for item in interview.answers if item.id == answer_id), None)
            if answer is None:
                raise MockInterviewValidationError("Вопрос не найден")
            if answer.answer is not None:
                return MockAnswerResult(
                    answer_id=answer.id,
                    score=answer.score or 0,
                    feedback=answer.feedback or "Ответ уже сохранён.",
                    completed=interview.status == "completed",
                    next_question=_current(interview),
                )
        else:
            answer = None
        if interview.status != "active":
            raise MockInterviewError("Собеседование уже завершено")
        if answer is None:
            answer = next((item for item in interview.answers if item.answer is None), None)
        if answer is None or (answer.question is None and not answer.question_text):
            raise MockInterviewError("Вопросы закончились")
        expected = next((item for item in interview.answers if item.answer is None), None)
        if expected is None or expected.id != answer.id:
            raise MockInterviewValidationError("Это не текущий вопрос")
        answer_id = answer.id
        question_text = answer.question_text or ""
        reference = answer.reference_answer
        criteria = answer.answer_criteria
        bind = db.get_bind()
        separate = isinstance(bind, Engine)
        if separate:
            db.close()
            write_db = Session(bind=bind)
        else:
            write_db = db
        try:
            score, feedback = (
                evaluate(question_text, text, reference, criteria)
                if allow_external
                else _fallback_feedback(text, criteria, reference)
            )
            fresh = write_db.scalar(
                select(MockInterview)
                .where(
                    MockInterview.id == interview_id,
                    MockInterview.user_id == user.id,
                    MockInterview.status == "active",
                )
                .with_for_update()
            )
            if fresh is None:
                saved = saved_result(write_db, user, interview_id, answer_id)
                if saved is not None:
                    return saved
                raise MockInterviewError("Собеседование завершено или недоступно")
            fresh_answer = next((item for item in fresh.answers if item.id == answer_id), None)
            if fresh_answer is None:
                raise MockInterviewError("Вопрос не найден")
            if fresh_answer.answer is not None:
                return MockAnswerResult(
                    answer_id=fresh_answer.id,
                    score=fresh_answer.score or 0,
                    feedback=fresh_answer.feedback or "Ответ уже сохранён.",
                    completed=fresh.status == "completed",
                    next_question=_current(fresh),
                )
            current_answer = _current(fresh)
            if current_answer is None or current_answer.answer_id != answer_id:
                raise MockInterviewValidationError("Это не текущий вопрос")
            fresh_answer.answer = text
            fresh_answer.score = score
            fresh_answer.feedback = feedback
            fresh_answer.processing_at = None
            if all(item.answer is not None for item in fresh.answers):
                fresh.status = "completed"
                fresh.completed_at = datetime.now(UTC)
                fresh.score = sum(item.score or 0 for item in fresh.answers)
            write_db.commit()
            write_db.refresh(fresh)
            return MockAnswerResult(
                answer_id=fresh_answer.id,
                score=score,
                feedback=feedback,
                completed=fresh.status == "completed",
                next_question=_current(fresh),
            )
        finally:
            if separate:
                write_db.close()


def claim_answer(db: Session, user: User, interview_id: int, answer_id: int) -> bool:
    """Атомарно резервирует текущий ответ до внешней оценки."""
    interview = db.scalar(
        select(MockInterview).where(
            MockInterview.id == interview_id,
            MockInterview.user_id == user.id,
            MockInterview.status == "active",
        )
    )
    if interview is None:
        return False
    current = _current(interview)
    if current is None or current.answer_id != answer_id:
        return False
    result = db.execute(
        update(MockInterviewAnswer)
        .where(
            MockInterviewAnswer.id == answer_id,
            MockInterviewAnswer.answer.is_(None),
            MockInterviewAnswer.processing_at.is_(None),
        )
        .values(processing_at=datetime.now(UTC))
    )
    db.commit()
    return result.rowcount == 1


def release_answer(db: Session, answer_id: int) -> None:
    db.execute(
        update(MockInterviewAnswer)
        .where(MockInterviewAnswer.id == answer_id)
        .values(processing_at=None)
    )
    db.commit()


def saved_result(
    db: Session, user: User, interview_id: int, answer_id: int
) -> MockAnswerResult | None:
    interview = db.scalar(
        select(MockInterview).where(
            MockInterview.id == interview_id, MockInterview.user_id == user.id
        )
    )
    if interview is None:
        return None
    answer = next((item for item in interview.answers if item.id == answer_id), None)
    if answer is None or answer.answer is None:
        return None
    return MockAnswerResult(
        answer_id=answer.id,
        score=answer.score or 0,
        feedback=answer.feedback or "Ответ уже сохранён.",
        completed=interview.status == "completed",
        next_question=_current(interview),
    )


def list_sessions(db: Session, user: User) -> list[MockSession]:
    interviews = list(
        db.scalars(
            select(MockInterview)
            .where(MockInterview.user_id == user.id)
            .order_by(MockInterview.id.desc())
            .limit(20)
        )
    )
    return [session_view(item) for item in interviews]


def get(db: Session, user: User, interview_id: int) -> MockReport:
    interview = db.scalar(
        select(MockInterview).where(
            MockInterview.id == interview_id, MockInterview.user_id == user.id
        )
    )
    if interview is None:
        raise MockInterviewError("Собеседование не найдено")
    return MockReport(
        id=interview.id,
        status=interview.status,
        score=interview.score,
        total=interview.total,
        created_at=interview.created_at,
        completed_at=interview.completed_at,
        answers=[
            MockAnswerRead(
                position=item.position,
                question=(
                    item.question_text or (item.question.text if item.question else "Вопрос удалён")
                ),
                answer=item.answer,
                feedback=item.feedback,
                score=item.score,
            )
            for item in interview.answers
            if interview.status == "completed" or item.answer is not None
        ],
    )
