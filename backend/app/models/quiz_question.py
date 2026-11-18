"""Вопрос квиза."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.quiz import Quiz
    from app.models.quiz_option import QuizOption

# Типы заданий из методики: теория, практическая ситуация, анализ результатов,
# поиск ошибки, выбор решения.
QUESTION_KINDS = ("theory", "situation", "analysis", "error", "decision")
_KINDS_SQL = ", ".join(f"'{kind}'" for kind in QUESTION_KINDS)


class QuizQuestion(TimestampMixin, Base):
    """Один вопрос с вариантами ответа и объяснением."""

    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "position"),
        CheckConstraint(f"kind IN ({_KINDS_SQL})", name="kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quizzes.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    # Почему правильный ответ именно такой: показывается после отправки.
    explanation: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    options: Mapped[list[QuizOption]] = relationship(
        back_populates="question",
        order_by="QuizOption.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
