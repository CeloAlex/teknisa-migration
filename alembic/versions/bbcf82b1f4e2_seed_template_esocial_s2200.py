"""seed template esocial s2200

Fase 7 (eSocial) — S-2200 (Admissão de Trabalhador) é o primeiro dos 3 eventos que dependiam
do levantamento funcional completo do Vínculo (revision 1d7a77f2492c) para poder ser
construído. Reaproveita a MESMA forma dos blocos de INSERT do template VINCULO (PARCNEGOCIO,
GPE_PESSOA, GPE_PESSOAH, GPE_VINCULOM, GPE_VINCULOH, GPE_ALTESITUFUNC, ENDERECOPARC,
COMUNICAPARC x3, GPE_MOVIMENTACAO x3) e os MESMOS `gerador_pk_contador` (mesmas tabelas
físicas de destino). Tags confirmadas contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-2200_*.xml`) e a lógica de
`ImportacaoXmlS2200.php`.

Diferenças de fidelidade em relação ao VINCULO (documentadas, não são lacunas silenciosas):

1. **Sem triplicação de GPE_VINCULOH**: a triplicação por ano (Decisão 2 da revisão
   1d7a77f2492c) era uma técnica específica de backfill em massa da migração inicial —
   aqui é um evento pontual, então só 1 histórico é gravado, na competência real do evento
   (`TRUNC(dtAdm,'MM')`), não `TRUNC(SYSDATE,'YYYY')`.
2. **FKs por CDESOCIAL, não por texto livre**: o PHP resolve estado civil, raça, grau de
   instrução, país e logradouro via `findOneBy(['cdesocial' => X])` — os XPaths trazem
   códigos da tabela de domínio do eSocial, não o texto livre que a planilha XLSX trazia.
   As subqueries usam `CDESOCIAL` como critério (mesmo padrão já usado no S-2299 para
   `FPA_TPDEMISSAO.CDESOCIAL`), não `upper_sem_acento`/`tipo_logradouro` (regras da
   planilha, que dependiam de texto livre já normalizado manualmente).
3. **Município por código IBGE**: `codMunic` é o código do IBGE — a subquery usa
   `CDMUNICIBGE`, não `NMMUNICIPIO` (diferente da regra `upper_sem_acento` usada no
   VINCULO, que casava por nome).
4. **Estrutura legal/gerencial/sindical por CNPJ**: o PHP localiza a estrutura por CNPJ +
   tipo de estrutura (`ESTRUTURAH.CDCNPJESTRUT` + `ESTRUTURAM.NRTIPOESTRUTURA`), não por
   `CDINTESTRUTURA` (código livre da planilha). Os tipos de estrutura (legal=20,
   gerencial=7, sindical=10) são resolvidos em runtime por configuração da organização no
   sistema de referência — fixados aqui como constantes, mesma simplificação já documentada
   em `6f30b1f0ac52_seed_template_esocial_s1000.py`. Sem filtro de vigência (mesma
   simplificação de "MAX() sem filtro de data" já usada em todo o motor).
5. **Telefone dividido em DDD+número** (`contato/fonePrinc`, `contato/foneAlternat`): o XML
   traz um único campo; duas novas regras de conversão (`ddd_telefone`/`numero_telefone`,
   em `app/transformation/conversions.py`) replicam o `substr()` condicional do PHP (só
   separa DDD quando o telefone tem mais de 9 dígitos).
6. **`NRVINCULOEMPREG`/`NRTPMOVTRANSFM`/`IDREMUNERACAO`/`IDTPPAGAMENTO`**: expressões `CASE`
   embutidas diretamente no SQL, replicando os `switch`/ternários do PHP sobre
   `natAtividade`, `indPriEmpr` e `undSalFixo` — não há regra de conversão Python para isso
   porque o valor final depende só do dado já presente na própria linha (mesmo raciocínio
   já usado para os `NVL()` do template ESTRUTURA).

Não implementado nesta leva (fora de escopo, mesmo padrão de transparência do restante da
Fase 7): criação automática de escala de trabalho/sindicato quando não encontrados (o PHP
cria essas entidades sob demanda; aqui a subquery resolve NULL, mesma filosofia da Decisão
1 da revisão 1d7a77f2492c — "sem fallback coringa"), fallback de ocupação por
CBO/nome com criação automática (só `codCargo` é mapeado), `GPE_ALTESALARIO` (Alteração
Salarial já é um template próprio, fora do escopo do Vínculo), dependentes
(`trabalhador/dependente`), condição física (`infoDeficiencia`, lógica de código não
confirmada no PHP com segurança), sucessão de vínculo (`sucessaoVinc`).

Revision ID: bbcf82b1f4e2
Revises: 1d7a77f2492c
Create Date: 2026-07-16 18:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bbcf82b1f4e2'
down_revision: Union[str, None] = '1d7a77f2492c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S2200"
TIPO_CODIGO = "MIG_ESOCIAL_S2200"
SEM_ORIGEM = "_fixo_"

# NRTIPOESTRUTURA fixos (legal=20, gerencial=7, sindical=10) — mesma simplificação
# documentada em 6f30b1f0ac52_seed_template_esocial_s1000.py (Divergência 4 acima).
_SUBQUERY_ESTRUTURA_LEGAL = (
    "( SELECT MAX(M.NRESTRUTURAM) FROM ESTRUTURAM M JOIN ESTRUTURAH H ON H.NRORG = "
    "M.NRORG AND H.NRESTRUTURAM = M.NRESTRUTURAM WHERE M.NRORG = @NRORG@ AND "
    "H.CDCNPJESTRUT = '@NRINSC@' AND M.NRTIPOESTRUTURA = 20 )"
)
_SUBQUERY_ESTRUTURA_GERENCIAL = (
    "( SELECT MAX(M.NRESTRUTURAM) FROM ESTRUTURAM M JOIN ESTRUTURAH H ON H.NRORG = "
    "M.NRORG AND H.NRESTRUTURAM = M.NRESTRUTURAM WHERE M.NRORG = @NRORG@ AND "
    "H.CDCNPJESTRUT = '@NRINSC@' AND M.NRTIPOESTRUTURA = 7 )"
)
_SUBQUERY_ESTRUTURA_SINDICAL = (
    "( SELECT MAX(M.NRESTRUTURAM) FROM ESTRUTURAM M JOIN ESTRUTURAH H ON H.NRORG = "
    "M.NRORG AND H.NRESTRUTURAM = M.NRESTRUTURAM WHERE M.NRORG = @NRORG@ AND "
    "H.CDCNPJESTRUT = '@CNPJSINDCATEGPROF@' AND M.NRTIPOESTRUTURA = 10 )"
)

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
    "CDESTACIVIL, NRCPFPESSOA, NRCTPSPESSOA, NRSERIECTPSPES, SGUFCTPSPES, NRPISPASEPPES, "
    "NRCARTHABPES, DTVALHABCARTPES, DSCATEGHABCART, NRRGPESSOA, CDEXRGPESSOA, "
    "DTEXRGPESSOA, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRRACAPESSOA, CDPAIS, "
    "SGESTADO, CDMUNICIPIO, DTNASCPESSOA, IDSEXOPESSOA, NRNACIONALID, NRGRAUINSTR ) "
    "VALUES ( @NRPESSOAH@, @NRPESSOA@, @NRORG@, TRUNC(TO_DATE('@DTADMISSAO@','DD/MM/YYYY'),"
    "'MM'), '@NOMEVINC@', ( SELECT MAX(CDESTACIVIL) FROM ESTADOCIVIL WHERE CDESOCIAL = "
    "'@ESTCIV@' ), '@CPF@', '@CTPS@', '@SERIECTPS@', '@UFCTPS@', '@PIS@', '@CNH@', "
    "'@DTVALCNH@', '@CATCNH@', '@NRRG@', '@CDEXRG@', '@DTEXRG@', SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', ( SELECT MAX(NRRACAPESSOA) FROM GPE_RACAPESSOA WHERE CDESOCIAL = "
    "'@RACACOR@' ), ( SELECT MAX(CDPAIS) FROM PAIS WHERE CDESOCIAL = '@PAISNASC@' ), "
    "'@UFNASC@', ( SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE CDMUNICIBGE = "
    "'@CODMUNIC@' ), '@DTNASCI@', '@IDSEXO@', ( SELECT MAX(NRNACIONALIDADE) FROM "
    "GPE_NACIONALIDADE WHERE CDPAIS = ( SELECT MAX(CDPAIS) FROM PAIS WHERE CDESOCIAL = "
    "'@PAISNAC@' ) ), ( SELECT MAX(NRGRAUINSTR) FROM GPE_GRAUINSTR WHERE CDESOCIAL = "
    "'@GRAUINSTR@' ) );"
)

SQL_GPE_VINCULOM = (
    "INSERT INTO GPE_VINCULOM (NRVINCULOM, NRPESSOA, NRORG, CDMATRICULA, DTADMISSAOVINC, "
    "DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOVINCULOM, NRVINCULOEMPREG, "
    "NRTPADMISSAO, DTOPCAOFGTS, DTPRIMADMISSAO, NMVINCULOM, DTFIMCONTRDETERMIN) "
    "VALUES (@NRVINCULOM@, @NRPESSOA@, @NRORG@, '@CDMATRICULA@', '@DTADMISSAO@', SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@', 1, ( CASE '@NATATIVIDADE@' WHEN '1' THEN 1 ELSE 4 END ), "
    "'@NRTPADMISSAO@', '@DTADMISSAO@', '@DTADMISSAO@', '@NOMEVINC@', "
    "'@DTFIMCONTRDETERMIN@');"
)

SQL_GPE_VINCULOH = (
    "INSERT INTO GPE_VINCULOH (NRVINCULOH, NRVINCULOM, NRSITUFUNCM, NRCARGO, NRFUNCAO, "
    "NRORG, DTMESCOMPETENC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, DTBASEFERIAS, "
    "IDREMUNERACAO, IDTPPAGAMENTO, NRESTRUTLEGAL, NRESTRUTGEREN, NRESTRUTSIND, IDMULTVINC, "
    "NRTPMOVTRANSFM, DTFIMCONTRDETERMIN, CONFIDENCIAL) "
    "VALUES (@NRVINCULOH@, @NRVINCULOM@, '@NRSITUFUNCM@', "
    "(SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND CDINTEGRACAO = "
    "'@CODCARGO@'), (SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND "
    "CDINTEGRACAO = '@CODFUNCAO@'), @NRORG@, TRUNC(TO_DATE('@DTADMISSAO@','DD/MM/YYYY'),"
    "'MM'), SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@DTADMISSAO@', "
    "( CASE '@UNDSALFIXO@' WHEN '1' THEN 'SAL2' ELSE 'SAL1' END ), "
    "( CASE '@UNDSALFIXO@' WHEN '1' THEN 'MENSAL_SALARIO_HORA' WHEN '2' THEN 'DIARIO' "
    "WHEN '3' THEN 'SEMANAL' WHEN '4' THEN 'QUINZENAL' WHEN '5' THEN 'MENSAL' "
    "WHEN '6' THEN 'TAREFA' END ), " + _SUBQUERY_ESTRUTURA_LEGAL + ", " +
    _SUBQUERY_ESTRUTURA_GERENCIAL + ", " + _SUBQUERY_ESTRUTURA_SINDICAL + ", 'UNICO', "
    "( CASE '@INDPRIEMPR@' WHEN 'S' THEN 1 ELSE 2 END ), '@DTFIMCONTRDETERMIN@', 'N' );"
)

SQL_GPE_ALTESITUFUNC = (
    "INSERT INTO GPE_ALTESITUFUNC ( NRALTESITUFUNC, NRORG, NRSITUFUNCM, NRVINCULOM, "
    "DTINISITUFUNC, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) "
    "VALUES ( @NRALTESITUFUNC@, @NRORG@, '@NRSITUFUNCM@', @NRVINCULOM@, "
    "'@DTADMISSAO@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
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
    "'PRINCIPAL', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '0055', "
    "( SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE CDMUNICIBGE = '@CODMUNIC_END@' ), "
    "( SELECT MAX(CDLOGRADOURO) FROM LOGRADOURO WHERE CDESOCIAL = '@TPLOGRAD@' ), "
    "'@BAIRRO_END@', '@COMPLEMENTO_END@', '@CEP_END@', '@DSLOGRAD_END@', "
    "'@NRLOGRAD_END@', '@UF_END@');"
)

SQL_MOVIMENTACAO_LEGAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_LEG@, "
    "@NRORG@, @NRVINCULOM@, 1, 1, " + _SUBQUERY_ESTRUTURA_LEGAL + ", '@DTADMISSAO@', "
    "'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 20 );"
)

SQL_MOVIMENTACAO_GERENCIAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_GER@, "
    "@NRORG@, @NRVINCULOM@, 2, 1, " + _SUBQUERY_ESTRUTURA_GERENCIAL + ", '@DTADMISSAO@', "
    "'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 7 );"
)

SQL_MOVIMENTACAO_SINDICAL = (
    "INSERT INTO GPE_MOVIMENTACAO ( NRMOVIMENTACAO, NRORG, NRVINCULOM, NRTIPOTRANSFER, "
    "NRTPMOVTRANSFM, NRESTRUTURAM, DTINIMOVIMENT, DSOBSERVACAO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRTIPOESTRUTURA ) VALUES ( @NRMOVIMENTACAO_SIN@, "
    "@NRORG@, @NRVINCULOM@, 1, 1, " + _SUBQUERY_ESTRUTURA_SINDICAL + ", '@DTADMISSAO@', "
    "'Movimentacao gerada via migracao ' || SYSDATE, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', 10 );"
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
            "nome": "eSocial S-2200 — Admissão de Trabalhador (via Vínculo)",
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
        campo(ordem=1, origem="evtAdmissao/trabalhador/cpfTrab", rotulo="CPF", campo="CPF",
              marcador="@CPF@", destino_tabela="PARCNEGOCIO/GPE_PESSOAH", destino_coluna="NRINSCRICAOPARC/NRCPFPESSOA",
              tipo="texto", obrigatorio=True, regra_conversao="cpf"),
        campo(ordem=2, origem="evtAdmissao/trabalhador/nmTrab", rotulo="Nome", campo="NOMEVINC",
              marcador="@NOMEVINC@", destino_tabela="PARCNEGOCIO/GPE_PESSOAH/GPE_VINCULOM",
              destino_coluna="NMPRINCIPALPARC/NMPESSOA/NMVINCULOM", tipo="texto", obrigatorio=True,
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=3, origem="evtAdmissao/trabalhador/sexo", rotulo="Sexo", campo="IDSEXO",
              marcador="@IDSEXO@", destino_tabela="GPE_PESSOAH", destino_coluna="IDSEXOPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=4, origem="evtAdmissao/trabalhador/racaCor", rotulo="Raça (eSocial)", campo="RACACOR",
              marcador="@RACACOR@", destino_tabela="GPE_RACAPESSOA", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=5, origem="evtAdmissao/trabalhador/estCiv", rotulo="Estado Civil (eSocial)", campo="ESTCIV",
              marcador="@ESTCIV@", destino_tabela="ESTADOCIVIL", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=6, origem="evtAdmissao/trabalhador/grauInstr", rotulo="Grau Instrução (eSocial)", campo="GRAUINSTR",
              marcador="@GRAUINSTR@", destino_tabela="GPE_GRAUINSTR", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=7, origem="evtAdmissao/trabalhador/nascimento/dtNascto", rotulo="Data Nascimento", campo="DTNASCI",
              marcador="@DTNASCI@", destino_tabela="PARCNEGOCIO/GPE_PESSOAH", destino_coluna="DTNASCIFUNDPARC/DTNASCPESSOA",
              tipo="data", regra_conversao="data_iso"),
        campo(ordem=8, origem="evtAdmissao/trabalhador/nascimento/paisNascto", rotulo="País Nascimento (eSocial)", campo="PAISNASC",
              marcador="@PAISNASC@", destino_tabela="PAIS", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=9, origem="evtAdmissao/trabalhador/nascimento/paisNac", rotulo="Nacionalidade (eSocial)", campo="PAISNAC",
              marcador="@PAISNAC@", destino_tabela="PAIS/GPE_NACIONALIDADE", destino_coluna="CDESOCIAL/CDPAIS", tipo="texto", regra_conversao="trim"),
        campo(ordem=10, origem="evtAdmissao/trabalhador/nascimento/codMunic", rotulo="Município Nascimento (IBGE)", campo="CODMUNIC",
              marcador="@CODMUNIC@", destino_tabela="MUNICIPIO", destino_coluna="CDMUNICIBGE", tipo="texto", regra_conversao="trim"),
        campo(ordem=11, origem="evtAdmissao/trabalhador/nascimento/uf", rotulo="UF Nascimento", campo="UFNASC",
              marcador="@UFNASC@", destino_tabela="GPE_PESSOAH", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        campo(ordem=12, origem="evtAdmissao/trabalhador/documentos/CTPS/nrCtps", rotulo="CTPS", campo="CTPS",
              marcador="@CTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRCTPSPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=13, origem="evtAdmissao/trabalhador/documentos/CTPS/serieCtps", rotulo="Série CTPS", campo="SERIECTPS",
              marcador="@SERIECTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRSERIECTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=14, origem="evtAdmissao/trabalhador/documentos/CTPS/ufCtps", rotulo="UF CTPS", campo="UFCTPS",
              marcador="@UFCTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="SGUFCTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=15, origem="evtAdmissao/trabalhador/documentos/RG/nrRg", rotulo="RG", campo="NRRG",
              marcador="@NRRG@", destino_tabela="GPE_PESSOAH", destino_coluna="NRRGPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=16, origem="evtAdmissao/trabalhador/documentos/RG/orgaoEmissor", rotulo="Órgão Emissor RG", campo="CDEXRG",
              marcador="@CDEXRG@", destino_tabela="GPE_PESSOAH", destino_coluna="CDEXRGPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=17, origem="evtAdmissao/trabalhador/documentos/RG/dtExped", rotulo="Data Emissão RG", campo="DTEXRG",
              marcador="@DTEXRG@", destino_tabela="GPE_PESSOAH", destino_coluna="DTEXRGPESSOA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=18, origem="evtAdmissao/trabalhador/documentos/CNH/nrRegCnh", rotulo="CNH", campo="CNH",
              marcador="@CNH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRCARTHABPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=19, origem="evtAdmissao/trabalhador/documentos/CNH/dtValid", rotulo="Vencimento CNH", campo="DTVALCNH",
              marcador="@DTVALCNH@", destino_tabela="GPE_PESSOAH", destino_coluna="DTVALHABCARTPES", tipo="data", regra_conversao="data_iso"),
        campo(ordem=20, origem="evtAdmissao/trabalhador/documentos/CNH/categoriaCnh", rotulo="Categoria CNH", campo="CATCNH",
              marcador="@CATCNH@", destino_tabela="GPE_PESSOAH", destino_coluna="DSCATEGHABCART", tipo="texto", regra_conversao="trim"),
        campo(ordem=21, origem="evtAdmissao/trabalhador/nisTrab", rotulo="PIS/PASEP", campo="PIS",
              marcador="@PIS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPISPASEPPES", tipo="texto", regra_conversao="trim"),
        # --- endereço (trabalhador/endereco/brasil) ---
        campo(ordem=22, origem="evtAdmissao/trabalhador/endereco/brasil/codMunic", rotulo="Município Endereço (IBGE)",
              campo="CODMUNIC_END", marcador="@CODMUNIC_END@", destino_tabela="MUNICIPIO", destino_coluna="CDMUNICIBGE",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=23, origem="evtAdmissao/trabalhador/endereco/brasil/tpLograd", rotulo="Tipo Logradouro (eSocial)",
              campo="TPLOGRAD", marcador="@TPLOGRAD@", destino_tabela="LOGRADOURO", destino_coluna="CDESOCIAL",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=24, origem="evtAdmissao/trabalhador/endereco/brasil/bairro", rotulo="Bairro", campo="BAIRRO_END",
              marcador="@BAIRRO_END@", destino_tabela="ENDERECOPARC", destino_coluna="NMBAIRROENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=25, origem="evtAdmissao/trabalhador/endereco/brasil/complemento", rotulo="Complemento", campo="COMPLEMENTO_END",
              marcador="@COMPLEMENTO_END@", destino_tabela="ENDERECOPARC", destino_coluna="DSCOMPLEENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=26, origem="evtAdmissao/trabalhador/endereco/brasil/cep", rotulo="CEP", campo="CEP_END",
              marcador="@CEP_END@", destino_tabela="ENDERECOPARC", destino_coluna="NRCEPENDERECO", tipo="texto", regra_conversao="trim"),
        campo(ordem=27, origem="evtAdmissao/trabalhador/endereco/brasil/dscLograd", rotulo="Endereço", campo="DSLOGRAD_END",
              marcador="@DSLOGRAD_END@", destino_tabela="ENDERECOPARC", destino_coluna="DSENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=28, origem="evtAdmissao/trabalhador/endereco/brasil/nrLograd", rotulo="Número", campo="NRLOGRAD_END",
              marcador="@NRLOGRAD_END@", destino_tabela="ENDERECOPARC", destino_coluna="NRIMOVELENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=29, origem="evtAdmissao/trabalhador/endereco/brasil/uf", rotulo="Estado (Endereço)", campo="UF_END",
              marcador="@UF_END@", destino_tabela="ENDERECOPARC", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        # --- derivado: existência de endereço (Seção 7.6/26.4) ---
        campo(ordem=30, origem="campo:DSLOGRAD_END,CODMUNIC_END", rotulo="Tem endereço? (derivado)",
              campo="_TEM_ENDERECO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- contato: telefone dividido em DDD+número (Divergência 5) ---
        campo(ordem=31, origem="evtAdmissao/trabalhador/contato/fonePrinc", rotulo="DDD Telefone Principal (derivado)",
              campo="DDDTELPRI", marcador="@DDDTELPRI@", destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC",
              tipo="texto", regra_conversao="ddd_telefone"),
        campo(ordem=32, origem="evtAdmissao/trabalhador/contato/fonePrinc", rotulo="Telefone Principal (derivado)",
              campo="TELPRI", marcador="@TELPRI@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC",
              tipo="texto", regra_conversao="numero_telefone"),
        campo(ordem=33, origem="campo:TELPRI", rotulo="Tem telefone principal? (derivado)",
              campo="_TEM_TELPRI", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=34, origem="evtAdmissao/trabalhador/contato/foneAlternat", rotulo="DDD Telefone Celular (derivado)",
              campo="DDDTELCEL", marcador="@DDDTELCEL@", destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC",
              tipo="texto", regra_conversao="ddd_telefone"),
        campo(ordem=35, origem="evtAdmissao/trabalhador/contato/foneAlternat", rotulo="Telefone Celular (derivado)",
              campo="TELCEL", marcador="@TELCEL@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC",
              tipo="texto", regra_conversao="numero_telefone"),
        campo(ordem=36, origem="campo:TELCEL", rotulo="Tem telefone celular? (derivado)",
              campo="_TEM_TELCEL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=37, origem="evtAdmissao/trabalhador/contato/emailPrinc", rotulo="E-mail", campo="EMAIL",
              marcador="@EMAIL@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=38, origem="campo:EMAIL", rotulo="Tem e-mail? (derivado)",
              campo="_TEM_EMAIL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- vínculo ---
        campo(ordem=39, origem="evtAdmissao/vinculo/matricula", rotulo="Nr. Vínculo (matrícula)", campo="CDMATRICULA",
              marcador="@CDMATRICULA@", destino_tabela="GPE_VINCULOM", destino_coluna="CDMATRICULA", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=40, origem="evtAdmissao/vinculo/infoRegimeTrab/infoCeletista/dtAdm", rotulo="Data Admissão",
              campo="DTADMISSAO", marcador="@DTADMISSAO@", destino_tabela="GPE_VINCULOM", destino_coluna="DTADMISSAOVINC",
              tipo="data", obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=41, origem="evtAdmissao/vinculo/infoRegimeTrab/infoCeletista/tpAdmissao", rotulo="Tipo Admissão",
              campo="NRTPADMISSAO", marcador="@NRTPADMISSAO@", destino_tabela="GPE_VINCULOM", destino_coluna="NRTPADMISSAO",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=42, origem="evtAdmissao/vinculo/infoRegimeTrab/infoCeletista/natAtividade", rotulo="Natureza Atividade (eSocial)",
              campo="NATATIVIDADE", marcador="@NATATIVIDADE@", destino_tabela="GPE_VINCULOM", destino_coluna="NRVINCULOEMPREG (derivado)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=43, origem="evtAdmissao/trabalhador/indPriEmpr", rotulo="Indicador Primeiro Emprego (eSocial)",
              campo="INDPRIEMPR", marcador="@INDPRIEMPR@", destino_tabela="GPE_VINCULOH", destino_coluna="NRTPMOVTRANSFM (derivado)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=44, origem="evtAdmissao/vinculo/infoRegimeTrab/infoCeletista/cnpjSindCategProf", rotulo="CNPJ Sindicato",
              campo="CNPJSINDCATEGPROF", marcador="@CNPJSINDCATEGPROF@", destino_tabela="ESTRUTURAH",
              destino_coluna="CDCNPJESTRUT (subquery)", tipo="texto", regra_conversao="remover_mascara"),
        campo(ordem=45, origem="evtAdmissao/vinculo/infoContrato/localTrabalho/localTrabGeral/nrInsc",
              rotulo="CNPJ Local de Trabalho", campo="NRINSC", marcador="@NRINSC@", destino_tabela="ESTRUTURAH",
              destino_coluna="CDCNPJESTRUT (subquery)", tipo="texto", obrigatorio=True, regra_conversao="remover_mascara"),
        campo(ordem=46, origem="evtAdmissao/vinculo/infoContrato/codCargo", rotulo="Código do Cargo (integração)",
              campo="CODCARGO", marcador="@CODCARGO@", destino_tabela="GPE_VINCULOH", destino_coluna="NRCARGO (subquery)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=47, origem="evtAdmissao/vinculo/infoContrato/codFuncao", rotulo="Código da Função (integração)",
              campo="CODFUNCAO", marcador="@CODFUNCAO@", destino_tabela="GPE_VINCULOH", destino_coluna="NRFUNCAO (subquery)",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=48, origem="evtAdmissao/vinculo/infoContrato/remuneracao/undSalFixo", rotulo="Unidade Salário Fixo (eSocial)",
              campo="UNDSALFIXO", marcador="@UNDSALFIXO@", destino_tabela="GPE_VINCULOH",
              destino_coluna="IDREMUNERACAO/IDTPPAGAMENTO (derivado)", tipo="texto", regra_conversao="trim"),
        campo(ordem=49, origem="evtAdmissao/vinculo/infoContrato/duracao/dtTerm", rotulo="Fim Contrato Determinado",
              campo="DTFIMCONTRDETERMIN", marcador="@DTFIMCONTRDETERMIN@", destino_tabela="GPE_VINCULOM/GPE_VINCULOH",
              destino_coluna="DTFIMCONTRDETERMIN", tipo="data", regra_conversao="data_iso"),
        # --- derivados de situação funcional (mesma regra do Vínculo — 1d7a77f2492c) ---
        campo(ordem=50, origem="evtAdmissao/vinculo/desligamento/dtDeslig", rotulo="Data Desligamento (raro em admissão)",
              campo="NRSITUFUNCM", marcador="@NRSITUFUNCM@", destino_tabela="GPE_VINCULOH/GPE_ALTESITUFUNC",
              destino_coluna="NRSITUFUNCM", tipo="texto", regra_conversao="situfuncm_por_rescisao"),
        # --- gerados (Key Resolution Service) — MESMOS contadores do template VINCULO ---
        campo(ordem=51, origem="(gerado)", rotulo="Nº PARCNEGOCIO (gerado)", campo="NRPARCNEGOCIO",
              marcador="@NRPARCNEGOCIO@", destino_tabela="PARCNEGOCIO", destino_coluna="NRPARCNEGOCIO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="PARCNEGOCIO", gerador_pk_seed=1738),
        campo(ordem=52, origem="(gerado)", rotulo="Nº GPE_PESSOA (gerado)", campo="NRPESSOA",
              marcador="@NRPESSOA@", destino_tabela="GPE_PESSOA", destino_coluna="NRPESSOA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOA", gerador_pk_seed=0),
        campo(ordem=53, origem="(gerado)", rotulo="Nº GPE_PESSOAH (gerado)", campo="NRPESSOAH",
              marcador="@NRPESSOAH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPESSOAH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOAH", gerador_pk_seed=0),
        campo(ordem=54, origem="(gerado)", rotulo="Nº GPE_VINCULOM (gerado)", campo="NRVINCULOM",
              marcador="@NRVINCULOM@", destino_tabela="GPE_VINCULOM", destino_coluna="NRVINCULOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOM", gerador_pk_seed=949700),
        campo(ordem=55, origem="(gerado)", rotulo="Nº GPE_VINCULOH (gerado)", campo="NRVINCULOH",
              marcador="@NRVINCULOH@", destino_tabela="GPE_VINCULOH", destino_coluna="NRVINCULOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOH", gerador_pk_seed=0),
        campo(ordem=56, origem="(gerado)", rotulo="Nº GPE_ALTESITUFUNC (gerado)", campo="NRALTESITUFUNC",
              marcador="@NRALTESITUFUNC@", destino_tabela="GPE_ALTESITUFUNC", destino_coluna="NRALTESITUFUNC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTESITUFUNC", gerador_pk_seed=6291),
        campo(ordem=57, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Principal (gerado)", campo="NRCOMUNICAPARC",
              marcador="@NRCOMUNICAPARC@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=58, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Celular (gerado)", campo="NRCOMUNICAPARC2",
              marcador="@NRCOMUNICAPARC2@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=59, origem="(gerado)", rotulo="Nº COMUNICAPARC — E-mail (gerado)", campo="NRCOMUNICAPARC3",
              marcador="@NRCOMUNICAPARC3@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=60, origem="(gerado)", rotulo="Nº ENDERECOPARC (gerado)", campo="NRENDERECOPARC",
              marcador="@NRENDERECOPARC@", destino_tabela="ENDERECOPARC", destino_coluna="NRENDERECOPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="ENDERECOPARC", gerador_pk_seed=1718),
        campo(ordem=61, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Legal (gerado)", campo="NRMOVIMENTACAO_LEG",
              marcador="@NRMOVIMENTACAO_LEG@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_MOVIMENTACAO", gerador_pk_seed=36640),
        campo(ordem=62, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Gerencial (gerado)", campo="NRMOVIMENTACAO_GER",
              marcador="@NRMOVIMENTACAO_GER@", destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRMOVIMENTACAO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_MOVIMENTACAO", gerador_pk_seed=36640),
        campo(ordem=63, origem="(gerado)", rotulo="Nº GPE_MOVIMENTACAO — Sindical (gerado)", campo="NRMOVIMENTACAO_SIN",
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
        {"ordem": 1, "condicao_campo": None, "template_sql": SQL_PARCNEGOCIO,
         "template_rollback": "DELETE FROM PARCNEGOCIO WHERE NRORG = @NRORG@ AND NRPARCNEGOCIO = @NRPARCNEGOCIO@;"},
        {"ordem": 2, "condicao_campo": None, "template_sql": SQL_GPE_PESSOA,
         "template_rollback": "DELETE FROM GPE_PESSOA WHERE NRORG = @NRORG@ AND NRPESSOA = @NRPESSOA@;"},
        {"ordem": 3, "condicao_campo": None, "template_sql": SQL_GPE_PESSOAH,
         "template_rollback": "DELETE FROM GPE_PESSOAH WHERE NRORG = @NRORG@ AND NRPESSOAH = @NRPESSOAH@;"},
        {"ordem": 4, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOM,
         "template_rollback": "DELETE FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND NRVINCULOM = @NRVINCULOM@;"},
        {"ordem": 5, "condicao_campo": None, "template_sql": SQL_GPE_VINCULOH,
         "template_rollback": "DELETE FROM GPE_VINCULOH WHERE NRORG = @NRORG@ AND NRVINCULOH = @NRVINCULOH@;"},
        {"ordem": 6, "condicao_campo": None, "template_sql": SQL_GPE_ALTESITUFUNC,
         "template_rollback": "DELETE FROM GPE_ALTESITUFUNC WHERE NRORG = @NRORG@ AND NRALTESITUFUNC = @NRALTESITUFUNC@;"},
        {"ordem": 7, "condicao_campo": "_TEM_TELPRI", "template_sql": SQL_COMUNICAPARC_TELPRI,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC@;"},
        {"ordem": 8, "condicao_campo": "_TEM_TELCEL", "template_sql": SQL_COMUNICAPARC_TELCEL,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC2@;"},
        {"ordem": 9, "condicao_campo": "_TEM_EMAIL", "template_sql": SQL_COMUNICAPARC_EMAIL,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC3@;"},
        {"ordem": 10, "condicao_campo": "_TEM_ENDERECO", "template_sql": SQL_ENDERECOPARC,
         "template_rollback": "DELETE FROM ENDERECOPARC WHERE NRORG = @NRORG@ AND NRENDERECOPARC = @NRENDERECOPARC@;"},
        {"ordem": 11, "condicao_campo": None, "template_sql": SQL_MOVIMENTACAO_LEGAL,
         "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_LEG@;"},
        {"ordem": 12, "condicao_campo": None, "template_sql": SQL_MOVIMENTACAO_GERENCIAL,
         "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_GER@;"},
        {"ordem": 13, "condicao_campo": None, "template_sql": SQL_MOVIMENTACAO_SINDICAL,
         "template_rollback": "DELETE FROM GPE_MOVIMENTACAO WHERE NRORG = @NRORG@ AND NRMOVIMENTACAO = @NRMOVIMENTACAO_SIN@;"},
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-2200 Admissão de Trabalhador"},
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
