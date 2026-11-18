from sqlalchemy import Engine, inspect

from app.core.config import get_settings
from tests.fixtures.database import TEST_DATABASE_PREFIX, new_test_database_name, run_alembic

APP_TABLES = {
    "users",
    "courses",
    "modules",
    "lessons",
    "lesson_blocks",
    "sessions",
    "lesson_progress",
}


def test_each_run_uses_its_own_test_database(test_engine):
    # Имя уникально для запуска: параллельные прогоны не удаляют базы друг друга.
    name = test_engine.url.database
    assert name.startswith(TEST_DATABASE_PREFIX)
    assert name != get_settings().postgres_db
    assert new_test_database_name() != new_test_database_name()


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_head_creates_all_tables(test_engine):
    assert APP_TABLES <= _table_names(test_engine)


def test_sessions_table_matches_model(test_engine):
    inspector = inspect(test_engine)

    columns = {column["name"] for column in inspector.get_columns("sessions")}
    # Столбца updated_at у сессий нет намеренно: сессия не редактируется.
    assert columns == {"id", "user_id", "token_hash", "expires_at", "created_at"}

    assert inspector.get_pk_constraint("sessions")["name"] == "pk_sessions"

    unique_names = {
        constraint["name"] for constraint in inspector.get_unique_constraints("sessions")
    }
    assert "uq_sessions_token_hash" in unique_names

    index_names = {index["name"] for index in inspector.get_indexes("sessions")}
    assert {"ix_sessions_user_id", "ix_sessions_expires_at"} <= index_names

    (foreign_key,) = inspector.get_foreign_keys("sessions")
    assert foreign_key["name"] == "fk_sessions_user_id_users"
    assert foreign_key["referred_table"] == "users"
    assert foreign_key["options"]["ondelete"] == "CASCADE"


def test_lesson_progress_table_matches_model(test_engine):
    inspector = inspect(test_engine)

    columns = {column["name"] for column in inspector.get_columns("lesson_progress")}
    assert columns == {"user_id", "lesson_id", "completed_at"}

    primary_key = inspector.get_pk_constraint("lesson_progress")
    assert primary_key["name"] == "pk_lesson_progress"
    assert primary_key["constrained_columns"] == ["user_id", "lesson_id"]

    foreign_keys = {
        foreign_key["name"]: foreign_key
        for foreign_key in inspector.get_foreign_keys("lesson_progress")
    }
    assert set(foreign_keys) == {
        "fk_lesson_progress_user_id_users",
        "fk_lesson_progress_lesson_id_lessons",
    }
    for foreign_key in foreign_keys.values():
        assert foreign_key["options"]["ondelete"] == "CASCADE"

    index_names = {index["name"] for index in inspector.get_indexes("lesson_progress")}
    assert "ix_lesson_progress_lesson_id" in index_names


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
