"""Сложные вопросы, список повторения и шпаргалки ученика."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Cheatsheet, ReviewItem, SavedQuestion, User
from app.services import course_service


class LessonNotFoundError(Exception):
    """Урок указан, но не найден или не опубликован."""


def _ensure_lesson(db: Session, lesson_id: int | None) -> None:
    if lesson_id is not None and course_service.published_lesson(db, lesson_id) is None:
        raise LessonNotFoundError


# --- Сложные вопросы -------------------------------------------------------------


def list_questions(db: Session, user: User) -> list[SavedQuestion]:
    return list(
        db.scalars(
            select(SavedQuestion)
            .where(SavedQuestion.user_id == user.id)
            .order_by(SavedQuestion.created_at.desc(), SavedQuestion.id.desc())
        )
    )


def create_question(db: Session, user: User, text: str, lesson_id: int | None) -> SavedQuestion:
    _ensure_lesson(db, lesson_id)
    question = SavedQuestion(user_id=user.id, text=text, lesson_id=lesson_id)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def _own_question(db: Session, user: User, question_id: int) -> SavedQuestion | None:
    return db.scalar(
        select(SavedQuestion).where(
            SavedQuestion.id == question_id, SavedQuestion.user_id == user.id
        )
    )


def set_question_resolved(
    db: Session, user: User, question_id: int, is_resolved: bool
) -> SavedQuestion | None:
    question = _own_question(db, user, question_id)
    if question is None:
        return None
    question.is_resolved = is_resolved
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, user: User, question_id: int) -> bool:
    result = db.execute(
        delete(SavedQuestion).where(
            SavedQuestion.id == question_id, SavedQuestion.user_id == user.id
        )
    )
    db.commit()
    return bool(result.rowcount)


# --- Список повторения -----------------------------------------------------------


def list_review_items(db: Session, user: User) -> list[ReviewItem]:
    return list(
        db.scalars(
            select(ReviewItem)
            .where(ReviewItem.user_id == user.id)
            .order_by(ReviewItem.is_done, ReviewItem.created_at.desc(), ReviewItem.id.desc())
        )
    )


def create_review_item(
    db: Session, user: User, title: str, note: str | None, lesson_id: int | None
) -> ReviewItem:
    _ensure_lesson(db, lesson_id)
    item = ReviewItem(user_id=user.id, title=title, note=note, lesson_id=lesson_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _own_review_item(db: Session, user: User, item_id: int) -> ReviewItem | None:
    return db.scalar(
        select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.user_id == user.id)
    )


def set_review_done(db: Session, user: User, item_id: int, is_done: bool) -> ReviewItem | None:
    item = _own_review_item(db, user, item_id)
    if item is None:
        return None
    item.is_done = is_done
    db.commit()
    db.refresh(item)
    return item


def delete_review_item(db: Session, user: User, item_id: int) -> bool:
    result = db.execute(
        delete(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.user_id == user.id)
    )
    db.commit()
    return bool(result.rowcount)


# --- Шпаргалки -------------------------------------------------------------------


def list_cheatsheets(db: Session, user: User) -> list[Cheatsheet]:
    return list(
        db.scalars(
            select(Cheatsheet)
            .where(Cheatsheet.user_id == user.id)
            .order_by(Cheatsheet.updated_at.desc(), Cheatsheet.id.desc())
        )
    )


def create_cheatsheet(
    db: Session, user: User, title: str, content: str, lesson_id: int | None
) -> Cheatsheet:
    _ensure_lesson(db, lesson_id)
    cheatsheet = Cheatsheet(user_id=user.id, title=title, content=content, lesson_id=lesson_id)
    db.add(cheatsheet)
    db.commit()
    db.refresh(cheatsheet)
    return cheatsheet


def _own_cheatsheet(db: Session, user: User, cheatsheet_id: int) -> Cheatsheet | None:
    return db.scalar(
        select(Cheatsheet).where(Cheatsheet.id == cheatsheet_id, Cheatsheet.user_id == user.id)
    )


def update_cheatsheet(
    db: Session,
    user: User,
    cheatsheet_id: int,
    title: str | None,
    content: str | None,
) -> Cheatsheet | None:
    cheatsheet = _own_cheatsheet(db, user, cheatsheet_id)
    if cheatsheet is None:
        return None
    if title is not None:
        cheatsheet.title = title
    if content is not None:
        cheatsheet.content = content
    db.commit()
    db.refresh(cheatsheet)
    return cheatsheet


def delete_cheatsheet(db: Session, user: User, cheatsheet_id: int) -> bool:
    result = db.execute(
        delete(Cheatsheet).where(Cheatsheet.id == cheatsheet_id, Cheatsheet.user_id == user.id)
    )
    db.commit()
    return bool(result.rowcount)
