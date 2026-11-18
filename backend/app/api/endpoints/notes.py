"""Конспект урока и выделенные фрагменты."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.tools import (
    LessonHighlightCreate,
    LessonHighlightRead,
    LessonNoteRead,
    LessonNoteUpdate,
)
from app.services import notes_service

router = APIRouter(tags=["Мои материалы"])


def _lesson_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Урок не найден")


@router.get("/lessons/{lesson_id}/note", response_model=LessonNoteRead)
def read_note(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonNoteRead:
    try:
        note = notes_service.get_note(db, user, lesson_id)
    except notes_service.LessonNotFoundError:
        raise _lesson_not_found() from None
    return LessonNoteRead(
        lesson_id=lesson_id,
        content=note.content if note else "",
        updated_at=note.updated_at if note else None,
    )


@router.put("/lessons/{lesson_id}/note", response_model=LessonNoteRead)
def save_note(
    lesson_id: int,
    data: LessonNoteUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonNoteRead:
    try:
        note = notes_service.save_note(db, user, lesson_id, data.content)
    except notes_service.LessonNotFoundError:
        raise _lesson_not_found() from None
    return LessonNoteRead(lesson_id=lesson_id, content=note.content, updated_at=note.updated_at)


@router.get("/lessons/{lesson_id}/highlights", response_model=list[LessonHighlightRead])
def read_highlights(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LessonHighlightRead]:
    try:
        return notes_service.list_highlights(db, user, lesson_id)
    except notes_service.LessonNotFoundError:
        raise _lesson_not_found() from None


@router.post(
    "/lessons/{lesson_id}/highlights",
    response_model=LessonHighlightRead,
    status_code=201,
)
def add_highlight(
    lesson_id: int,
    data: LessonHighlightCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonHighlightRead:
    try:
        return notes_service.add_highlight(db, user, lesson_id, data.text)
    except notes_service.LessonNotFoundError:
        raise _lesson_not_found() from None


@router.delete("/highlights/{highlight_id}", status_code=204)
def delete_highlight(
    highlight_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not notes_service.delete_highlight(db, user, highlight_id):
        raise HTTPException(status_code=404, detail="Выделение не найдено")
    return Response(status_code=204)
