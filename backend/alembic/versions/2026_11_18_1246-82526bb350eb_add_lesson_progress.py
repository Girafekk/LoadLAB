"""add_lesson_progress: отметки «урок пройден» и индексы сессий

Revision ID: 82526bb350eb
Revises: 16bfad2a4028
Create Date: 2026-11-18 12:46:53.027094

Таблица `lesson_progress` хранит по одной строке на пару «ученик + урок»:
составной первичный ключ не даёт создать две отметки одного урока.
Индексы `sessions` ускоряют очистку просроченных сессий и каскадное удаление
сессий пользователя.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "82526bb350eb"
down_revision: str | Sequence[str] | None = "16bfad2a4028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_progress",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_progress_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_lesson_progress_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "lesson_id", name=op.f("pk_lesson_progress")),
    )
    op.create_index(
        op.f("ix_lesson_progress_lesson_id"), "lesson_progress", ["lesson_id"], unique=False
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_index(op.f("ix_lesson_progress_lesson_id"), table_name="lesson_progress")
    op.drop_table("lesson_progress")
