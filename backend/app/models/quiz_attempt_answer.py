"""Ответ на один вопрос внутри попытки."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.quiz_attempt import QuizAttempt
    from app.models.quiz_option import QuizOption

# Выбранные варианты: отдельная таблица, чтобы база сама следила за ссылочной
# целостностью. Дубликат «ответ + вариант» невозможен из-за составного ключа.
quiz_attempt_selected_options = Table(
    "quiz_attempt_selected_options",
    Base.metadata,
    Column(
        "answer_id",
        BigInteger,
        ForeignKey("quiz_attempt_answers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "option_id",
        BigInteger,
        ForeignKey("quiz_options.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class QuizAttemptAnswer(Base):
    """Верно ли отвечен конкретный вопрос в конкретной попытке."""

    __tablename__ = "quiz_attempt_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quiz_attempts.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="CASCADE")
    )
    is_correct: Mapped[bool] = mapped_column(Boolean)

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")
    selected_options: Mapped[list[QuizOption]] = relationship(
        secondary=quiz_attempt_selected_options,
        passive_deletes=True,
    )
