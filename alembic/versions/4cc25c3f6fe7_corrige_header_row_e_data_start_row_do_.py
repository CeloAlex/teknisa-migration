"""corrige header_row e data_start_row do template vinculo

O template VINCULO foi seedado com `header_row=2, data_start_row=3` (Seção 26.2), seguindo
o padrão de 2 linhas de cabeçalho (linha 1 = marcador @CAMPO@/"→", linha 2 = rótulo) do
arquivo de referência "04_Vinculo_v26_BETA.xlsx". O arquivo real do cliente
("gera___04_vinculo_layout_tela_2_v2_...xlsx", aba "Resultado da consulta" — um export de
relatório, não a planilha de referência) só tem **uma** linha de cabeçalho: linha 1 = rótulo
direto ("Nr. Vínculo" etc.), dado já começa na linha 2.

Com a config antiga, a linha 2 (primeiro registro real) era tratada como cabeçalho e
descartada silenciosamente — confirmado: matrícula "9272_000001" (primeira linha de dados
do arquivo) nunca chegou a ser importada em nenhuma migração, enquanto outros templates
(Ficha Financeira, Movimentações) referenciam esse funcionário normalmente, porque os
arquivos deles têm layout diferente e não sofrem desse desalinhamento.

As letras de coluna do dicionário (origem="A", "B", "C"...) continuam batendo com o arquivo
real (conferido: C1 = "Nr. Vínculo" no arquivo real, igual ao `origem="C"` já configurado
para CDMATRICULA) — só a linha inicial estava errada.

Revision ID: 4cc25c3f6fe7
Revises: 75b2225eab10
Create Date: 2026-07-27 19:41:36.118749

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4cc25c3f6fe7'
down_revision: Union[str, None] = '75b2225eab10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "VINCULO"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE template SET header_row = 1, data_start_row = 2 WHERE codigo = :codigo"),
        {"codigo": TEMPLATE_CODIGO},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE template SET header_row = 2, data_start_row = 3 WHERE codigo = :codigo"),
        {"codigo": TEMPLATE_CODIGO},
    )
