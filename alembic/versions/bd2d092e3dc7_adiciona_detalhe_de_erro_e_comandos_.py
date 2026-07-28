"""adiciona detalhe de erro e comandos executados na aplicacao

Pedido do usuário: a aba Execução mostrava só "Falha ao aplicar" sem detalhe nenhum — o
erro real do Oracle (ex.: "ORA-00001: unique constraint...") só aparecia na Trilha
completa/Relatório, longe de onde o operador realmente está olhando quando clica em
"Executar no Oracle". Guarda o detalhe direto no `MigracaoTemplateStatus` pra exibir na
própria aba.

Revision ID: bd2d092e3dc7
Revises: db38e7cd2c5b
Create Date: 2026-07-28 12:08:35.126908

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bd2d092e3dc7'
down_revision: Union[str, None] = 'db38e7cd2c5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("migracao_template_status", sa.Column("detalhe_erro_aplicacao", sa.Text(), nullable=True))
    op.add_column("migracao_template_status", sa.Column("comandos_executados_aplicacao", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("migracao_template_status", "comandos_executados_aplicacao")
    op.drop_column("migracao_template_status", "detalhe_erro_aplicacao")
