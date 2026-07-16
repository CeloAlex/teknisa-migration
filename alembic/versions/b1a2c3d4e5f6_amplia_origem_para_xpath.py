"""amplia coluna origem para xpath esocial

100 caracteres bastava para referências de coluna XLSX ("A", "campo:X,Y") — XPath eSocial
(Fase 7), especialmente com união de variantes inclusão/alteração
("caminho/a | caminho/b"), passa disso facilmente.

Revision ID: b1a2c3d4e5f6
Revises: 93d7c22f0d66
Create Date: 2026-07-16 16:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = '93d7c22f0d66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('template_campo', 'origem', type_=sa.String(length=300))


def downgrade() -> None:
    op.alter_column('template_campo', 'origem', type_=sa.String(length=100))
