"""seed template alteracao salarial

Cadastra o template "Alteração Salarial" (Seção 26.2): uma única tabela
(GPE_ALTESALARIO), PK sequencial via Key Resolution Service, vínculo resolvido por
subquery a partir da matrícula (FK via subquery embutida no texto do script — o mesmo
padrão já suportado desde a Fase 3, sem nenhuma mudança de motor). Dicionário e template de
script extraídos diretamente de docs/planilhas-originais/06_AlteracaoSalarial_v12.xlsx.

Revision ID: 6c31b8f0babc
Revises: 1913c658c4eb
Create Date: 2026-07-16 07:19:29.402094

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6c31b8f0babc'
down_revision: Union[str, None] = '1913c658c4eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ALTERACAO_SALARIAL"

# Texto extraído verbatim da célula Q2 do arquivo real, com a mesma troca do operador
# técnico fixo '000000099991' por @USUARIO_TECNICO@ (Seção 13.3).
TEMPLATE_SQL = (
    "INSERT INTO GPE_ALTESALARIO ( NRALTESALARIO, NRORG, NRVINCULOM, DTALTESALARIO, "
    "NROCORRENCIA, NRTIPOALTERA, VRSALARIO, IDTPSALARIO, DSOBSERVACAO, NRTPMODALIDSAL, "
    "DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO ) VALUES ( @NRALTESALARIO@, @NRORG@, "
    "( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE NRORG = @NRORG@ AND "
    "CDMATRICULA = '@CDMATRICULA@' ), '@DTALTESALARIO@', @NROCORRENCIA@, '@NRTIPOALTERA@', "
    "@VRSALARIO@, '@IDTPSALARIO@', NVL( '@DSOBSERVACAO@', 'Alteracao salarial importada "
    "via migracao ' || SYSDATE ), 1, SYSDATE, @NRORG@, '@USUARIO_TECNICO@' );"
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
            "nome": "Alteração Salarial",
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
        campo(ordem=1, origem="A", rotulo="Nr Vinculo", campo="CDMATRICULA", marcador="@CDMATRICULA@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=2, origem="B", rotulo="Dt. Alteração", campo="DTALTESALARIO", marcador="@DTALTESALARIO@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="DTALTESALARIO", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        # Vazio => 1 (default original da planilha) — bare/sem aspas no script.
        campo(ordem=3, origem="C", rotulo="Numero Ocorrencia", campo="NROCORRENCIA", marcador="@NROCORRENCIA@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="NROCORRENCIA", tipo="numerico",
              valor_padrao="1"),
        campo(ordem=4, origem="D", rotulo="Tipo Alteração", campo="NRTIPOALTERA", marcador="@NRTIPOALTERA@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="NRTIPOALTERA", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        # Planilha original bloqueia salário vazio ou zerado ("Verificação Sal. Zerado");
        # aqui cobrimos apenas a obrigatoriedade (vazio) — valor zero passar da validação é
        # uma lacuna conhecida (Seção 7.6, regra de negócio ainda não implementada).
        campo(ordem=5, origem="E", rotulo="Salário", campo="VRSALARIO", marcador="@VRSALARIO@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="VRSALARIO", tipo="monetario",
              obrigatorio=True, regra_conversao="numero_decimal"),
        campo(ordem=6, origem="F", rotulo="Tipo Salário", campo="IDTPSALARIO", marcador="@IDTPSALARIO@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="IDTPSALARIO", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=7, origem="G", rotulo="Observação", campo="DSOBSERVACAO", marcador="@DSOBSERVACAO@",
              destino_tabela="GPE_ALTESALARIO", destino_coluna="DSOBSERVACAO", tipo="texto",
              regra_conversao="trim"),
        campo(ordem=8, origem="(gerado)", rotulo="Nº sequencial (gerado)", campo="NRALTESALARIO",
              marcador="@NRALTESALARIO@", destino_tabela="GPE_ALTESALARIO", destino_coluna="NRALTESALARIO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_ALTESALARIO", gerador_pk_seed=0),
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
                "DELETE FROM GPE_ALTESALARIO WHERE NRORG = @NRORG@ AND NRALTESALARIO = @NRALTESALARIO@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
