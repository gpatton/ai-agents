"""allow users without email

Revision ID: a02a0085727b
Revises: 8dace45b763a
Create Date: 2026-09-21 21:25:11.707135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a02a0085727b'
down_revision: Union[str, Sequence[str], None] = '8dace45b763a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Allow Clerk users to be created before an email is available."""
    op.alter_column(
        "users",
        "email",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    """Restore the original email requirement."""
    op.alter_column(
        "users",
        "email",
        existing_type=sa.Text(),
        nullable=False,
    )
