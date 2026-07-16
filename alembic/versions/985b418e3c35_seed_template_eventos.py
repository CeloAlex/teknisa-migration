"""seed template eventos

Cadastra o template "Eventos de Folha" (catálogo/de-para, Seção 26.2/26.4) — o único dos
treze que não migra dados de um funcionário, e sim o catálogo de rubricas de folha
compartilhado pela organização (`eh_catalogo=True`) e o mapeamento "de-para" entre o código
do cliente e o código interno do HCM. Achado ao conferir o arquivo real (não coberto pelo
protótipo, que sempre gerava os três INSERTs): a lógica é de fato condicional — se "Nr
Evento Pebbian" (NRDE) estiver vazio, o evento é novo e o bloco FPA_EVENTOM/FPA_EVENTOH é
disparado; se estiver preenchido, só o de-para é gerado, reaproveitando o evento existente.
Reaproveita o mesmo mecanismo de bloco condicional (`condicao_campo`) da Fase 3, com uma
nova regra derivada complementar (`esta_vazio`, o inverso de `nenhum_vazio`). É
pré-requisito funcional de Ficha Financeira (13), que resolve `MIG_MIGRAMDEPARA` para
encontrar o código de evento de cada lançamento histórico. Dicionário e templates de script
extraídos diretamente de "docs/planilhas-originais/11_Eventos_v08_.xlsx".

Revision ID: 985b418e3c35
Revises: a9d749d7d4fa
Create Date: 2026-07-16 07:23:23.975864

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '985b418e3c35'
down_revision: Union[str, None] = 'a9d749d7d4fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "EVENTOS"

# Bloco 1 (condicional a _EVENTO_NOVO): evento novo. Texto extraído verbatim da célula O2.
TEMPLATE_SQL_EVENTO_NOVO = (
    "INSERT INTO FPA_EVENTOM ( NREVENTOM, DTINIVIGENCIA, NRORG, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, IDTIPOEVENTO ) VALUES ( @NREVENTOM@, '@DTINIVIGENCIA@', @NRORG@, "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@IDTIPOEVENTO@' ); INSERT INTO FPA_EVENTOH ( "
    "NREVENTOH, NREVENTOM, DTMESCOMPETENC, IDIMPRESSEVENTO, IDTIPOOCORREVEN, "
    "IDEVENTODEMONST, IDRETROCEDEVENT, IDZERAEVENFECHA, CDINTEGRAEVENTO, IDMEDIAEVENFERI, "
    "IDFALTAS13RESC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NMEVENTOH, IDDTOCORRENCIA, "
    "NRORG, VRPISOEVENTO, VRTETOEVENTO, IDATIVO ) VALUES ( @NREVENTOH@, @NREVENTOM@, "
    "'@DTMESCOMPETENC@', 'S', 'EVENTUAL', 'N', 'SEMPRE', 'N', '@NRDE@', 'N', 'N', SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@', '@NMEVENTOH@', 'COMPETENCIA', @NRORG@, 0, 9999999999, "
    "'S' );"
)

# Bloco 2 (sempre gerado): de-para. Texto extraído verbatim da célula P2.
TEMPLATE_SQL_DEPARA = (
    "INSERT INTO MIG_MIGRAMDEPARA ( NRMIGRAMDEPARA, NMTABELADBF, NRORG, NRPARA, NRDE ) "
    "VALUES ( @NRMIGRAMDEPARA@, 'EVENTO', @NRORG@, @NRPARA@, '@NRDE@' );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, sheet_name,
                                   header_row, data_start_row, ativo, eh_catalogo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :sheet_name,
                    :header_row, :data_start_row, true, true)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "Eventos de Folha (catálogo + de-para)",
            "versao": "8",
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
        campo(ordem=1, origem="A", rotulo="Data Início", campo="DTINIVIGENCIA", marcador="@DTINIVIGENCIA@",
              destino_tabela="FPA_EVENTOM", destino_coluna="DTINIVIGENCIA", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=2, origem="B", rotulo="Tipo Evento", campo="IDTIPOEVENTO", marcador="@IDTIPOEVENTO@",
              destino_tabela="FPA_EVENTOH", destino_coluna="IDTIPOEVENTO", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="C", rotulo="Mês Competencia", campo="DTMESCOMPETENC", marcador="@DTMESCOMPETENC@",
              destino_tabela="FPA_EVENTOH", destino_coluna="DTMESCOMPETENC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Descrição", campo="NMEVENTOH", marcador="@NMEVENTOH@",
              destino_tabela="FPA_EVENTOH", destino_coluna="NMEVENTOH", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        # Se vazio, o evento é novo (dispara o bloco FPA_EVENTOM/H); se preenchido, reaproveita
        # o evento já existente no HCM e só o de-para é gerado (Seção 26.4).
        campo(ordem=5, origem="E", rotulo="Nr Evento Pebbian (HCM)", campo="NRDE", marcador="@NRDE@",
              destino_tabela="MIG_MIGRAMDEPARA", destino_coluna="NRDE", tipo="texto",
              regra_conversao="trim"),
        campo(ordem=6, origem="F", rotulo="Nr Evento Cliente", campo="NRPARA", marcador="@NRPARA@",
              destino_tabela="MIG_MIGRAMDEPARA", destino_coluna="NRPARA", tipo="numerico",
              obrigatorio=True),
        # --- campo derivado: condição do bloco de evento novo (Seção 26.4) ---
        campo(ordem=7, origem="campo:NRDE", rotulo="Evento é novo? (derivado)",
              campo="_EVENTO_NOVO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="esta_vazio"),
        # --- campos com PK sequencial ---
        campo(ordem=8, origem="(gerado)", rotulo="Nº evento mestre (gerado)", campo="NREVENTOM",
              marcador="@NREVENTOM@", destino_tabela="FPA_EVENTOM", destino_coluna="NREVENTOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_EVENTOM", gerador_pk_seed=100073312),
        campo(ordem=9, origem="(gerado)", rotulo="Nº evento histórico (gerado)", campo="NREVENTOH",
              marcador="@NREVENTOH@", destino_tabela="FPA_EVENTOH", destino_coluna="NREVENTOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_EVENTOH", gerador_pk_seed=100072812),
        campo(ordem=10, origem="(gerado)", rotulo="Nº de-para (gerado)", campo="NRMIGRAMDEPARA",
              marcador="@NRMIGRAMDEPARA@", destino_tabela="MIG_MIGRAMDEPARA", destino_coluna="NRMIGRAMDEPARA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="MIG_MIGRAMDEPARA", gerador_pk_seed=0),
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
                "template_id": template_id, "ordem": 1, "condicao_campo": "_EVENTO_NOVO",
                "template_sql": TEMPLATE_SQL_EVENTO_NOVO,
                "template_rollback": (
                    "DELETE FROM FPA_EVENTOH WHERE NREVENTOH = @NREVENTOH@; "
                    "DELETE FROM FPA_EVENTOM WHERE NREVENTOM = @NREVENTOM@;"
                ),
            },
            {
                "template_id": template_id, "ordem": 2, "condicao_campo": None,
                "template_sql": TEMPLATE_SQL_DEPARA,
                "template_rollback": (
                    "DELETE FROM MIG_MIGRAMDEPARA WHERE NRORG = @NRORG@ AND NRMIGRAMDEPARA = @NRMIGRAMDEPARA@;"
                ),
            },
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
