"""adiciona dominio de valores em tp ocupacao

Revision ID: ae5c7211f308
Revises: da18bbdba361
Create Date: 2026-08-13 11:23:27.037158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae5c7211f308'
down_revision: Union[str, None] = 'da18bbdba361'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TEMPLATE_CODIGO = "OCUPACAO"
DOMINIO_TP_OCUPACAO = "1,2,3,4,5,6,7"


def upgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            "UPDATE template_campo SET dominio_valores = :dominio "
            "WHERE template_id = :template_id AND campo = 'NRTIPOOCUPACAO'"
        ),
        {"template_id": template_id, "dominio": DOMINIO_TP_OCUPACAO},
    )


def downgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            "UPDATE template_campo SET dominio_valores = NULL "
            "WHERE template_id = :template_id AND campo = 'NRTIPOOCUPACAO'"
        ),
        {"template_id": template_id},
    )
