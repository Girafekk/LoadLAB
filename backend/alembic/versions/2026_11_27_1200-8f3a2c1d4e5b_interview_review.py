"""review columns for interview questions

Revision ID: 8f3a2c1d4e5b
Revises: dccb1b8eb59c
Create Date: 2026-11-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8f3a2c1d4e5b"
down_revision: Union[str, None] = "dccb1b8eb59c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_questions",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column("interview_questions", sa.Column("review_comment", sa.Text(), nullable=True))
    op.add_column(
        "interview_questions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interview_questions",
        sa.Column("reviewed_by_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_interview_questions_reviewed_by_id_users",
        "interview_questions",
        "users",
        ["reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_interview_questions_review_status",
        "interview_questions",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_questions_review_status", table_name="interview_questions")
    op.drop_constraint(
        "fk_interview_questions_reviewed_by_id_users",
        "interview_questions",
        type_="foreignkey",
    )
    op.drop_column("interview_questions", "reviewed_by_id")
    op.drop_column("interview_questions", "reviewed_at")
    op.drop_column("interview_questions", "review_comment")
    op.drop_column("interview_questions", "review_status")
