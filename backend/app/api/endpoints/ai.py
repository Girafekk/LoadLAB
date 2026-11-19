"""AI Teacher: вопросы по уроку, история, рекомендации и шпаргалка."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import ai_teacher_rate_limiter
from app.db.session import get_db
from app.models import User
from app.schemas.ai_teacher import (
    AiAnswer,
    AiHistoryItem,
    AiQuestion,
    AiRecommendation,
    AiStatus,
    CheatsheetSuggestion,
)
from app.services import ai_teacher_service

router = APIRouter(prefix="/ai/teacher", tags=["AI Teacher"])


@router.get("/status", response_model=AiStatus, summary="Провайдер AI Teacher")
def status(user: User = Depends(get_current_user)) -> AiStatus:
    return ai_teacher_service.provider_status()


@router.post("/ask", response_model=AiAnswer, summary="Спросить AI Teacher по уроку")
def ask(
    data: AiQuestion, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AiAnswer:
    retry_after = ai_teacher_rate_limiter.reserve_attempt(f"ai-teacher:{user.id}")
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Слишком много вопросов. Подождите немного.",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        return ai_teacher_service.ask(db, user, data.lesson_id, data.question)
    except ai_teacher_service.AiTeacherNotFoundError:
        raise HTTPException(status_code=404, detail="Урок не найден или не опубликован") from None


@router.get("/history", response_model=list[AiHistoryItem], summary="История вопросов")
def history(
    lesson_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AiHistoryItem]:
    return ai_teacher_service.history(db, user, lesson_id)


@router.get("/recommendations", response_model=list[AiRecommendation], summary="Что повторить")
def recommendations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AiRecommendation]:
    return ai_teacher_service.recommendations(db, user)


@router.get("/cheatsheet", response_model=CheatsheetSuggestion, summary="Предложить шпаргалку")
def cheatsheet(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CheatsheetSuggestion:
    return ai_teacher_service.cheatsheet(db, user)
