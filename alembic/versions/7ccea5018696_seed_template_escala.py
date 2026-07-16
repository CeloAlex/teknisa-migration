"""seed template escala

Cadastra o template "Escala de Trabalho" — duas tabelas (GPE_ESCALATRABM/H), sem PK
sequencial (o número da escala é informado pelo operador na própria planilha e reutilizado
como PK de ambas as tabelas — diferente de Estrutura/Ocupação), sem FK e sem bloco
condicional. Dicionário de dados e template de script extraídos diretamente de
"docs/planilhas-originais/03_EscalaTrabalho_v09.xlsx" (aba Dados, linha 2 =
cabeçalho/template, linha 3 = primeira linha real).

Revision ID: 7ccea5018696
Revises: c8711c9c0350
Create Date: 2026-07-15 20:56:29.893588

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7ccea5018696'
down_revision: Union[str, None] = 'c8711c9c0350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESCALA"

# Texto extraído verbatim da célula W2 da planilha real, com a mesma troca do operador
# técnico fixo '000000099991' por @USUARIO_TECNICO@ (Seção 13.3).
TEMPLATE_SQL = (
    "INSERT INTO GPE_ESCALATRABM ( NRESCALATRABM, NRORG, DTINIVIGENCIA, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO) VALUES ( @NRESCALA@, @NRORG@, '@DTINIVIGENCIA@', "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@'); INSERT INTO GPE_ESCALATRABH ( NRESCALATRABH, "
    "NRESCALATRABM, NRORG, DTMESCOMPETENC, NMESCALATRABH, QTHRESCALATRABH, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, QTHRSEMESCTRABH, PRIENTRADA, PRISAIDA, SEGENTRADA, "
    "SEGSAIDA, DESCANSOSEMANAL) VALUES ( @NRESCALA@, @NRESCALA@, @NRORG@, "
    "'@DTMESCOMPETENC@', '@NMESCALATRABH@', @QTHRESCALATRABH@, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@', @QTHRSEMESCTRABH@, '@PRIENTRADA@', '@PRISAIDA@', '@SEGENTRADA@', "
    "'@SEGSAIDA@', '@DESCANSOSEMANAL@');"
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
            "nome": "Escala de Trabalho",
            "versao": "9",
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
        campo(ordem=1, origem="A", rotulo="Início Vigência", campo="DTINIVIGENCIA",
              marcador="@DTINIVIGENCIA@", destino_tabela="GPE_ESCALATRABM", destino_coluna="DTINIVIGENCIA",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        # Nr Escala: PK informada pelo próprio operador — não é gerada por sequencial
        # (diferente de Estrutura/Ocupação); o mesmo marcador @NRESCALA@ é reutilizado tanto
        # para NRESCALATRABM quanto para NRESCALATRABH no texto do script.
        campo(ordem=2, origem="B", rotulo="Nr Escala", campo="NRESCALA", marcador="@NRESCALA@",
              destino_tabela="GPE_ESCALATRABM/H", destino_coluna="NRESCALATRABM / NRESCALATRABH",
              tipo="numerico", obrigatorio=True, eh_pk=True),
        campo(ordem=3, origem="C", rotulo="hr semana Trab", campo="QTHRSEMESCTRABH",
              marcador="@QTHRSEMESCTRABH@", destino_tabela="GPE_ESCALATRABH", destino_coluna="QTHRSEMESCTRABH",
              tipo="numerico", regra_conversao="numero_decimal"),
        campo(ordem=4, origem="D", rotulo="Jornada Diária", campo="QTHRESCALATRABH",
              marcador="@QTHRESCALATRABH@", destino_tabela="GPE_ESCALATRABH", destino_coluna="QTHRESCALATRABH",
              tipo="numerico", regra_conversao="numero_decimal"),
        campo(ordem=5, origem="E", rotulo="COMPETÊNCIA", campo="DTMESCOMPETENC",
              marcador="@DTMESCOMPETENC@", destino_tabela="GPE_ESCALATRABH", destino_coluna="DTMESCOMPETENC",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=6, origem="F", rotulo="Nome", campo="NMESCALATRABH", marcador="@NMESCALATRABH@",
              destino_tabela="GPE_ESCALATRABH", destino_coluna="NMESCALATRABH", tipo="texto",
              obrigatorio=True, regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=7, origem="G", rotulo="1ª Entrada", campo="PRIENTRADA", marcador="@PRIENTRADA@",
              destino_tabela="GPE_ESCALATRABH", destino_coluna="PRIENTRADA", tipo="hora", regra_conversao="trim"),
        campo(ordem=8, origem="H", rotulo="1ª Saida", campo="PRISAIDA", marcador="@PRISAIDA@",
              destino_tabela="GPE_ESCALATRABH", destino_coluna="PRISAIDA", tipo="hora", regra_conversao="trim"),
        campo(ordem=9, origem="I", rotulo="2ª Entrada", campo="SEGENTRADA", marcador="@SEGENTRADA@",
              destino_tabela="GPE_ESCALATRABH", destino_coluna="SEGENTRADA", tipo="hora", regra_conversao="trim"),
        campo(ordem=10, origem="J", rotulo="2ª Saida", campo="SEGSAIDA", marcador="@SEGSAIDA@",
              destino_tabela="GPE_ESCALATRABH", destino_coluna="SEGSAIDA", tipo="hora", regra_conversao="trim"),
        campo(ordem=11, origem="K", rotulo="Descanso Semanal", campo="DESCANSOSEMANAL",
              marcador="@DESCANSOSEMANAL@", destino_tabela="GPE_ESCALATRABH", destino_coluna="DESCANSOSEMANAL",
              tipo="texto"),
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
                "DELETE FROM GPE_ESCALATRABH WHERE NRORG = @NRORG@ AND NRESCALATRABH = @NRESCALA@; "
                "DELETE FROM GPE_ESCALATRABM WHERE NRORG = @NRORG@ AND NRESCALATRABM = @NRESCALA@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
