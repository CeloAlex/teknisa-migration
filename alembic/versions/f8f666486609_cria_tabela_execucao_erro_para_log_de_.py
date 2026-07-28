"""cria tabela execucao_erro para log de comandos que falharam

Pedido do usuário: a persistência de todos os erros de uma execução, linha a linha, para
análise posterior (exportável) — não só o primeiro erro encontrado, resumido no evento da
trilha. `acoes.aplicar` limpa os registros da tentativa anterior antes de gravar os da
nova (sempre reflete a última execução).

Revision ID: f8f666486609
Revises: bd2d092e3dc7
Create Date: 2026-07-28 12:35:29.708657

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f8f666486609'
down_revision: Union[str, None] = 'bd2d092e3dc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execucao_erro",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "migracao_template_status_id",
            sa.Integer(),
            sa.ForeignKey("migracao_template_status.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("indice_comando", sa.Integer(), nullable=False),
        sa.Column("comando_sql", sa.Text(), nullable=False),
        sa.Column("mensagem_erro", sa.Text(), nullable=False),
        sa.Column("dt_execucao", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("execucao_erro")
