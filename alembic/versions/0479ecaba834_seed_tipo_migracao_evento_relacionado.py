"""seed tipo migracao evento relacionado

Cria um `TipoMigracao` próprio para o template EVENTO_RELACIONADO (769ec8de265b) — mesmo
padrão já usado para cada evento eSocial (ex. ESOCIAL_S2230): um único
`tipo_migracao_template` obrigatório, sem sequência travada (`sequencia_obrigatoria=false`,
já que não há outro template dependente aqui) e com concorrência permitida
(`permite_concorrencia=true`), igual aos demais tipos "avulsos" de template único.

Revision ID: 0479ecaba834
Revises: 769ec8de265b
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0479ecaba834'
down_revision: Union[str, None] = '769ec8de265b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "EVENTO_RELACIONADO"
TIPO_CODIGO = "MIG_EVENTO_RELACIONADO"


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    tipo_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', true, 'SCRIPT', false)
            RETURNING id
            """
        ),
        {"codigo": TIPO_CODIGO, "nome": "Evento Relacionado (Vínculo/Estrutura/Ocupação)"},
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
            VALUES (:tipo_id, :template_id, 1, true)
            """
        ),
        {"tipo_id": tipo_id, "template_id": template_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM tipo_migracao_template
            WHERE tipo_migracao_id IN (SELECT id FROM tipo_migracao WHERE codigo = :tipo_codigo)
            """
        ),
        {"tipo_codigo": TIPO_CODIGO},
    )
    conn.execute(sa.text("DELETE FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": TIPO_CODIGO})
