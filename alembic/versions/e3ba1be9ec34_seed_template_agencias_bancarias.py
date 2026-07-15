"""seed template agencias bancarias

Migração de dados (não de esquema): cadastra o template "Agências Bancárias" — o mais
simples dos treze (sem PK sequencial, sem FK) — como configuração de metadados, replicando
o dicionário de dados e o template de script real extraído de
docs/planilhas-originais/00_Agencias_Bancarias.xlsx (Seção 13.2 / Seção 24 / Anexo E).

Revision ID: e3ba1be9ec34
Revises: bd07a3970c79
Create Date: 2026-07-15 20:11:46.363909

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3ba1be9ec34'
down_revision: Union[str, None] = 'bd07a3970c79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "AGENCIAS_BANCARIAS"
TIPO_MIGRACAO_CODIGO = "MIG_AGENCIAS_INDIVIDUAL"

# Template de INSERT extraído diretamente da coluna E do arquivo real
# 00_Agencias_Bancarias.xlsx (mesma formatação, incluindo o espaçamento original de
# "CDBANCO,CDAGENCIA"). O COMMIT final é responsabilidade do Script Generator, não do
# template em si (Seção 10.1 — controle de commit por lote, não por linha).
TEMPLATE_SQL_INCLUSAO = (
    "INSERT INTO AGENCIA ( CDBANCO,CDAGENCIA, NMAGENCIA, NRORG, DTINCLUSAO, CDOPERINCLUSAO, "
    "NRORGINCLUSAO, IDATIVO ) VALUES ( '@CDBANCO@', '@CDAGENCIA@', '@NMAGENCIA@', @NRORG@, "
    "SYSDATE,'@USUARIO_TECNICO@', @NRORG@, 'S' );"
)
TEMPLATE_ROLLBACK_INCLUSAO = (
    "DELETE FROM AGENCIA WHERE NRORG = @NRORG@ AND CDBANCO = '@CDBANCO@' AND "
    "CDAGENCIA = '@CDAGENCIA@';"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, sheet_name,
                                   header_row, data_start_row, ativo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :sheet_name,
                    :header_row, :data_start_row, true)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "Agências Bancárias",
            "versao": "1.0",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Sheet1",
            "header_row": 1,
            "data_start_row": 2,
        },
    ).scalar_one()

    campos = [
        {
            "ordem": 1, "origem": "A", "rotulo": "Banco", "campo": "CDBANCO",
            "marcador": "@CDBANCO@", "destino_tabela": "AGENCIA", "destino_coluna": "CDBANCO",
            "tipo": "texto", "tamanho_maximo": 3, "obrigatorio": True,
            "regra_conversao": "trim", "eh_pk": True,
        },
        {
            "ordem": 2, "origem": "B", "rotulo": "Cd. Agência", "campo": "CDAGENCIA",
            "marcador": "@CDAGENCIA@", "destino_tabela": "AGENCIA", "destino_coluna": "CDAGENCIA",
            "tipo": "texto", "tamanho_maximo": 4, "obrigatorio": True,
            "regra_conversao": "trim", "eh_pk": True,
        },
        {
            "ordem": 3, "origem": "C", "rotulo": "Agência", "campo": "NMAGENCIA",
            "marcador": "@NMAGENCIA@", "destino_tabela": "AGENCIA", "destino_coluna": "NMAGENCIA",
            "tipo": "texto", "tamanho_maximo": 60, "obrigatorio": True,
            "regra_conversao": "trim", "eh_pk": False,
        },
        {
            "ordem": 4, "origem": "parametro_execucao.NRORG", "rotulo": "Organização",
            "campo": "NRORG", "marcador": "@NRORG@", "destino_tabela": "AGENCIA",
            "destino_coluna": "NRORG", "tipo": "numerico", "tamanho_maximo": None,
            "obrigatorio": True, "regra_conversao": None, "eh_pk": False,
        },
    ]
    for campo in campos:
        conn.execute(
            sa.text(
                """
                INSERT INTO template_campo (template_id, ordem, origem, rotulo, campo,
                                             marcador, destino_tabela, destino_coluna, tipo,
                                             tamanho_maximo, obrigatorio, regra_conversao, eh_pk,
                                             gerador_pk)
                VALUES (:template_id, :ordem, :origem, :rotulo, :campo, :marcador,
                        :destino_tabela, :destino_coluna, :tipo, :tamanho_maximo, :obrigatorio,
                        :regra_conversao, :eh_pk, false)
                """
            ),
            {**campo, "template_id": template_id},
        )

    conn.execute(
        sa.text(
            """
            INSERT INTO template_script (template_id, operacao, dialeto_banco, template_sql,
                                          template_rollback)
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', :template_sql, :template_rollback)
            """
        ),
        {
            "template_id": template_id,
            "template_sql": TEMPLATE_SQL_INCLUSAO,
            "template_rollback": TEMPLATE_ROLLBACK_INCLUSAO,
        },
    )

    tipo_migracao_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', false, 'SCRIPT', false)
            RETURNING id
            """
        ),
        {
            "codigo": TIPO_MIGRACAO_CODIGO,
            "nome": "Migração de Agências Bancárias (importação individual)",
        },
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
            VALUES (:tipo_migracao_id, :template_id, 1, true)
            """
        ),
        {"tipo_migracao_id": tipo_migracao_id, "template_id": template_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": TIPO_MIGRACAO_CODIGO})
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
