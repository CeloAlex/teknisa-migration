"""seed template dependentes

Cadastra o template "Dependentes" (Seção 26.2, planilha "05_Dependentes_v12.xlsx") — a 14ª
planilha original, nunca implementada até agora (o levantamento anterior só cobriu
"04_Vinculo_v26_BETA.xlsx"; ver commit fbd0627). Fecha as 3 tabelas que ficaram de fora da
auditoria de cobertura da migração integral: RELACIONAPARC e FPA_DEPVINCULO (a 3ª,
FPA_CALCULOFOLHA, é tratada à parte, dentro de Ficha Financeira).

Dois blocos de script por linha aprovada:
- Bloco principal (sempre gerado): PARCNEGOCIO (pessoa física do dependente) + GPE_PESSOA +
  GPE_PESSOAH + RELACIONAPARC (relação de parentesco entre o dependente e o titular do
  vínculo). Reaproveita os contadores de PARCNEGOCIO/GPE_PESSOA/GPE_PESSOAH já usados por
  Estrutura/Vínculo (mesmas tabelas físicas — precisa ser o MESMO contador, não um novo).
- Bloco FPA_DEPVINCULO (sempre gerado): vínculo funcional do dependente, dependente
  explicitamente do Vínculo já existente no destino (`SELECT MAX(NRVINCULOM) FROM
  GPE_VINCULOM WHERE CDMATRICULA = '@NRVINCULOM@'`) — por isso Dependentes precisa ser o
  último template da sequência quando a migração é do tipo sequência travada (ver migração
  seguinte, que registra essa dependência em `tipo_migracao_template_dependencia`).

Dicionário extraído da aba "Dados" da planilha original: linha 1 = marcador @CAMPO@ (texto
literal de cada bloco de script, célula AA2/AB2 — já usa marcadores, extraído verbatim),
linha 2 = rótulo, linha 3+ = dado de exemplo. Colunas A-J são as 10 colunas de entrada
reais (as demais, K em diante, são área de fórmula/depuração da planilha original, não
usadas aqui — o Transformation Engine já resolve via `regra_conversao` o que lá era feito
com fórmulas de planilha, ex. `cpf` para extrair só dígitos do CPF mascarado).

`'000000099991'` hardcoded nas duas células originais virou `@USUARIO_TECNICO@`, mesma
adaptação já feita em Estrutura/Vínculo/Ficha Financeira/Movimentações (Seção 13.3).

Revision ID: 0cb18dd6c579
Revises: 021e22cab3d9
Create Date: 2026-07-27 15:30:53.483279

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0cb18dd6c579'
down_revision: Union[str, None] = '021e22cab3d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "DEPENDENTES"

# Texto extraído verbatim da célula AA2 do arquivo real — bloco principal.
TEMPLATE_SQL_PRINCIPAL = (
    "INSERT INTO PARCNEGOCIO ( NRPARCNEGOCIO, NRORG, NMPRINCIPALPARC, NMSECUNDARIPARC, "
    "DTNASCIFUNDPARC, NRINSCRICAOPARC, IDATIVO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, "
    "CDTIPOPARCPRINCIPAL, CDTIPOINSCRICAO, IDPESSOAFISICA, IDINSTITUICAO, IDPARCFUNDIDO ) "
    "VALUES ( @NRPARCNEGOCIO@, @NRORG@ , '@NOME@', '@NOME@', '@DTNASCIMENTO@', '@CPF@', "
    "'S', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', 'PESSOA', 'CPF', 'S', 'N', 'N' ); "
    "INSERT INTO GPE_PESSOA ( NRPESSOA, NRORG, NRPARCNEGOCIO, DTINCLUSAO, NRORGINCLUSAO, "
    "CDOPERINCLUSAO ) VALUES ( @NRPESSOA@, @NRORG@, @NRPARCNEGOCIO@, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@' ); "
    "INSERT INTO GPE_PESSOAH ( NRPESSOAH, NRPESSOA, NRORG, DTMESCOMPETENC, NMPESSOA, "
    "NRCPFPESSOA, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, DTNASCPESSOA, IDSEXOPESSOA, "
    "NRRGPESSOA, SGESTADO) VALUES ( @NRPESSOAH@, @NRPESSOA@, @NRORG@, '@DTMESCOMPETENC@', "
    "'@NOME@', '@CPF@', SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@DTNASCIMENTO@', "
    "'@IDSEXOPESSOA@', '@NRRGPESSOA@', '@SGESTADO@'); "
    "INSERT INTO RELACIONAPARC ( NRRELACIONAPARC, NRORG, NRPARCNEGOCIO, NRPARCNEGRELAC, "
    "NRTIPORELACIONA, NRORGINCLUSAO, DTINCLUSAO, CDOPERINCLUSAO ) VALUES ( "
    "@NRRELACIONAPARC@, @NRORG@, ( SELECT NRPARCNEGOCIO FROM GPE_PESSOA WHERE NRORG = "
    "@NRORG@ AND NRPESSOA = ( SELECT MAX(NRPESSOA) FROM GPE_VINCULOM WHERE NRORG = @NRORG@ "
    "AND CDMATRICULA = '@NRVINCULOM@' ) ), @NRPARCNEGOCIO@, @NRTIPORELACIONA@, @NRORG@, "
    "SYSDATE, '@USUARIO_TECNICO@');"
)

# Texto extraído verbatim da célula AB2 do arquivo real — bloco de vínculo do dependente.
TEMPLATE_SQL_DEPVINCULO = (
    "INSERT INTO FPA_DEPVINCULO ( NRORG, NRDEPVINCULO, NRVINCULOM, NRPESSOA, NRTIPODEPENDE, "
    "DTINIDEPENDE, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) VALUES ( @NRORG@, "
    "@NRDEPVINCULO@, ( SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND "
    "CDMATRICULA = '@NRVINCULOM@' ), @NRPESSOA@, @NRTIPODEPENDE@, '@DTMESCOMPETENC@', "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, sheet_name,
                                   header_row, data_start_row, ativo, pre_requisito_externo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :sheet_name,
                    :header_row, :data_start_row, true, :pre_requisito_externo)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "Dependentes",
            "versao": "12",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Dados",
            "header_row": 2,
            "data_start_row": 3,
            "pre_requisito_externo": (
                "Depende do Vínculo do titular já existente no destino (subquery "
                "`SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE CDMATRICULA = "
                "'@NRVINCULOM@'`) — precisa ser o último template importado na sequência "
                "quando a migração é do tipo sequência travada (Seção 26.3)."
            ),
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
        campo(ordem=1, origem="A", rotulo="Tipo de Relacionamento", campo="NRTIPORELACIONA",
              marcador="@NRTIPORELACIONA@", destino_tabela="RELACIONAPARC", destino_coluna="NRTIPORELACIONA",
              tipo="numerico", obrigatorio=True),
        campo(ordem=2, origem="B", rotulo="Nr Vínculo (do titular)", campo="NRVINCULOM",
              marcador="@NRVINCULOM@", destino_tabela="FPA_DEPVINCULO", destino_coluna="NRVINCULOM",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="C", rotulo="Competência", campo="DTMESCOMPETENC", marcador="@DTMESCOMPETENC@",
              destino_tabela="GPE_PESSOAH", destino_coluna="DTMESCOMPETENC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Nome do Dependente", campo="NOME", marcador="@NOME@",
              destino_tabela="PARCNEGOCIO", destino_coluna="NMPRINCIPALPARC", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="E", rotulo="CPF", campo="CPF", marcador="@CPF@",
              destino_tabela="PARCNEGOCIO", destino_coluna="NRINSCRICAOPARC", tipo="texto",
              obrigatorio=True, regra_conversao="cpf"),
        campo(ordem=6, origem="F", rotulo="RG", campo="NRRGPESSOA", marcador="@NRRGPESSOA@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRRGPESSOA", tipo="texto",
              regra_conversao="trim"),
        campo(ordem=7, origem="G", rotulo="UF", campo="SGESTADO", marcador="@SGESTADO@",
              destino_tabela="GPE_PESSOAH", destino_coluna="SGESTADO", tipo="texto",
              tamanho_maximo=2, regra_conversao="upper_sem_acento"),
        campo(ordem=8, origem="H", rotulo="Data de Nascimento", campo="DTNASCIMENTO", marcador="@DTNASCIMENTO@",
              destino_tabela="PARCNEGOCIO", destino_coluna="DTNASCIFUNDPARC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=9, origem="I", rotulo="Sexo", campo="IDSEXOPESSOA", marcador="@IDSEXOPESSOA@",
              destino_tabela="GPE_PESSOAH", destino_coluna="IDSEXOPESSOA", tipo="texto",
              tamanho_maximo=1, obrigatorio=True, regra_conversao="trim"),
        campo(ordem=10, origem="J", rotulo="Tipo de Dependência", campo="NRTIPODEPENDE",
              marcador="@NRTIPODEPENDE@", destino_tabela="FPA_DEPVINCULO", destino_coluna="NRTIPODEPENDE",
              tipo="numerico", obrigatorio=True),
        # PKs geradas (Key Resolution Service) — PARCNEGOCIO/GPE_PESSOA/GPE_PESSOAH reaproveitam
        # os MESMOS contadores de Estrutura/Vínculo (mesma tabela física); RELACIONAPARC e
        # FPA_DEPVINCULO são contadores novos, seeds a partir dos valores de exemplo do arquivo.
        campo(ordem=11, origem="(gerado)", rotulo="Nº PARCNEGOCIO (gerado)", campo="NRPARCNEGOCIO",
              marcador="@NRPARCNEGOCIO@", destino_tabela="PARCNEGOCIO", destino_coluna="NRPARCNEGOCIO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="PARCNEGOCIO", gerador_pk_seed=1738),
        campo(ordem=12, origem="(gerado)", rotulo="Nº GPE_PESSOA (gerado)", campo="NRPESSOA",
              marcador="@NRPESSOA@", destino_tabela="GPE_PESSOA", destino_coluna="NRPESSOA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOA", gerador_pk_seed=0),
        campo(ordem=13, origem="(gerado)", rotulo="Nº GPE_PESSOAH (gerado)", campo="NRPESSOAH",
              marcador="@NRPESSOAH@", destino_tabela="GPE_PESSOAH", destino_coluna="NRPESSOAH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_PESSOAH", gerador_pk_seed=0),
        campo(ordem=14, origem="(gerado)", rotulo="Nº RELACIONAPARC (gerado)", campo="NRRELACIONAPARC",
              marcador="@NRRELACIONAPARC@", destino_tabela="RELACIONAPARC", destino_coluna="NRRELACIONAPARC",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="RELACIONAPARC", gerador_pk_seed=117565),
        campo(ordem=15, origem="(gerado)", rotulo="Nº FPA_DEPVINCULO (gerado)", campo="NRDEPVINCULO",
              marcador="@NRDEPVINCULO@", destino_tabela="FPA_DEPVINCULO", destino_coluna="NRDEPVINCULO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_DEPVINCULO", gerador_pk_seed=24426),
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
            "template_sql": TEMPLATE_SQL_PRINCIPAL,
            "template_rollback": (
                "DELETE FROM RELACIONAPARC WHERE NRORG = @NRORG@ AND NRRELACIONAPARC = @NRRELACIONAPARC@; "
                "DELETE FROM GPE_PESSOAH WHERE NRORG = @NRORG@ AND NRPESSOAH = @NRPESSOAH@; "
                "DELETE FROM GPE_PESSOA WHERE NRORG = @NRORG@ AND NRPESSOA = @NRPESSOA@; "
                "DELETE FROM PARCNEGOCIO WHERE NRORG = @NRORG@ AND NRPARCNEGOCIO = @NRPARCNEGOCIO@;"
            ),
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO template_script (template_id, operacao, dialeto_banco, ordem,
                                          condicao_campo, template_sql, template_rollback)
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', 2, NULL, :template_sql, :template_rollback)
            """
        ),
        {
            "template_id": template_id,
            "template_sql": TEMPLATE_SQL_DEPVINCULO,
            "template_rollback": (
                "DELETE FROM FPA_DEPVINCULO WHERE NRORG = @NRORG@ AND NRDEPVINCULO = @NRDEPVINCULO@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
