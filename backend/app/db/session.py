"""Подключение к PostgreSQL через SQLAlchemy."""

import logging
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger("loadlab.db")


@lru_cache
def get_engine() -> Engine:
    """Создаёт «движок» — объект, который управляет соединениями с базой.

    Само соединение открывается только при первом запросе, поэтому backend
    запускается, даже если база данных ещё не поднята.
    """
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_db() -> Iterator[Session]:
    """Зависимость FastAPI: выдаёт сессию базы данных на время одного запроса."""
    session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    with session_factory() as session:
        yield session


def is_database_available() -> bool:
    """Проверяет связь с базой простым запросом `SELECT 1`."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as error:
        logger.warning("База данных недоступна: %s", error.__class__.__name__)
        return False
