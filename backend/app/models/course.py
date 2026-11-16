from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.module import Module


class Course(TimestampMixin, Base):
    """Курс — верхний уровень учебной программы."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # slug — короткое имя для адресов, например «load-testing».
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    # passive_deletes: дочерние строки удаляет сама база (ON DELETE CASCADE).
    modules: Mapped[list[Module]] = relationship(
        back_populates="course",
        order_by="Module.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
