from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Единые правила именования ограничений и индексов. Без них PostgreSQL
# придумывает имена сам, и в миграциях на них нельзя надёжно сослаться.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0_label)s",
}


class Base(DeclarativeBase):
    """Базовый класс для всех моделей (таблиц) SQLAlchemy.

    Модели наследуются от него и размещаются в папке `app/models`.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
