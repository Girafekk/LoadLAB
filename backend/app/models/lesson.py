from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.lesson_block import LessonBlock
    from app.models.module import Module


class Lesson(TimestampMixin, Base):
    """Урок — одна небольшая тема внутри модуля."""

    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("module_id", "position"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    module_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("modules.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    # Сколько минут занимает урок вместе с практикой и квизом.
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=90, server_default="90")
    # Порядковый номер внутри модуля, начинается с 1.
    position: Mapped[int] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    module: Mapped[Module] = relationship(back_populates="lessons")
    blocks: Mapped[list[LessonBlock]] = relationship(
        back_populates="lesson",
        order_by="LessonBlock.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
