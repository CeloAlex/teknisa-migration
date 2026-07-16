"""seed template esocial s2206

Fase 7 (eSocial) — S-2206 (Alteração de Contrato de Trabalho). Terceiro e último dos 3
eventos que dependiam do levantamento funcional completo do Vínculo (revision
1d7a77f2492c). Tags confirmadas contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-2206_*.xml`) e `ImportacaoXmlS2206.php`. O XML
real usa a tag aninhada em `altContratual/vinculo/infoRegimeTrab|infoContrato`, mas o
schema também permite `altContratual/infoRegimeTrab|infoContrato` direto (o PHP checa os
dois caminhos com `isset`) — os `origem` usam `|` (união XPath) para cobrir ambos, mesmo
padrão já usado em `6f30b1f0ac52_seed_template_esocial_s1000.py`.

`NRVINCULOM` é resolvido por subquery via matrícula (`ideVinculo/matricula`), mesmo padrão
do `UPDATE` do S-2299 (`f0a0033203b3`). Diferença central de fidelidade: assim como no
S-2205, o PHP decide em runtime entre atualizar o histórico vigente (se a competência da
alteração bater com a do histórico atual) ou inserir um novo — aqui sempre se insere um
novo histórico de vínculo (`GPE_VINCULOH`), mesmo padrão de simplificação já documentado no
S-2205 e no próprio VINCULO (que também sempre insere histórico novo).

Reaproveita as MESMAS subqueries por CNPJ+NRTIPOESTRUTURA (legal=20, sindical=10) do
S-2200/S-2205 para localizar a estrutura — o PHP só registra uma nova movimentação
**legal** em alteração de contrato (não gerencial nem sindical), então só há 1 bloco de
`GPE_MOVIMENTACAO` aqui, condicionado a `_TEM_ESTRUTLEGAL`.

Não implementado nesta leva (fora de escopo, mesmo padrão do restante da Fase 7):
`GPE_ALTESALARIO` (Alteração Salarial já é um template próprio), `GPE_ALTEOCUPACAO`/
`GPE_ALTEESCALA` (o PHP só os grava quando o cargo/escala realmente muda em relação ao
vínculo atual — decisão que depende de consultar o destino, fora do alcance de um motor
sem conexão viva ao Oracle no momento da geração do script), sucessão/transferência de
domicílio (`transfDom`, não presente neste evento).

Revision ID: 3441380a317b
Revises: e54519c6e6b6
Create Date: 2026-07-16 18:50:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3441380a317b'
down_revision: Union[str, None] = 'e54519c6e6b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S2206"
TIPO_CODIGO = "MIG_ESOCIAL_S2206"

_SUBQUERY_NRVINCULOM = (
    "( SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND "
    "CDMATRICULA = '@CDMATRICULA@' )"
)
_SUBQUERY_ESTRUTURA_LEGAL = (
    "( SELECT MAX(M.NRESTRUTURAM) FROM ESTRUTURAM M JOIN ESTRUTURAH H ON H.NRORG = "
    "M.NRORG AND H.NRESTRUTURAM = M.NRESTRUTURAM WHERE M.NRORG = @NRORG@ AND "
    "H.CDCNPJESTRUT = '@NRINSC@' AND M.NRTIPOESTRUTURA = 20 )"
)
_SUBQUERY_ESTRUTURA_SINDICAL = (
    "( SELECT MAX(M.NRESTRUTURAM) FROM ESTRUTURAM M JOIN ESTRUTURAH H ON H.NRORG = "
    "M.NRORG AND H.NRESTRUTURAM = M.NRESTRUTURAM WHERE M.NRORG = @NRORG@ AND "
    "H.CDCNPJESTRUT = '@CNPJSINDCATEGPROF@' AND M.NRTIPOESTRUTURA = 10 )"
)

SQL_GPE_VINCULOH = (
    "INSERT INTO GPE_VINCULOH (NRVINCULOH, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, "
    "NRORG, DTMESCOMPETENC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRESTRUTLEGAL, "
    "NRESTRUTSIND, DTFIMCONTRDETERMIN, CONFIDENCIAL) "
    "VALUES (@NRVINCULOH@, " + _SUBQUERY_NRVINCULOM + ", '@NRSITUFUNCM@', "
    "(SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND CDINTEGRACAO = "
    "'@CODCARGO@'), (SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND "
    "CDINTEGRACAO = '@CODFUNCAO@'), @NRORG@, TRUNC(TO_DATE('@DTALTERACAO@','DD/MM/YYYY'),"
    "'MM'), SYSDATE, @NRORG@, '@USUARIO_TECNICO@', " + _SUBQUERY_ESTRUTURA_LEGAL + ", " +
    _SUBQUERY_ESTRUTURA_SINDICAL + ", '@DTFIMCONTRDETERMIN@', 'N' );"
)

SQL_MOVIMENTACAO_LEGAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_LEG@, "
    "@NRORG@, " + _SUBQUERY_NRVINCULOM + ", 1, 8, " + _SUBQUERY_ESTRUTURA_LEGAL + ", "
    "'@DTALTERACAO@', 'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 20 );"
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
            "nome": "eSocial S-2206 — Alteração de Contrato de Trabalho (via Vínculo)",
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
        campo(ordem=1, origem="evtAltContratual/ideVinculo/matricula", rotulo="Nr. Vínculo (matrícula)",
              campo="CDMATRICULA", marcador="@CDMATRICULA@", destino_tabela="GPE_VINCULOM",
              destino_coluna="NRVINCULOM (subquery)", tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="evtAltContratual/altContratual/dtAlteracao", rotulo="Data da Alteração",
              campo="DTALTERACAO", marcador="@DTALTERACAO@", destino_tabela="GPE_VINCULOH/GPE_MOVIMENTACAO",
              destino_coluna="DTMESCOMPETENC/DTINIMOVIMENT", tipo="data", obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=3,
              origem="evtAltContratual/altContratual/infoRegimeTrab/infoCeletista/cnpjSindCategProf | "
                     "evtAltContratual/altContratual/vinculo/infoRegimeTrab/infoCeletista/cnpjSindCategProf",
              rotulo="CNPJ Sindicato", campo="CNPJSINDCATEGPROF", marcador="@CNPJSINDCATEGPROF@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCNPJESTRUT (subquery)", tipo="texto",
              regra_conversao="remover_mascara"),
        campo(ordem=4,
              origem="evtAltContratual/altContratual/infoContrato/localTrabalho/localTrabGeral/nrInsc | "
                     "evtAltContratual/altContratual/vinculo/infoContrato/localTrabalho/localTrabGeral/nrInsc",
              rotulo="CNPJ Local de Trabalho", campo="NRINSC", marcador="@NRINSC@", destino_tabela="ESTRUTURAH",
              destino_coluna="CDCNPJESTRUT (subquery)", tipo="texto", regra_conversao="remover_mascara"),
        campo(ordem=5,
              origem="evtAltContratual/altContratual/infoContrato/codCargo | "
                     "evtAltContratual/altContratual/vinculo/infoContrato/codCargo",
              rotulo="Código do Cargo (integração)", campo="CODCARGO", marcador="@CODCARGO@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRCARGO (subquery)", tipo="texto", regra_conversao="trim"),
        campo(ordem=6,
              origem="evtAltContratual/altContratual/infoContrato/codFuncao | "
                     "evtAltContratual/altContratual/vinculo/infoContrato/codFuncao",
              rotulo="Código da Função (integração)", campo="CODFUNCAO", marcador="@CODFUNCAO@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRFUNCAO (subquery)", tipo="texto", regra_conversao="trim"),
        campo(ordem=7,
              origem="evtAltContratual/altContratual/infoContrato/duracao/dtTerm | "
                     "evtAltContratual/altContratual/vinculo/infoContrato/duracao/dtTerm",
              rotulo="Fim Contrato Determinado", campo="DTFIMCONTRDETERMIN", marcador="@DTFIMCONTRDETERMIN@",
              destino_tabela="GPE_VINCULOH", destino_coluna="DTFIMCONTRDETERMIN", tipo="data", regra_conversao="data_iso"),
        # --- derivado: situação funcional (mesma regra do Vínculo — 1d7a77f2492c). Este
        # evento não tem tag de desligamento — o marcador nunca casa, resultando sempre "1".
        campo(ordem=8, origem="evtAltContratual/altContratual/desligamento/dtDeslig", rotulo="(sem origem neste evento)",
              campo="NRSITUFUNCM", marcador="@NRSITUFUNCM@", destino_tabela="GPE_VINCULOH", destino_coluna="NRSITUFUNCM",
              tipo="texto", regra_conversao="situfuncm_por_rescisao"),
        # --- derivado: existência de estrutura legal (condiciona o bloco de movimentação) ---
        campo(ordem=9, origem="campo:NRINSC", rotulo="Tem estrutura legal? (derivado)",
              campo="_TEM_ESTRUTLEGAL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- gerado (Key Resolution Service) — MESMOS contadores do template VINCULO ---
        campo(ordem=10, origem="(gerado)", rotulo="Nº GPE_VINCULOH (gerado)", campo="NRVINCULOH",
              marcador="@NRVINCULOH@", destino_tabela="GPE_VINCULOH", destino_coluna="NRVINCULOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOH", gerador_pk_seed=0),
        campo(ordem=11, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Legal (gerado)", campo="NRMOVIMENTACAO_LEG",
              marcador="@NRMOVIMENTACAO_LEG@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
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

    scripts = [
        {"ordem": 1, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOH,
         "template_rollback": "DELETE FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@;"},
        {"ordem": 2, "condicao_campo": "_TEM_ESTRUTLEGAL", "template_sql": SQL_MOVIMENTACAO_LEGAL,
         "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_LEG@;"},
    ]
    for s in scripts:
        s["template_id"] = template_id

    conn.execute(
        sa.text(
            """
            INSERT INTO template_script (template_id, operacao, dialeto_banco, ordem,
                                          condicao_campo, template_sql, template_rollback)
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', :ordem, :condicao_campo,
                    :template_sql, :template_rollback)
            """
        ),
        scripts,
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-2206 Alteração de Contrato de Trabalho"},
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
