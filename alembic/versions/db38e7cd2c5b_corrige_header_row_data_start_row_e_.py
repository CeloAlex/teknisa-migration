"""corrige header_row data_start_row e sheet_name dos templates gerados por relatorio

Mesmo bug do VINCULO (`4cc25c3f6fe7`), só que sistêmico: abri os 11 arquivos reais
("gera___...xlsx") usados na migração #901 e TODOS têm a mesma estrutura — aba única
"Resultado da consulta" (um export de relatório do cliente, não a planilha de referência
usada para montar os dicionários), com **uma só** linha de cabeçalho e dado já começando na
linha 2. Os templates estavam configurados com `header_row=2, data_start_row=3` (padrão de
2 linhas de cabeçalho da planilha de referência original) — ou seja, TODO template dessa
migração estava descartando silenciosamente a primeira linha de dados do arquivo, não só o
Vínculo.

`OCUPACAO` também tinha `sheet_name='Script'` (nunca bateu com o arquivo real — só não
quebrou porque `ler_xlsx` cai pro primeiro aba quando o nome configurado não existe, e o
arquivo real só tem uma aba mesmo).

DEPENDENTES (seedado nesta mesma conversa a partir da planilha de referência
"05_Dependentes_v12.xlsx", sem arquivo real do cliente ainda pra conferir) foi ajustado pelo
mesmo padrão, por inferência — os 11 arquivos reais conferidos são unânimes nesse formato.

Revision ID: db38e7cd2c5b
Revises: 4cc25c3f6fe7
Create Date: 2026-07-27 19:46:36.774429

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'db38e7cd2c5b'
down_revision: Union[str, None] = '4cc25c3f6fe7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SHEET_REAL = "Resultado da consulta"

# Todos conferidos diretamente contra o arquivo real do cliente, exceto DEPENDENTES
# (inferido pelo padrão unânime dos outros 11).
TEMPLATES = [
    "ESTRUTURA", "OCUPACAO", "ESCALA", "ALTERACAO_SALARIAL", "ALTERACAO_ESCALA",
    "ALTERACAO_OCUPACAO", "SITUACAO_FUNCIONAL", "FERIAS", "EVENTOS",
    "MOVIMENTACOES_ESTRUTURA", "FICHA_FINANCEIRA", "DEPENDENTES",
]


def upgrade() -> None:
    conn = op.get_bind()
    for codigo in TEMPLATES:
        conn.execute(
            sa.text(
                "UPDATE template SET header_row = 1, data_start_row = 2, sheet_name = :sheet "
                "WHERE codigo = :codigo"
            ),
            {"codigo": codigo, "sheet": SHEET_REAL},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for codigo in TEMPLATES:
        conn.execute(
            sa.text(
                "UPDATE template SET header_row = 2, data_start_row = 3, sheet_name = 'Dados' "
                "WHERE codigo = :codigo"
            ),
            {"codigo": codigo},
        )
