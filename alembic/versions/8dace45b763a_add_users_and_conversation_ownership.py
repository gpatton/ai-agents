"""add users and conversation ownership

Revision ID: 8dace45b763a
Revises: 68cb167642ec
Create Date: 2026-09-19 21:37:55.659828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8dace45b763a'
down_revision: Union[str, Sequence[str], None] = '68cb167642ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create users and assign existing conversations to a development user."""

    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.add_column(
        "conversations",
        sa.Column("user_id", sa.Text(), nullable=True),
    )

    development_user_id = "00000000-0000-4000-8000-000000000001"

    op.execute(
        sa.text(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (
                :user_id,
                'development@agentforge.local',
                NULL,
                CURRENT_TIMESTAMP
            )
            """
        ).bindparams(user_id=development_user_id)
    )

    op.execute(
        sa.text(
            """
            UPDATE conversations
            SET user_id = :user_id
            WHERE user_id IS NULL
            """
        ).bindparams(user_id=development_user_id)
    )

    op.alter_column(
        "conversations",
        "user_id",
        existing_type=sa.Text(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_conversations_user_id",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_conversations_user_id_created_at_id",
        "conversations",
        ["user_id", "created_at", "id"],
    )


def downgrade() -> None:
    """Remove ownership while preserving conversations and messages."""

    op.drop_index(
        "ix_conversations_user_id_created_at_id",
        table_name="conversations",
    )

    op.drop_constraint(
        "fk_conversations_user_id",
        "conversations",
        type_="foreignkey",
    )

    op.drop_column("conversations", "user_id")
    op.drop_table("users")
