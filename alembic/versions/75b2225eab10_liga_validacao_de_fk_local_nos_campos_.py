"""liga validacao de fk local nos campos que resolvem por subquery

Preenche `fk_template_codigo`/`fk_campo` (migração anterior) nos campos que hoje viram uma
subquery `SELECT ... WHERE CDMATRICULA = '@X@'`/`WHERE CDINTESTRUTURA = '@X@'` no script —
levantados via grep em todos os `TEMPLATE_SQL` dos 13 templates (`CDMATRICULA = '@`):
Ficha Financeira, Alteração Salarial/Ocupação/Escala, Situação Funcional, Férias,
Movimentações de Estrutura (2 campos: vínculo e estrutura) e Dependentes.

Revision ID: 75b2225eab10
Revises: 6ddaa5b710b7
Create Date: 2026-07-27 18:43:49.186815

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '75b2225eab10'
down_revision: Union[str, None] = '6ddaa5b710b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (template_codigo, campo, fk_template_codigo, fk_campo)
LIGACOES = [
    ("MOVIMENTACOES_ESTRUTURA", "NRESTRUTURAM", "ESTRUTURA", "NRESTRUTURA"),
    ("MOVIMENTACOES_ESTRUTURA", "NRVINCULOM", "VINCULO", "CDMATRICULA"),
    ("FICHA_FINANCEIRA", "CDMATRICULA", "VINCULO", "CDMATRICULA"),
    ("ALTERACAO_SALARIAL", "CDMATRICULA", "VINCULO", "CDMATRICULA"),
    ("ALTERACAO_OCUPACAO", "VINC", "VINCULO", "CDMATRICULA"),
    ("ALTERACAO_ESCALA", "NRVINCULOM", "VINCULO", "CDMATRICULA"),
    ("SITUACAO_FUNCIONAL", "NRVINCULOM", "VINCULO", "CDMATRICULA"),
    ("FERIAS", "NRVINCULOM", "VINCULO", "CDMATRICULA"),
    ("DEPENDENTES", "NRVINCULOM", "VINCULO", "CDMATRICULA"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for template_codigo, campo, fk_template_codigo, fk_campo in LIGACOES:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET fk_template_codigo = :fk_template_codigo, fk_campo = :fk_campo
                WHERE campo = :campo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {
                "template_codigo": template_codigo,
                "campo": campo,
                "fk_template_codigo": fk_template_codigo,
                "fk_campo": fk_campo,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for template_codigo, campo, _fk_template_codigo, _fk_campo in LIGACOES:
        conn.execute(
            sa.text(
                """
                UPDATE template_campo SET fk_template_codigo = NULL, fk_campo = NULL
                WHERE campo = :campo
                  AND template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
                """
            ),
            {"template_codigo": template_codigo, "campo": campo},
        )
