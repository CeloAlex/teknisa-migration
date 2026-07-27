"""corrige mapeamento de colunas ficha financeira

O layout real do arquivo de Ficha Financeira usado pelo cliente não bate com o do
`13_FichaFinanceira_v15.xlsx` de referência (que gerou o seed original em `157982505200`).
Confirmado pelo usuário o layout real:

    A Tp Movimento | B Nr. Vínculo | C Nr. Evento | D Valor | E Descrição do Cálculo |
    F Data de Ocorrência | G Valor de Referência | H Data de Competência

Ou seja, na prática, "Competência" foi para o fim (H) e os demais campos (Nr. Evento,
Valor, Descrição, Data de Ocorrência, Valor de Referência) andaram uma coluna para trás
(D->C, E->D, F->E, G->F, H->G). Isso bate com os dados reais já importados (Seção
investigada na conversa: coluna D sempre com valor monetário, coluna E sempre vazia — E
agora é a Descrição, opcional, então ficar vazia não é mais erro).

Revision ID: 021e22cab3d9
Revises: a1ec72c59c09
Create Date: 2026-07-27 12:13:32.587194

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '021e22cab3d9'
down_revision: Union[str, None] = 'a1ec72c59c09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "FICHA_FINANCEIRA"

# campo -> (origem_antiga, ordem_antiga, origem_nova, ordem_nova)
REMAPEAMENTO = [
    ("NRTIPOMOVIMENT", "A", 1, "A", 1),
    ("CDMATRICULA", "B", 2, "B", 2),
    ("DTMESCOMPETENC", "C", 3, "H", 8),
    ("NREVENTO", "D", 4, "C", 3),
    ("VREVENTOFOLHA", "E", 5, "D", 4),
    ("DSITEMCALCFOLHA", "F", 6, "E", 5),
    ("DTOCORRENCIA", "G", 7, "F", 6),
    ("VRREFFOLHA", "H", 8, "G", 7),
]


def upgrade() -> None:
    conn = op.get_bind()
    for campo_codigo, _origem_antiga, _ordem_antiga, origem_nova, ordem_nova in REMAPEAMENTO:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET origem = :origem, ordem = :ordem
                WHERE campo = :campo_codigo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {
                "template_codigo": TEMPLATE_CODIGO,
                "campo_codigo": campo_codigo,
                "origem": origem_nova,
                "ordem": ordem_nova,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for campo_codigo, origem_antiga, ordem_antiga, _origem_nova, _ordem_nova in REMAPEAMENTO:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET origem = :origem, ordem = :ordem
                WHERE campo = :campo_codigo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {
                "template_codigo": TEMPLATE_CODIGO,
                "campo_codigo": campo_codigo,
                "origem": origem_antiga,
                "ordem": ordem_antiga,
            },
        )
