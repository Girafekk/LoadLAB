"""add_tools_indexes: индексы для мягких ссылок на урок

Revision ID: d736490807f5
Revises: c5aae170bfb6
Create Date: 2026-11-18 18:36:53.085337

При удалении урока PostgreSQL обновляет или удаляет личные записи по `lesson_id`.
Индексы делают эти операции предсказуемыми. Отдельный индекс `lesson_notes.user_id`
убран: его полностью покрывает уникальный ключ (`user_id`, `lesson_id`).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d736490807f5"
down_revision: str | Sequence[str] | None = "c5aae170bfb6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(op.f("ix_cheatsheets_lesson_id"), "cheatsheets", ["lesson_id"], unique=False)
    op.create_index(
        op.f("ix_lesson_highlights_lesson_id"), "lesson_highlights", ["lesson_id"], unique=False
    )
    op.drop_index(op.f("ix_lesson_notes_user_id"), table_name="lesson_notes")
    op.create_index(op.f("ix_review_items_lesson_id"), "review_items", ["lesson_id"], unique=False)
    op.create_index(
        op.f("ix_saved_questions_lesson_id"), "saved_questions", ["lesson_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_questions_lesson_id"), table_name="saved_questions")
    op.drop_index(op.f("ix_review_items_lesson_id"), table_name="review_items")
    op.create_index(op.f("ix_lesson_notes_user_id"), "lesson_notes", ["user_id"], unique=False)
    op.drop_index(op.f("ix_lesson_highlights_lesson_id"), table_name="lesson_highlights")
    op.drop_index(op.f("ix_cheatsheets_lesson_id"), table_name="cheatsheets")
