"""catalogo destino ddl

Catálogo de destino (Anexo `docs/especificação/base_vazia.txt`, exemplo de script de DDL
Oracle) — duas tabelas novas (`catalogo_destino_tabela`/`catalogo_destino_coluna`)
populadas por um importador de DDL (`app/metadata/ddl_import.py`), usadas como FK-guia
opcional para `TemplateCampo.destino_tabela`/`destino_coluna` a partir de agora.

`TemplateCampo` ganha uma coluna nova nullable (`destino_coluna_catalogo_id`) — os campos
de texto livre `destino_tabela`/`destino_coluna` continuam existindo e funcionando
exatamente como antes (nunca foram lidos pelo motor de transformação/validação/script,
só exibidos na tela de detalhe e ecoados pela API). Os ~24 templates já semeados ficam com
`destino_coluna_catalogo_id = NULL` e não precisam de backfill — a FK é o caminho
preferencial só para campos novos cadastrados pelo formulário do portal a partir de agora.

Revision ID: 8aec5c1396da
Revises: 3441380a317b
Create Date: 2026-07-16 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aec5c1396da'
down_revision: Union[str, None] = '3441380a317b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'catalogo_destino_tabela',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome_tabela', sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_catalogo_destino_tabela')),
    )
    op.create_index(
        op.f('ix_catalogo_destino_tabela_nome_tabela'), 'catalogo_destino_tabela', ['nome_tabela'], unique=True
    )

    op.create_table(
        'catalogo_destino_coluna',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tabela_id', sa.Integer(), nullable=False),
        sa.Column('nome_coluna', sa.String(length=128), nullable=False),
        sa.Column('tipo_dado', sa.String(length=50), nullable=True),
        sa.Column('obrigatoria', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['tabela_id'], ['catalogo_destino_tabela.id'], name=op.f('fk_catalogo_destino_coluna_tabela_id_catalogo_destino_tabela')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_catalogo_destino_coluna')),
        sa.UniqueConstraint('tabela_id', 'nome_coluna', name=op.f('uq_catalogo_destino_coluna_tabela_id')),
    )
    op.create_index(
        op.f('ix_catalogo_destino_coluna_tabela_id'), 'catalogo_destino_coluna', ['tabela_id'], unique=False
    )

    op.add_column(
        'template_campo', sa.Column('destino_coluna_catalogo_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f('fk_template_campo_destino_coluna_catalogo_id_catalogo_destino_coluna'),
        'template_campo', 'catalogo_destino_coluna',
        ['destino_coluna_catalogo_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f('fk_template_campo_destino_coluna_catalogo_id_catalogo_destino_coluna'),
        'template_campo', type_='foreignkey',
    )
    op.drop_column('template_campo', 'destino_coluna_catalogo_id')
    op.drop_index(op.f('ix_catalogo_destino_coluna_tabela_id'), table_name='catalogo_destino_coluna')
    op.drop_table('catalogo_destino_coluna')
    op.drop_index(op.f('ix_catalogo_destino_tabela_nome_tabela'), table_name='catalogo_destino_tabela')
    op.drop_table('catalogo_destino_tabela')
