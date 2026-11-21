"""Квиз урока: вопросы, отправка ответов и история попыток."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.quiz import (
    QuizAttemptCreate,
    QuizAttemptResult,
    QuizAttemptSummary,
    QuizWithHistory,
)
from app.services import quiz_service

router = APIRouter(prefix="/lessons")


def _quiz_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Квиз не найден")


def _content_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Квиз временно недоступен: проверьте настройки вопросов",
    )


@router.get("/{lesson_id}/quiz", response_model=QuizWithHistory)
def read_lesson_quiz(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizWithHistory:
    try:
        quiz = quiz_service.get_lesson_quiz(db, lesson_id, user.id)
    except quiz_service.QuizContentError:
        raise _content_unavailable() from None
    if quiz is None:
        raise _quiz_not_found()
    return quiz


@router.get("/{lesson_id}/quiz/attempts", response_model=list[QuizAttemptSummary])
def read_lesson_quiz_attempts(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuizAttemptSummary]:
    try:
        attempts = quiz_service.list_attempts(db, lesson_id, user.id)
    except quiz_service.QuizContentError:
        raise _content_unavailable() from None
    if attempts is None:
        raise _quiz_not_found()
    return attempts


@router.post(
    "/{lesson_id}/quiz/attempts",
    response_model=QuizAttemptResult,
    status_code=status.HTTP_201_CREATED,
)
def submit_lesson_quiz(
    lesson_id: int,
    data: QuizAttemptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizAttemptResult:
    try:
        return quiz_service.submit_attempt(db, lesson_id, user, data)
    except quiz_service.QuizNotFoundError:
        raise _quiz_not_found() from None
    except quiz_service.QuizContentError:
        raise _content_unavailable() from None
    except quiz_service.QuizDuplicateError:
        raise HTTPException(status_code=409, detail="Эта попытка уже сохранена") from None
    except quiz_service.QuizValidationError as error:
        raise HTTPException(status_code=422, detail=error.message) from None
