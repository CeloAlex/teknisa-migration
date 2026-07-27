"""corrige obrigatoriedade nrtpmovtransfm e vreventofolha

Revisão funcional do dicionário (pedido do usuário) — dois campos que tinham sido seedados
como `obrigatorio=True` na verdade não são obrigatórios:

- MOVIMENTACOES_ESTRUTURA.NRTPMOVTRANSFM ("Nr Motivo Transferência (código)").
- FICHA_FINANCEIRA.VREVENTOFOLHA ("Valor").

Correção via migração nova (não editando os seeds originais em
`e5513421e14a`/`157982505200`) porque esses seeds já rodaram em bancos existentes — só uma
migração posterior alcança quem já aplicou os dois seeds.

Revision ID: 9329916f6963
Revises: 6df3d7f10a14
Create Date: 2026-07-27 11:20:34.070954

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9329916f6963'
down_revision: Union[str, None] = '6df3d7f10a14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CORRECOES = [
    ("MOVIMENTACOES_ESTRUTURA", "NRTPMOVTRANSFM"),
    ("FICHA_FINANCEIRA", "VREVENTOFOLHA"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for template_codigo, campo_codigo in CORRECOES:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET obrigatorio = false
                WHERE campo = :campo_codigo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {"template_codigo": template_codigo, "campo_codigo": campo_codigo},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for template_codigo, campo_codigo in CORRECOES:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET obrigatorio = true
                WHERE campo = :campo_codigo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {"template_codigo": template_codigo, "campo_codigo": campo_codigo},
        )
