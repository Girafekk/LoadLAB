"""Сложный вопрос, который ученик сохранил для разбора."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class SavedQuestion(TimestampMixin, Base):
    """Личный вопрос ученика; урок указывать не обязательно."""

    __tablename__ = "saved_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lessons.id", ondelete="SET NULL"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
