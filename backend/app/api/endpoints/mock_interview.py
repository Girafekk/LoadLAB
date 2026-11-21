"""Пробное собеседование для ученика."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import ai_teacher_rate_limiter
from app.db.session import get_db
from app.models import User
from app.schemas.mock_interview import (
    MockAnswerInput,
    MockAnswerResult,
    MockReport,
    MockSession,
)
from app.services import mock_interview_service

router = APIRouter(prefix="/mock-interviews", tags=["Пробное собеседование"])


@router.post("", response_model=MockSession, status_code=201)
def start_interview(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MockSession:
    try:
        return mock_interview_service.start(db, user)
    except mock_interview_service.MockInterviewError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("", response_model=list[MockSession])
def list_interviews(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MockSession]:
    return mock_interview_service.list_sessions(db, user)


@router.post("/{interview_id}/answers", response_model=MockAnswerResult)
def submit_answer(
    interview_id: int,
    data: MockAnswerInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockAnswerResult:
    saved = mock_interview_service.saved_result(db, user, interview_id, data.answer_id)
    if saved is not None:
        return saved
    retry_after = ai_teacher_rate_limiter.reserve_attempt(f"mock-interview:{user.id}")
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Слишком много ответов. Подождите минуту.",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        return mock_interview_service.submit(
            db,
            user,
            interview_id,
            data.answer,
            answer_id=data.answer_id,
            allow_external=data.allow_external,
        )
    except mock_interview_service.MockInterviewValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except mock_interview_service.MockInterviewError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.get("/{interview_id}", response_model=MockReport)
def get_interview(
    interview_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockReport:
    try:
        return mock_interview_service.get(db, user, interview_id)
    except mock_interview_service.MockInterviewError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
