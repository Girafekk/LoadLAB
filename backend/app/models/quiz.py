"""Квиз: проверка понимания после урока или модуля."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.lesson import Lesson
    from app.models.module import Module
    from app.models.quiz_attempt import QuizAttempt
    from app.models.quiz_question import QuizQuestion


class Quiz(TimestampMixin, Base):
    """Квиз принадлежит уроку или модулю (ровно одному родителю).

    Проверка `(lesson_id IS NULL) <> (module_id IS NULL)` не даёт создать квиз
    без родителя или сразу у двух: тогда результаты нельзя однозначно привязать
    к теме программы.
    """

    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint(
            "(lesson_id IS NULL) <> (module_id IS NULL)",
            name="one_parent",
        ),
        UniqueConstraint("lesson_id"),
        UniqueConstraint("module_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lessons.id", ondelete="CASCADE")
    )
    module_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("modules.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    lesson: Mapped[Lesson | None] = relationship(back_populates="quiz")
    module: Mapped[Module | None] = relationship(back_populates="quiz")
    questions: Mapped[list[QuizQuestion]] = relationship(
        back_populates="quiz",
        order_by="QuizQuestion.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attempts: Mapped[list[QuizAttempt]] = relationship(
        back_populates="quiz",
        order_by="QuizAttempt.created_at.desc()",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
