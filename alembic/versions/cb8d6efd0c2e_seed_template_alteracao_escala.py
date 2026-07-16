"""seed template alteracao escala

Cadastra o template "Alteração de Escala de Trabalho" (Seção 26.2): uma única tabela
(GPE_ALTEESCALA), PK sequencial via Key Resolution Service. Achado ao conferir o arquivo
real: a coluna "Nr Vinculo" traz o número interno de vínculo (NRVINCULOM) diretamente, não a
matrícula — diferente do padrão de subquery por CDMATRICULA usado nos demais templates de
alteração; portado fielmente ao dicionário (nenhuma mudança de motor necessária, já que
tanto a passagem direta quanto a subquery são apenas texto de template). Volume real: 3.587
linhas — o maior entre os treze. Dicionário e template de script extraídos diretamente de
"docs/planilhas-originais/07_Alteracao de Escala_v10.xlsx".

Revision ID: cb8d6efd0c2e
Revises: 6c31b8f0babc
Create Date: 2026-07-16 07:20:03.807787

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'cb8d6efd0c2e'
down_revision: Union[str, None] = '6c31b8f0babc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ALTERACAO_ESCALA"

# Texto extraído verbatim da célula J2 do arquivo real.
TEMPLATE_SQL = (
    "INSERT INTO GPE_ALTEESCALA ( NRORG, NRALTEESCALA, NRVINCULOM, DTINIESCALA, "
    "NRESCALATRABM, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, DSOBSERVACAO ) VALUES ( "
    "@NRORG@, @NRALTEESCALA@, @NRVINCULOM@, '@DTINIESCALA@', @NRESCALATRABM@, SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@', 'Gerado via migracao' );"
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
            "nome": "Alteração de Escala de Trabalho",
            "versao": "10",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Dados",
            "header_row": 2,
            "data_start_row": 3,
        },
    ).scalar_one()

    def campo(**kw):
        base = {
            "template_id": template_id, "tamanho_maximo": None, "obrigatorio": False,
            "valor_padrao": None, "regra_conversao": None, "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
        }
        base.update(kw)
        return base

    campos = [
        # Bare/sem aspas no script — obrigatório para não gerar SQL inválido.
        campo(ordem=1, origem="A", rotulo="Nr Vinculo (nº interno)", campo="NRVINCULOM",
              marcador="@NRVINCULOM@", destino_tabela="GPE_ALTEESCALA", destino_coluna="NRVINCULOM",
              tipo="numerico", obrigatorio=True),
        campo(ordem=2, origem="B", rotulo="Dt Alteracao", campo="DTINIESCALA", marcador="@DTINIESCALA@",
              destino_tabela="GPE_ALTEESCALA", destino_coluna="DTINIESCALA", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="Escala", campo="NRESCALATRABM", marcador="@NRESCALATRABM@",
              destino_tabela="GPE_ALTEESCALA", destino_coluna="NRESCALATRABM", tipo="numerico",
              obrigatorio=True),
        campo(ordem=4, origem="(gerado)", rotulo="Nº sequencial (gerado)", campo="NRALTEESCALA",
              marcador="@NRALTEESCALA@", destino_tabela="GPE_ALTEESCALA", destino_coluna="NRALTEESCALA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTEESCALA", gerador_pk_seed=14957),
    ]

    conn.execute(
        sa.text(
            """
            INSERT INTO template_campo (template_id, ordem, origem, rotulo, campo, marcador,
                                         destino_tabela, destino_coluna, tipo, tamanho_maximo,
                                         obrigatorio, valor_padrao, regra_conversao, eh_pk,
                                         gerador_pk, gerador_pk_contador, gerador_pk_seed)
            VALUES (:template_id, :ordem, :origem, :rotulo, :campo, :marcador, :destino_tabela,
                    :destino_coluna, :tipo, :tamanho_maximo, :obrigatorio, :valor_padrao,
                    :regra_conversao, :eh_pk, :gerador_pk, :gerador_pk_contador, :gerador_pk_seed)
            """
        ),
        campos,
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO template_script (template_id, operacao, dialeto_banco, ordem,
                                          condicao_campo, template_sql, template_rollback)
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', 1, NULL, :template_sql, :template_rollback)
            """
        ),
        {
            "template_id": template_id,
            "template_sql": TEMPLATE_SQL,
            "template_rollback": (
                "DELETE FROM GPE_ALTEESCALA WHERE NRORG = @NRORG@ AND NRALTEESCALA = @NRALTEESCALA@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
