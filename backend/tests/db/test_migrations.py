from sqlalchemy import Engine, inspect

from tests.db.conftest import run_alembic

APP_TABLES = {"users", "courses", "modules", "lessons", "lesson_blocks"}


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_head_creates_all_tables(test_engine):
    assert APP_TABLES <= _table_names(test_engine)


def test_downgrade_base_removes_all_tables(test_engine):
    try:
        with test_engine.connect() as connection:
            run_alembic(connection, "downgrade", "base")

        # Остаётся только служебная таблица Alembic с номером версии.
        assert _table_names(test_engine) == {"alembic_version"}
    finally:
        # Возвращаем схему для остальных тестов.
        with test_engine.connect() as connection:
            run_alembic(connection, "upgrade", "head")

    assert APP_TABLES <= _table_names(test_engine)
