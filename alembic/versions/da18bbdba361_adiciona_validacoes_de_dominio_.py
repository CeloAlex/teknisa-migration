"""adiciona validacoes de dominio duplicidade e ausencia condicional no template estrutura

Feedback do piloto NUTRIBEM-TOTAL (comparação com a ferramenta legada do cliente):
- CNPJ duplicado entre estruturas do mesmo NRTPESTRUTURA vira alerta (não bloqueia — o
  cliente pode optar por importar "as is" e depois sanear).
- NRESTRUTURA (Nº Estrutura, coluna D) duplicado vira erro impeditivo — quebra a integração
  com Vínculo/Movimentações, que usam esse valor como chave (CDINTESTRUTURA).
- NRTPESTRUTURA fora do domínio de tipos conhecidos vira alerta — domínio fornecido pelo
  usuário como snapshot atual (é dado vivo, cresce por organização).
- Ausência de endereço/CNAE/FPAS/CNPJ/natureza jurídica/tipo de empresa quando
  NRTPESTRUTURA em (1, 2, 20) vira alerta — não é impeditivo, mas gera responsabilidade para
  as áreas de cliente/implantação/migração resolverem.
- FPAS (coluna K) não existia como TemplateCampo (lida na planilha mas descartada, Seção
  13.2) — precisa existir pra alertar sobre ausência, então é inserida como campo só de
  validação (destino "—", nunca vai pro script), no mesmo padrão do derivado
  `_TEM_ENDERECO`.

Revision ID: da18bbdba361
Revises: 794618fabba5
Create Date: 2026-08-13 11:22:27.122332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da18bbdba361'
down_revision: Union[str, None] = '794618fabba5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "ESTRUTURA"

DOMINIO_NRTPESTRUTURA = (
    "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,30,31,32,33,"
    "35,36,37,38,39,40,41,42,43,44,45,46,48,49,50,51,52,53,54,55,58,59,60,61,62,63,65,66,67,"
    "68,69,70,72,73,74,75,76,80,83,84,85,86,87,88,89,90,91,92,93,94,95,97,98,99,100,101,103,"
    "104,105,106,107,108,109,110,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,"
    "127,128,129,130,133,135,136,138,139,140,142,144,145,146,147,148,149,150,151,153,155,156,"
    "157,158,159,161,162,163,166,167,168,169,170,171,173"
)

CAMPO_GATILHO = "NRTPESTRUTURA"
VALORES_GATILHO = "1,2,20"

CAMPOS_AUSENCIA_CONDICIONAL = ["CNPJ", "NATJURIDICA", "CDCNAE", "IDTPEMPRESA", "LOGRADOURO", "FPAS"]


def upgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text(
            "UPDATE template_campo SET dominio_valores = :dominio "
            "WHERE template_id = :template_id AND campo = 'NRTPESTRUTURA'"
        ),
        {"template_id": template_id, "dominio": DOMINIO_NRTPESTRUTURA},
    )

    conn.execute(
        sa.text(
            "UPDATE template_campo SET duplicata_no_lote = 'erro_impeditivo' "
            "WHERE template_id = :template_id AND campo = 'NRESTRUTURA'"
        ),
        {"template_id": template_id},
    )

    conn.execute(
        sa.text(
            "UPDATE template_campo SET duplicata_no_lote = 'alerta', duplicata_agrupado_por = 'NRTPESTRUTURA' "
            "WHERE template_id = :template_id AND campo = 'CNPJ'"
        ),
        {"template_id": template_id},
    )

    conn.execute(
        sa.text(
            "UPDATE template_campo SET alerta_se_vazio_quando_campo = :campo_gatilho, "
            "alerta_se_vazio_quando_valores = :valores_gatilho "
            "WHERE template_id = :template_id AND campo IN ('CNPJ', 'NATJURIDICA', 'CDCNAE', 'IDTPEMPRESA', 'LOGRADOURO')"
        ),
        {"template_id": template_id, "campo_gatilho": CAMPO_GATILHO, "valores_gatilho": VALORES_GATILHO},
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO template_campo (template_id, ordem, origem, rotulo, campo, marcador,
                                         destino_tabela, destino_coluna, tipo, tamanho_maximo,
                                         obrigatorio, valor_padrao, regra_conversao, eh_pk,
                                         gerador_pk, alerta_se_vazio_quando_campo,
                                         alerta_se_vazio_quando_valores)
            VALUES (:template_id, 36, 'K', 'FPAS', 'FPAS', NULL, '—', '—', 'texto', NULL,
                    FALSE, NULL, 'trim', FALSE, FALSE, :campo_gatilho, :valores_gatilho)
            """
        ),
        {"template_id": template_id, "campo_gatilho": CAMPO_GATILHO, "valores_gatilho": VALORES_GATILHO},
    )


def downgrade() -> None:
    conn = op.get_bind()
    template_id = conn.execute(
        sa.text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO}
    ).scalar_one()

    conn.execute(
        sa.text("DELETE FROM template_campo WHERE template_id = :template_id AND campo = 'FPAS'"),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            "UPDATE template_campo SET alerta_se_vazio_quando_campo = NULL, alerta_se_vazio_quando_valores = NULL "
            "WHERE template_id = :template_id AND campo IN ('CNPJ', 'NATJURIDICA', 'CDCNAE', 'IDTPEMPRESA', 'LOGRADOURO')"
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            "UPDATE template_campo SET duplicata_no_lote = NULL, duplicata_agrupado_por = NULL "
            "WHERE template_id = :template_id AND campo = 'CNPJ'"
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            "UPDATE template_campo SET duplicata_no_lote = NULL "
            "WHERE template_id = :template_id AND campo = 'NRESTRUTURA'"
        ),
        {"template_id": template_id},
    )
    conn.execute(
        sa.text(
            "UPDATE template_campo SET dominio_valores = NULL "
            "WHERE template_id = :template_id AND campo = 'NRTPESTRUTURA'"
        ),
        {"template_id": template_id},
    )
