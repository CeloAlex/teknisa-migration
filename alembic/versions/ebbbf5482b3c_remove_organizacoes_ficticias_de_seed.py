"""remove organizacoes ficticias de seed

As cinco organizações semeadas em 23bd8d788a9b existiam apenas para simular migrações
durante o desenvolvimento (mesmos números/nomes do protótipo navegável). Elas não
correspondem a organizações reais e devem ser removidas antes do uso em produção. Os tipos
de migração e templates (que não têm nr_org) permanecem intactos.

Revision ID: ebbbf5482b3c
Revises: a4f8946567e6
Create Date: 2026-07-29 15:28:53.428754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebbbf5482b3c'
down_revision: Union[str, None] = 'a4f8946567e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORGANIZACOES = [
    (3260, "Grupo Lallegro Industrial"),
    (1410, "Rede Varejo Sul"),
    (4385, "Serviços Corporativos ABC"),
    (5521, "Comércio Atacadista Nordeste"),
    (6810, "Grupo Educacional Vértice"),
]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM organizacao WHERE nr_org = ANY(:nr_orgs)"),
        {"nr_orgs": [nr_org for nr_org, _ in ORGANIZACOES]},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO organizacao (nr_org, nome, ativo) VALUES (:nr_org, :nome, true)"),
        [{"nr_org": nr_org, "nome": nome} for nr_org, nome in ORGANIZACOES],
    )
