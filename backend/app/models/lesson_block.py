from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.lesson import Lesson

BLOCK_TYPES = ("heading", "text", "code", "callout", "image", "table", "list")
_TYPES_SQL = ", ".join(f"'{block_type}'" for block_type in BLOCK_TYPES)


class LessonBlock(TimestampMixin, Base):
    """Блок урока: заголовок, текст, код, таблица и т.д.

    Урок собирается из блоков по порядку. Содержимое блока хранится в JSON,
    потому что у разных типов оно разное (у кода — язык и текст, у таблицы — строки).
    """

    __tablename__ = "lesson_blocks"
    __table_args__ = (
        UniqueConstraint("lesson_id", "position"),
        CheckConstraint(f"type IN ({_TYPES_SQL})", name="type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lessons.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(30))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Порядковый номер внутри урока, начинается с 1.
    position: Mapped[int] = mapped_column(Integer)

    lesson: Mapped[Lesson] = relationship(back_populates="blocks")
