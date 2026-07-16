"""seed template estrutura

Cadastra o template "Estrutura Organizacional" — o mais complexo dos três validados na
Fase 3: gera quatro tabelas de destino por linha (PARCNEGOCIO, ESTRUTURAM, ESTRUTURAH e,
condicionalmente, ENDERECOPARC), com PK sequencial via Key Resolution Service para as
quatro, dois campos derivados (NMPRINCIPALPARC e o flag de condição do bloco de endereço) e
uma FK resolvida via subquery embutida no próprio texto do script (MUNICIPIO). Dicionário de
dados e templates de script extraídos diretamente de
"docs/planilhas-originais/01_Estrutura_v12 [melhorias da v11].xlsx" (aba Dados, linha 2 =
cabeçalho/template, linha 3 = primeira linha real).

Revision ID: 06d5b9d23be9
Revises: 9c32e9ab80e3
Create Date: 2026-07-15 20:56:27.132039

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '06d5b9d23be9'
down_revision: Union[str, None] = '9c32e9ab80e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESTRUTURA"

# Bloco 1 (sempre gerado): PARCNEGOCIO + ESTRUTURAM + ESTRUTURAH. Texto extraído
# verbatim da célula BM2 da planilha real, com uma única mudança deliberada: o operador
# técnico fixo '000000099991' vira o marcador @USUARIO_TECNICO@ (mesma melhoria já aplicada
# no template de Agências Bancárias na Fase 2 — Seção 13.3).
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

# Bloco 2 (condicional a _TEM_ENDERECO): ENDERECOPARC, com a FK a MUNICIPIO resolvida por
# subquery embutida no próprio texto do script — o motor não faz nenhuma consulta ao
# destino para resolver isso; o valor de @MUNICIPIO@ (já em upper_sem_acento) só é
# interpolado dentro do WHERE da subquery, que o Oracle resolve na hora de executar o
# script (Seção 6.2/26.4). Texto extraído verbatim da célula BN2 da planilha real, com a
# mesma troca do operador técnico fixo por @USUARIO_TECNICO@.
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
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, sheet_name,
                                   header_row, data_start_row, ativo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :sheet_name,
                    :header_row, :data_start_row, true)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "Estrutura Organizacional",
            "versao": "12",
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
        # --- campos diretos do arquivo ---
        campo(ordem=1, origem="A", rotulo="Tipo de Estrutura Teknisa", campo="NRTPESTRUTURA",
              marcador="@NRTPESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="NRTIPOESTRUTURA",
              tipo="numerico", obrigatorio=True),
        campo(ordem=2, origem="B", rotulo="Início de Vigência", campo="DTINIVIGENCIA",
              marcador="@DTINIVIGENCIA@", destino_tabela="ESTRUTURAM", destino_coluna="DTINIVIGENCIA",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="Fim de Vigência", campo="DTFIMVIGENCIA",
              marcador="@DTFIMVIGENCIA@", destino_tabela="ESTRUTURAM", destino_coluna="DTFIMVIGENCIA",
              tipo="data", regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Nº Estrutura", campo="NRESTRUTURA",
              marcador="@NRESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="CDINTESTRUTURA",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="E", rotulo="Mês Competência", campo="COMPETENCIA",
              marcador="@COMPETENCIA@", destino_tabela="ESTRUTURAH", destino_coluna="DTMESCOMPETENC",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=6, origem="F", rotulo="CNPJ", campo="CNPJ", marcador="@CNPJ@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCNPJESTRUT", tipo="texto",
              tamanho_maximo=14, regra_conversao="remover_mascara"),
        campo(ordem=7, origem="G", rotulo="CEI", campo="CEI", marcador="@CEI@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCEIESTRUT", tipo="texto",
              regra_conversao="remover_mascara"),
        campo(ordem=8, origem="H", rotulo="Razão Social", campo="RAZAOSOCIAL",
              marcador="@RAZAOSOCIAL@", destino_tabela="ESTRUTURAH", destino_coluna="NMRAZSOCESTRUT",
              tipo="texto", regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=9, origem="I", rotulo="Natureza Jurídica", campo="NATJURIDICA",
              marcador="@NATJURIDICA@", destino_tabela="ESTRUTURAH", destino_coluna="CDNATUJURI",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=10, origem="J", rotulo="CNAE", campo="CDCNAE", marcador="@CDCNAE@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCNAE", tipo="texto", regra_conversao="trim"),
        # Coluna K (FPAS) é lida na planilha original mas não referenciada por nenhum
        # INSERT (Seção 13.2) — não cadastrada como campo do dicionário.
        campo(ordem=11, origem="L", rotulo="CAGED", campo="CDCAGED", marcador="@CDCAGED@",
              destino_tabela="ESTRUTURAH", destino_coluna="NRCAGED", tipo="texto", regra_conversao="trim"),
        campo(ordem=12, origem="M", rotulo="Tipo de Empresa", campo="IDTPEMPRESA",
              marcador="@IDTPEMPRESA@", destino_tabela="ESTRUTURAH", destino_coluna="IDTIPOEMPR", tipo="texto"),
        campo(ordem=13, origem="N", rotulo="Optante Simples", campo="IDSIMPLES",
              marcador="@IDSIMPLES@", destino_tabela="ESTRUTURAH", destino_coluna="IDOPTSIMPLES",
              tipo="booleano", regra_conversao="vazio_para_n"),
        campo(ordem=14, origem="O", rotulo="Participação PAT", campo="IDPARTICIPAT",
              marcador="@IDPARTICIPAT@", destino_tabela="ESTRUTURAH", destino_coluna="IDPARTICIPAT",
              tipo="booleano", regra_conversao="trim"),
        campo(ordem=15, origem="P", rotulo="Tp Endereço", campo="IDENDERECO",
              marcador="@IDENDERECO@", destino_tabela="ENDERECOPARC", destino_coluna="CDTIPOENDERECO",
              tipo="texto", regra_conversao="trim"),
        # CDPAIS: o LPAD(...,4,'0') já está embutido no texto do script (bloco de
        # endereço) — o campo só precisa chegar "trim"ado até lá.
        campo(ordem=16, origem="Q", rotulo="Pais", campo="CDPAIS", marcador="@CDPAIS@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDPAIS", tipo="texto",
              tamanho_maximo=4, regra_conversao="trim"),
        campo(ordem=17, origem="R", rotulo="Estado", campo="SGESTADO", marcador="@SGESTADO@",
              destino_tabela="ENDERECOPARC", destino_coluna="SGESTADO", tipo="texto",
              tamanho_maximo=2, regra_conversao="trim"),
        campo(ordem=18, origem="S", rotulo="Município", campo="MUNICIPIO", marcador="@MUNICIPIO@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDMUNICIPIO", tipo="texto",
              regra_conversao="upper_sem_acento"),
        campo(ordem=19, origem="T", rotulo="Logradouro", campo="LOGRADOURO", marcador="@LOGRADOURO@",
              destino_tabela="ENDERECOPARC", destino_coluna="CDLOGRADOURO", tipo="texto", regra_conversao="trim"),
        campo(ordem=20, origem="U", rotulo="Endereço", campo="ENDERECO", marcador="@ENDERECO@",
              destino_tabela="ENDERECOPARC", destino_coluna="DSENDERECO", tipo="texto", regra_conversao="trim"),
        campo(ordem=21, origem="V", rotulo="Numero", campo="NUMERO", marcador="@NUMERO@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRIMOVELENDERECO", tipo="numerico", regra_conversao="trim"),
        campo(ordem=22, origem="W", rotulo="Nome do Bairro", campo="BAIRRO", marcador="@BAIRRO@",
              destino_tabela="ENDERECOPARC", destino_coluna="NMBAIRROENDERECO", tipo="texto", regra_conversao="trim"),
        campo(ordem=23, origem="X", rotulo="CEP", campo="CEP", marcador="@CEP@",
              destino_tabela="ENDERECOPARC", destino_coluna="NRCEPENDERECO", tipo="texto",
              tamanho_maximo=8, regra_conversao="remover_mascara"),
        campo(ordem=24, origem="Y", rotulo="Referência do Endereço", campo="REFERENCIAENDERECO",
              marcador="@REFERENCIAENDERECO@", destino_tabela="ENDERECOPARC", destino_coluna="DSREFERENCIAENDE",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=25, origem="Z", rotulo="Nome Fantasia", campo="NMFANTASIA", marcador="@NMFANTASIA@",
              destino_tabela="ESTRUTURAH", destino_coluna="NMFANTASIA", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=26, origem="AA", rotulo="Nome Estrutura", campo="NMESTRUTURA", marcador="@NMESTRUTURA@",
              destino_tabela="ESTRUTURAM/H", destino_coluna="NMESTRUTURAM / NMESTRUTURAH", tipo="texto",
              regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=27, origem="AB", rotulo="CPF", campo="CDCPFESTRUTURA", marcador="@CDCPFESTRUTURA@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDCPFESTRUTURA", tipo="texto",
              tamanho_maximo=11, regra_conversao="remover_mascara"),
        campo(ordem=28, origem="AC", rotulo="Data Base Sindical", campo="DTBASESINDICAL",
              marcador="@DTBASESINDICAL@", destino_tabela="ESTRUTURAH", destino_coluna="DTBASESINDICAL",
              tipo="data", regra_conversao="data_br"),
        campo(ordem=29, origem="AD", rotulo="Cód Sindicato", campo="CDSINDICAL", marcador="@CDSINDICAL@",
              destino_tabela="ESTRUTURAH", destino_coluna="CDSINDICAL", tipo="texto", regra_conversao="trim"),
        # --- campo derivado: nome do parceiro de negócio (Seção 13.2 — NVL em cascata) ---
        campo(ordem=30, origem="campo:RAZAOSOCIAL,NMFANTASIA,NMESTRUTURA", rotulo="Nome Principal do Parceiro (derivado)",
              campo="NMPRINCIPALPARC", marcador="@NMPRINCIPALPARC@", destino_tabela="PARCNEGOCIO",
              destino_coluna="NMPRINCIPALPARC", tipo="texto", regra_conversao="primeiro_nao_vazio"),
        # --- campo derivado: condição do bloco de endereço (Seção 7.6/26.4) ---
        campo(ordem=31, origem="campo:IDENDERECO,LOGRADOURO", rotulo="Tem endereço? (derivado)",
              campo="_TEM_ENDERECO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="nenhum_vazio"),
        # --- campos com PK sequencial (Key Resolution Service — Seção 6.1) ---
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


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
