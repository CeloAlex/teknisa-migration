"""seed template esocial s1200

Fase 7 (eSocial) — S-1200 (Remuneração de Trabalhador vinculado ao RGPS) mapeia para
FICHA_FINANCEIRA, reaproveitando o MESMO `template_sql` (INSERT em FPA_ITECALCFOLHA com as
mesmas subqueries de FK para GPE_VINCULOM via matrícula e MIG_MIGRAMDEPARA via código de
evento). Diferente dos demais eventos eSocial desta leva, S-1200 tem uma estrutura
repetida por linha (`dmDev/infoPerApur/remunPerApur/itensRemun`, um por rubrica de folha) —
`xml_registro_xpath` seleciona essa lista, e cada `itensRemun` vira uma linha de staging,
com `matricula` resolvida relativa ao pai (`../matricula`) e a competência (`perApur`)
resolvida por caminho absoluto a partir da raiz do documento (é um valor de evento único,
não repetido por rubrica). Tags confirmadas contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-1200_*.xml`).

Mesma dependência externa documentada no template FICHA_FINANCEIRA original: a subquery de
NRCALCULOFOLHA depende de um FPA_CALCULOFOLHA já existente no destino (Seção 26.2/26.4).

Não implementado nesta leva (Seção "fora desta leva" do relatório de viabilidade): S-1210
(Pagamentos) não tem a mesma estrutura repetida de rubrica/valor — é um registro de
pagamento líquido único ligado a S-1200 por `ideDmDev`, sem "código de evento" equivalente
a `NREVENTO`, então não serve para o dicionário desta FICHA_FINANCEIRA como está.

Revision ID: e10869df4346
Revises: e86cfd975df3
Create Date: 2026-07-16 16:25:10.625963

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e10869df4346'
down_revision: Union[str, None] = 'e86cfd975df3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S1200"
TIPO_CODIGO = "MIG_ESOCIAL_S1200"
SEM_ORIGEM = "_fixo_"

REGISTRO_XPATH = "evtRemun/dmDev/infoPerApur/ideEstabLot/remunPerApur/itensRemun"

TEMPLATE_SQL = (
    "INSERT INTO FPA_ITECALCFOLHA ( NRITEMCALCFOLHA, NRCALCULOFOLHA, NRVINCULOM, NREVENTOM, "
    "NRORG, IDEVENDEMONCALC, VRREFFOLHA, VREVENTOFOLHA, IDREFEVALORCALC, DTINCLUSAO, "
    "DTOCORRENCIA, DSITEMCALCFOLHA, QTOCORPROXPERI ) VALUES ( @NRO@, ( SELECT "
    "MAX(NRCALCULOFOLHA) FROM FPA_CALCULOFOLHA WHERE NRORG = @NRORG@ AND NRTIPOMOVIMENT = "
    "@NRTIPOMOVIMENT@ AND DTOCORRENCIA = '@DTMESCOMPETENC@' AND NRTPMODALIDCAL = 1 AND "
    "NROCORRECAL = 1 ), ( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE NRORG = "
    "@NRORG@ AND CDMATRICULA = '@CDMATRICULA@' ), ( SELECT MAX(NRPARA) FROM "
    "MIG_MIGRAMDEPARA WHERE NRORG = @NRORG@ AND NRDE = '@NREVENTO@' ), @NRORG@, 'N', "
    "@VRREFFOLHA@, @VREVENTOFOLHA@, 'REFERENCIA_VALOR', SYSDATE, '@DTOCORRENCIA@', "
    "'@DSITEMCALCFOLHA@', 1 );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, xml_registro_xpath, ativo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :xml_registro_xpath, true)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "eSocial S-1200 — Remuneração RGPS (via Ficha Financeira, 1 linha por rubrica)",
            "versao": "v_S_01_03_00",
            "formatos_aceitos": ["XML"],
            "xml_registro_xpath": REGISTRO_XPATH,
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
        campo(ordem=1, origem=SEM_ORIGEM, rotulo="Tp Movimento (fixo=1)", campo="NRTIPOMOVIMENT",
              marcador="@NRTIPOMOVIMENT@", destino_tabela="FPA_ITECALCFOLHA", destino_coluna="NRTIPOMOVIMENT",
              tipo="numerico", obrigatorio=True, valor_padrao="1"),
        campo(ordem=2, origem="../matricula", rotulo="Nr. Vínculo (matrícula, relativo ao dmDev pai)",
              campo="CDMATRICULA", marcador="@CDMATRICULA@", destino_tabela="FPA_ITECALCFOLHA",
              destino_coluna="NRVINCULOM", tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="/eSocial/evtRemun/ideEvento/perApur", rotulo="Competência (evento inteiro)",
              campo="DTMESCOMPETENC", marcador="@DTMESCOMPETENC@", destino_tabela="FPA_CALCULOFOLHA",
              destino_coluna="DTOCORRENCIA", tipo="data", obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=4, origem="codRubr", rotulo="Nr. Evento (código de rubrica)", campo="NREVENTO",
              marcador="@NREVENTO@", destino_tabela="MIG_MIGRAMDEPARA", destino_coluna="NRDE",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="vrRubr", rotulo="Valor", campo="VREVENTOFOLHA", marcador="@VREVENTOFOLHA@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="VREVENTOFOLHA", tipo="monetario",
              obrigatorio=True, regra_conversao="numero_decimal"),
        campo(ordem=6, origem=SEM_ORIGEM, rotulo="Descrição do Cálculo (sem origem no evento)",
              campo="DSITEMCALCFOLHA", marcador="@DSITEMCALCFOLHA@", destino_tabela="FPA_ITECALCFOLHA",
              destino_coluna="DSITEMCALCFOLHA", tipo="texto"),
        campo(ordem=7, origem="/eSocial/evtRemun/ideEvento/perApur", rotulo="Data de Ocorrência (evento inteiro)",
              campo="DTOCORRENCIA", marcador="@DTOCORRENCIA@", destino_tabela="FPA_ITECALCFOLHA",
              destino_coluna="DTOCORRENCIA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=8, origem=SEM_ORIGEM, rotulo="Valor de Referência (sem origem no evento)",
              campo="VRREFFOLHA", marcador="@VRREFFOLHA@", destino_tabela="FPA_ITECALCFOLHA",
              destino_coluna="VRREFFOLHA", tipo="numerico", regra_conversao="numero_ou_null"),
        campo(ordem=9, origem="(gerado)", rotulo="Nº sequencial do item (gerado)", campo="NRO",
              marcador="@NRO@", destino_tabela="FPA_ITECALCFOLHA", destino_coluna="NRITEMCALCFOLHA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_ITECALCFOLHA", gerador_pk_seed=0),
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
                "DELETE FROM FPA_ITECALCFOLHA WHERE NRORG = @NRORG@ AND NRITEMCALCFOLHA = @NRO@;"
            ),
        },
    )

    tipo_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', true, 'SCRIPT', false)
            RETURNING id
            """
        ),
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-1200 Remuneração RGPS"},
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
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
