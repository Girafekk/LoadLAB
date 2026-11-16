"""Общие части моделей."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Добавляет таблице столбцы «когда создано» и «когда изменено».

    Значения проставляет сама база (`DEFAULT now()`); при изменении строки
    через ORM `updated_at` обновляется автоматически.
    """

    # sort_order ставит эти столбцы в конец таблицы, после «содержательных».
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), sort_order=101
    )
