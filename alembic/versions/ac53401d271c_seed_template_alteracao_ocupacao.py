"""seed template alteracao ocupacao

Cadastra o template "Alteração de Ocupação" (Seção 26.2): uma única tabela
(GPE_ALTEOCUPACAO), PK sequencial, duas FKs via subquery embutida no texto do script
(vínculo por matrícula em GPE_VINCULOM, ocupação por código de integração em
GPE_OCUPACAOH). Dicionário e template de script extraídos diretamente de
"docs/planilhas-originais/08_AlteracaoOcupacao_v11.xlsx" (835 linhas reais).

Revision ID: ac53401d271c
Revises: cb8d6efd0c2e
Create Date: 2026-07-16 07:20:44.885803

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ac53401d271c'
down_revision: Union[str, None] = 'cb8d6efd0c2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ALTERACAO_OCUPACAO"

# Texto extraído verbatim da célula I2 do arquivo real, com a mesma troca do operador
# técnico fixo por @USUARIO_TECNICO@.
TEMPLATE_SQL = (
    "INSERT INTO GPE_ALTEOCUPACAO ( NRORG, NRALTEOCUPACAO, NRVINCULOM, DTINIOCUPACAO, "
    "NROCUPACAOM, NRTPMODALIDSAL, DSOBSERVACAO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "NRTIPOOCUPACAO ) VALUES ( @NRORG@, @NRALTEOCUPACAO@, ( SELECT /*MAX(*/NRVINCULOM/*)*/ "
    "FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA = '@VINC@' ), "
    "'@DTINIOCUPACAO@', ( SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ "
    "AND CDINTEGRACAO = '@NROCUPA@' ), 1, 'Alteracao incluida via migracao realizada em: ' "
    "|| TO_CHAR(SYSDATE), SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 1 );"
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
            "nome": "Alteração de Ocupação",
            "versao": "11",
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
        campo(ordem=1, origem="A", rotulo="Nr Vinculo", campo="VINC", marcador="@VINC@",
              destino_tabela="GPE_ALTEOCUPACAO", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="B", rotulo="Dt Alteracao", campo="DTINIOCUPACAO", marcador="@DTINIOCUPACAO@",
              destino_tabela="GPE_ALTEOCUPACAO", destino_coluna="DTINIOCUPACAO", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="Ocupacao (código de integração)", campo="NROCUPA",
              marcador="@NROCUPA@", destino_tabela="GPE_ALTEOCUPACAO", destino_coluna="NROCUPACAOM",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=4, origem="(gerado)", rotulo="Nº sequencial (gerado)", campo="NRALTEOCUPACAO",
              marcador="@NRALTEOCUPACAO@", destino_tabela="GPE_ALTEOCUPACAO", destino_coluna="NRALTEOCUPACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTEOCUPACAO", gerador_pk_seed=83350),
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
                "DELETE FROM GPE_ALTEOCUPACAO WHERE NRORG = @NRORG@ AND NRALTEOCUPACAO = @NRALTEOCUPACAO@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
