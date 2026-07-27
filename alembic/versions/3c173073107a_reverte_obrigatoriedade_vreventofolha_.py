"""reverte obrigatoriedade vreventofolha ficha financeira

Correção da migração anterior (`9329916f6963`): o usuário confirmou que
FICHA_FINANCEIRA.VREVENTOFOLHA ("Valor") É obrigatório de fato — a migração anterior errou
ao marcá-lo como opcional. O erro impeditivo que motivou a mudança era real, mas a causa não
era o dicionário: era um desalinhamento de coluna na ingestão de um arquivo específico (ver
investigação na conversa — coluna D do arquivo real trazia o valor, não a coluna E mapeada
pelo dicionário `origem="E"`). MOVIMENTACOES_ESTRUTURA.NRTPMOVTRANSFM, a outra correção feita
por `9329916f6963`, não foi contestada e permanece opcional.

Revision ID: 3c173073107a
Revises: 9329916f6963
Create Date: 2026-07-27 11:35:37.950323

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3c173073107a'
down_revision: Union[str, None] = '9329916f6963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "FICHA_FINANCEIRA"
CAMPO_CODIGO = "VREVENTOFOLHA"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE template_campo SET obrigatorio = true
            WHERE campo = :campo_codigo
              AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
            """
        ),
        {"template_codigo": TEMPLATE_CODIGO, "campo_codigo": CAMPO_CODIGO},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE template_campo SET obrigatorio = false
            WHERE campo = :campo_codigo
              AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
            """
        ),
        {"template_codigo": TEMPLATE_CODIGO, "campo_codigo": CAMPO_CODIGO},
    )
