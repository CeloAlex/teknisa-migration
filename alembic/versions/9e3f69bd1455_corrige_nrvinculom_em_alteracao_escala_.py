"""corrige nrvinculom em alteracao_escala para subquery por matricula

O seed original (`cb8d6efd0c2e_seed_template_alteracao_escala.py`) documentava que a
coluna "Nr Vinculo" desse template traria o número interno de vínculo (NRVINCULOM) direto,
diferente dos demais templates de alteração (que resolvem por CDMATRICULA via subquery) —
achado que se provou errado com dado real: a organização 3749 tem "Nr Vinculo" com valor
`9272_000001` (formato de matrícula, `orgcode_seq`), gerando um INSERT sintaticamente
inválido (`NRVINCULOM = 9272_000001` sem aspas, e o campo era `tipo=numerico`).

Corrige para o mesmo padrão de ALTERACAO_SALARIAL/ALTERACAO_OCUPACAO/SITUACAO_FUNCIONAL:
campo vira `texto` (com `trim`) e o script passa a resolver o vínculo via
`(SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA =
'@NRVINCULOM@')`, igual aos demais.

Revision ID: 9e3f69bd1455
Revises: 0ff1ded08d83
Create Date: 2026-07-27 17:11:15.095488

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9e3f69bd1455'
down_revision: Union[str, None] = '0ff1ded08d83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ALTERACAO_ESCALA"

TEMPLATE_SQL_ANTIGO = (
    "INSERT INTO GPE_ALTEESCALA ( NRORG, NRALTEESCALA, NRVINCULOM, DTINIESCALA, "
    "NRESCALATRABM, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, DSOBSERVACAO ) VALUES ( "
    "@NRORG@, @NRALTEESCALA@, @NRVINCULOM@, '@DTINIESCALA@', @NRESCALATRABM@, SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@', 'Gerado via migracao' );"
)

TEMPLATE_SQL_NOVO = (
    "INSERT INTO GPE_ALTEESCALA ( NRORG, NRALTEESCALA, NRVINCULOM, DTINIESCALA, "
    "NRESCALATRABM, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, DSOBSERVACAO ) VALUES ( "
    "@NRORG@, @NRALTEESCALA@, ( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE "
    "NRORG = @NRORG@ AND CDMATRICULA = '@NRVINCULOM@' ), '@DTINIESCALA@', @NRESCALATRABM@, "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 'Gerado via migracao' );"
)


def upgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            UPDATE template_campo SET tipo = 'texto', regra_conversao = 'trim'
            WHERE template_id = :template_id AND campo = 'NRVINCULOM'
            """
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            """
            UPDATE template_script SET template_sql = :sql
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 1
            """
        ),
        {"template_id": template_id, "sql": TEMPLATE_SQL_NOVO},
    )


def downgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            UPDATE template_campo SET tipo = 'numerico', regra_conversao = NULL
            WHERE template_id = :template_id AND campo = 'NRVINCULOM'
            """
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            """
            UPDATE template_script SET template_sql = :sql
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 1
            """
        ),
        {"template_id": template_id, "sql": TEMPLATE_SQL_ANTIGO},
    )
