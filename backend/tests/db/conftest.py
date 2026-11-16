"""Фикстуры для тестов базы данных.

Тесты работают в отдельной базе `loadlab_test` на том же сервере PostgreSQL.
Она создаётся перед тестами, получает схему через миграции Alembic
и удаляется после. База разработки (`loadlab`) не затрагивается.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings

TEST_DATABASE_NAME = "loadlab_test"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_alembic(connection: Connection, action: str, revision: str) -> None:
    """Выполняет `alembic upgrade/downgrade` на переданном соединении."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["connection"] = connection
    getattr(command, action)(config, revision)
    connection.commit()


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    # Защита от ошибки в настройках: тесты никогда не работают с базой разработки.
    assert settings.postgres_db != TEST_DATABASE_NAME

    # Создавать и удалять базы можно только вне транзакции и из другой базы.
    admin_engine = create_engine(
        settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE_NAME} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {TEST_DATABASE_NAME}"))

    engine = create_engine(settings.database_url.set(database=TEST_DATABASE_NAME))
    try:
        with engine.connect() as connection:
            run_alembic(connection, "upgrade", "head")
        yield engine
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE_NAME} WITH (FORCE)"))
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
