"""Источники собеседований и извлечённые вопросы."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.lesson import Lesson
    from app.models.user import User


class InterviewSource(TimestampMixin, Base):
    __tablename__ = "interview_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uploaded_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="extracted")
    error: Mapped[str | None] = mapped_column(Text)

    uploader: Mapped[User] = relationship()
    questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="source", passive_deletes=True
    )


class InterviewQuestion(TimestampMixin, Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    text: Mapped[str] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(120), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="junior")
    level: Mapped[str] = mapped_column(String(20), default="base")
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    source_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interview_sources.id", ondelete="SET NULL"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lessons.id", ondelete="SET NULL"), index=True
    )
    reference_answer: Mapped[str | None] = mapped_column(Text)
    answer_criteria: Mapped[str | None] = mapped_column(Text)

    source: Mapped[InterviewSource | None] = relationship(back_populates="questions")
    lesson: Mapped[Lesson | None] = relationship()


class InterviewQuestionSource(Base):
    """Вклад одного источника в вопрос: защищает occurrences от двойного счёта."""

    __tablename__ = "interview_question_sources"

    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interview_questions.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("interview_sources.id", ondelete="CASCADE"), primary_key=True
    )
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
