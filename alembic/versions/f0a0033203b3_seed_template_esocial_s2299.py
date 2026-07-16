"""seed template esocial s2299

Fase 7 (eSocial) — S-2299 (Desligamento) é o único dos 8 eventos desta leva sem um
template XLSX equivalente para reaproveitar SQL: o usuário descreveu isso como um UPDATE
direto em GPE_VINCULOM com os campos de rescisão. Lido diretamente de
`ImportacaoXmlS2299.php` e confirmado contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-2299_*.xml`) — o PHP usa setters ORM
(`setDtrescisaovinc` etc.), não SQL literal, então o texto do UPDATE abaixo foi escrito do
zero a partir dos nomes de coluna que os setters implicam, não copiado de lugar nenhum.

Duas divergências reais em relação ao que foi informado inicialmente: (1) `nrmotivoresc`
não existe no PHP — o único campo de motivo é `nrtpdemissao` (resolvido via lookup em
FPA_TPDEMISSAO por `cdesocial`); (2) `dtavisoprevio` vem de `infoDeslig/dtProjFimAPI`, não
de `infoDeslig/dtAvPrv` (que também existe no XML real, mas o PHP usa explicitamente
dtProjFimAPI para essa coluna — confirmado lendo a lógica do PHP, não só o nome da tag).

Operação registrada como 'ALTERACAO' (não 'INCLUSAO', o padrão dos demais 7 templates
desta leva) porque é literalmente um UPDATE, não um INSERT — o operador precisa selecionar
"Alteração" na tela de geração de script.

Não implementado (fora de escopo desta leva): `GPE_PESSOAH.NRCERTOBITO` (segunda tabela,
resolução de PK por pessoa/competência mais complexa que o padrão de subquery por
matrícula já usado nos outros templates) — óbito é um caso raro dentro de um evento já raro
(desligamento), fica para complementar depois.

Revision ID: f0a0033203b3
Revises: 73f032179673
Create Date: 2026-07-16 16:25:13.057848

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f0a0033203b3'
down_revision: Union[str, None] = '73f032179673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S2299"
TIPO_CODIGO = "MIG_ESOCIAL_S2299"

TEMPLATE_SQL = (
    "UPDATE GPE_VINCULOM SET DTRESCISAOVINC = '@DTRESCISAOVINC@', "
    "DTAVISOPREVIO = '@DTAVISOPREVIO@', DSOBSRESCISAO = '@DSOBSRESCISAO@', "
    "NRPROCJUD = '@NRPROCJUD@', "
    "NRTPDEMISSAO = ( SELECT MAX(NRTPDEMISSAO) FROM FPA_TPDEMISSAO WHERE CDESOCIAL = '@MTVDESLIG@' ), "
    "NRTPAVIPRE = ( SELECT MAX(NRTPAVIPRE) FROM GPE_TIPOAVISOPRE WHERE CDESOCIAL = '@INDCUMPRPARC@' ) "
    "WHERE NRORG = @NRORG@ AND NRVINCULOM = "
    "( SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND CDMATRICULA = '@CDMATRICULA@' );"
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
            "nome": "eSocial S-2299 — Desligamento (UPDATE em GPE_VINCULOM)",
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
        campo(ordem=1, origem="evtDeslig/ideVinculo/matricula", rotulo="Nr. Vínculo (matrícula)",
              campo="CDMATRICULA", marcador="@CDMATRICULA@", destino_tabela="GPE_VINCULOM",
              destino_coluna="NRVINCULOM", tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="evtDeslig/infoDeslig/dtDeslig", rotulo="Data de Rescisão",
              campo="DTRESCISAOVINC", marcador="@DTRESCISAOVINC@", destino_tabela="GPE_VINCULOM",
              destino_coluna="DTRESCISAOVINC", tipo="data", obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=3, origem="evtDeslig/infoDeslig/dtProjFimAPI", rotulo="Data de Aviso Prévio",
              campo="DTAVISOPREVIO", marcador="@DTAVISOPREVIO@", destino_tabela="GPE_VINCULOM",
              destino_coluna="DTAVISOPREVIO", tipo="data", regra_conversao="data_iso"),
        campo(ordem=4, origem="evtDeslig/infoDeslig/observacao", rotulo="Observação da Rescisão",
              campo="DSOBSRESCISAO", marcador="@DSOBSRESCISAO@", destino_tabela="GPE_VINCULOM",
              destino_coluna="DSOBSRESCISAO", tipo="texto", regra_conversao="trim"),
        campo(ordem=5, origem="evtDeslig/infoDeslig/nrProcTrab", rotulo="Nº Processo Judicial",
              campo="NRPROCJUD", marcador="@NRPROCJUD@", destino_tabela="GPE_VINCULOM",
              destino_coluna="NRPROCJUD", tipo="texto", regra_conversao="trim"),
        campo(ordem=6, origem="evtDeslig/infoDeslig/mtvDeslig", rotulo="Motivo do Desligamento (eSocial)",
              campo="MTVDESLIG", marcador="@MTVDESLIG@", destino_tabela="FPA_TPDEMISSAO",
              destino_coluna="CDESOCIAL", tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=7, origem="evtDeslig/infoDeslig/indCumprParc", rotulo="Tipo de Cumprimento do Aviso Prévio (eSocial)",
              campo="INDCUMPRPARC", marcador="@INDCUMPRPARC@", destino_tabela="GPE_TIPOAVISOPRE",
              destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
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
            VALUES (:template_id, 'ALTERACAO', 'ORACLE', 1, NULL, :template_sql, :template_rollback)
            """
        ),
        {
            "template_id": template_id,
            "template_sql": TEMPLATE_SQL,
            "template_rollback": (
                "UPDATE GPE_VINCULOM SET DTRESCISAOVINC = NULL, DTAVISOPREVIO = NULL, "
                "DSOBSRESCISAO = NULL, NRPROCJUD = NULL, NRTPDEMISSAO = NULL, NRTPAVIPRE = NULL "
                "WHERE NRORG = @NRORG@ AND CDMATRICULA = '@CDMATRICULA@';"
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-2299 Desligamento"},
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
