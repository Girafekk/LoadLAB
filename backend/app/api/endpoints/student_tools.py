"""Сложные вопросы, список повторения, шпаргалки и слабые темы ученика."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.tools import (
    CheatsheetCreate,
    CheatsheetRead,
    CheatsheetUpdate,
    ReviewItemCreate,
    ReviewItemRead,
    ReviewItemUpdate,
    SavedQuestionCreate,
    SavedQuestionRead,
    SavedQuestionUpdate,
    WeakTopicRead,
)
from app.services import study_tools_service, weak_topics_service

router = APIRouter(tags=["Мои материалы"])


def _lesson_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Урок не найден")


# --- Сложные вопросы -------------------------------------------------------------


@router.get("/saved-questions", response_model=list[SavedQuestionRead])
def list_saved_questions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[SavedQuestionRead]:
    return study_tools_service.list_questions(db, user)


@router.post("/saved-questions", response_model=SavedQuestionRead, status_code=201)
def create_saved_question(
    data: SavedQuestionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedQuestionRead:
    try:
        return study_tools_service.create_question(db, user, data.text, data.lesson_id)
    except study_tools_service.LessonNotFoundError:
        raise _lesson_not_found() from None


@router.patch("/saved-questions/{question_id}", response_model=SavedQuestionRead)
def update_saved_question(
    question_id: int,
    data: SavedQuestionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedQuestionRead:
    question = study_tools_service.set_question_resolved(db, user, question_id, data.is_resolved)
    if question is None:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return question


@router.delete("/saved-questions/{question_id}", status_code=204)
def delete_saved_question(
    question_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not study_tools_service.delete_question(db, user, question_id):
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    return Response(status_code=204)


# --- Список повторения -----------------------------------------------------------


@router.get("/review-items", response_model=list[ReviewItemRead])
def list_review_items(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ReviewItemRead]:
    return study_tools_service.list_review_items(db, user)


@router.post("/review-items", response_model=ReviewItemRead, status_code=201)
def create_review_item(
    data: ReviewItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    try:
        return study_tools_service.create_review_item(
            db, user, data.title, data.note, data.lesson_id
        )
    except study_tools_service.LessonNotFoundError:
        raise _lesson_not_found() from None


@router.patch("/review-items/{item_id}", response_model=ReviewItemRead)
def update_review_item(
    item_id: int,
    data: ReviewItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    item = study_tools_service.set_review_done(db, user, item_id, data.is_done)
    if item is None:
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return item


@router.delete("/review-items/{item_id}", status_code=204)
def delete_review_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not study_tools_service.delete_review_item(db, user, item_id):
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return Response(status_code=204)


# --- Шпаргалки -------------------------------------------------------------------


@router.get("/cheatsheets", response_model=list[CheatsheetRead])
def list_cheatsheets(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CheatsheetRead]:
    return study_tools_service.list_cheatsheets(db, user)


@router.post("/cheatsheets", response_model=CheatsheetRead, status_code=201)
def create_cheatsheet(
    data: CheatsheetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheatsheetRead:
    try:
        return study_tools_service.create_cheatsheet(
            db, user, data.title, data.content, data.lesson_id
        )
    except study_tools_service.LessonNotFoundError:
        raise _lesson_not_found() from None


@router.patch("/cheatsheets/{cheatsheet_id}", response_model=CheatsheetRead)
def update_cheatsheet(
    cheatsheet_id: int,
    data: CheatsheetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheatsheetRead:
    cheatsheet = study_tools_service.update_cheatsheet(
        db, user, cheatsheet_id, data.title, data.content
    )
    if cheatsheet is None:
        raise HTTPException(status_code=404, detail="Шпаргалка не найдена")
    return cheatsheet


@router.delete("/cheatsheets/{cheatsheet_id}", status_code=204)
def delete_cheatsheet(
    cheatsheet_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not study_tools_service.delete_cheatsheet(db, user, cheatsheet_id):
        raise HTTPException(status_code=404, detail="Шпаргалка не найдена")
    return Response(status_code=204)


# --- Слабые темы -----------------------------------------------------------------


@router.get("/users/me/weak-topics", response_model=list[WeakTopicRead])
def read_weak_topics(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WeakTopicRead]:
    return weak_topics_service.weak_topics(db, user.id)
