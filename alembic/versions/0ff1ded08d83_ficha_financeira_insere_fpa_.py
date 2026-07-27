"""ficha financeira insere fpa_calculofolha condicional

Pedido do usuário: Ficha Financeira passa a inserir também em FPA_CALCULOFOLHA (até aqui
tratada só como pré-requisito externo, nunca criada por nenhum dos 13 templates) — mas só
quando ainda não existir um cálculo para o mesmo NRTIPOMOVIMENT + DTOCORRENCIA daquela
organização (mesmo par que a subquery de FPA_ITECALCFOLHA já usa para localizar o cálculo:
`NRTPMODALIDCAL = 1 AND NROCORRECAL = 1`). Implementado como `INSERT ... SELECT ... WHERE
NOT EXISTS` (um único comando, sem bloco PL/SQL — a Execution Engine só executa uma
instrução por vez) — precisa rodar ANTES do bloco de FPA_ITECALCFOLHA na mesma linha, por
isso vira o novo bloco de `ordem = 1` e o bloco existente sobe para `ordem = 2`.

Novo campo gerado NRCALCULOFOLHA (Key Resolution Service, contador próprio, nunca usado
antes). NMCALCULOFOLHA reaproveita o valor já capturado em "Descrição do Cálculo"
(DSITEMCALCFOLHA, coluna E) — o pedido não trouxe uma coluna nova pra isso.

Revision ID: 0ff1ded08d83
Revises: 0216a0f1b7f7
Create Date: 2026-07-27 15:33:49.296783

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0ff1ded08d83'
down_revision: Union[str, None] = '0216a0f1b7f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "FICHA_FINANCEIRA"

TEMPLATE_SQL_CALCULOFOLHA = (
    "INSERT INTO FPA_CALCULOFOLHA ( NRCALCULOFOLHA, NRORG, NRTIPOMOVIMENT, DTINCLUSAO, "
    "DTOCORRENCIA, NRTPMODALIDCAL, NROCORRECAL, NMCALCULOFOLHA, IDATIVO ) "
    "SELECT @NRCALCULOFOLHA@, @NRORG@, @NRTIPOMOVIMENT@, SYSDATE, '@DTMESCOMPETENC@', 1, 1, "
    "'@DSITEMCALCFOLHA@', 'S' FROM DUAL WHERE NOT EXISTS ( SELECT 1 FROM FPA_CALCULOFOLHA "
    "WHERE NRORG = @NRORG@ AND NRTIPOMOVIMENT = @NRTIPOMOVIMENT@ AND DTOCORRENCIA = "
    "'@DTMESCOMPETENC@' AND NRTPMODALIDCAL = 1 AND NROCORRECAL = 1 );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            INSERT INTO template_campo (template_id, ordem, origem, rotulo, campo, marcador,
                                         destino_tabela, destino_coluna, tipo, tamanho_maximo,
                                         obrigatorio, valor_padrao, regra_conversao, eh_pk,
                                         gerador_pk, gerador_pk_contador, gerador_pk_seed)
            VALUES (:template_id, 10, '(gerado)', 'Nº FPA_CALCULOFOLHA (gerado)', 'NRCALCULOFOLHA',
                    '@NRCALCULOFOLHA@', 'FPA_CALCULOFOLHA', 'NRCALCULOFOLHA', 'numerico', NULL,
                    false, NULL, NULL, true, true, 'FPA_CALCULOFOLHA', 0)
            """
        ),
        {"template_id": template_id},
    )

    # Abre espaço para o novo bloco entrar como ordem=1 — o bloco de FPA_ITECALCFOLHA
    # precisa continuar rodando DEPOIS, já que sua subquery lê o cálculo recém-inserido.
    conn.execute(
        sa.text(
            """
            UPDATE template_script SET ordem = 2
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 1
            """
        ),
        {"template_id": template_id},
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
            "template_sql": TEMPLATE_SQL_CALCULOFOLHA,
            "template_rollback": (
                "DELETE FROM FPA_CALCULOFOLHA WHERE NRORG = @NRORG@ AND NRCALCULOFOLHA = @NRCALCULOFOLHA@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            """
            DELETE FROM template_script
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 1
              AND template_sql LIKE 'INSERT INTO FPA_CALCULOFOLHA%'
            """
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            """
            UPDATE template_script SET ordem = 1
            WHERE template_id = :template_id AND operacao = 'INCLUSAO' AND ordem = 2
            """
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            "DELETE FROM template_campo WHERE template_id = :template_id AND campo = 'NRCALCULOFOLHA'"
        ),
        {"template_id": template_id},
    )
