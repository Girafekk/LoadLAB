"""Фикстуры для тестов, которым нужна база данных.

Каждый запуск создаёт собственную базу `loadlab_test_<случайный суффикс>`
на том же сервере PostgreSQL, накатывает на неё миграции Alembic и удаляет
только её. Уникальное имя позволяет запускать тесты параллельно: прогоны
не мешают друг другу и не удаляют чужие базы. База разработки не затрагивается.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings

# По этому префиксу видно, что база создана тестами, и её можно безопасно удалить.
TEST_DATABASE_PREFIX = "loadlab_test_"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def new_test_database_name() -> str:
    """Уникальное имя тестовой базы для одного запуска."""
    return f"{TEST_DATABASE_PREFIX}{uuid.uuid4().hex[:12]}"


def run_alembic(connection: Connection, action: str, revision: str) -> None:
    """Выполняет `alembic upgrade/downgrade` на переданном соединении."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["connection"] = connection
    getattr(command, action)(config, revision)
    connection.commit()


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    database_name = new_test_database_name()
    # Защита от ошибки в настройках: тесты никогда не работают с базой разработки.
    assert database_name.startswith(TEST_DATABASE_PREFIX)
    assert database_name != settings.postgres_db

    # Создавать и удалять базы можно только вне транзакции и из другой базы.
    admin_engine = create_engine(
        settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))

    engine = create_engine(settings.database_url.set(database=database_name))
    try:
        with engine.connect() as connection:
            run_alembic(connection, "upgrade", "head")
        yield engine
    finally:
        engine.dispose()
        # Удаляем только базу, созданную этим запуском.
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
        admin_engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Сессия для одного теста. Всё сделанное в тесте откатывается после него."""
    with test_engine.connect() as connection:
        transaction = connection.begin()
        # create_savepoint: rollback внутри теста (после ожидаемой ошибки)
        # откатывает только последний шаг, а не всю внешнюю транзакцию.
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
