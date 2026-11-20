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
    "quizzes",
    "quiz_questions",
    "quiz_options",
    "quiz_attempts",
    "quiz_attempt_answers",
    "quiz_attempt_selected_options",
    "lesson_notes",
    "lesson_highlights",
    "saved_questions",
    "review_items",
    "cheatsheets",
    "ai_teacher_messages",
    "interview_sources",
    "interview_questions",
    "mock_interviews",
    "mock_interview_answers",
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


def test_ai_teacher_messages_schema(test_engine):
    inspector = inspect(test_engine)
    columns = {column["name"] for column in inspector.get_columns("ai_teacher_messages")}
    assert columns == {
        "id",
        "user_id",
        "lesson_id",
        "question",
        "answer",
        "mode",
        "created_at",
        "updated_at",
    }
    indexes = {index["name"] for index in inspector.get_indexes("ai_teacher_messages")}
    assert {"ix_ai_teacher_messages_user_id", "ix_ai_teacher_messages_lesson_id"} <= indexes
    foreign_keys = {
        foreign_key["name"]: foreign_key
        for foreign_key in inspector.get_foreign_keys("ai_teacher_messages")
    }
    assert set(foreign_keys) == {
        "fk_ai_teacher_messages_user_id_users",
        "fk_ai_teacher_messages_lesson_id_lessons",
    }
    assert all(item["options"]["ondelete"] == "CASCADE" for item in foreign_keys.values())


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


def test_quiz_tables_match_model(test_engine):
    inspector = inspect(test_engine)

    quiz_columns = {column["name"] for column in inspector.get_columns("quizzes")}
    assert quiz_columns == {
        "id",
        "lesson_id",
        "module_id",
        "title",
        "description",
        "is_published",
        "created_at",
        "updated_at",
    }
    assert inspector.get_pk_constraint("quizzes")["name"] == "pk_quizzes"
    unique_names = {
        constraint["name"] for constraint in inspector.get_unique_constraints("quizzes")
    }
    assert {"uq_quizzes_lesson_id", "uq_quizzes_module_id"} <= unique_names
    check_names = {constraint["name"] for constraint in inspector.get_check_constraints("quizzes")}
    assert "ck_quizzes_one_parent" in check_names

    question_columns = {column["name"] for column in inspector.get_columns("quiz_questions")}
    assert {"kind", "text", "explanation", "position"} <= question_columns
    option_columns = {column["name"] for column in inspector.get_columns("quiz_options")}
    assert {"text", "is_correct", "position"} <= option_columns

    attempt_indexes = {index["name"] for index in inspector.get_indexes("quiz_attempts")}
    assert {"ix_quiz_attempts_quiz_id", "ix_quiz_attempts_user_id"} <= attempt_indexes

    answer_columns = {column["name"] for column in inspector.get_columns("quiz_attempt_answers")}
    assert {"attempt_id", "question_id", "is_correct"} <= answer_columns

    selected_columns = {
        column["name"] for column in inspector.get_columns("quiz_attempt_selected_options")
    }
    assert selected_columns == {"answer_id", "option_id"}


def test_student_tools_tables_match_model(test_engine):
    inspector = inspect(test_engine)

    assert {column["name"] for column in inspector.get_columns("lesson_notes")} >= {
        "user_id",
        "lesson_id",
        "content",
    }
    note_unique = {
        constraint["name"] for constraint in inspector.get_unique_constraints("lesson_notes")
    }
    assert "uq_lesson_notes_user_id_lesson_id" in note_unique

    highlight_indexes = {index["name"] for index in inspector.get_indexes("lesson_highlights")}
    assert "ix_lesson_highlights_user_id_lesson_id" in highlight_indexes

    for table in ("saved_questions", "review_items", "cheatsheets"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert {"user_id", "lesson_id"} <= columns
        (lesson_fk,) = [
            foreign_key
            for foreign_key in inspector.get_foreign_keys(table)
            if foreign_key["constrained_columns"] == ["lesson_id"]
        ]
        # Личные записи не должны исчезать вместе с уроком.
        assert lesson_fk["options"]["ondelete"] == "SET NULL"


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
