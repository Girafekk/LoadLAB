"""Отметки конкретного ученика."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import LessonProgress


def completions(db: Session, user_id: int, lesson_ids: list[int]) -> list[int]:
    return list(
        db.scalars(
            select(LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(lesson_ids))
            .order_by(LessonProgress.completed_at.desc(), LessonProgress.lesson_id.desc())
        )
    )


def set_completed(db: Session, user_id: int, lesson_id: int, completed: bool) -> None:
    if completed:
        db.execute(
            insert(LessonProgress)
            .values(user_id=user_id, lesson_id=lesson_id)
            .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
        )
    else:
        db.execute(
            delete(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
            )
        )
    db.commit()
