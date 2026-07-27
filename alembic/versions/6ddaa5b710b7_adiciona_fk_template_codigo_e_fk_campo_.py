"""adiciona fk_template_codigo e fk_campo em template_campo

Suporte a uma nova classe de validação (Seção 7.4 — "validações relacionais"): antecipar,
antes mesmo da geração do script, que uma FK resolvida por subquery (`SELECT ... WHERE
CDMATRICULA = '@X@'`) vai encontrar valor — comparando contra os dados já importados no
template referenciado, dentro da mesma migração. Pedido do usuário após um caso real:
Estrutura com código `9272000000001_001`, Movimentações referenciando
`9272000000001001` (sem o "_") — a subquery resolveria para NULL só na hora de aplicar.

Revision ID: 6ddaa5b710b7
Revises: d49c05cd300d
Create Date: 2026-07-27 18:42:20.672131

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6ddaa5b710b7'
down_revision: Union[str, None] = 'd49c05cd300d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("template_campo", sa.Column("fk_template_codigo", sa.String(length=50), nullable=True))
    op.add_column("template_campo", sa.Column("fk_campo", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("template_campo", "fk_campo")
    op.drop_column("template_campo", "fk_template_codigo")
