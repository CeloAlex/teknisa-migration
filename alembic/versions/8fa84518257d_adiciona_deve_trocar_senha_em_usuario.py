"""adiciona deve_trocar_senha em usuario

Revision ID: 8fa84518257d
Revises: ebbbf5482b3c
Create Date: 2026-07-29 15:41:29.754436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fa84518257d'
down_revision: Union[str, None] = 'ebbbf5482b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuario', sa.Column('deve_trocar_senha', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('usuario', 'deve_trocar_senha')
