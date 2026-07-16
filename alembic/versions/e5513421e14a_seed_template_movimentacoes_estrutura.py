"""seed template movimentacoes estrutura

Cadastra o template "Movimentações de Estrutura" (transferências, Seção 26.2): uma única
tabela (GPE_MOVIMENTACAO), PK sequencial, duas FKs via subquery embutida no texto do script
(vínculo por matrícula em GPE_VINCULOM, estrutura por código de integração em ESTRUTURAM) —
depende de Vínculo e de Estrutura simultaneamente. Dicionário e template de script
extraídos diretamente de "docs/planilhas-originais/12_MovimentacoesEstrutura_v07.xlsx".

Revision ID: e5513421e14a
Revises: 985b418e3c35
Create Date: 2026-07-16 07:24:21.898427

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5513421e14a'
down_revision: Union[str, None] = '985b418e3c35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "MOVIMENTACOES_ESTRUTURA"

# Texto extraído verbatim da célula Y2 do arquivo real.
TEMPLATE_SQL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DTFIMMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA, DTMOVIMENTRETRO, NRMOTIVOTRANSF ) "
    "VALUES ( @NRMOVIMENTACAO@, @NRORG@, ( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM "
    "GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA = '@NRVINCULOM@' ), "
    "@NRTIPOTRANSFER@, @NRTPMOVTRANSFM@,( SELECT MAX( NRESTRUTURAM ) FROM ESTRUTURAM WHERE "
    "NRORG = @NRORG@ AND CDINTESTRUTURA = '@NRESTRUTURAM@' ), '@DTINIMOVIMENT@', "
    "'@DTFIMMOVIMENT@', '@DSOBSERVACAO@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', "
    "@NRTIPOESTRUTURA@, '@DTMOVIMENTRETRO@', '@NRMOTIVOTRANSF@' );"
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
            "nome": "Movimentações de Estrutura",
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
        campo(ordem=1, origem="A", rotulo="Nr Vínculo", campo="NRVINCULOM", marcador="@NRVINCULOM@",
              destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="B", rotulo="Nr Tipo Transferência", campo="NRTIPOTRANSFER",
              marcador="@NRTIPOTRANSFER@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRTIPOTRANSFER",
              tipo="numerico", obrigatorio=True),
        campo(ordem=3, origem="C", rotulo="Nr Motivo Transferência (código)", campo="NRTPMOVTRANSFM",
              marcador="@NRTPMOVTRANSFM@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRTPMOVTRANSFM",
              tipo="numerico", obrigatorio=True),
        campo(ordem=4, origem="D", rotulo="Nr Estrutura (código de integração)", campo="NRESTRUTURAM",
              marcador="@NRESTRUTURAM@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRESTRUTURAM",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="E", rotulo="Obervação", campo="DSOBSERVACAO", marcador="@DSOBSERVACAO@",
              destino_tabela="GPE_MOVIMENTACAO", destino_coluna="DSOBSERVACAO", tipo="texto",
              regra_conversao="trim"),
        campo(ordem=6, origem="F", rotulo="Dt Fim Movimentação", campo="DTFIMMOVIMENT", marcador="@DTFIMMOVIMENT@",
              destino_tabela="GPE_MOVIMENTACAO", destino_coluna="DTFIMMOVIMENT", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=7, origem="G", rotulo="Dt Início Movimentação", campo="DTINIMOVIMENT", marcador="@DTINIMOVIMENT@",
              destino_tabela="GPE_MOVIMENTACAO", destino_coluna="DTINIMOVIMENT", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        # Bare/sem aspas no script — obrigatório para não gerar SQL inválido.
        campo(ordem=8, origem="H", rotulo="Nr Tipo Estrutura", campo="NRTIPOESTRUTURA",
              marcador="@NRTIPOESTRUTURA@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRTIPOESTRUTURA",
              tipo="numerico", obrigatorio=True),
        campo(ordem=9, origem="I", rotulo="Dt Mov Retroativa", campo="DTMOVIMENTRETRO", marcador="@DTMOVIMENTRETRO@",
              destino_tabela="GPE_MOVIMENTACAO", destino_coluna="DTMOVIMENTRETRO", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=10, origem="J", rotulo="Motivo da Transferência (texto)", campo="NRMOTIVOTRANSF",
              marcador="@NRMOTIVOTRANSF@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOTIVOTRANSF",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=11, origem="(gerado)", rotulo="Nº sequencial (gerado)", campo="NRMOVIMENTACAO",
              marcador="@NRMOVIMENTACAO@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_MOVIMENTACAO", gerador_pk_seed=36640),
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
                "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
