"""adiciona origem em validacao_resultado

Guarda a coluna da planilha (ex.: "E") ou o XPath do XML de onde o campo validado é lido,
junto de cada `ValidacaoResultado` — pedido do usuário para que alertas/inconsistências
apontem não só o campo, mas também de onde no arquivo ele vem, facilitando localizar a
origem da informação (ver conversa: confusão de coluna D vs E no template Ficha
Financeira). Nula para campos vindos de parâmetro de execução (ex.: NRORG), que não têm
origem no arquivo.

Revision ID: a1ec72c59c09
Revises: 3c173073107a
Create Date: 2026-07-27 11:52:38.364804

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1ec72c59c09'
down_revision: Union[str, None] = '3c173073107a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("validacao_resultado", sa.Column("origem", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("validacao_resultado", "origem")
