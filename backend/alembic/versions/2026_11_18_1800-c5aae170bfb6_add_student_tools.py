"""add_student_tools: конспект, выделения, вопросы, повторение и шпаргалки

Revision ID: c5aae170bfb6
Revises: 5216ebe8886c
Create Date: 2026-11-18 18:00:56.623567

Личные материалы ученика привязаны к пользователю с ON DELETE CASCADE.
Ссылка на урок мягкая (`SET NULL`) для вопросов, повторения и шпаргалок:
если урок уберут из программы, записи ученика не должны исчезнуть. Для конспекта
и выделений урок обязателен, поэтому там каскад.

Здесь же добавлена уникальность квиза модуля: модель объявляет связь «один к одному»,
и база должна это гарантировать.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5aae170bfb6"
down_revision: str | Sequence[str] | None = "5216ebe8886c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cheatsheets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_cheatsheets_lesson_id_lessons"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_cheatsheets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cheatsheets")),
    )
    op.create_index(op.f("ix_cheatsheets_user_id"), "cheatsheets", ["user_id"], unique=False)
    op.create_table(
        "lesson_highlights",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_highlights_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_lesson_highlights_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_highlights")),
    )
    op.create_index(
        "ix_lesson_highlights_user_id_lesson_id",
        "lesson_highlights",
        ["user_id", "lesson_id"],
        unique=False,
    )
    op.create_table(
        "lesson_notes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_notes_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_lesson_notes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_notes")),
        sa.UniqueConstraint("user_id", "lesson_id", name=op.f("uq_lesson_notes_user_id_lesson_id")),
    )
    op.create_index(op.f("ix_lesson_notes_lesson_id"), "lesson_notes", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_lesson_notes_user_id"), "lesson_notes", ["user_id"], unique=False)
    op.create_table(
        "review_items",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_review_items_lesson_id_lessons"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_review_items_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_items")),
    )
    op.create_index(op.f("ix_review_items_user_id"), "review_items", ["user_id"], unique=False)
    op.create_table(
        "saved_questions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("lesson_id", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_saved_questions_lesson_id_lessons"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_saved_questions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_questions")),
    )
    op.create_index(
        op.f("ix_saved_questions_user_id"), "saved_questions", ["user_id"], unique=False
    )
    op.create_unique_constraint(op.f("uq_quizzes_module_id"), "quizzes", ["module_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_quizzes_module_id"), "quizzes", type_="unique")
    op.drop_index(op.f("ix_saved_questions_user_id"), table_name="saved_questions")
    op.drop_table("saved_questions")
    op.drop_index(op.f("ix_review_items_user_id"), table_name="review_items")
    op.drop_table("review_items")
    op.drop_index(op.f("ix_lesson_notes_user_id"), table_name="lesson_notes")
    op.drop_index(op.f("ix_lesson_notes_lesson_id"), table_name="lesson_notes")
    op.drop_table("lesson_notes")
    op.drop_index("ix_lesson_highlights_user_id_lesson_id", table_name="lesson_highlights")
    op.drop_table("lesson_highlights")
    op.drop_index(op.f("ix_cheatsheets_user_id"), table_name="cheatsheets")
    op.drop_table("cheatsheets")
