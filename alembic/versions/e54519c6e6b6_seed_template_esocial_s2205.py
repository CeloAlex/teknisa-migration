"""seed template esocial s2205

Fase 7 (eSocial) — S-2205 (Alteração de Dados Cadastrais). Segundo dos 3 eventos que
dependiam do levantamento funcional completo do Vínculo (revision 1d7a77f2492c). Reaproveita
o subconjunto do dicionário de PESSOA/PESSOAH/ENDERECOPARC/COMUNICAPARC já usado em
`bbcf82b1f4e2_seed_template_esocial_s2200.py` (mesmas subqueries por CDESOCIAL/CDMUNICIBGE,
mesmo split de telefone em DDD+número). Tags confirmadas contra o XML real de exemplo
(`docs/eSocial/eventos_xml/XML_envio_S-2205_*.xml`) e `ImportacaoXmlS2205.php`.

Diferença central de fidelidade: o PHP decide em runtime entre **atualizar em vaco** o
histórico de pessoa atual (`GPE_PESSOAH`) — se a competência da alteração for igual à do
histórico vigente — ou **inserir um novo histórico** (se for uma competência diferente). O
motor de scripts deste projeto gera INSERTs/UPDATEs de forma determinística a partir do
dicionário, sem consultar o estado atual do destino para decidir entre os dois caminhos;
por isso este template sempre **insere um novo histórico de pessoa** (mesmo padrão já usado
pelo próprio VINCULO, que também sempre insere um novo `GPE_PESSOAH` a cada execução) —
mais simples e seguro que tentar replicar a lógica condicional do PHP sem acesso ao banco
de destino em tempo de geração do script. `NRPESSOA` é resolvido via subquery por CPF
(mesmo padrão usado no `UPDATE` do S-2299 para `NRVINCULOM` por matrícula).

Endereço e contato só são gerados se ainda não existirem no destino no arquivo real (o PHP
faz `findOneBy(...)` antes de inserir) — aqui, como não há consulta ao destino, o bloco
sempre insere quando o XML traz o dado (mesmo padrão de simplificação do restante da Fase 7:
o operador é responsável por não reprocessar o mesmo evento duas vezes).

Não implementado nesta leva (fora de escopo, mesmo padrão do restante da Fase 7):
dependentes (`dadosTrabalhador/dependente`), pai/mãe (`RELACIONAPARC`), endereço no
exterior (`endereco/exterior`), trabalhador estrangeiro (`trabEstrangeiro`).

Revision ID: e54519c6e6b6
Revises: bbcf82b1f4e2
Create Date: 2026-07-16 18:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e54519c6e6b6'
down_revision: Union[str, None] = 'bbcf82b1f4e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESOCIAL_S2205"
TIPO_CODIGO = "MIG_ESOCIAL_S2205"

_SUBQUERY_NRPESSOA = (
    "( SELECT MAX(P.NRPESSOA) FROM GPE_PESSOA P JOIN PARCNEGOCIO PN ON PN.NRORG = P.NRORG "
    "AND PN.NRPARCNEGOCIO = P.NRPARCNEGOCIO WHERE P.NRORG = @NRORG@ AND "
    "PN.NRINSCRICAOPARC = '@CPF@' )"
)
_SUBQUERY_NRPARCNEGOCIO = (
    "( SELECT MAX(P.NRPARCNEGOCIO) FROM GPE_PESSOA P JOIN PARCNEGOCIO PN ON PN.NRORG = "
    "P.NRORG AND PN.NRPARCNEGOCIO = P.NRPARCNEGOCIO WHERE P.NRORG = @NRORG@ AND "
    "PN.NRINSCRICAOPARC = '@CPF@' )"
)

SQL_GPE_PESSOAH = (
    "INSERT INTO GPE_PESSOAH ( NRPESSOAH, NRPESSOA, NRORG, DTMESCOMPETENC, NMPESSOA, "
    "CDESTACIVIL, NRCTPSPESSOA, NRSERIECTPSPES, SGUFCTPSPES, NRPISPASEPPES, NRCARTHABPES, "
    "DTVALHABCARTPES, DSCATEGHABCART, NRRGPESSOA, CDEXRGPESSOA, DTEXRGPESSOA, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, NRRACAPESSOA, CDPAIS, SGESTADO, CDMUNICIPIO, "
    "DTNASCPESSOA, IDSEXOPESSOA, NRNACIONALID, NRGRAUINSTR, NRCPFPESSOA ) "
    "VALUES ( @NRPESSOAH@, " + _SUBQUERY_NRPESSOA + ", @NRORG@, "
    "TRUNC(TO_DATE('@DTALTERACAO@','DD/MM/YYYY'),'MM'), '@NOMEVINC@', "
    "( SELECT MAX(CDESTACIVIL) FROM ESTADOCIVIL WHERE CDESOCIAL = '@ESTCIV@' ), "
    "'@CTPS@', '@SERIECTPS@', '@UFCTPS@', '@PIS@', '@CNH@', '@DTVALCNH@', '@CATCNH@', "
    "'@NRRG@', '@CDEXRG@', '@DTEXRG@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', "
    "( SELECT MAX(NRRACAPESSOA) FROM GPE_RACAPESSOA WHERE CDESOCIAL = '@RACACOR@' ), "
    "( SELECT MAX(CDPAIS) FROM PAIS WHERE CDESOCIAL = '@PAISNAC@' ), '@UFNASC@', "
    "( SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE CDMUNICIBGE = '@CODMUNIC@' ), "
    "'@DTNASCI@', '@IDSEXO@', ( SELECT MAX(NRNACIONALIDADE) FROM GPE_NACIONALIDADE WHERE "
    "CDPAIS = ( SELECT MAX(CDPAIS) FROM PAIS WHERE CDESOCIAL = '@PAISNAC@' ) ), "
    "( SELECT MAX(NRGRAUINSTR) FROM GPE_GRAUINSTR WHERE CDESOCIAL = '@GRAUINSTR@' ), "
    "'@CPF@' );"
)

SQL_COMUNICAPARC_TELPRI = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDPREFIXCOMUPARC, CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRCOMUNICAPARC@, " + _SUBQUERY_NRPARCNEGOCIO + ", '01', "
    "'@DDDTELPRI@', '@TELPRI@', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_COMUNICAPARC_TELCEL = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDPREFIXCOMUPARC, CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRCOMUNICAPARC2@, " + _SUBQUERY_NRPARCNEGOCIO + ", '02', "
    "'@DDDTELCEL@', '@TELCEL@', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_COMUNICAPARC_EMAIL = (
    "INSERT INTO COMUNICAPARC ( NRCOMUNICAPARC, NRPARCNEGOCIO, CDFORMACOMU, "
    "CDCOMUNICAPARC, NRORG, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) "
    "VALUES ( @NRCOMUNICAPARC3@, " + _SUBQUERY_NRPARCNEGOCIO + ", '05', '@EMAIL@', "
    "@NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)

SQL_ENDERECOPARC = (
    "INSERT INTO ENDERECOPARC ( NRENDERECOPARC, NRPARCNEGOCIO, CDTIPOENDERECO, NRORG, "
    "IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, CDPAIS, CDMUNICIPIO, "
    "CDLOGRADOURO, NMBAIRROENDERECO, DSCOMPLEENDERECO, NRCEPENDERECO, DSENDERECO, "
    "NRIMOVELENDERECO, SGESTADO ) VALUES ( @NRENDERECOPARC@, " + _SUBQUERY_NRPARCNEGOCIO +
    ", 'PRINCIPAL', @NRORG@, 'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '0055', "
    "( SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE CDMUNICIBGE = '@CODMUNIC_END@' ), "
    "( SELECT MAX(CDLOGRADOURO) FROM LOGRADOURO WHERE CDESOCIAL = '@TPLOGRAD@' ), "
    "'@BAIRRO_END@', '@COMPLEMENTO_END@', '@CEP_END@', '@DSLOGRAD_END@', "
    "'@NRLOGRAD_END@', '@UF_END@');"
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
            "nome": "eSocial S-2205 — Alteração de Dados Cadastrais (via Vínculo)",
            "versao": "v_S_01_02_00",
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
        campo(ordem=1, origem="evtAltCadastral/ideTrabalhador/cpfTrab", rotulo="CPF", campo="CPF",
              marcador="@CPF@", destino_tabela="GPE_PESSOA/PARCNEGOCIO", destino_coluna="NRPESSOA (subquery)/NRINSCRICAOPARC",
              tipo="texto", obrigatorio=True, regra_conversao="cpf"),
        campo(ordem=2, origem="evtAltCadastral/alteracao/dtAlteracao", rotulo="Data da Alteração",
              campo="DTALTERACAO", marcador="@DTALTERACAO@", destino_tabela="GPE_PESSOAH", destino_coluna="DTMESCOMPETENC",
              tipo="data", obrigatorio=True, regra_conversao="data_iso"),
        campo(ordem=3, origem="evtAltCadastral/alteracao/dadosTrabalhador/nmTrab", rotulo="Nome", campo="NOMEVINC",
              marcador="@NOMEVINC@", destino_tabela="GPE_PESSOAH", destino_coluna="NMPESSOA", tipo="texto",
              obrigatorio=True, regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=4, origem="evtAltCadastral/alteracao/dadosTrabalhador/sexo", rotulo="Sexo", campo="IDSEXO",
              marcador="@IDSEXO@", destino_tabela="GPE_PESSOAH", destino_coluna="IDSEXOPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=5, origem="evtAltCadastral/alteracao/dadosTrabalhador/racaCor", rotulo="Raça (eSocial)", campo="RACACOR",
              marcador="@RACACOR@", destino_tabela="GPE_RACAPESSOA", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=6, origem="evtAltCadastral/alteracao/dadosTrabalhador/estCiv", rotulo="Estado Civil (eSocial)", campo="ESTCIV",
              marcador="@ESTCIV@", destino_tabela="ESTADOCIVIL", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=7, origem="evtAltCadastral/alteracao/dadosTrabalhador/grauInstr", rotulo="Grau Instrução (eSocial)", campo="GRAUINSTR",
              marcador="@GRAUINSTR@", destino_tabela="GPE_GRAUINSTR", destino_coluna="CDESOCIAL", tipo="texto", regra_conversao="trim"),
        campo(ordem=8, origem="evtAltCadastral/alteracao/dadosTrabalhador/paisNac", rotulo="Nacionalidade (eSocial)", campo="PAISNAC",
              marcador="@PAISNAC@", destino_tabela="PAIS/GPE_NACIONALIDADE", destino_coluna="CDESOCIAL/CDPAIS", tipo="texto", regra_conversao="trim"),
        campo(ordem=9, origem="evtAltCadastral/alteracao/dadosTrabalhador/nascimento/dtNascto", rotulo="Data Nascimento", campo="DTNASCI",
              marcador="@DTNASCI@", destino_tabela="GPE_PESSOAH", destino_coluna="DTNASCPESSOA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=10, origem="evtAltCadastral/alteracao/dadosTrabalhador/nascimento/codMunic", rotulo="Município Nascimento (IBGE)",
              campo="CODMUNIC", marcador="@CODMUNIC@", destino_tabela="MUNICIPIO", destino_coluna="CDMUNICIBGE", tipo="texto", regra_conversao="trim"),
        campo(ordem=11, origem="evtAltCadastral/alteracao/dadosTrabalhador/nascimento/uf", rotulo="UF Nascimento", campo="UFNASC",
              marcador="@UFNASC@", destino_tabela="GPE_PESSOAH", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        campo(ordem=12, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CTPS/nrCtps", rotulo="CTPS", campo="CTPS",
              marcador="@CTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRCTPSPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=13, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CTPS/serieCtps", rotulo="Série CTPS", campo="SERIECTPS",
              marcador="@SERIECTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRSERIECTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=14, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CTPS/ufCtps", rotulo="UF CTPS", campo="UFCTPS",
              marcador="@UFCTPS@", destino_tabela="GPE_PESSOAH", destino_coluna="SGUFCTPSPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=15, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/RG/nrRg", rotulo="RG", campo="NRRG",
              marcador="@NRRG@", destino_tabela="GPE_PESSOAH", destino_coluna="NRRGPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=16, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/RG/orgaoEmissor", rotulo="Órgão Emissor RG", campo="CDEXRG",
              marcador="@CDEXRG@", destino_tabela="GPE_PESSOAH", destino_coluna="CDEXRGPESSOA", tipo="texto", regra_conversao="trim"),
        campo(ordem=17, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/RG/dtExped", rotulo="Data Emissão RG", campo="DTEXRG",
              marcador="@DTEXRG@", destino_tabela="GPE_PESSOAH", destino_coluna="DTEXRGPESSOA", tipo="data", regra_conversao="data_iso"),
        campo(ordem=18, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CNH/nrRegCnh", rotulo="CNH", campo="CNH",
              marcador="@CNH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRCARTHABPES", tipo="texto", regra_conversao="trim"),
        campo(ordem=19, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CNH/dtValid", rotulo="Vencimento CNH", campo="DTVALCNH",
              marcador="@DTVALCNH@", destino_tabela="GPE_PESSOAH", destino_coluna="DTVALHABCARTPES", tipo="data", regra_conversao="data_iso"),
        campo(ordem=20, origem="evtAltCadastral/alteracao/dadosTrabalhador/documentos/CNH/categoriaCnh", rotulo="Categoria CNH", campo="CATCNH",
              marcador="@CATCNH@", destino_tabela="GPE_PESSOAH", destino_coluna="DSCATEGHABCART", tipo="texto", regra_conversao="trim"),
        campo(ordem=21, origem="evtAltCadastral/alteracao/dadosTrabalhador/nisTrab", rotulo="PIS/PASEP", campo="PIS",
              marcador="@PIS@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPISPASEPPES", tipo="texto", regra_conversao="trim"),
        # --- endereço (dadosTrabalhador/endereco/brasil) ---
        campo(ordem=22, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/codMunic", rotulo="Município Endereço (IBGE)",
              campo="CODMUNIC_END", marcador="@CODMUNIC_END@", destino_tabela="MUNICIPIO", destino_coluna="CDMUNICIBGE",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=23, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/tpLograd", rotulo="Tipo Logradouro (eSocial)",
              campo="TPLOGRAD", marcador="@TPLOGRAD@", destino_tabela="LOGRADOURO", destino_coluna="CDESOCIAL",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=24, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/bairro", rotulo="Bairro", campo="BAIRRO_END",
              marcador="@BAIRRO_END@", destino_tabela="ENDERECOPARC", destino_coluna="NMBAIRROENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=25, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/complemento", rotulo="Complemento", campo="COMPLEMENTO_END",
              marcador="@COMPLEMENTO_END@", destino_tabela="ENDERECOPARC", destino_coluna="DSCOMPLEENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=26, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/cep", rotulo="CEP", campo="CEP_END",
              marcador="@CEP_END@", destino_tabela="ENDERECOPARC", destino_coluna="NRCEPENDERECO", tipo="texto", regra_conversao="trim"),
        campo(ordem=27, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/dscLograd", rotulo="Endereço", campo="DSLOGRAD_END",
              marcador="@DSLOGRAD_END@", destino_tabela="ENDERECOPARC", destino_coluna="DSENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=28, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/nrLograd", rotulo="Número", campo="NRLOGRAD_END",
              marcador="@NRLOGRAD_END@", destino_tabela="ENDERECOPARC", destino_coluna="NRIMOVELENDERECO", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=29, origem="evtAltCadastral/alteracao/dadosTrabalhador/endereco/brasil/uf", rotulo="Estado (Endereço)", campo="UF_END",
              marcador="@UF_END@", destino_tabela="ENDERECOPARC", destino_coluna="SGESTADO", tipo="texto", regra_conversao="trim"),
        campo(ordem=30, origem="campo:DSLOGRAD_END,CODMUNIC_END", rotulo="Tem endereço? (derivado)",
              campo="_TEM_ENDERECO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- contato: telefone dividido em DDD+número ---
        campo(ordem=31, origem="evtAltCadastral/alteracao/dadosTrabalhador/contato/fonePrinc", rotulo="DDD Telefone Principal (derivado)",
              campo="DDDTELPRI", marcador="@DDDTELPRI@", destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC",
              tipo="texto", regra_conversao="ddd_telefone"),
        campo(ordem=32, origem="evtAltCadastral/alteracao/dadosTrabalhador/contato/fonePrinc", rotulo="Telefone Principal (derivado)",
              campo="TELPRI", marcador="@TELPRI@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC",
              tipo="texto", regra_conversao="numero_telefone"),
        campo(ordem=33, origem="campo:TELPRI", rotulo="Tem telefone principal? (derivado)",
              campo="_TEM_TELPRI", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=34, origem="evtAltCadastral/alteracao/dadosTrabalhador/contato/foneAlternat", rotulo="DDD Telefone Celular (derivado)",
              campo="DDDTELCEL", marcador="@DDDTELCEL@", destino_tabela="COMUNICAPARC", destino_coluna="CDPREFIXCOMUPARC",
              tipo="texto", regra_conversao="ddd_telefone"),
        campo(ordem=35, origem="evtAltCadastral/alteracao/dadosTrabalhador/contato/foneAlternat", rotulo="Telefone Celular (derivado)",
              campo="TELCEL", marcador="@TELCEL@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC",
              tipo="texto", regra_conversao="numero_telefone"),
        campo(ordem=36, origem="campo:TELCEL", rotulo="Tem telefone celular? (derivado)",
              campo="_TEM_TELCEL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        campo(ordem=37, origem="evtAltCadastral/alteracao/dadosTrabalhador/contato/emailPrinc", rotulo="E-mail", campo="EMAIL",
              marcador="@EMAIL@", destino_tabela="COMUNICAPARC", destino_coluna="CDCOMUNICAPARC", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=38, origem="campo:EMAIL", rotulo="Tem e-mail? (derivado)",
              campo="_TEM_EMAIL", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- gerado (Key Resolution Service) — MESMOS contadores do template VINCULO ---
        campo(ordem=39, origem="(gerado)", rotulo="Nº GPE_PESSOAH (gerado)", campo="NRPESSOAH",
              marcador="@NRPESSOAH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPESSOAH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOAH", gerador_pk_seed=0),
        campo(ordem=40, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Principal (gerado)", campo="NRCOMUNICAPARC",
              marcador="@NRCOMUNICAPARC@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=41, origem="(gerado)", rotulo="Nº COMUNICAPARC — Telefone Celular (gerado)", campo="NRCOMUNICAPARC2",
              marcador="@NRCOMUNICAPARC2@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=42, origem="(gerado)", rotulo="Nº COMUNICAPARC — E-mail (gerado)", campo="NRCOMUNICAPARC3",
              marcador="@NRCOMUNICAPARC3@", destino_tabela="COMUNICAPARC", destino_coluna="NRCOMUNICAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="COMUNICAPARC", gerador_pk_seed=0),
        campo(ordem=43, origem="(gerado)", rotulo="Nº ENDERECOPARC (gerado)", campo="NRENDERECOPARC",
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

    scripts = [
        {"ordem": 1, "condicao_campo": None, "template_sql": SQL_GPE_PESSOAH,
         "template_rollback": "DELETE FROM GPE_PESSOAH WHERE NRORG = @NRORG@ AND NRPESSOAH = @NRPESSOAH@;"},
        {"ordem": 2, "condicao_campo": "_TEM_TELPRI", "template_sql": SQL_COMUNICAPARC_TELPRI,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC@;"},
        {"ordem": 3, "condicao_campo": "_TEM_TELCEL", "template_sql": SQL_COMUNICAPARC_TELCEL,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC2@;"},
        {"ordem": 4, "condicao_campo": "_TEM_EMAIL", "template_sql": SQL_COMUNICAPARC_EMAIL,
         "template_rollback": "DELETE FROM COMUNICAPARC WHERE NRORG = @NRORG@ AND NRCOMUNICAPARC = @NRCOMUNICAPARC3@;"},
        {"ordem": 5, "condicao_campo": "_TEM_ENDERECO", "template_sql": SQL_ENDERECOPARC,
         "template_rollback": "DELETE FROM ENDERECOPARC WHERE NRORG = @NRORG@ AND NRENDERECOPARC = @NRENDERECOPARC@;"},
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
        {"codigo": TIPO_CODIGO, "nome": "eSocial — S-2205 Alteração de Dados Cadastrais"},
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
