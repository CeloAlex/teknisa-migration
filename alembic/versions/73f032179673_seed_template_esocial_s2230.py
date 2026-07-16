"""seed template esocial s2230

Fase 7 (eSocial) — S-2230 (Afastamento Temporário) é o mais estrutural dos 8: um único
evento roteia para DOIS templates existentes diferentes, dependendo do motivo do
afastamento (`codMotAfast`, confirmado contra o XML real de
`docs/eSocial/eventos_xml/XML_envio_S-2230_*.xml`) — `codMotAfast == "15"` é Férias;
qualquer outro código é Situação Funcional. O motor já suporta blocos condicionais
(`condicao_campo`, o mesmo mecanismo usado no bloco de endereço de Estrutura e no gozo de
Férias) — aqui ele decide qual TABELA de destino usar, não só se um bloco extra roda.

Duas novas regras de conversão em `app/transformation/conversions.py`
(`codigo_igual_15`/`codigo_diferente_15`) resolvem esse roteamento a partir de
`codMotAfast`.

**Implementado nesta leva apenas o ramo Férias** (script gerado ponta a ponta, reaproveita
o `template_sql` do template FERIAS): o período aquisitivo (`perAquis/dtInicio`/`dtFim`)
está de fato presente no XML real, então DTINIAQUISICAO/DTFIMAQUISICAO não precisam da
lógica de janela de 12 meses que o PHP de referência calcula. O ramo Situação Funcional
**fica só com o dicionário cadastrado, sem bloco de script** — `NRSITUFUNCM` (código da
situação funcional) não tem uma tag correspondente no XML (o PHP de referência deriva esse
valor por lógica de negócio própria, não documentada com segurança aqui); como o campo é
obrigatório, uma linha não-Férias hoje fica corretamente bloqueada na validação (erro
impeditivo por campo obrigatório vazio) em vez de gerar um script com um código adivinhado
— comportamento seguro, a ser complementado depois. `CDDIAGNOST`/`infoAtestado.codCID` é
best-effort (sem amostra real de afastamento médico disponível para confirmar o caminho).

Revision ID: 73f032179673
Revises: e10869df4346
Create Date: 2026-07-16 16:25:11.867243

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '73f032179673'
down_revision: Union[str, None] = 'e10869df4346'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S2230"
TIPO_CODIGO = "MIG_ESOCIAL_S2230"
SEM_ORIGEM = "_fixo_"

# Blocos idênticos ao template FERIAS (mesmas tabelas físicas de destino).
TEMPLATE_SQL_FERIAS = (
    "INSERT INTO FPA_FERIAS ( NRFERIAS, NRVINCULOM, NRTIPOFERIAS, NRORG, DTINIAQUISICAO, "
    "DTFIMAQUISICAO, QTMESAFASTAMENT, QTFALTASPERIODO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, IDCONTROLFERIAS ) VALUES ( @NRFERIAS@, (SELECT /*MAX(*/NRVINCULOM/*)*/ "
    "FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA = '@NRVINCULOM@' ), '1', "
    "@NRORG@, '@DTINIAQUISICAO@', '@DTFIMAQUISICAO@', '@QTMESAFASTAMENT@', "
    "'@QTFALTASPERIODO@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@IDCONTROLFERIAS@' );"
)

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
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, xml_registro_xpath, ativo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :xml_registro_xpath, true)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "eSocial S-2230 — Afastamento Temporário (Férias completo; Situação Funcional só dicionário)",
            "versao": "v_S_01_03_00",
            "formatos_aceitos": ["XML"],
            "xml_registro_xpath": None,
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
        # --- compartilhado pelos dois ramos ---
        campo(ordem=1, origem="evtAfastTemp/ideVinculo/matricula", rotulo="Nr Vínculo (matrícula)",
              campo="NRVINCULOM", marcador="@NRVINCULOM@", destino_tabela="GPE_ALTESITUFUNC/FPA_FERIAS",
              destino_coluna="NRVINCULOM", tipo="texto", obrigatorio=True, regra_conversao="trim"),
        # --- intermediário + roteamento (Seção 26.4 — bloco condicional decide a TABELA) ---
        campo(ordem=2, origem="evtAfastTemp/infoAfastamento/iniAfastamento/codMotAfast",
              rotulo="Código do motivo de afastamento (eSocial)", campo="_CODMOTAFAST", marcador=None,
              destino_tabela="—", destino_coluna="—", tipo="texto"),
        campo(ordem=3, origem="campo:_CODMOTAFAST", rotulo="É férias? (derivado — codMotAfast==15)",
              campo="_EH_FERIAS", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="codigo_igual_15"),
        campo(ordem=4, origem="campo:_CODMOTAFAST", rotulo="É afastamento/situação funcional? (derivado)",
              campo="_EH_AFASTAMENTO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="codigo_diferente_15"),
        # --- ramo Situação Funcional (só dicionário — sem bloco de script nesta leva) ---
        # NÃO marcado obrigatorio=True: o validador genérico não sabe que este campo só
        # importa quando _EH_AFASTAMENTO é verdadeiro (ele não enxerga condicao_campo, que
        # só existe no Script Generator) — se fosse obrigatório aqui, bloquearia a
        # aprovação até de linhas roteadas para Férias, que nunca usam este campo.
        campo(ordem=5, origem=SEM_ORIGEM, rotulo="Sit. Funcional (sem origem no XML — gap documentado)",
              campo="NRSITUFUNCM", marcador="@NRSITUFUNCM@", destino_tabela="GPE_ALTESITUFUNC",
              destino_coluna="NRSITUFUNCM", tipo="numerico"),
        campo(ordem=6, origem="evtAfastTemp/infoAfastamento/iniAfastamento/dtIniAfast",
              rotulo="Data Início (Situação Funcional)", campo="DTINISITUFUNC", marcador="@DTINISITUFUNC@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="DTINISITUFUNC", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=7, origem="evtAfastTemp/infoAfastamento/fimAfastamento/dtTermAfast",
              rotulo="Data Fim (Situação Funcional)", campo="DTFIMSITUFUNC", marcador="@DTFIMSITUFUNC@",
              destino_tabela="GPE_ALTESITUFUNC", destino_coluna="DTFIMSITUFUNC", tipo="data", regra_conversao="data_iso"),
        campo(ordem=8, origem=SEM_ORIGEM, rotulo="CDTABECDI (sem origem no XML)", campo="CDTABECDI",
              marcador="@CDTABECDI@", destino_tabela="GPE_ALTESITUFUNC", destino_coluna="CDTABECDI", tipo="texto"),
        campo(ordem=9, origem="evtAfastTemp/infoAfastamento/iniAfastamento/infoAtestado/codCID",
              rotulo="CDDIAGNOST (dado de saúde sensível — LGPD; best-effort, sem amostra real)",
              campo="CDDIAGNOST", marcador="@CDDIAGNOST@", destino_tabela="GPE_ALTESITUFUNC",
              destino_coluna="CDDIAGNOST", tipo="texto", regra_conversao="trim"),
        campo(ordem=10, origem="(gerado)", rotulo="Nº sequencial Situação Funcional (gerado)",
              campo="NRALTESITUFUNC", marcador="@NRALTESITUFUNC@", destino_tabela="GPE_ALTESITUFUNC",
              destino_coluna="NRALTESITUFUNC", tipo="numerico", eh_pk=True, gerador_pk=True,
              gerador_pk_contador="GPE_ALTESITUFUNC", gerador_pk_seed=6291),
        # --- ramo Férias (implementado ponta a ponta) ---
        campo(ordem=11, origem="evtAfastTemp/infoAfastamento/iniAfastamento/perAquis/dtInicio",
              rotulo="Início Aquisição", campo="DTINIAQUISICAO", marcador="@DTINIAQUISICAO@",
              destino_tabela="FPA_FERIAS", destino_coluna="DTINIAQUISICAO", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=12, origem="evtAfastTemp/infoAfastamento/iniAfastamento/perAquis/dtFim",
              rotulo="Fim Aquisição", campo="DTFIMAQUISICAO", marcador="@DTFIMAQUISICAO@",
              destino_tabela="FPA_FERIAS", destino_coluna="DTFIMAQUISICAO", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=13, origem=SEM_ORIGEM, rotulo="Mês Afastamento (fixo=0, sem origem no XML)",
              campo="QTMESAFASTAMENT", marcador="@QTMESAFASTAMENT@", destino_tabela="FPA_FERIAS",
              destino_coluna="QTMESAFASTAMENT", tipo="numerico", valor_padrao="0"),
        campo(ordem=14, origem=SEM_ORIGEM, rotulo="Dias Faltas Mês (fixo=0, sem origem no XML)",
              campo="QTFALTASPERIODO", marcador="@QTFALTASPERIODO@", destino_tabela="FPA_FERIAS",
              destino_coluna="QTFALTASPERIODO", tipo="numerico", valor_padrao="0"),
        campo(ordem=15, origem=SEM_ORIGEM, rotulo="Status Férias (sem origem no XML)",
              campo="IDCONTROLFERIAS", marcador="@IDCONTROLFERIAS@", destino_tabela="FPA_FERIAS",
              destino_coluna="IDCONTROLFERIAS", tipo="texto"),
        campo(ordem=16, origem="evtAfastTemp/infoAfastamento/iniAfastamento/dtIniAfast",
              rotulo="Início Gozo", campo="DTINIGOZOFERIAS", marcador="@DTINIGOZOFERIAS@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="DTINIGOZOFERIAS", tipo="data", regra_conversao="data_iso"),
        campo(ordem=17, origem="evtAfastTemp/infoAfastamento/fimAfastamento/dtTermAfast",
              rotulo="Fim Gozo", campo="DTFIMGOZOFERIAS", marcador="@DTFIMGOZOFERIAS@",
              destino_tabela="FPA_GOZOFERIAS", destino_coluna="DTFIMGOZOFERIAS", tipo="data", regra_conversao="data_iso"),
        campo(ordem=18, origem=SEM_ORIGEM, rotulo="Dt Retorno Férias (sem origem no XML)",
              campo="DTRETORNOFERIAS", marcador="@DTRETORNOFERIAS@", destino_tabela="FPA_GOZOFERIAS",
              destino_coluna="DTRETORNOFERIAS", tipo="data"),
        campo(ordem=19, origem=SEM_ORIGEM, rotulo="Dias Abono (fixo=0, sem origem no XML)",
              campo="QTDIASABONOFERI", marcador="@QTDIASABONOFERI@", destino_tabela="FPA_GOZOFERIAS",
              destino_coluna="QTDIASABONOFERI", tipo="numerico", valor_padrao="0"),
        campo(ordem=20, origem="(gerado)", rotulo="Nº período aquisitivo (gerado)", campo="NRFERIAS",
              marcador="@NRFERIAS@", destino_tabela="FPA_FERIAS", destino_coluna="NRFERIAS",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_FERIAS", gerador_pk_seed=0),
        campo(ordem=21, origem="(gerado)", rotulo="Nº período de gozo (gerado)", campo="NRGOZOFERIAS",
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

    # Só o ramo Férias tem bloco de script nesta leva — ver docstring da revisão. Ambos os
    # blocos são gatilhados pelo mesmo `_EH_FERIAS` (uma linha roteada para Férias sempre
    # tem as datas de gozo no XML de afastamento, ao contrário do template FERIAS via XLSX
    # original, onde gozo é genuinamente opcional por linha).
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
                "template_id": template_id, "ordem": 1, "condicao_campo": "_EH_FERIAS",
                "template_sql": TEMPLATE_SQL_FERIAS,
                "template_rollback": "DELETE FROM FPA_FERIAS WHERE NRORG = @NRORG@ AND NRFERIAS = @NRFERIAS@;",
            },
            {
                "template_id": template_id, "ordem": 2, "condicao_campo": "_EH_FERIAS",
                "template_sql": TEMPLATE_SQL_GOZO,
                "template_rollback": "DELETE FROM FPA_GOZOFERIAS WHERE NRORG = @NRORG@ AND NRGOZOFERIAS = @NRGOZOFERIAS@;",
            },
        ],
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-2230 Afastamento Temporário"},
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
