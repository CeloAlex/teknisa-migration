"""adiciona dependentes aos tipos migracao integral

Registra o template DEPENDENTES (migração anterior) como o 14º membro dos dois tipos de
"Migração Integral do Cliente" (`dc048688bf05_seed_tipos_migracao_integral.py`):

- MIG_INTEGRAL_INDIVIDUAL: ordem 14, opcional (mesmo padrão dos outros 13 — cada template
  pode ser importado isoladamente).
- MIG_INTEGRAL_ONBOARDING: ordem 14, obrigatório, com dependência de VINCULO (Seção 26.3 —
  Dependentes só libera depois do Vínculo do titular já estar validado, já que o script
  resolve a matrícula via subquery em GPE_VINCULOM).

Revision ID: 0216a0f1b7f7
Revises: 0cb18dd6c579
Create Date: 2026-07-27 15:32:50.326873

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0216a0f1b7f7'
down_revision: Union[str, None] = '0cb18dd6c579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "DEPENDENTES"
TIPO_INDIVIDUAL_CODIGO = "MIG_INTEGRAL_INDIVIDUAL"
TIPO_ONBOARDING_CODIGO = "MIG_INTEGRAL_ONBOARDING"
ORDEM = 14


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()
    vinculo_template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": "VINCULO"}
    ).scalar_one()

    tipo_individual_id = conn.execute(
        sa.text("SELECT id FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": TIPO_INDIVIDUAL_CODIGO}
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
            VALUES (:tipo_id, :template_id, :ordem, false)
            """
        ),
        {"tipo_id": tipo_individual_id, "template_id": template_id, "ordem": ORDEM},
    )

    tipo_onboarding_id = conn.execute(
        sa.text("SELECT id FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": TIPO_ONBOARDING_CODIGO}
    ).scalar_one()
    tmt_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
            VALUES (:tipo_id, :template_id, :ordem, true)
            RETURNING id
            """
        ),
        {"tipo_id": tipo_onboarding_id, "template_id": template_id, "ordem": ORDEM},
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao_template_dependencia (tipo_migracao_template_id, depende_de_template_id)
            VALUES (:tmt_id, :dep_template_id)
            """
        ),
        {"tmt_id": tmt_id, "dep_template_id": vinculo_template_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM tipo_migracao_template_dependencia
            WHERE tipo_migracao_template_id IN (
                SELECT tmt.id FROM tipo_migracao_template tmt
                JOIN tipo_migracao tm ON tm.id = tmt.tipo_migracao_id
                JOIN template t ON t.id = tmt.template_id
                WHERE tm.codigo = :tipo_codigo AND t.codigo = :template_codigo
            )
            """
        ),
        {"tipo_codigo": TIPO_ONBOARDING_CODIGO, "template_codigo": TEMPLATE_CODIGO},
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM tipo_migracao_template
            WHERE template_id = (SELECT id FROM template WHERE codigo = :template_codigo)
              AND tipo_migracao_id IN (
                  SELECT id FROM tipo_migracao WHERE codigo IN (:tipo_individual, :tipo_onboarding)
              )
            """
        ),
        {
            "template_codigo": TEMPLATE_CODIGO,
            "tipo_individual": TIPO_INDIVIDUAL_CODIGO,
            "tipo_onboarding": TIPO_ONBOARDING_CODIGO,
        },
    )
