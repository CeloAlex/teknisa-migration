"""consolidar tipos migracao esocial

Consolida os 11 `TipoMigracao` individuais de eventos eSocial (`MIG_ESOCIAL_S1000` ...
`MIG_ESOCIAL_S2299`, cada um com exatamente 1 template obrigatório) em um único tipo
`MIG_ESOCIAL` contendo os 11 templates como membros — permitindo ao operador migrar um
evento isolado ou vários juntos na mesma migração, em vez de precisar escolher um tipo de
migração diferente por evento (pedido explícito do usuário).

**Pré-requisito resolvido antes desta migração** (não faz parte deste arquivo): a máquina de
estados (`app/migracoes/estado.py::recalcular_status`) calculava o status da migração só a
partir de templates `obrigatorio=True` — com essa lista vazia (necessário aqui, já que os 11
templates precisam ser todos opcionais para permitir migrar qualquer subconjunto), a
migração ficava travada em "Aguardando arquivos" para sempre. Corrigido com um fallback para
os templates já tocados (`status != PENDENTE`) quando não há nenhum obrigatório — ver commit
correspondente e `tests/test_estado_migracao.py`.

Confirmado antes de escrever esta migração: nenhuma `Migracao` real usa os 11 tipos antigos
hoje (consulta direta ao banco) — não há histórico para perder ou realocar.

Revision ID: 6df3d7f10a14
Revises: 8aec5c1396da
Create Date: 2026-07-17 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6df3d7f10a14'
down_revision: Union[str, None] = '8aec5c1396da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOVO_TIPO_CODIGO = "MIG_ESOCIAL"

TIPOS_ANTIGOS = [
    ("MIG_ESOCIAL_S1000", "eSocial — S-1000 Informações do Empregador"),
    ("MIG_ESOCIAL_S1005", "eSocial — S-1005 Tabela de Estabelecimentos"),
    ("MIG_ESOCIAL_S1020", "eSocial — S-1020 Tabela de Lotações Tributárias"),
    ("MIG_ESOCIAL_S1030", "eSocial — S-1030 Tabela de Cargos"),
    ("MIG_ESOCIAL_S1040", "eSocial — S-1040 Tabela de Funções"),
    ("MIG_ESOCIAL_S1200", "eSocial — S-1200 Remuneração RGPS"),
    ("MIG_ESOCIAL_S2200", "eSocial — S-2200 Admissão de Trabalhador"),
    ("MIG_ESOCIAL_S2205", "eSocial — S-2205 Alteração de Dados Cadastrais"),
    ("MIG_ESOCIAL_S2206", "eSocial — S-2206 Alteração de Contrato de Trabalho"),
    ("MIG_ESOCIAL_S2230", "eSocial — S-2230 Afastamento Temporário"),
    ("MIG_ESOCIAL_S2299", "eSocial — S-2299 Desligamento"),
]

# Mesma ordem cronológica/numérica já usada nos 11 tipos originais.
TEMPLATES_CODIGOS_EM_ORDEM = [
    "ESOCIAL_S1000", "ESOCIAL_S1005", "ESOCIAL_S1020", "ESOCIAL_S1030", "ESOCIAL_S1040",
    "ESOCIAL_S1200", "ESOCIAL_S2200", "ESOCIAL_S2205", "ESOCIAL_S2206", "ESOCIAL_S2230",
    "ESOCIAL_S2299",
]


def upgrade() -> None:
    conn = op.get_bind()

    novo_tipo_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', true, 'SCRIPT', false)
            RETURNING id
            """
        ),
        {"codigo": NOVO_TIPO_CODIGO, "nome": "eSocial — Eventos XML"},
    ).scalar_one()

    for ordem, codigo_template in enumerate(TEMPLATES_CODIGOS_EM_ORDEM, start=1):
        template_id = conn.execute(
            sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": codigo_template}
        ).scalar_one()
        conn.execute(
            sa.text(
                """
                INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
                VALUES (:tipo_id, :template_id, :ordem, false)
                """
            ),
            {"tipo_id": novo_tipo_id, "template_id": template_id, "ordem": ordem},
        )

    codigos_antigos = [codigo for codigo, _ in TIPOS_ANTIGOS]
    conn.execute(
        sa.text(
            """
            DELETE FROM tipo_migracao_template
            WHERE tipo_migracao_id IN (SELECT id FROM tipo_migracao WHERE codigo = ANY(:codigos))
            """
        ),
        {"codigos": codigos_antigos},
    )
    conn.execute(
        sa.text("DELETE FROM tipo_migracao WHERE codigo = ANY(:codigos)"),
        {"codigos": codigos_antigos},
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM tipo_migracao_template
            WHERE tipo_migracao_id IN (SELECT id FROM tipo_migracao WHERE codigo = :codigo)
            """
        ),
        {"codigo": NOVO_TIPO_CODIGO},
    )
    conn.execute(sa.text("DELETE FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": NOVO_TIPO_CODIGO})

    for codigo_tipo, nome in TIPOS_ANTIGOS:
        codigo_template = "ESOCIAL_" + codigo_tipo.replace("MIG_ESOCIAL_", "")
        tipo_id = conn.execute(
            sa.text(
                """
                INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                            modo_aplicacao, sequencia_obrigatoria)
                VALUES (:codigo, :nome, 'ORACLE', true, 'SCRIPT', false)
                RETURNING id
                """
            ),
            {"codigo": codigo_tipo, "nome": nome},
        ).scalar_one()
        template_id = conn.execute(
            sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": codigo_template}
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
