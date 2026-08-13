"""adiciona validacoes de dominio duplicidade e ausencia condicional em template_campo

Revision ID: b49e9782ea08
Revises: 8fa84518257d
Create Date: 2026-08-13 11:21:50.969290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b49e9782ea08'
down_revision: Union[str, None] = '8fa84518257d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('template_campo', sa.Column('dominio_valores', sa.Text(), nullable=True))
    op.add_column('template_campo', sa.Column('duplicata_no_lote', sa.String(length=20), nullable=True))
    op.add_column('template_campo', sa.Column('duplicata_agrupado_por', sa.String(length=100), nullable=True))
    op.add_column('template_campo', sa.Column('alerta_se_vazio_quando_campo', sa.String(length=100), nullable=True))
    op.add_column('template_campo', sa.Column('alerta_se_vazio_quando_valores', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('template_campo', 'alerta_se_vazio_quando_valores')
    op.drop_column('template_campo', 'alerta_se_vazio_quando_campo')
    op.drop_column('template_campo', 'duplicata_agrupado_por')
    op.drop_column('template_campo', 'duplicata_no_lote')
    op.drop_column('template_campo', 'dominio_valores')
