"""adiciona cdoperador em usuario

Revision ID: 794618fabba5
Revises: b49e9782ea08
Create Date: 2026-08-13 11:22:12.715164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '794618fabba5'
down_revision: Union[str, None] = 'b49e9782ea08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuario', sa.Column('cdoperador', sa.String(length=12), nullable=True))


def downgrade() -> None:
    op.drop_column('usuario', 'cdoperador')
