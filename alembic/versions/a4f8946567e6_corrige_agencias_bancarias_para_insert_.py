"""corrige agencias_bancarias para insert idempotente (agencia e catalogo global entre orgs)

Investigando o ORA-00001 (unique constraint PK_AGENCIA) relatado pelo usuário na aplicação
real da migração 901 (org 3749): a PK de AGENCIA no Oracle é (CDBANCO, CDAGENCIA) — SEM
NRORG. Consulta direta ao banco de teste confirmou que a tabela é catálogo compartilhado
entre organizações (13424 linhas, 116 NRORG distintos) — os códigos '001'/'0019',
'001'/'0051' e '033'/'0125' do arquivo da Mana já existiam lá, cadastrados por outro NRORG
(1410). O INSERT incondicional do template sempre falha nesse cenário, comum: bancos e
agências são dados públicos (Febraban), reaproveitados entre clientes.

Corrige para `INSERT ... SELECT ... WHERE NOT EXISTS` — insere só se a agência ainda não
existir (por qualquer org); se já existir, o comando simplesmente não afeta linha nenhuma
(sem erro), e a migração pode seguir referenciando o registro já compartilhado.

Revision ID: a4f8946567e6
Revises: f8f666486609
Create Date: 2026-07-28 12:51:07.630469

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a4f8946567e6'
down_revision: Union[str, None] = 'f8f666486609'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "AGENCIAS_BANCARIAS"

TEMPLATE_SQL_ANTIGO = (
    "INSERT INTO AGENCIA ( CDBANCO,CDAGENCIA, NMAGENCIA, NRORG, DTINCLUSAO, "
    "CDOPERINCLUSAO, NRORGINCLUSAO, IDATIVO ) VALUES ( '@CDBANCO@', '@CDAGENCIA@', "
    "'@NMAGENCIA@', @NRORG@, SYSDATE,'@USUARIO_TECNICO@', @NRORG@, 'S' );"
)

TEMPLATE_SQL_NOVO = (
    "INSERT INTO AGENCIA ( CDBANCO, CDAGENCIA, NMAGENCIA, NRORG, DTINCLUSAO, "
    "CDOPERINCLUSAO, NRORGINCLUSAO, IDATIVO ) SELECT '@CDBANCO@', '@CDAGENCIA@', "
    "'@NMAGENCIA@', @NRORG@, SYSDATE, '@USUARIO_TECNICO@', @NRORG@, 'S' FROM DUAL WHERE NOT "
    "EXISTS ( SELECT 1 FROM AGENCIA WHERE CDBANCO = '@CDBANCO@' AND CDAGENCIA = "
    "'@CDAGENCIA@' );"
)


def upgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

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
            UPDATE template_script SET template_sql = :sql
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 1
            """
        ),
        {"template_id": template_id, "sql": TEMPLATE_SQL_ANTIGO},
    )
