"""seed template esocial s1040

Fase 7 (eSocial) — S-1040 (Tabela de Funções), fora do mapeamento originalmente informado
mas presente no material de referência (`ImportacaoXmlS1040.php`) e claramente equivalente:
mapeia para OCUPACAO com NRTIPOOCUPACAO fixo=2 (Função — a mesma tabela de S-1030, código
de tipo diferente). Mesma ressalva do S-1030: **sem amostra real de XML disponível**, XPath
inferido da leitura direta do PHP (`evtTabFuncao/infoFuncao/{inclusao|alteracao}/
ideFuncao` e `.../dadosFuncao`).

Revision ID: e86cfd975df3
Revises: 6b13ec762a4c
Create Date: 2026-07-16 16:25:09.306352

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e86cfd975df3'
down_revision: Union[str, None] = '6b13ec762a4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S1040"
TIPO_CODIGO = "MIG_ESOCIAL_S1040"
SEM_ORIGEM = "_fixo_"

TEMPLATE_SQL = (
    "INSERT INTO GPE_OCUPACAOM (NRORG, NROCUPACAOM, NRTIPOOCUPACAO, DTINIVIGENCIA, "
    "DTFIMVIGENCIA, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO) VALUES (@NRORG@, "
    "@NROCUPACAOM@, @NRTIPOOCUPACAO@, '@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@'); INSERT INTO GPE_OCUPACAOH (NRORG, NROCUPACAOH, "
    "NROCUPACAOM, DTMESCOMPETENC, NMOCUPACAOH, CDINTEGRACAO, NRCBO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO) VALUES (@NRORG@, @NROCUPACAOH@, @NROCUPACAOM@, "
    "'@COMPETENCIA@', '@NMOCUPACAOH@', '@CDINTEGRACAO@', @NRCBO@, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@' );"
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
            "nome": "eSocial S-1040 — Tabela de Funções (via Ocupação, NRTIPOOCUPACAO=2; XPath não verificado contra XML real)",
            "versao": "v_S_01_00_00",
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
        campo(ordem=1, origem=SEM_ORIGEM, rotulo="tp ocupação (fixo=2, Função)", campo="NRTIPOOCUPACAO",
              marcador="@NRTIPOOCUPACAO@", destino_tabela="GPE_OCUPACAOM", destino_coluna="NRTIPOOCUPACAO",
              tipo="numerico", obrigatorio=True, valor_padrao="2"),
        campo(ordem=2, origem="evtTabFuncao/infoFuncao/inclusao/ideFuncao/iniValid | "
                              "evtTabFuncao/infoFuncao/alteracao/ideFuncao/iniValid",
              rotulo="Início Vigência", campo="DTINIVIGENCIA", marcador="@DTINIVIGENCIA@",
              destino_tabela="GPE_OCUPACAOM", destino_coluna="DTINIVIGENCIA", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=3, origem="evtTabFuncao/infoFuncao/inclusao/ideFuncao/fimValid | "
                              "evtTabFuncao/infoFuncao/alteracao/ideFuncao/fimValid",
              rotulo="Fim Vigência", campo="DTFIMVIGENCIA", marcador="@DTFIMVIGENCIA@",
              destino_tabela="GPE_OCUPACAOM", destino_coluna="DTFIMVIGENCIA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=4, origem="evtTabFuncao/infoFuncao/inclusao/ideFuncao/codFuncao | "
                              "evtTabFuncao/infoFuncao/alteracao/ideFuncao/codFuncao",
              rotulo="Nr Ocupacao (código de integração)", campo="CDINTEGRACAO", marcador="@CDINTEGRACAO@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="CDINTEGRACAO", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="evtTabFuncao/infoFuncao/inclusao/ideFuncao/iniValid | "
                              "evtTabFuncao/infoFuncao/alteracao/ideFuncao/iniValid",
              rotulo="Competência (aproximada pela vigência)", campo="COMPETENCIA", marcador="@COMPETENCIA@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="DTMESCOMPETENC", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=6, origem="evtTabFuncao/infoFuncao/inclusao/dadosFuncao/dscFuncao | "
                              "evtTabFuncao/infoFuncao/alteracao/dadosFuncao/dscFuncao",
              rotulo="Descrição", campo="NMOCUPACAOH", marcador="@NMOCUPACAOH@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="NMOCUPACAOH", tipo="texto",
              tamanho_maximo=100, obrigatorio=True, regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=7, origem="evtTabFuncao/infoFuncao/inclusao/dadosFuncao/codCBO | "
                              "evtTabFuncao/infoFuncao/alteracao/dadosFuncao/codCBO",
              rotulo="CBO", campo="NRCBO", marcador="@NRCBO@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="NRCBO", tipo="numerico",
              tamanho_maximo=6, regra_conversao="cbo"),
        campo(ordem=8, origem="(gerado)", rotulo="Nº GPE_OCUPACAOM (gerado)", campo="NROCUPACAOM",
              marcador="@NROCUPACAOM@", destino_tabela="GPE_OCUPACAOM", destino_coluna="NROCUPACAOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_OCUPACAOM", gerador_pk_seed=0),
        campo(ordem=9, origem="(gerado)", rotulo="Nº GPE_OCUPACAOH (gerado)", campo="NROCUPACAOH",
              marcador="@NROCUPACAOH@", destino_tabela="GPE_OCUPACAOH", destino_coluna="NROCUPACAOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_OCUPACAOH", gerador_pk_seed=0),
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
                "DELETE FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND NROCUPACAOH = @NROCUPACAOH@; "
                "DELETE FROM GPE_OCUPACAOM WHERE NRORG = @NRORG@ AND NROCUPACAOM = @NROCUPACAOM@;"
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-1040 Tabela de Funções"},
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
