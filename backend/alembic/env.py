"""Окружение Alembic: связывает миграции с настройками и моделями приложения."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool

import app.models  # noqa: F401  — импорт нужен, чтобы Alembic увидел все модели
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# По этим метаданным Alembic сравнивает модели с реальной базой (autogenerate).
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Режим без подключения к базе: только генерирует SQL-скрипт."""
    context.configure(
        url=get_settings().database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Обычный режим: подключается к базе и применяет миграции.

    Тесты передают готовое соединение с тестовой базой через
    `config.attributes["connection"]` — тогда используется оно,
    а не база из настроек приложения.
    """
    external_connection = config.attributes.get("connection")
    if external_connection is not None:
        _run_with_connection(external_connection)
        return

    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        _run_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
