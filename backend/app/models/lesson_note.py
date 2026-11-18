"""Личный конспект ученика по уроку."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class LessonNote(TimestampMixin, Base):
    """Одна заметка-конспект на пару «ученик + урок»."""

    __tablename__ = "lesson_notes"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    lesson_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text, default="", server_default="")
