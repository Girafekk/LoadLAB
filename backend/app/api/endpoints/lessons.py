"""Уроки и личные отметки о прохождении."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.course import LessonRead
from app.services import course_service, progress_service

router = APIRouter(prefix="/lessons")


@router.get("/{lesson_id}", response_model=LessonRead)
def read_lesson(
    lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> LessonRead:
    lesson = course_service.get_lesson(db, user.id, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Урок не найден")
    return lesson


def _complete(db: Session, user: User, lesson_id: int, completed: bool) -> Response:
    if course_service.published_lesson(db, lesson_id) is None:
        raise HTTPException(status_code=404, detail="Урок не найден")
    progress_service.set_completed(db, user.id, lesson_id, completed)
    return Response(status_code=204)


@router.post("/{lesson_id}/complete", status_code=204)
def complete_lesson(
    lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    return _complete(db, user, lesson_id, True)


@router.delete("/{lesson_id}/complete", status_code=204)
def uncomplete_lesson(
    lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    return _complete(db, user, lesson_id, False)
