"""seed organizacoes

Semeia as cinco organizações usadas como referência no protótipo navegável (mesmos números e
nomes), para manter continuidade com o material já usado ao longo do projeto.

Revision ID: 23bd8d788a9b
Revises: b7f4f3205980
Create Date: 2026-07-16 10:09:30.805836

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '23bd8d788a9b'
down_revision: Union[str, None] = 'b7f4f3205980'
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
        sa.text("INSERT INTO organizacao (nr_org, nome, ativo) VALUES (:nr_org, :nome, true)"),
        [{"nr_org": nr_org, "nome": nome} for nr_org, nome in ORGANIZACOES],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM organizacao WHERE nr_org = ANY(:nr_orgs)"),
        {"nr_orgs": [nr_org for nr_org, _ in ORGANIZACOES]},
    )
