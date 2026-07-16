"""seed template situacao funcional

Cadastra o template "Situação Funcional" (afastamentos, Seção 26.2): uma única tabela
(GPE_ALTESITUFUNC), PK sequencial, FK a Vínculo via subquery por matrícula. Traz dado de
saúde sensível (CDTABECDI/CDDIAGNOST, ex. CID-10) que exige as mesmas salvaguardas de LGPD
já descritas para Vínculo (Seção 12) — ainda não implementadas nesta fase (mascaramento de
dados sensíveis é tratado na camada de segurança/portal, fora do escopo do motor genérico).
Dicionário e template de script extraídos diretamente de
"docs/planilhas-originais/09_SituacaoFuncional_v07.xlsx".

Revision ID: bebd0b36fb89
Revises: ac53401d271c
Create Date: 2026-07-16 07:21:24.438550

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bebd0b36fb89'
down_revision: Union[str, None] = 'ac53401d271c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "SITUACAO_FUNCIONAL"

# Texto extraído verbatim da célula P2 do arquivo real.
TEMPLATE_SQL = (
    "INSERT INTO GPE_ALTESITUFUNC ( NRALTESITUFUNC, NRORG, NRSITUFUNCM, NRVINCULOM, "
    "DTINISITUFUNC, DTFIMSITUFUNC, CDTABECDI, CDDIAGNOST, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRALTESITUFUNC@, @NRORG@, @NRSITUFUNCM@, "
    "( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND "
    "CDMATRICULA = '@NRVINCULOM@' ), '@DTINISITUFUNC@', '@DTFIMSITUFUNC@', '@CDTABECDI@', "
    "'@CDDIAGNOST@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
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
            "nome": "Situação Funcional",
            "versao": "7",
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
        # Marcador @NRVINCULOM@ traz a matrícula (usada como parâmetro da subquery) — o
        # nome do marcador replica exatamente o que está no script real da planilha.
        campo(ordem=1, origem="A", rotulo="Nr Vinculo", campo="NRVINCULOM", marcador="@NRVINCULOM@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="B", rotulo="Sit. Funcional", campo="NRSITUFUNCM", marcador="@NRSITUFUNCM@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="NRSITUFUNCM", tipo="numerico",
              obrigatorio=True),
        campo(ordem=3, origem="C", rotulo="Data Inicio", campo="DTINISITUFUNC", marcador="@DTINISITUFUNC@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="DTINISITUFUNC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Data Fim", campo="DTFIMSITUFUNC", marcador="@DTFIMSITUFUNC@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="DTFIMSITUFUNC", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=5, origem="E", rotulo="CDTABECDI", campo="CDTABECDI", marcador="@CDTABECDI@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="CDTABECDI", tipo="texto",
              regra_conversao="trim"),
        campo(ordem=6, origem="F", rotulo="CDDIAGNOST (dado de saúde sensível — LGPD)", campo="CDDIAGNOST",
              marcador="@CDDIAGNOST@", destino_tabela="GPE_ALTESITUFUNC", destino_coluna="CDDIAGNOST",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=7, origem="(gerado)", rotulo="Nº sequencial (gerado)", campo="NRALTESITUFUNC",
              marcador="@NRALTESITUFUNC@", destino_tabela="GPE_ALTESITUFUNC", destino_coluna="NRALTESITUFUNC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTESITUFUNC", gerador_pk_seed=6291),
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
                "DELETE FROM GPE_ALTESITUFUNC WHERE NRORG = @NRORG@ AND NRALTESITUFUNC = @NRALTESITUFUNC@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
