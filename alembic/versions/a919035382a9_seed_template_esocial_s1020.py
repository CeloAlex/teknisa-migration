"""seed template esocial s1020

Fase 7 (eSocial) — S-1020 (Tabela de Lotações Tributárias) mapeia para ESTRUTURA com
NRTIPOESTRUTURA=7. Diferente de S-1000/S-1005, este evento traz um código de lotação
(`codLotacao`) que mapeia diretamente para `NRESTRUTURA`/`CDINTESTRUTURA` — a melhor
fidelidade dos três eventos de Estrutura. Tags confirmadas contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-1020_*.xml`).

Mesma ressalva de fidelidade parcial dos outros dois: razão social, endereço etc. não têm
origem neste evento (a lotação tributária eSocial não carrega esses dados) — ficam vazios.

Revision ID: a919035382a9
Revises: a4ed9d761539
Create Date: 2026-07-16 16:25:06.858508

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a919035382a9'
down_revision: Union[str, None] = 'a4ed9d761539'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S1020"
TIPO_CODIGO = "MIG_ESOCIAL_S1020"
SEM_ORIGEM = "_fixo_"

TEMPLATE_SQL_PRINCIPAL = (
    "INSERT INTO PARCNEGOCIO ( NRORG, NRPARCNEGOCIO, NMPRINCIPALPARC, NMSECUNDARIPARC, "
    "NRINSCRICAOPARC, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "CDTIPOPARCPRINCIPAL, CDTIPOINSCRICAO, IDPESSOAFISICA, IDINSTITUICAO, IDPARCFUNDIDO ) "
    "VALUES ( @NRORG@, @NRPARCNEGOCIO@, '@NMPRINCIPALPARC@', '@NMPRINCIPALPARC@', '@CNPJ@', "
    "'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 'ESTRUTURA', 'CNPJ', 'N', 'N', 'N' ); "
    "INSERT INTO ESTRUTURAM ( NRORG, NRESTRUTURAM, NRPARCNEGOCIO, CDINTESTRUTURA, "
    "NRTIPOESTRUTURA, DTINIVIGENCIA, DTFIMVIGENCIA, NMESTRUTURAM, IDATIVO, DTINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRORG@, @NRESTRUTURAM@, @NRPARCNEGOCIO@, '@NRESTRUTURA@', "
    "@NRTPESTRUTURA@, '@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', NVL( '@NMESTRUTURA@', "
    "NVL( '@NMFANTASIA@', '@RAZAOSOCIAL@' ) ), 'S', SYSDATE, '@USUARIO_TECNICO@'); "
    "INSERT INTO ESTRUTURAH ( NRORG, NRESTRUTURAM, NRESTRUTURAH, NRPARCNEGOCIO, "
    "DTMESCOMPETENC, CDCNPJESTRUT, CDCEIESTRUT, NMRAZSOCESTRUT, NMFANTASIA, NMESTRUTURAH, "
    "CDNATUJURI, CDCNAE, NRCAGED, IDTIPOEMPR, IDOPTSIMPLES, IDPARTICIPAT, CDCPFESTRUTURA, "
    "DTBASESINDICAL, CDSINDICAL, IDATIVO, DTINCLUSAO, CDOPERINCLUSAO)  VALUES ( @NRORG@, "
    "@NRESTRUTURAM@, @NRESTRUTURAH@, @NRPARCNEGOCIO@, '@COMPETENCIA@', '@CNPJ@', '@CEI@', "
    "'@RAZAOSOCIAL@', '@NMFANTASIA@', NVL( '@NMESTRUTURA@', NVL( '@NMFANTASIA@', "
    "'@RAZAOSOCIAL@' ) ), '@NATJURIDICA@', '@CDCNAE@', '@CDCAGED@', '@IDTPEMPRESA@', "
    "NVL( '@IDSIMPLES@', 'N' ), '@IDPARTICIPAT@', '@CDCPFESTRUTURA@', '@DTBASESINDICAL@', "
    "'@CDSINDICAL@', 'S', SYSDATE, '@USUARIO_TECNICO@');"
)

TEMPLATE_SQL_ENDERECO = (
    "INSERT INTO ENDERECOPARC ( NRORG, NRENDERECOPARC, NRPARCNEGOCIO, CDTIPOENDERECO, "
    "IDATIVO, DTINCLUSAO, CDOPERINCLUSAO, CDPAIS, SGESTADO, CDLOGRADOURO, NMBAIRROENDERECO, "
    "DSREFERENCIAENDE, NRCEPENDERECO, DSENDERECO, NRIMOVELENDERECO, CDMUNICIPIO ) VALUES ( "
    "@NRORG@, @NRENDERECOPARC@, @NRPARCNEGOCIO@, '@IDENDERECO@', 'S', SYSDATE, "
    "'@USUARIO_TECNICO@', LPAD( '@CDPAIS@', 4, '0' ), '@SGESTADO@', '@LOGRADOURO@', "
    "'@BAIRRO@', '@REFERENCIAENDERECO@', '@CEP@', '@ENDERECO@', '@NUMERO@', "
    "( SELECT MAX( CDMUNICIPIO ) FROM MUNICIPIO WHERE UPPER( NMMUNICIPIO ) = '@MUNICIPIO@' "
    "AND CDPAIS = LPAD( '@CDPAIS@', 4, '0' ) AND SGESTADO = '@SGESTADO@' ) );"
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
            "nome": "eSocial S-1020 — Tabela de Lotações Tributárias (via Estrutura, NRTIPOESTRUTURA=7)",
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
        campo(ordem=1, origem=SEM_ORIGEM, rotulo="Tipo de Estrutura Teknisa (fixo=7)", campo="NRTPESTRUTURA",
              marcador="@NRTPESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="NRTIPOESTRUTURA",
              tipo="numerico", obrigatorio=True, valor_padrao="7"),
        campo(ordem=2, origem="evtTabLotacao/infoLotacao/inclusao/ideLotacao/codLotacao | "
                              "evtTabLotacao/infoLotacao/alteracao/ideLotacao/codLotacao",
              rotulo="Código da Lotação", campo="NRESTRUTURA", marcador="@NRESTRUTURA@",
              destino_tabela="ESTRUTURAM", destino_coluna="CDINTESTRUTURA", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="evtTabLotacao/infoLotacao/inclusao/ideLotacao/iniValid | "
                              "evtTabLotacao/infoLotacao/alteracao/ideLotacao/iniValid",
              rotulo="Início de Vigência", campo="DTINIVIGENCIA", marcador="@DTINIVIGENCIA@",
              destino_tabela="ESTRUTURAM", destino_coluna="DTINIVIGENCIA", tipo="data",
              obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=4, origem="evtTabLotacao/infoLotacao/inclusao/ideLotacao/fimValid | "
                              "evtTabLotacao/infoLotacao/alteracao/ideLotacao/fimValid",
              rotulo="Fim de Vigência", campo="DTFIMVIGENCIA", marcador="@DTFIMVIGENCIA@",
              destino_tabela="ESTRUTURAM", destino_coluna="DTFIMVIGENCIA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=5, origem="evtTabLotacao/infoLotacao/inclusao/dadosLotacao/nrInsc | "
                              "evtTabLotacao/infoLotacao/alteracao/dadosLotacao/nrInsc",
              rotulo="CNPJ da Lotação", campo="CNPJ", marcador="@CNPJ@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCNPJESTRUT", tipo="texto",
              tamanho_maximo=14, regra_conversao="remover_mascara"),
        campo(ordem=6, origem=SEM_ORIGEM, rotulo="Competência (sem origem neste evento)", campo="COMPETENCIA",
              marcador="@COMPETENCIA@", destino_tabela="ESTRUTURAH", destino_coluna="DTMESCOMPETENC", tipo="data"),
        campo(ordem=7, origem=SEM_ORIGEM, rotulo="CEI", campo="CEI", marcador="@CEI@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCEIESTRUT", tipo="texto"),
        campo(ordem=8, origem=SEM_ORIGEM, rotulo="Razão Social", campo="RAZAOSOCIAL", marcador="@RAZAOSOCIAL@",
              destino_tabela="ESTRUTURAH", destino_coluna="NMRAZSOCESTRUT", tipo="texto"),
        campo(ordem=9, origem=SEM_ORIGEM, rotulo="Natureza Jurídica", campo="NATJURIDICA", marcador="@NATJURIDICA@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDNATUJURI", tipo="texto"),
        campo(ordem=10, origem=SEM_ORIGEM, rotulo="CNAE", campo="CDCNAE", marcador="@CDCNAE@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCNAE", tipo="texto"),
        campo(ordem=11, origem=SEM_ORIGEM, rotulo="CAGED", campo="CDCAGED", marcador="@CDCAGED@",
              destino_tabela="ESTRUTURAH", destino_coluna="NRCAGED", tipo="texto"),
        campo(ordem=12, origem=SEM_ORIGEM, rotulo="Tipo de Empresa", campo="IDTPEMPRESA", marcador="@IDTPEMPRESA@",
              destino_tabela="ESTRUTURAH", destino_coluna="IDTIPOEMPR", tipo="texto"),
        campo(ordem=13, origem=SEM_ORIGEM, rotulo="Optante Simples", campo="IDSIMPLES", marcador="@IDSIMPLES@",
              destino_tabela="ESTRUTURAH", destino_coluna="IDOPTSIMPLES", tipo="booleano", regra_conversao="vazio_para_n"),
        campo(ordem=14, origem=SEM_ORIGEM, rotulo="Participação PAT", campo="IDPARTICIPAT", marcador="@IDPARTICIPAT@",
              destino_tabela="ESTRUTURAH", destino_coluna="IDPARTICIPAT", tipo="booleano"),
        campo(ordem=15, origem=SEM_ORIGEM, rotulo="Nome Fantasia", campo="NMFANTASIA", marcador="@NMFANTASIA@",
              destino_tabela="ESTRUTURAH", destino_coluna="NMFANTASIA", tipo="texto"),
        campo(ordem=16, origem=SEM_ORIGEM, rotulo="Nome Estrutura", campo="NMESTRUTURA", marcador="@NMESTRUTURA@",
              destino_tabela="ESTRUTURAM/H", destino_coluna="NMESTRUTURAM / NMESTRUTURAH", tipo="texto"),
        campo(ordem=17, origem=SEM_ORIGEM, rotulo="CPF", campo="CDCPFESTRUTURA", marcador="@CDCPFESTRUTURA@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCPFESTRUTURA", tipo="texto"),
        campo(ordem=18, origem=SEM_ORIGEM, rotulo="Data Base Sindical", campo="DTBASESINDICAL", marcador="@DTBASESINDICAL@",
              destino_tabela="ESTRUTURAH", destino_coluna="DTBASESINDICAL", tipo="data"),
        campo(ordem=19, origem=SEM_ORIGEM, rotulo="Cód Sindicato", campo="CDSINDICAL", marcador="@CDSINDICAL@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDSINDICAL", tipo="texto"),
        campo(ordem=20, origem=SEM_ORIGEM, rotulo="Tp Endereço", campo="IDENDERECO", marcador="@IDENDERECO@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDTIPOENDERECO", tipo="texto"),
        campo(ordem=21, origem=SEM_ORIGEM, rotulo="Logradouro", campo="LOGRADOURO", marcador="@LOGRADOURO@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDLOGRADOURO", tipo="texto"),
        campo(ordem=22, origem=SEM_ORIGEM, rotulo="Pais", campo="CDPAIS", marcador="@CDPAIS@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDPAIS", tipo="texto"),
        campo(ordem=23, origem=SEM_ORIGEM, rotulo="Estado", campo="SGESTADO", marcador="@SGESTADO@",
              destino_tabela="ENDERECOPARC", destino_coluna="SGESTADO", tipo="texto"),
        campo(ordem=24, origem=SEM_ORIGEM, rotulo="Município", campo="MUNICIPIO", marcador="@MUNICIPIO@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDMUNICIPIO", tipo="texto"),
        campo(ordem=25, origem=SEM_ORIGEM, rotulo="Endereço", campo="ENDERECO", marcador="@ENDERECO@",
              destino_tabela="ENDERECOPARC", destino_coluna="DSENDERECO", tipo="texto"),
        campo(ordem=26, origem=SEM_ORIGEM, rotulo="Numero", campo="NUMERO", marcador="@NUMERO@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRIMOVELENDERECO", tipo="numerico"),
        campo(ordem=27, origem=SEM_ORIGEM, rotulo="Nome do Bairro", campo="BAIRRO", marcador="@BAIRRO@",
              destino_tabela="ENDERECOPARC", destino_coluna="NMBAIRROENDERECO", tipo="texto"),
        campo(ordem=28, origem=SEM_ORIGEM, rotulo="CEP", campo="CEP", marcador="@CEP@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRCEPENDERECO", tipo="texto"),
        campo(ordem=29, origem=SEM_ORIGEM, rotulo="Referência do Endereço", campo="REFERENCIAENDERECO",
              marcador="@REFERENCIAENDERECO@", destino_tabela="ENDERECOPARC", destino_coluna="DSREFERENCIAENDE", tipo="texto"),
        campo(ordem=30, origem="campo:RAZAOSOCIAL,NMFANTASIA,NMESTRUTURA", rotulo="Nome Principal do Parceiro (derivado)",
              campo="NMPRINCIPALPARC", marcador="@NMPRINCIPALPARC@", destino_tabela="PARCNEGOCIO",
              destino_coluna="NMPRINCIPALPARC", tipo="texto", regra_conversao="primeiro_nao_vazio"),
        campo(ordem=31, origem="campo:IDENDERECO,LOGRADOURO", rotulo="Tem endereço? (derivado)",
              campo="_TEM_ENDERECO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=32, origem="(gerado)", rotulo="Nº PARCNEGOCIO (gerado)", campo="NRPARCNEGOCIO",
              marcador="@NRPARCNEGOCIO@", destino_tabela="PARCNEGOCIO", destino_coluna="NRPARCNEGOCIO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="PARCNEGOCIO", gerador_pk_seed=1738),
        campo(ordem=33, origem="(gerado)", rotulo="Nº ESTRUTURAM (gerado)", campo="NRESTRUTURAM",
              marcador="@NRESTRUTURAM@", destino_tabela="ESTRUTURAM", destino_coluna="NRESTRUTURAM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="ESTRUTURAM", gerador_pk_seed=166),
        campo(ordem=34, origem="(gerado)", rotulo="Nº ESTRUTURAH (gerado)", campo="NRESTRUTURAH",
              marcador="@NRESTRUTURAH@", destino_tabela="ESTRUTURAH", destino_coluna="NRESTRUTURAH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="ESTRUTURAH", gerador_pk_seed=166),
        campo(ordem=35, origem="(gerado)", rotulo="Nº ENDERECOPARC (gerado)", campo="NRENDERECOPARC",
              marcador="@NRENDERECOPARC@", destino_tabela="ENDERECOPARC", destino_coluna="NRENDERECOPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="ENDERECOPARC", gerador_pk_seed=1718),
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
                "template_sql": TEMPLATE_SQL_PRINCIPAL,
                "template_rollback": (
                    "DELETE FROM ESTRUTURAH WHERE NRORG = @NRORG@ AND NRESTRUTURAH = @NRESTRUTURAH@; "
                    "DELETE FROM ESTRUTURAM WHERE NRORG = @NRORG@ AND NRESTRUTURAM = @NRESTRUTURAM@; "
                    "DELETE FROM PARCNEGOCIO WHERE NRORG = @NRORG@ AND NRPARCNEGOCIO = @NRPARCNEGOCIO@;"
                ),
            },
            {
                "template_id": template_id, "ordem": 2, "condicao_campo": "_TEM_ENDERECO",
                "template_sql": TEMPLATE_SQL_ENDERECO,
                "template_rollback": (
                    "DELETE FROM ENDERECOPARC WHERE NRORG = @NRORG@ AND NRENDERECOPARC = @NRENDERECOPARC@;"
                ),
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-1020 Tabela de Lotações Tributárias"},
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
