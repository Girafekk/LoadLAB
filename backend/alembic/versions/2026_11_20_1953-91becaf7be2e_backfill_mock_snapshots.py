"""backfill_mock_snapshots

Revision ID: 91becaf7be2e
Revises: 04abf3dbf941
Create Date: 2026-11-20 19:53:23.663395
"""

from collections.abc import Sequence

from alembic import op

revision: str = "91becaf7be2e"
down_revision: str | Sequence[str] | None = "04abf3dbf941"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE mock_interview_answers AS a
        SET question_text = q.text,
            reference_answer = q.reference_answer,
            answer_criteria = q.answer_criteria
        FROM interview_questions AS q
        WHERE a.question_id = q.id AND a.question_text IS NULL
        """
    )


def downgrade() -> None:
    pass
