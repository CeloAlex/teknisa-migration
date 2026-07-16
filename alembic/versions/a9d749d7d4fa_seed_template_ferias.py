"""seed template ferias

Cadastra o template "Férias e Gozo de Férias" (Seção 26.2/26.4) — o único dos treze com
relação um-para-N por linha de origem: cada linha sempre gera um período aquisitivo
(FPA_FERIAS) e, condicionalmente, um período de gozo associado (FPA_GOZOFERIAS, cuja PK
referencia a PK recém-gerada de FPA_FERIAS), disparado apenas quando a data de início de
gozo está preenchida — o mesmo mecanismo de bloco condicional (`condicao_campo`) já usado
para o endereço de Estrutura na Fase 3, reaproveitado sem nenhuma mudança de motor.
Dicionário e templates de script extraídos diretamente de
"docs/planilhas-originais/10_Ferias_(padrão)_v07.xlsx" (2.162 linhas reais).

Revision ID: a9d749d7d4fa
Revises: bebd0b36fb89
Create Date: 2026-07-16 07:22:24.965535

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9d749d7d4fa'
down_revision: Union[str, None] = 'bebd0b36fb89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "FERIAS"

# Bloco 1 (sempre gerado): período aquisitivo. Texto extraído verbatim da célula AF2.
TEMPLATE_SQL_FERIAS = (
    "INSERT INTO FPA_FERIAS ( NRFERIAS, NRVINCULOM, NRTIPOFERIAS, NRORG, DTINIAQUISICAO, "
    "DTFIMAQUISICAO, QTMESAFASTAMENT, QTFALTASPERIODO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, IDCONTROLFERIAS ) VALUES ( @NRFERIAS@, (SELECT /*MAX(*/NRVINCULOM/*)*/ "
    "FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA = '@NRVINCULOM@' ), '1', "
    "@NRORG@, '@DTINIAQUISICAO@', '@DTFIMAQUISICAO@', '@QTMESAFASTAMENT@', "
    "'@QTFALTASPERIODO@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@IDCONTROLFERIAS@' );"
)

# Bloco 2 (condicional a _TEM_GOZO): período de gozo. Texto extraído verbatim da célula AG2.
TEMPLATE_SQL_GOZO = (
    "INSERT INTO FPA_GOZOFERIAS ( NRGOZOFERIAS, NRFERIAS, NRORG, DTINIGOZOFERIAS, "
    "DTFIMGOZOFERIAS, QTDIASABONOFERI, DTRETORNOFERIAS, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, DSGOZOFERIAS ) VALUES ( @NRGOZOFERIAS@, @NRFERIAS@, @NRORG@, "
    "'@DTINIGOZOFERIAS@', '@DTFIMGOZOFERIAS@', '@QTDIASABONOFERI@', '@DTRETORNOFERIAS@', "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 'Migrado' );"
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
            "nome": "Férias e Gozo de Férias",
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
        campo(ordem=1, origem="A", rotulo="VÍNCULO", campo="NRVINCULOM", marcador="@NRVINCULOM@",
              destino_tabela="FPA_FERIAS", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="B", rotulo="INÍCIO AQUISIÇÃO", campo="DTINIAQUISICAO", marcador="@DTINIAQUISICAO@",
              destino_tabela="FPA_FERIAS", destino_coluna="DTINIAQUISICAO", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="FIM AQUISIÇÃO", campo="DTFIMAQUISICAO", marcador="@DTFIMAQUISICAO@",
              destino_tabela="FPA_FERIAS", destino_coluna="DTFIMAQUISICAO", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="MÊS AFASTAMENTO", campo="QTMESAFASTAMENT", marcador="@QTMESAFASTAMENT@",
              destino_tabela="FPA_FERIAS", destino_coluna="QTMESAFASTAMENT", tipo="numerico",
              regra_conversao="numero_decimal"),
        campo(ordem=5, origem="E", rotulo="STATUS FÉRIAS", campo="IDCONTROLFERIAS", marcador="@IDCONTROLFERIAS@",
              destino_tabela="FPA_FERIAS", destino_coluna="IDCONTROLFERIAS", tipo="texto",
              regra_conversao="trim"),
        # Coluna F (Dias Afastamento) é lida na planilha original mas não referenciada por
        # nenhum INSERT (uso apenas interno na lógica de status) — não cadastrada.
        campo(ordem=6, origem="G", rotulo="INICIO GOZO", campo="DTINIGOZOFERIAS", marcador="@DTINIGOZOFERIAS@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="DTINIGOZOFERIAS", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=7, origem="H", rotulo="FIM GOZO", campo="DTFIMGOZOFERIAS", marcador="@DTFIMGOZOFERIAS@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="DTFIMGOZOFERIAS", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=8, origem="I", rotulo="DT RETORNO FÉRIAS", campo="DTRETORNOFERIAS", marcador="@DTRETORNOFERIAS@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="DTRETORNOFERIAS", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=9, origem="J", rotulo="DIAS ABONO", campo="QTDIASABONOFERI", marcador="@QTDIASABONOFERI@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="QTDIASABONOFERI", tipo="numerico",
              regra_conversao="numero_decimal"),
        campo(ordem=10, origem="K", rotulo="DIAS FALTAS MÊS", campo="QTFALTASPERIODO", marcador="@QTFALTASPERIODO@",
              destino_tabela="FPA_FERIAS", destino_coluna="QTFALTASPERIODO", tipo="numerico",
              regra_conversao="numero_decimal"),
        # --- campo derivado: condição do bloco de gozo (Seção 26.4) ---
        campo(ordem=11, origem="campo:DTINIGOZOFERIAS", rotulo="Tem gozo? (derivado)",
              campo="_TEM_GOZO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- campos com PK sequencial ---
        campo(ordem=12, origem="(gerado)", rotulo="Nº período aquisitivo (gerado)", campo="NRFERIAS",
              marcador="@NRFERIAS@", destino_tabela="FPA_FERIAS", destino_coluna="NRFERIAS",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_FERIAS", gerador_pk_seed=0),
        campo(ordem=13, origem="(gerado)", rotulo="Nº período de gozo (gerado)", campo="NRGOZOFERIAS",
              marcador="@NRGOZOFERIAS@", destino_tabela="FPA_GOZOFERIAS", destino_coluna="NRGOZOFERIAS",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_GOZOFERIAS", gerador_pk_seed=0),
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
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', :ordem, :condicao_campo,
                    :template_sql, :template_rollback)
            """
        ),
        [
            {
                "template_id": template_id, "ordem": 1, "condicao_campo": None,
                "template_sql": TEMPLATE_SQL_FERIAS,
                "template_rollback": "DELETE FROM FPA_FERIAS WHERE NRORG = @NRORG@ AND NRFERIAS = @NRFERIAS@;",
            },
            {
                "template_id": template_id, "ordem": 2, "condicao_campo": "_TEM_GOZO",
                "template_sql": TEMPLATE_SQL_GOZO,
                "template_rollback": "DELETE FROM FPA_GOZOFERIAS WHERE NRORG = @NRORG@ AND NRGOZOFERIAS = @NRGOZOFERIAS@;",
            },
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
