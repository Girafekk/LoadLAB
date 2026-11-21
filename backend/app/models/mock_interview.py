"""Пробное собеседование по подтверждённым вопросам."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.interview import InterviewQuestion
    from app.models.user import User


class MockInterview(TimestampMixin, Base):
    __tablename__ = "mock_interviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
    answers: Mapped[list[MockInterviewAnswer]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="MockInterviewAnswer.position",
    )


class MockInterviewAnswer(Base):
    __tablename__ = "mock_interview_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("mock_interviews.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interview_questions.id", ondelete="SET NULL"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    question_text: Mapped[str | None] = mapped_column(Text)
    question_topic: Mapped[str | None] = mapped_column(String(120))
    reference_answer: Mapped[str | None] = mapped_column(Text)
    answer_criteria: Mapped[str | None] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    feedback: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)

    interview: Mapped[MockInterview] = relationship(back_populates="answers")
    question: Mapped[InterviewQuestion | None] = relationship()
