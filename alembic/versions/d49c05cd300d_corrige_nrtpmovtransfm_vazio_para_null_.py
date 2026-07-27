"""corrige nrtpmovtransfm vazio para NULL literal em movimentacoes_estrutura

O marcador @NRTPMOVTRANSFM@ é usado "bare" (sem aspas) no script de MOVIMENTACOES_ESTRUTURA
— o comentário original do seed (`e5513421e14a`) já avisava: "Bare/sem aspas no script —
obrigatório para não gerar SQL inválido". A migração `9329916f6963` desta mesma conversa
tornou o campo opcional (pedido do usuário, confirmado com dado real onde a coluna C vinha
preenchida — mas outras linhas legitimamente vêm vazias) sem ajustar essa consequência:
quando vazio, o marcador vira string vazia e desaparece entre as vírgulas
(`..., 2.0, ,( SELECT ...` — ORA-00936 "missing expression", visto na linha 18 de um script
real gerado para a migração #901).

Corrige com o mesmo padrão já usado para outro campo numérico opcional "bare" no dicionário
(VRREFFOLHA, Ficha Financeira): regra de conversão `numero_ou_null`, que vira o literal
`NULL` quando vazio em vez de string vazia.

Revision ID: d49c05cd300d
Revises: 9e3f69bd1455
Create Date: 2026-07-27 17:58:55.901847

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd49c05cd300d'
down_revision: Union[str, None] = '9e3f69bd1455'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "MOVIMENTACOES_ESTRUTURA"
CAMPO_CODIGO = "NRTPMOVTRANSFM"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE template_campo SET regra_conversao = 'numero_ou_null'
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
            UPDATE template_campo SET regra_conversao = NULL
            WHERE campo = :campo_codigo
              AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
            """
        ),
        {"template_codigo": TEMPLATE_CODIGO, "campo_codigo": CAMPO_CODIGO},
    )
