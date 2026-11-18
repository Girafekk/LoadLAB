"""Конспект ученика и выделенные фрагменты урока."""

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import LessonHighlight, LessonNote, User
from app.services import course_service


class LessonNotFoundError(Exception):
    """Урока нет или он не опубликован."""


def _ensure_published_lesson(db: Session, lesson_id: int) -> None:
    if course_service.published_lesson(db, lesson_id) is None:
        raise LessonNotFoundError


def get_note(db: Session, user: User, lesson_id: int) -> LessonNote | None:
    """Конспект по уроку или None, если ученик его ещё не вёл."""
    _ensure_published_lesson(db, lesson_id)
    return db.scalar(
        select(LessonNote).where(LessonNote.user_id == user.id, LessonNote.lesson_id == lesson_id)
    )


def save_note(db: Session, user: User, lesson_id: int, content: str) -> LessonNote:
    """Создаёт или обновляет конспект. Пустой текст допустим — это очистка.

    Запись идёт одним `INSERT ... ON CONFLICT`: два одновременных сохранения
    из разных вкладок не создают дубль и не падают с 500 на уникальном ключе.
    """
    _ensure_published_lesson(db, lesson_id)
    db.execute(
        insert(LessonNote)
        .values(user_id=user.id, lesson_id=lesson_id, content=content)
        .on_conflict_do_update(
            index_elements=["user_id", "lesson_id"],
            set_={"content": content, "updated_at": func.now()},
        )
    )
    db.commit()
    note = db.scalar(
        select(LessonNote).where(LessonNote.user_id == user.id, LessonNote.lesson_id == lesson_id)
    )
    if note is None:  # защита от неверного состояния; на практике недостижимо
        raise RuntimeError("Конспект не сохранился")
    return note


def list_highlights(db: Session, user: User, lesson_id: int) -> list[LessonHighlight]:
    _ensure_published_lesson(db, lesson_id)
    return list(
        db.scalars(
            select(LessonHighlight)
            .where(
                LessonHighlight.user_id == user.id,
                LessonHighlight.lesson_id == lesson_id,
            )
            .order_by(LessonHighlight.created_at.desc(), LessonHighlight.id.desc())
        )
    )


def add_highlight(db: Session, user: User, lesson_id: int, text: str) -> LessonHighlight:
    _ensure_published_lesson(db, lesson_id)
    highlight = LessonHighlight(user_id=user.id, lesson_id=lesson_id, text=text)
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    return highlight


def delete_highlight(db: Session, user: User, highlight_id: int) -> bool:
    """Удаляет только своё выделение. Чужое выглядит как отсутствующее."""
    result = db.execute(
        delete(LessonHighlight).where(
            LessonHighlight.id == highlight_id,
            LessonHighlight.user_id == user.id,
        )
    )
    db.commit()
    return bool(result.rowcount)
