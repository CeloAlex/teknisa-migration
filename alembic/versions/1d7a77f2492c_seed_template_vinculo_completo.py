"""seed template vinculo completo

Levantamento funcional completo do template "Vínculo", substituindo o dicionário parcial
(3 campos) cadastrado na Fase 4 (`951bcfc70d80_seed_template_vinculo_parcial.py`) por um
dicionário e um conjunto completo de blocos de script, extraídos diretamente de
`docs/planilhas-originais/04_Vinculo_v26_BETA.xlsx` (aba "Dados": 224 colunas, linha 1 =
marcadores @CAMPO@, linha 2 = rótulos, linha 3 = fórmulas reais de conversão — as abas
"Base" e "prototipo 3" são só apoio/lookup interno da planilha, não dados de migração).

Reaproveita o MESMO `template_id` já existente (não recria o Template) — só troca nome/
versão e substitui os `template_campo` antigos pelo conjunto completo; nenhuma referência
de `tipo_migracao_template`/`tipo_migracao_template_dependencia` precisa mudar.

10 tabelas de destino, 14 blocos de INSERT (GPE_VINCULOH aparece 3 vezes — ver decisão
abaixo): PARCNEGOCIO, GPE_PESSOA, GPE_PESSOAH, GPE_VINCULOM, GPE_VINCULOH (x3),
GPE_ALTESITUFUNC, CONTCORRPARC, COMUNICAPARC (x3: telefone principal/celular/e-mail),
ENDERECOPARC, GPE_MOVIMENTACAO (x3: legal/gerencial/sindical).

Decisões tomadas em conjunto com o usuário durante o levantamento (divergem do arquivo de
exemplo em pontos específicos, de propósito):

1. **Estruturas coringa removidas**: o arquivo real usa `NVL(subquery, 999992/999993)`
   para gerencial/sindical quando a estrutura não é encontrada — o usuário decidiu não
   inserir nenhum valor de fallback; a subquery agora resolve para NULL quando não
   encontrar correspondência, sem NVL.
2. **GPE_VINCULOH triplicado por ano, não por datas fixas**: o arquivo de exemplo grava 3
   históricos (competência real + 2 cópias em datas fixas hardcoded na própria planilha,
   01/01/2024 e 01/01/2025 — específicas de quando o exemplo foi criado). O usuário pediu
   3 históricos relativos ao ano corrente (ano corrente, ano anterior, 2 anos atrás),
   calculados no próprio Oracle via `TRUNC(SYSDATE,'YYYY')`/`ADD_MONTHS(...)` — assim o
   script continua correto não importa quando for de fato aplicado no destino. Reaproveita
   o padrão do arquivo real de gerar as 2 cópias via `INSERT ... SELECT ... FROM
   GPE_VINCULOH WHERE NRVINCULOH = @NRVINCULOH@` (copia os demais campos do histórico
   recém-inserido) — só 1 PK sequencial é reservada (`NRVINCULOH`); as outras duas são
   `@NRVINCULOH@+1`/`@NRVINCULOH@+2`, aritmética simples, sem precisar de 2 reservas a
   mais no Key Resolution Service (mesma economia que o arquivo real já fazia).
3. **NRSITUFUNCM é campo derivado, não de origem direta**: a coluna D ("Situ. Funcional")
   do arquivo real não é preenchida manualmente — é a fórmula `=IF(DTRESCISAO="",1,13)`.
   Direcionado pelo usuário: com data de rescisão preenchida, código 13; sem rescisão,
   código 1 (nova regra `situfuncm_por_rescisao`). Isso também simplifica o `CASE` que o
   arquivo real usa no INSERT de GPE_ALTESITUFUNC — como o valor derivado nunca vem vazio,
   o `CASE` do SQL original virou desnecessário e foi removido.
4. **NRTPMOVTRANSFM fixo em 2** (assim como no arquivo real) — a coluna BL ("Tp. Mov.
   Transferência") existe na planilha mas não é referenciada por nenhum dos blocos de
   script no arquivo real nem nesta migração (mesma situação já documentada para a coluna
   FPAS da Estrutura, Fase 3) — lida mas não usada. A coluna F ("Mês Competência") também
   não é referenciada por nenhum INSERT.

Verificações de existência de FK contra a aba "Base" (se ocupação/escala/estrutura já
existem no destino, célula a célula) **não foram replicadas** — são um recurso de
pré-checagem client-side da planilha que dependeria de sincronizar manualmente uma cópia
local das tabelas do Oracle de destino; a resolução de FK em si (via subquery embutida no
SQL) já funciona sem isso, igual aos demais templates.

Pequenas simplificações de fidelidade assumidas (documentadas, não são lacunas graves):
CDEXRG/NRRG usam `remover_aspas_e_comercial` como aproximação da limpeza exata de aspas
usada no arquivo real (que remove só `'`/`+`, não `&`); NMMUNICIPIO_END usa
`upper_sem_acento` como aproximação de "upper + remover aspas/comercial" combinados (não
há uma regra só para essa combinação exata ainda).

Revision ID: 1d7a77f2492c
Revises: f0a0033203b3
Create Date: 2026-07-16 18:08:02.910372

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1d7a77f2492c'
down_revision: Union[str, None] = 'f0a0033203b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "VINCULO"

# --- blocos de script (extraídos/adaptados verbatim do arquivo real, ordem EQ2..FF2) ---

SQL_PARCNEGOCIO = (
    "INSERT INTO PARCNEGOCIO ( NRPARCNEGOCIO, NRORG, NMPRINCIPALPARC, NMSECUNDARIPARC, "
    "DTNASCIFUNDPARC, NRINSCRICAOPARC, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "CDTIPOPARCPRINCIPAL, CDTIPOINSCRICAO, IDPESSOAFISICA, IDINSTITUICAO, IDPARCFUNDIDO ) "
    "VALUES ( @NRPARCNEGOCIO@, @NRORG@, '@NOMEVINC@', '@NOMEVINC@', '@DTNASCI@', '@CPF@', "
    "'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 'PESSOA', 'CPF', 'S', 'N', 'N' );"
)

SQL_GPE_PESSOA = (
    "INSERT INTO GPE_PESSOA ( NRPESSOA, NRORG, NRPARCNEGOCIO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRPESSOA@, @NRORG@, @NRPARCNEGOCIO@, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@' );"
)

SQL_GPE_PESSOAH = (
    "INSERT INTO GPE_PESSOAH ( NRPESSOAH, NRPESSOA, NRORG, DTMESCOMPETENC, NMPESSOA, "
    "CDESTACIVIL, NRCPFPESSOA, NRCTPSPESSOA, NRSERIECTPSPES, SGUFCTPSPES, DTCTPSPESSOA, "
    "NRPISPASEPPES, DTINSCPISPASEP, NRTITUELEIPES, NRSECAELEIPES, NRZONAELEIPES, "
    "NRCARTHABPES, DTVALHABCARTPES, DSCATEGHABCART, NRCATMILITARPE, NRCERTRESEPES, "
    "DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRRACAPESSOA, CDPAIS, SGESTADO, "
    "CDMUNICIPIO, DTNASCPESSOA, IDSEXOPESSOA, NRRGPESSOA, CDEXRGPESSOA, SGUFRGPESSOA, "
    "DTEXRGPESSOA, NRNACIONALID, NRGRAUINSTR, NRCONDFISPES ) "
    "VALUES ( @NRPESSOAH@, @NRPESSOA@, @NRORG@, '01/01/2000', '@NOMEVINC@', "
    "'@CDESTACIVIL@', '@CPF@', '@CTPS@', '@SERIECTPS@', '@UFCTPS@', '@DTCTPS@', '@PIS@', "
    "'@DTPIS@', '@TITUELEI@', '@SECAOELEI@', '@ZONAELEI@', '@CNH@', '@DTVALCNH@', "
    "'@CATCNH@', (SELECT NRCATMILITARPE FROM GPE_CATMILITARPE WHERE NRCATMILITARPE = "
    "'@NRCATMILITARPE@'), '@NRCERTRESE@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', "
    "'@NRRACA@', '@CDPAIS@', '@SGESTADO@', (SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE "
    "NMMUNICIPIO = '@NMMUNICIPIO@'), '@DTNASCI@', '@IDSEXO@', '@NRRG@', '@CDEXRG@', "
    "'@UFRG@', '@DTEXRG@', '@NRNACIONALID@', '@NRGRAUINSTR@' , '@NRCONDFISPES@');"
)

SQL_GPE_VINCULOM = (
    "INSERT INTO GPE_VINCULOM (NRVINCULOM, NRPESSOA, NRORG, CDMATRICULA, DTADMISSAOVINC, "
    "DTRESCISAOVINC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOVINCULOM, "
    "NRVINCULOEMPREG, NRTPADMISSAO, NRTPDEMISSAO, DTOPCAOFGTS, DTAPOSENTAFGTS, "
    "DTPRIMADMISSAO, NMVINCULOM, NRMOTIVORESC, DSOBSRESCISAO, DTAVISOPREVIO, "
    "NRDIASCONTRATOEXP, NRDIASCONTRATOEXPPRO, DTEXAMEMEDICO, DTAVISOTRCT) "
    "VALUES (@NRVINCULOM@, @NRPESSOA@, @NRORG@, '@CDMATRICULA@', '@DTADMISSAO@', "
    "'@DTRESCISAO@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@NRTIPOVINCULOM@', "
    "'@NRVINCULOEMPREG@', '@NRTPADMISSAO@', '@NRTPDEMISSAO@', '@DTOPCAOFGTS@', "
    "'@DTAPOSENTAFGTS@', '@DTPRIMADMISSAO@', '@NOMEVINC@', '@NRMOTIVORESC@', "
    "'@DSOBSRESCISAO@', '@DTAVISOPREVIO@', '@NRDIASCONTRATOEXP@', "
    "'@NRDIASCONTRATOEXPPRO@', '@DTEXAMEMEDICO@', '@DTAVISOTRCT@');"
)

# Bloco de histórico 1/3 (ano corrente) — os outros dois (ano anterior / 2 anos atrás) são
# cópias deste via INSERT...SELECT (Decisão 2 da docstring), sem precisar repetir marcador
# nenhum.
SQL_GPE_VINCULOH_ANO_CORRENTE = (
    "INSERT INTO GPE_VINCULOH (NRVINCULOH, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, "
    "NRORG, DTMESCOMPETENC, IDCONTRIBUISIND, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "NRDEPENDIR, NRDEPENDSFAM, DTBASEFERIAS, IDREMUNERACAO, IDTPPAGAMENTO, NRESTRUTLEGAL, "
    "NRESTRUTGEREN, NRESTRUTSIND, NRTPMODALIDSAL, IDMULTVINC, CDCONTRIBINDIVIDUAL, "
    "NRTPMOVTRANSFM, DTFIMCONTRDETERMIN, CONFIDENCIAL, NRESCALATRABM) "
    "VALUES (@NRVINCULOH@, @NRVINCULOM@, '@NRSITUFUNCM@', "
    "(SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND CDINTEGRACAO = "
    "'@OCUPACAO@'), (SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND "
    "CDINTEGRACAO = '@OCUPACAO@'), @NRORG@, TRUNC(SYSDATE,'YYYY'), '@IDCONTRIBUISIND@', "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@NRDEPENDIR@', '@NRDEPENDSFAM@', "
    "'@DTBASEFERIAS@', '@IDREMUNERACAO@', '@IDTPPAGAMENTO@', "
    "(SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE NRORG = @NRORG@ AND CDINTESTRUTURA = "
    "'@ESTRUTLEGAL@'), (SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE NRORG = @NRORG@ AND "
    "CDINTESTRUTURA = '@ESTRUTGEREN@'), (SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE "
    "NRORG = @NRORG@ AND CDINTESTRUTURA = '@ESTRUTSIND@'), '@NRTPMODALIDSAL@', "
    "'@IDMULTVINC@', '@CDCONTRIBINDIVIDUAL@', 2, '@DTFIMCONTRDETERMIN@', 'N', "
    "(SELECT MAX(NRESCALATRABM) FROM GPE_ESCALATRABH WHERE NRORG = @NRORG@ AND "
    "NRESCALATRABM = '@NRESCALATRABM@') );"
)

_COLUNAS_VINCULOH = (
    "NRVINCULOH, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, NRORG, DTMESCOMPETENC, "
    "IDCONTRIBUISIND, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRDEPENDIR, "
    "NRDEPENDSFAM, DTBASEFERIAS, IDREMUNERACAO, IDTPPAGAMENTO, NRESTRUTLEGAL, "
    "NRESTRUTGEREN, NRESTRUTSIND, NRTPMODALIDSAL, IDMULTVINC, CDCONTRIBINDIVIDUAL, "
    "NRTPMOVTRANSFM, DTFIMCONTRDETERMIN, CONFIDENCIAL, NRESCALATRABM"
)

# Bloco 2/3 (ano anterior) e 3/3 (2 anos atrás): cópias do histórico recém-inserido via
# INSERT...SELECT, só trocando NRVINCULOH (+1/+2, aritmética simples — evita reservar mais
# 2 códigos no Key Resolution Service) e DTMESCOMPETENC (ano anterior/retrasado, calculado
# no próprio Oracle a partir de SYSDATE — Decisão 2 da docstring).
SQL_GPE_VINCULOH_ANO_ANTERIOR = (
    f"INSERT INTO GPE_VINCULOH ({_COLUNAS_VINCULOH}) "
    "SELECT @NRVINCULOH@+1, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, NRORG, "
    "ADD_MONTHS(TRUNC(SYSDATE,'YYYY'),-12), IDCONTRIBUISIND, SYSDATE, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, NRDEPENDIR, NRDEPENDSFAM, DTBASEFERIAS, IDREMUNERACAO, "
    "IDTPPAGAMENTO, NRESTRUTLEGAL, NRESTRUTGEREN, NRESTRUTSIND, NRTPMODALIDSAL, "
    "IDMULTVINC, CDCONTRIBINDIVIDUAL, NRTPMOVTRANSFM, DTFIMCONTRDETERMIN, CONFIDENCIAL, "
    "NRESCALATRABM FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@;"
)

SQL_GPE_VINCULOH_DOIS_ANOS_ATRAS = (
    f"INSERT INTO GPE_VINCULOH ({_COLUNAS_VINCULOH}) "
    "SELECT @NRVINCULOH@+2, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, NRORG, "
    "ADD_MONTHS(TRUNC(SYSDATE,'YYYY'),-24), IDCONTRIBUISIND, SYSDATE, NRORGINCLUSAO, "
    "CDOPERINCLUSAO, NRDEPENDIR, NRDEPENDSFAM, DTBASEFERIAS, IDREMUNERACAO, "
    "IDTPPAGAMENTO, NRESTRUTLEGAL, NRESTRUTGEREN, NRESTRUTSIND, NRTPMODALIDSAL, "
    "IDMULTVINC, CDCONTRIBINDIVIDUAL, NRTPMOVTRANSFM, DTFIMCONTRDETERMIN, CONFIDENCIAL, "
    "NRESCALATRABM FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@;"
)

SQL_GPE_ALTESITUFUNC = (
    "INSERT INTO GPE_ALTESITUFUNC ( NRALTESITUFUNC, NRORG, NRSITUFUNCM, NRVINCULOM, "
    "DTINISITUFUNC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) "
    "VALUES ( @NRALTESITUFUNC@, @NRORG@, '@NRSITUFUNCM@', @NRVINCULOM@, "
    "'@DTINISITUFUNC@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_CONTCORRPARC = (
    "INSERT INTO CONTCORRPARC ( NRCONTCORRPARC, NRORG, NRPARCNEGOCIO, CDBANCO, "
    "CDAGENCIA, CDCONTCORR, NRTPCONTCORR, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "IDATIVO ) VALUES ( @NRCONTCORRPARC@, @NRORG@, @NRPARCNEGOCIO@, '@CDBANCO@', "
    "'@CDAGENCIA@', '@CDCONTCORR@', '@NRTPCONTCORR@', SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 'S' );"
)

SQL_COMUNICAPARC_TELPRI = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDPREFIXCOMUPARC, CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRCOMUNICAPARC@, @NRPARCNEGOCIO@, '01', '@DDDTELPRI@', "
    "'@TELPRI@', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_COMUNICAPARC_TELCEL = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDPREFIXCOMUPARC, CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRCOMUNICAPARC2@, @NRPARCNEGOCIO@, '02', '@DDDTELCEL@', "
    "'@TELCEL@', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_COMUNICAPARC_EMAIL = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) "
    "VALUES ( @NRCOMUNICAPARC3@, @NRPARCNEGOCIO@, '05', '@EMAIL@', @NRORG@, 'S', "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_ENDERECOPARC = (
    "INSERT INTO ENDERECOPARC ( NRENDERECOPARC, NRPARCNEGOCIO, CDTIPOENDERECO, NRORG, "
    "IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, CDPAIS, CDMUNICIPIO, "
    "CDLOGRADOURO, NMBAIRROENDERECO, DSCOMPLEENDERECO, NRCEPENDERECO, DSENDERECO, "
    "NRIMOVELENDERECO, SGESTADO ) VALUES ( @NRENDERECOPARC@, @NRPARCNEGOCIO@, "
    "'PRINCIPAL', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@CDPAIS_END@', "
    "( SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE NMMUNICIPIO = '@NMMUNICIPIO_END@' "
    "AND SGESTADO = '@SGESTADO_END@' ), '@CDLOGRADOURO_END@', '@NMBAIRROENDERECO_END@', "
    "'@DSCOMPLEENDERECO_END@', '@NRCEPENDERECO_END@', '@DSENDERECO_END@', "
    "'@NRIMOVELENDERECO_END@', '@SGESTADO_END@');"
)

SQL_MOVIMENTACAO_LEGAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_LEG@, "
    "@NRORG@, @NRVINCULOM@, 1, 1, (SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE NRORG "
    "= @NRORG@ AND CDINTESTRUTURA = '@ESTRUTLEGAL@' AND NRTIPOESTRUTURA = (SELECT "
    "NRTPESTRUTLEGAL FROM GPE_PARAMORG WHERE NRORG = @NRORG@)), '@DTADMISSAO@', "
    "'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', ( SELECT NRTPESTRUTLEGAL FROM GPE_PARAMORG WHERE NRORG = "
    "@NRORG@ ) );"
)

SQL_MOVIMENTACAO_GERENCIAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_GER@, "
    "@NRORG@, @NRVINCULOM@, 2, 1, (SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE NRORG "
    "= @NRORG@ AND CDINTESTRUTURA = '@ESTRUTGEREN@' AND NRTIPOESTRUTURA = (SELECT "
    "NRTPESTRUTGEREN FROM GPE_PARAMORG WHERE NRORG = @NRORG@)), '@DTADMISSAO@', "
    "'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', ( SELECT NRTPESTRUTGEREN FROM GPE_PARAMORG WHERE NRORG = "
    "@NRORG@ ) );"
)

SQL_MOVIMENTACAO_SINDICAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_SIN@, "
    "@NRORG@, @NRVINCULOM@, 1, 1, (SELECT MAX(NRESTRUTURAM) FROM ESTRUTURAM WHERE NRORG "
    "= @NRORG@ AND CDINTESTRUTURA = '@ESTRUTSIND@' AND NRTIPOESTRUTURA = 10), "
    "'@DTADMISSAO@', 'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 10 );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"),
        {"codigo": TEMPLATE_CODIGO},
    ).scalar_one()

    conn.execute(
        sa.text(
            "UPDATE template SET nome = :nome, versao = :versao WHERE id = :template_id"
        ),
        {
            "template_id": template_id,
            "nome": "Vínculo",
            "versao": "26_BETA",
        },
    )

    conn.execute(
        sa.text("DELETE FROM template_campo WHERE template_id = :template_id"),
        {"template_id": template_id},
    )

    def campo(**kw):
        base = {
            "template_id": template_id, "tamanho_maximo": None, "obrigatorio": False,
            "valor_padrao": None, "regra_conversao": None, "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
        }
        base.update(kw)
        return base

    campos = [
        # --- campos diretos do arquivo (aba Dados, linha 1 = marcador, linha 3 = fórmula) ---
        campo(ordem=1, origem="A", rotulo="Data Admissão", campo="DTADMISSAO", marcador="@DTADMISSAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTADMISSAOVINC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=2, origem="B", rotulo="Data Rescisão", campo="DTRESCISAO", marcador="@DTRESCISAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTRESCISAOVINC", tipo="data",
              regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="Nr. Vínculo (matrícula)", campo="CDMATRICULA", marcador="@CDMATRICULA@",
              destino_tabela="GPE_VINCULOM", destino_coluna="CDMATRICULA", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=4, origem="E", rotulo="Escala Trabalho", campo="NRESCALATRABM", marcador="@NRESCALATRABM@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRESCALATRABM (subquery GPE_ESCALATRABH)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=5, origem="G", rotulo="Contribuição Sindical", campo="IDCONTRIBUISIND", marcador="@IDCONTRIBUISIND@",
              destino_tabela="GPE_VINCULOH", destino_coluna="IDCONTRIBUISIND", tipo="texto",
              regra_conversao="upper_sem_acento"),
        campo(ordem=6, origem="H", rotulo="Nome", campo="NOMEVINC", marcador="@NOMEVINC@",
              destino_tabela="PARCNEGOCIO/GPE_PESSOAH/GPE_VINCULOM", destino_coluna="NMPRINCIPALPARC/NMPESSOA/NMVINCULOM",
              tipo="texto", obrigatorio=True, regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=7, origem="I", rotulo="Estado Civil", campo="CDESTACIVIL", marcador="@CDESTACIVIL@",
              destino_tabela="GPE_PESSOAH", destino_coluna="CDESTACIVIL", tipo="texto", regra_conversao="trim"),
        campo(ordem=8, origem="J", rotulo="CPF", campo="CPF", marcador="@CPF@",
              destino_tabela="PARCNEGOCIO/GPE_PESSOAH", destino_coluna="NRINSCRICAOPARC/NRCPFPESSOA",
              tipo="texto", tamanho_maximo=11, obrigatorio=True, regra_conversao="cpf"),
        campo(ordem=9, origem="K", rotulo="CTPS", campo="CTPS", marcador="@CTPS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCTPSPESSOA", tipo="texto",
              tamanho_maximo=7, regra_conversao="ctps"),
        campo(ordem=10, origem="L", rotulo="Série CTPS", campo="SERIECTPS", marcador="@SERIECTPS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRSERIECTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=11, origem="M", rotulo="UF CTPS", campo="UFCTPS", marcador="@UFCTPS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="SGUFCTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=12, origem="N", rotulo="Emissão CTPS", campo="DTCTPS", marcador="@DTCTPS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DTCTPSPESSOA", tipo="data", regra_conversao="data_br"),
        campo(ordem=13, origem="O", rotulo="PIS/PASEP", campo="PIS", marcador="@PIS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRPISPASEPPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=14, origem="P", rotulo="Data Cadastro PIS", campo="DTPIS", marcador="@DTPIS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DTINSCPISPASEP", tipo="data", regra_conversao="data_br"),
        campo(ordem=15, origem="Q", rotulo="Carteira de Identidade (RG)", campo="NRRG", marcador="@NRRG@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRRGPESSOA", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=16, origem="R", rotulo="Órgão Emissor RG", campo="CDEXRG", marcador="@CDEXRG@",
              destino_tabela="GPE_PESSOAH", destino_coluna="CDEXRGPESSOA", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=17, origem="S", rotulo="UF Carteira de Identidade", campo="UFRG", marcador="@UFRG@",
              destino_tabela="GPE_PESSOAH", destino_coluna="SGUFRGPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=18, origem="T", rotulo="Data Emissão RG", campo="DTEXRG", marcador="@DTEXRG@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DTEXRGPESSOA", tipo="data", regra_conversao="data_br"),
        campo(ordem=19, origem="U", rotulo="Título Eleitor", campo="TITUELEI", marcador="@TITUELEI@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRTITUELEIPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=20, origem="V", rotulo="Seção Votação", campo="SECAOELEI", marcador="@SECAOELEI@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRSECAELEIPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=21, origem="W", rotulo="Zona Votação", campo="ZONAELEI", marcador="@ZONAELEI@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRZONAELEIPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=22, origem="X", rotulo="CNH", campo="CNH", marcador="@CNH@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCARTHABPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=23, origem="Y", rotulo="Vencimento CNH", campo="DTVALCNH", marcador="@DTVALCNH@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DTVALHABCARTPES", tipo="data", regra_conversao="data_br"),
        campo(ordem=24, origem="Z", rotulo="Tipo CNH", campo="CATCNH", marcador="@CATCNH@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DSCATEGHABCART", tipo="texto", regra_conversao="trim"),
        campo(ordem=25, origem="AA", rotulo="Certificado Reservista", campo="NRCERTRESE", marcador="@NRCERTRESE@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCERTRESEPES", tipo="texto",
              tamanho_maximo=20, regra_conversao="truncar"),
        campo(ordem=26, origem="AB", rotulo="Categoria Militar", campo="NRCATMILITARPE", marcador="@NRCATMILITARPE@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCATMILITARPE (subquery GPE_CATMILITARPE)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=27, origem="AC", rotulo="Raça", campo="NRRACA", marcador="@NRRACA@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRRACAPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=28, origem="AD", rotulo="País", campo="CDPAIS", marcador="@CDPAIS@",
              destino_tabela="GPE_PESSOAH", destino_coluna="CDPAIS", tipo="texto", regra_conversao="trim"),
        campo(ordem=29, origem="AE", rotulo="Estado", campo="SGESTADO", marcador="@SGESTADO@",
              destino_tabela="GPE_PESSOAH", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        campo(ordem=30, origem="AF", rotulo="Naturalidade (Município)", campo="NMMUNICIPIO", marcador="@NMMUNICIPIO@",
              destino_tabela="GPE_PESSOAH", destino_coluna="CDMUNICIPIO (subquery MUNICIPIO)",
              tipo="texto", regra_conversao="upper_sem_acento"),
        campo(ordem=31, origem="AG", rotulo="Data Nascimento", campo="DTNASCI", marcador="@DTNASCI@",
              destino_tabela="PARCNEGOCIO/GPE_PESSOAH", destino_coluna="DTNASCIFUNDPARC/DTNASCPESSOA",
              tipo="data", regra_conversao="data_br"),
        campo(ordem=32, origem="AH", rotulo="Sexo", campo="IDSEXO", marcador="@IDSEXO@",
              destino_tabela="GPE_PESSOAH", destino_coluna="IDSEXOPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=33, origem="AI", rotulo="Tipo Remuneração", campo="IDREMUNERACAO", marcador="@IDREMUNERACAO@",
              destino_tabela="GPE_VINCULOH", destino_coluna="IDREMUNERACAO", tipo="texto", regra_conversao="trim"),
        campo(ordem=34, origem="AJ", rotulo="Banco", campo="CDBANCO", marcador="@CDBANCO@",
              destino_tabela="CONTCORRPARC", destino_coluna="CDBANCO", tipo="texto",
              tamanho_maximo=3, regra_conversao="zero_esquerda"),
        campo(ordem=35, origem="AK", rotulo="Agência", campo="CDAGENCIA", marcador="@CDAGENCIA@",
              destino_tabela="CONTCORRPARC", destino_coluna="CDAGENCIA", tipo="texto",
              regra_conversao="agencia_bancaria"),
        campo(ordem=36, origem="AL", rotulo="Conta Corrente", campo="CDCONTCORR", marcador="@CDCONTCORR@",
              destino_tabela="CONTCORRPARC", destino_coluna="CDCONTCORR", tipo="texto",
              regra_conversao="conta_corrente"),
        campo(ordem=37, origem="AM", rotulo="Tipo Conta Corrente", campo="NRTPCONTCORR", marcador="@NRTPCONTCORR@",
              destino_tabela="CONTCORRPARC", destino_coluna="NRTPCONTCORR", tipo="texto", regra_conversao="trim"),
        campo(ordem=38, origem="AN", rotulo="Nacionalidade", campo="NRNACIONALID", marcador="@NRNACIONALID@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRNACIONALID", tipo="texto", regra_conversao="trim"),
        campo(ordem=39, origem="AO", rotulo="Tipo Pagamento", campo="IDTPPAGAMENTO", marcador="@IDTPPAGAMENTO@",
              destino_tabela="GPE_VINCULOH", destino_coluna="IDTPPAGAMENTO", tipo="texto", regra_conversao="trim"),
        campo(ordem=40, origem="AP", rotulo="Estrutura Trabalho (Legal)", campo="ESTRUTLEGAL", marcador="@ESTRUTLEGAL@",
              destino_tabela="GPE_VINCULOH/GPE_MOVIMENTACAO", destino_coluna="NRESTRUTLEGAL (subquery ESTRUTURAM)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=41, origem="AQ", rotulo="Estrutura Gerencial", campo="ESTRUTGEREN", marcador="@ESTRUTGEREN@",
              destino_tabela="GPE_VINCULOH/GPE_MOVIMENTACAO", destino_coluna="NRESTRUTGEREN (subquery ESTRUTURAM)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=42, origem="AR", rotulo="País (Endereço)", campo="CDPAIS_END", marcador="@CDPAIS_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDPAIS", tipo="texto",
              tamanho_maximo=4, regra_conversao="zero_esquerda"),
        campo(ordem=43, origem="AS", rotulo="Estado (Endereço)", campo="SGESTADO_END", marcador="@SGESTADO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        campo(ordem=44, origem="AT", rotulo="Município (Endereço)", campo="NMMUNICIPIO_END", marcador="@NMMUNICIPIO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDMUNICIPIO (subquery MUNICIPIO)",
              tipo="texto", regra_conversao="upper_sem_acento"),
        campo(ordem=45, origem="AU", rotulo="Logradouro (Endereço)", campo="CDLOGRADOURO_END", marcador="@CDLOGRADOURO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDLOGRADOURO", tipo="texto",
              regra_conversao="tipo_logradouro"),
        campo(ordem=46, origem="AV", rotulo="Endereço", campo="DSENDERECO_END", marcador="@DSENDERECO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="DSENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=47, origem="AW", rotulo="Número (Endereço)", campo="NRIMOVELENDERECO_END", marcador="@NRIMOVELENDERECO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRIMOVELENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=48, origem="AX", rotulo="Bairro (Endereço)", campo="NMBAIRROENDERECO_END", marcador="@NMBAIRROENDERECO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="NMBAIRROENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=49, origem="AY", rotulo="Complemento (Endereço)", campo="DSCOMPLEENDERECO_END", marcador="@DSCOMPLEENDERECO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="DSCOMPLEENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=50, origem="AZ", rotulo="CEP (Endereço)", campo="NRCEPENDERECO_END", marcador="@NRCEPENDERECO_END@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRCEPENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=51, origem="BA", rotulo="Tipo Vínculo Mestre", campo="NRTIPOVINCULOM", marcador="@NRTIPOVINCULOM@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRTIPOVINCULOM", tipo="texto", regra_conversao="trim"),
        campo(ordem=52, origem="BB", rotulo="Tipo de Demissão", campo="NRTPDEMISSAO", marcador="@NRTPDEMISSAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRTPDEMISSAO", tipo="texto", regra_conversao="trim"),
        campo(ordem=53, origem="BC", rotulo="Data Opção FGTS", campo="DTOPCAOFGTS", marcador="@DTOPCAOFGTS@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTOPCAOFGTS", tipo="data", regra_conversao="data_br"),
        campo(ordem=54, origem="BD", rotulo="Data Aposentadoria FGTS", campo="DTAPOSENTAFGTS", marcador="@DTAPOSENTAFGTS@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTAPOSENTAFGTS", tipo="data", regra_conversao="data_br"),
        campo(ordem=55, origem="BE", rotulo="Data Primeira Admissão", campo="DTPRIMADMISSAO", marcador="@DTPRIMADMISSAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTPRIMADMISSAO", tipo="data", regra_conversao="data_br"),
        campo(ordem=56, origem="BF", rotulo="Ocupação", campo="OCUPACAO", marcador="@OCUPACAO@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRCARGO/NRFUNCAO (subquery GPE_OCUPACAOH)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=57, origem="BG", rotulo="Múltiplos Vínculos", campo="IDMULTVINC", marcador="@IDMULTVINC@",
              destino_tabela="GPE_VINCULOH", destino_coluna="IDMULTVINC", tipo="texto", regra_conversao="trim"),
        campo(ordem=58, origem="BH", rotulo="Nr Contrib Individual", campo="CDCONTRIBINDIVIDUAL", marcador="@CDCONTRIBINDIVIDUAL@",
              destino_tabela="GPE_VINCULOH", destino_coluna="CDCONTRIBINDIVIDUAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=59, origem="BI", rotulo="Motivo da Rescisão", campo="NRMOTIVORESC", marcador="@NRMOTIVORESC@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRMOTIVORESC", tipo="texto", regra_conversao="trim"),
        campo(ordem=60, origem="BJ", rotulo="Observação Rescisão", campo="DSOBSRESCISAO", marcador="@DSOBSRESCISAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DSOBSRESCISAO", tipo="texto", regra_conversao="trim"),
        campo(ordem=61, origem="BK", rotulo="Data Aviso Prévio", campo="DTAVISOPREVIO", marcador="@DTAVISOPREVIO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTAVISOPREVIO", tipo="data", regra_conversao="data_br"),
        campo(ordem=62, origem="BM", rotulo="Fim Contrato Determinado", campo="DTFIMCONTRDETERMIN", marcador="@DTFIMCONTRDETERMIN@",
              destino_tabela="GPE_VINCULOH", destino_coluna="DTFIMCONTRDETERMIN", tipo="data", regra_conversao="data_br"),
        campo(ordem=63, origem="BN", rotulo="Vínculo Empregatício", campo="NRVINCULOEMPREG", marcador="@NRVINCULOEMPREG@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRVINCULOEMPREG", tipo="texto", regra_conversao="trim"),
        campo(ordem=64, origem="BO", rotulo="Tipo Admissão", campo="NRTPADMISSAO", marcador="@NRTPADMISSAO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRTPADMISSAO", tipo="texto", regra_conversao="trim"),
        campo(ordem=65, origem="BP", rotulo="Data Base Férias", campo="DTBASEFERIAS", marcador="@DTBASEFERIAS@",
              destino_tabela="GPE_VINCULOH", destino_coluna="DTBASEFERIAS", tipo="data", regra_conversao="data_br"),
        campo(ordem=66, origem="BQ", rotulo="Dependentes IR", campo="NRDEPENDIR", marcador="@NRDEPENDIR@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRDEPENDIR", tipo="texto", regra_conversao="trim"),
        campo(ordem=67, origem="BR", rotulo="Dependentes Sal. Família", campo="NRDEPENDSFAM", marcador="@NRDEPENDSFAM@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRDEPENDSFAM", tipo="texto", regra_conversao="trim"),
        campo(ordem=68, origem="BS", rotulo="Modalidade Salário", campo="NRTPMODALIDSAL", marcador="@NRTPMODALIDSAL@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRTPMODALIDSAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=69, origem="BT", rotulo="Grau Instrução", campo="NRGRAUINSTR", marcador="@NRGRAUINSTR@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRGRAUINSTR", tipo="texto", regra_conversao="trim"),
        campo(ordem=70, origem="BU", rotulo="Estrutura Sindical", campo="ESTRUTSIND", marcador="@ESTRUTSIND@",
              destino_tabela="GPE_VINCULOH/GPE_MOVIMENTACAO", destino_coluna="NRESTRUTSIND (subquery ESTRUTURAM)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=71, origem="BV", rotulo="Dias Contrato Experiência", campo="NRDIASCONTRATOEXP", marcador="@NRDIASCONTRATOEXP@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRDIASCONTRATOEXP", tipo="numerico", regra_conversao="numero_decimal"),
        campo(ordem=72, origem="BW", rotulo="Dias Contrato Experiência (Prorrogação)", campo="NRDIASCONTRATOEXPPRO", marcador="@NRDIASCONTRATOEXPPRO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="NRDIASCONTRATOEXPPRO", tipo="numerico", regra_conversao="numero_decimal"),
        campo(ordem=73, origem="BX", rotulo="Data Exame Médico", campo="DTEXAMEMEDICO", marcador="@DTEXAMEMEDICO@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTEXAMEMEDICO", tipo="data", regra_conversao="data_br"),
        campo(ordem=74, origem="BY", rotulo="Data Aviso TRCT", campo="DTAVISOTRCT", marcador="@DTAVISOTRCT@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTAVISOTRCT", tipo="data", regra_conversao="data_br"),
        campo(ordem=75, origem="CC", rotulo="Condição Física", campo="NRCONDFISPES", marcador="@NRCONDFISPES@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCONDFISPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=76, origem="CD", rotulo="Telefone Principal", campo="TELPRI", marcador="@TELPRI@",
              destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC", tipo="texto", regra_conversao="trim"),
        campo(ordem=77, origem="CE", rotulo="E-mail", campo="EMAIL", marcador="@EMAIL@",
              destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=78, origem="CI", rotulo="DDD Telefone Principal", campo="DDDTELPRI", marcador="@DDDTELPRI@",
              destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC", tipo="texto", regra_conversao="trim"),
        campo(ordem=79, origem="CJ", rotulo="DDD Telefone Celular", campo="DDDTELCEL", marcador="@DDDTELCEL@",
              destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC", tipo="texto", regra_conversao="trim"),
        campo(ordem=80, origem="CK", rotulo="Telefone Celular", campo="TELCEL", marcador="@TELCEL@",
              destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        # --- campos derivados (Seção 7.6/26.4) ---
        campo(ordem=81, origem="campo:DTRESCISAO", rotulo="Situação Funcional (derivado)", campo="NRSITUFUNCM",
              marcador="@NRSITUFUNCM@", destino_tabela="GPE_VINCULOH/GPE_ALTESITUFUNC", destino_coluna="NRSITUFUNCM",
              tipo="texto", regra_conversao="situfuncm_por_rescisao"),
        campo(ordem=82, origem="campo:DTRESCISAO,DTADMISSAO", rotulo="Data Início Situação Funcional (derivado)",
              campo="DTINISITUFUNC", marcador="@DTINISITUFUNC@", destino_tabela="GPE_ALTESITUFUNC",
              destino_coluna="DTINISITUFUNC", tipo="data", regra_conversao="primeiro_nao_vazio"),
        campo(ordem=83, origem="campo:CDBANCO,CDAGENCIA,CDCONTCORR", rotulo="Tem conta corrente? (derivado)",
              campo="_TEM_CONTA", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=84, origem="campo:TELPRI", rotulo="Tem telefone principal? (derivado)",
              campo="_TEM_TELPRI", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=85, origem="campo:TELCEL", rotulo="Tem telefone celular? (derivado)",
              campo="_TEM_TELCEL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=86, origem="campo:EMAIL", rotulo="Tem e-mail? (derivado)",
              campo="_TEM_EMAIL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=87, origem="campo:DSENDERECO_END", rotulo="Tem endereço? (derivado)",
              campo="_TEM_ENDERECO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=88, origem="campo:ESTRUTLEGAL", rotulo="Tem estrutura legal? (derivado)",
              campo="_TEM_ESTRUTLEGAL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=89, origem="campo:ESTRUTGEREN", rotulo="Tem estrutura gerencial? (derivado)",
              campo="_TEM_ESTRUTGEREN", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=90, origem="campo:ESTRUTSIND", rotulo="Tem estrutura sindical? (derivado)",
              campo="_TEM_ESTRUTSIND", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- campos com PK sequencial (Key Resolution Service — Seção 6.1) ---
        # Contadores reaproveitados de templates já existentes que escrevem nas mesmas
        # tabelas físicas: PARCNEGOCIO/ENDERECOPARC (Estrutura), GPE_VINCULOM/
        # GPE_ALTESITUFUNC (Vínculo parcial/Situação Funcional), GPE_MOVIMENTACAO
        # (Movimentações de Estrutura). GPE_PESSOA/H, GPE_VINCULOH, CONTCORRPARC e
        # COMUNICAPARC são contadores novos (seed 0) — nenhum template anterior grava
        # nessas tabelas.
        campo(ordem=91, origem="(gerado)", rotulo="Nº PARCNEGOCIO (gerado)", campo="NRPARCNEGOCIO",
              marcador="@NRPARCNEGOCIO@", destino_tabela="PARCNEGOCIO", destino_coluna="NRPARCNEGOCIO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="PARCNEGOCIO", gerador_pk_seed=1738),
        campo(ordem=92, origem="(gerado)", rotulo="Nº GPE_PESSOA (gerado)", campo="NRPESSOA",
              marcador="@NRPESSOA@", destino_tabela="GPE_PESSOA", destino_coluna="NRPESSOA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOA", gerador_pk_seed=0),
        campo(ordem=93, origem="(gerado)", rotulo="Nº GPE_PESSOAH (gerado)", campo="NRPESSOAH",
              marcador="@NRPESSOAH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPESSOAH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOAH", gerador_pk_seed=0),
        campo(ordem=94, origem="(gerado)", rotulo="Nº GPE_VINCULOM (gerado)", campo="NRVINCULOM",
              marcador="@NRVINCULOM@", destino_tabela="GPE_VINCULOM", destino_coluna="NRVINCULOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOM", gerador_pk_seed=949700),
        campo(ordem=95, origem="(gerado)", rotulo="Nº GPE_VINCULOH (gerado, ano corrente — os outros 2 anos são "
              "@NRVINCULOH@+1/+2, aritmética)", campo="NRVINCULOH", marcador="@NRVINCULOH@",
              destino_tabela="GPE_VINCULOH", destino_coluna="NRVINCULOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOH", gerador_pk_seed=0),
        campo(ordem=96, origem="(gerado)", rotulo="Nº GPE_ALTESITUFUNC (gerado)", campo="NRALTESITUFUNC",
              marcador="@NRALTESITUFUNC@", destino_tabela="GPE_ALTESITUFUNC", destino_coluna="NRALTESITUFUNC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTESITUFUNC", gerador_pk_seed=6291),
        campo(ordem=97, origem="(gerado)", rotulo="Nº CONTCORRPARC (gerado)", campo="NRCONTCORRPARC",
              marcador="@NRCONTCORRPARC@", destino_tabela="CONTCORRPARC", destino_coluna="NRCONTCORRPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="CONTCORRPARC", gerador_pk_seed=0),
        campo(ordem=98, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Principal (gerado)", campo="NRCOMUNICAPARC",
              marcador="@NRCOMUNICAPARC@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=99, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Celular (gerado)", campo="NRCOMUNICAPARC2",
              marcador="@NRCOMUNICAPARC2@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=100, origem="(gerado)", rotulo="Nº COMUNICAPARC — E-mail (gerado)", campo="NRCOMUNICAPARC3",
              marcador="@NRCOMUNICAPARC3@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=101, origem="(gerado)", rotulo="Nº ENDERECOPARC (gerado)", campo="NRENDERECOPARC",
              marcador="@NRENDERECOPARC@", destino_tabela="ENDERECOPARC", destino_coluna="NRENDERECOPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="ENDERECOPARC", gerador_pk_seed=1718),
        campo(ordem=102, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Legal (gerado)", campo="NRMOVIMENTACAO_LEG",
              marcador="@NRMOVIMENTACAO_LEG@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_MOVIMENTACAO", gerador_pk_seed=36640),
        campo(ordem=103, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Gerencial (gerado)", campo="NRMOVIMENTACAO_GER",
              marcador="@NRMOVIMENTACAO_GER@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_MOVIMENTACAO", gerador_pk_seed=36640),
        campo(ordem=104, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Sindical (gerado)", campo="NRMOVIMENTACAO_SIN",
              marcador="@NRMOVIMENTACAO_SIN@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
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
        {
            "ordem": 1, "condicao_campo": None, "template_sql": SQL_PARCNEGOCIO,
            "template_rollback": "DELETE FROM PARCNEGOCIO WHERE NRORG = @NRORG@ AND NRPARCNEGOCIO = @NRPARCNEGOCIO@;",
        },
        {
            "ordem": 2, "condicao_campo": None, "template_sql": SQL_GPE_PESSOA,
            "template_rollback": "DELETE FROM GPE_PESSOA WHERE NRORG = @NRORG@ AND NRPESSOA = @NRPESSOA@;",
        },
        {
            "ordem": 3, "condicao_campo": None, "template_sql": SQL_GPE_PESSOAH,
            "template_rollback": "DELETE FROM GPE_PESSOAH WHERE NRORG = @NRORG@ AND NRPESSOAH = @NRPESSOAH@;",
        },
        {
            "ordem": 4, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOM,
            "template_rollback": "DELETE FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND NRVINCULOM = @NRVINCULOM@;",
        },
        {
            "ordem": 5, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOH_ANO_CORRENTE,
            "template_rollback": "DELETE FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@;",
        },
        {
            "ordem": 6, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOH_ANO_ANTERIOR,
            "template_rollback": "DELETE FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@+1;",
        },
        {
            "ordem": 7, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOH_DOIS_ANOS_ATRAS,
            "template_rollback": "DELETE FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@+2;",
        },
        {
            "ordem": 8, "condicao_campo": None, "template_sql": SQL_GPE_ALTESITUFUNC,
            "template_rollback": "DELETE FROM GPE_ALTESITUFUNC WHERE NRORG = @NRORG@ AND NRALTESITUFUNC = @NRALTESITUFUNC@;",
        },
        {
            "ordem": 9, "condicao_campo": "_TEM_CONTA", "template_sql": SQL_CONTCORRPARC,
            "template_rollback": "DELETE FROM CONTCORRPARC WHERE NRORG = @NRORG@ AND NRCONTCORRPARC = @NRCONTCORRPARC@;",
        },
        {
            "ordem": 10, "condicao_campo": "_TEM_TELPRI", "template_sql": SQL_COMUNICAPARC_TELPRI,
            "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC@;",
        },
        {
            "ordem": 11, "condicao_campo": "_TEM_TELCEL", "template_sql": SQL_COMUNICAPARC_TELCEL,
            "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC2@;",
        },
        {
            "ordem": 12, "condicao_campo": "_TEM_EMAIL", "template_sql": SQL_COMUNICAPARC_EMAIL,
            "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC3@;",
        },
        {
            "ordem": 13, "condicao_campo": "_TEM_ENDERECO", "template_sql": SQL_ENDERECOPARC,
            "template_rollback": "DELETE FROM ENDERECOPARC WHERE NRORG = @NRORG@ AND NRENDERECOPARC = @NRENDERECOPARC@;",
        },
        {
            "ordem": 14, "condicao_campo": "_TEM_ESTRUTLEGAL", "template_sql": SQL_MOVIMENTACAO_LEGAL,
            "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_LEG@;",
        },
        {
            "ordem": 15, "condicao_campo": "_TEM_ESTRUTGEREN", "template_sql": SQL_MOVIMENTACAO_GERENCIAL,
            "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_GER@;",
        },
        {
            "ordem": 16, "condicao_campo": "_TEM_ESTRUTSIND", "template_sql": SQL_MOVIMENTACAO_SINDICAL,
            "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_SIN@;",
        },
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


def downgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"),
        {"codigo": TEMPLATE_CODIGO},
    ).scalar_one()

    conn.execute(
        sa.text("DELETE FROM template_script WHERE template_id = :template_id"),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text("DELETE FROM template_campo WHERE template_id = :template_id"),
        {"template_id": template_id},
    )

    conn.execute(
        sa.text(
            "UPDATE template SET nome = :nome, versao = :versao WHERE id = :template_id"
        ),
        {
            "template_id": template_id,
            "nome": "Vínculo (dicionário parcial — pendente de levantamento funcional completo)",
            "versao": "26_BETA",
        },
    )

    campos_parciais = [
        {
            "template_id": template_id, "ordem": 1, "origem": "A", "rotulo": "Data Admissão",
            "campo": "DTADMISSAOVINC", "marcador": "@DTADMISSAOVINC@", "destino_tabela": "GPE_VINCULOM",
            "destino_coluna": "DTADMISSAOVINC", "tipo": "data", "tamanho_maximo": None,
            "obrigatorio": True, "valor_padrao": None, "regra_conversao": "data_br", "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
        },
        {
            "template_id": template_id, "ordem": 2, "origem": "C", "rotulo": "Nr. Vínculo (matrícula)",
            "campo": "CDMATRICULA", "marcador": "@CDMATRICULA@", "destino_tabela": "GPE_VINCULOM",
            "destino_coluna": "CDMATRICULA", "tipo": "texto", "tamanho_maximo": None,
            "obrigatorio": True, "valor_padrao": None, "regra_conversao": "trim", "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
        },
        {
            "template_id": template_id, "ordem": 3, "origem": "J", "rotulo": "CPF",
            "campo": "NRCPFPESSOA", "marcador": "@CDCPFPESSOA@", "destino_tabela": "GPE_PESSOAH",
            "destino_coluna": "NRCPFPESSOA", "tipo": "texto", "tamanho_maximo": 11,
            "obrigatorio": True, "valor_padrao": None, "regra_conversao": "remover_mascara", "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
        },
        {
            "template_id": template_id, "ordem": 4, "origem": "(gerado)",
            "rotulo": "Nº sequencial de vínculo (gerado)", "campo": "NRVINCULOM",
            "marcador": "@NRVINCULOM@", "destino_tabela": "GPE_VINCULOM", "destino_coluna": "NRVINCULOM",
            "tipo": "numerico", "tamanho_maximo": None, "obrigatorio": False, "valor_padrao": None,
            "regra_conversao": None, "eh_pk": True, "gerador_pk": True,
            "gerador_pk_contador": "GPE_VINCULOM", "gerador_pk_seed": 949700,
        },
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
        campos_parciais,
    )
