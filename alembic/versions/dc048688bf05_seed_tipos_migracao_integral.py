"""seed tipos migracao integral

Cadastra os dois tipos de "Migração Integral do Cliente" (Seção 26.5), consolidando os
treze templates agora disponíveis:

- MIG_INTEGRAL_INDIVIDUAL: sem sequência obrigatória, cada template pode ser importado
  isoladamente (operação corrente pós-implantação — ex.: só um lote de Férias).
- MIG_INTEGRAL_ONBOARDING: sequência travada, aplicando o grafo de dependências completo da
  Seção 26.3 via `tipo_migracao_template_dependencia` (ex.: Vínculo só libera após Agências +
  Estrutura + Ocupação + Escala; Ficha Financeira só libera após Vínculo + Eventos).

A ordem numérica (`ordem`) usada em ambos os tipos já é uma ordenação topológica válida do
grafo — usada para exibição e para a Fase 5/6 (execução guiada), mas quem efetivamente
define o travamento de sequência no modo ONBOARDING são as arestas de dependência, não a
ordem por si só (Estrutura e Ocupação, por exemplo, não dependem uma da outra, mesmo
aparecendo em posições sequenciais).

Revision ID: dc048688bf05
Revises: 951bcfc70d80
Create Date: 2026-07-16 07:27:15.648224

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'dc048688bf05'
down_revision: Union[str, None] = '951bcfc70d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CODIGOS_EM_ORDEM = [
    "AGENCIAS_BANCARIAS",
    "ESTRUTURA",
    "OCUPACAO",
    "ESCALA",
    "EVENTOS",
    "VINCULO",
    "ALTERACAO_SALARIAL",
    "ALTERACAO_ESCALA",
    "ALTERACAO_OCUPACAO",
    "SITUACAO_FUNCIONAL",
    "FERIAS",
    "MOVIMENTACOES_ESTRUTURA",
    "FICHA_FINANCEIRA",
]

# Grafo de dependências (Seção 26.3) — só usado pelo tipo ONBOARDING.
DEPENDENCIAS = {
    "VINCULO": ["AGENCIAS_BANCARIAS", "ESTRUTURA", "OCUPACAO", "ESCALA"],
    "ALTERACAO_SALARIAL": ["VINCULO"],
    "ALTERACAO_ESCALA": ["VINCULO", "ESCALA"],
    "ALTERACAO_OCUPACAO": ["VINCULO", "OCUPACAO"],
    "SITUACAO_FUNCIONAL": ["VINCULO"],
    "FERIAS": ["VINCULO"],
    "MOVIMENTACOES_ESTRUTURA": ["VINCULO", "ESTRUTURA"],
    "FICHA_FINANCEIRA": ["VINCULO", "EVENTOS"],
}

TIPO_INDIVIDUAL_CODIGO = "MIG_INTEGRAL_INDIVIDUAL"
TIPO_ONBOARDING_CODIGO = "MIG_INTEGRAL_ONBOARDING"


def upgrade() -> None:
    conn = op.get_bind()

    template_ids = {
        codigo: conn.execute(
            sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": codigo}
        ).scalar_one()
        for codigo in CODIGOS_EM_ORDEM
    }

    # --- Tipo 1: importação individual, sem sequência obrigatória ---
    tipo_individual_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', false, 'SCRIPT', false)
            RETURNING id
            """
        ),
        {
            "codigo": TIPO_INDIVIDUAL_CODIGO,
            "nome": "Migração Integral do Cliente — 13 Templates (importação individual)",
        },
    ).scalar_one()

    for ordem, codigo in enumerate(CODIGOS_EM_ORDEM, start=1):
        conn.execute(
            sa.text(
                """
                INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
                VALUES (:tipo_id, :template_id, :ordem, false)
                """
            ),
            {"tipo_id": tipo_individual_id, "template_id": template_ids[codigo], "ordem": ordem},
        )

    # --- Tipo 2: implantação completa, sequência travada pelo grafo de dependências ---
    tipo_onboarding_id = conn.execute(
        sa.text(
            """
            INSERT INTO tipo_migracao (codigo, nome, banco_destino, permite_concorrencia,
                                        modo_aplicacao, sequencia_obrigatoria)
            VALUES (:codigo, :nome, 'ORACLE', false, 'SCRIPT', true)
            RETURNING id
            """
        ),
        {
            "codigo": TIPO_ONBOARDING_CODIGO,
            "nome": "Migração Integral do Cliente — Implantação Completa (sequência travada)",
        },
    ).scalar_one()

    tmt_ids = {}
    for ordem, codigo in enumerate(CODIGOS_EM_ORDEM, start=1):
        tmt_ids[codigo] = conn.execute(
            sa.text(
                """
                INSERT INTO tipo_migracao_template (tipo_migracao_id, template_id, ordem, obrigatorio)
                VALUES (:tipo_id, :template_id, :ordem, true)
                RETURNING id
                """
            ),
            {"tipo_id": tipo_onboarding_id, "template_id": template_ids[codigo], "ordem": ordem},
        ).scalar_one()

    for codigo, dependencias in DEPENDENCIAS.items():
        for dep_codigo in dependencias:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO tipo_migracao_template_dependencia
                        (tipo_migracao_template_id, depende_de_template_id)
                    VALUES (:tmt_id, :dep_template_id)
                    """
                ),
                {"tmt_id": tmt_ids[codigo], "dep_template_id": template_ids[dep_codigo]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for codigo in (TIPO_INDIVIDUAL_CODIGO, TIPO_ONBOARDING_CODIGO):
        conn.execute(
            sa.text(
                """
                DELETE FROM tipo_migracao_template_dependencia
                WHERE tipo_migracao_template_id IN (
                    SELECT tmt.id FROM tipo_migracao_template tmt
                    JOIN tipo_migracao tm ON tm.id = tmt.tipo_migracao_id
                    WHERE tm.codigo = :codigo
                )
                """
            ),
            {"codigo": codigo},
        )
        conn.execute(
            sa.text(
                """
                DELETE FROM tipo_migracao_template
                WHERE tipo_migracao_id IN (SELECT id FROM tipo_migracao WHERE codigo = :codigo)
                """
            ),
            {"codigo": codigo},
        )
        conn.execute(sa.text("DELETE FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": codigo})
