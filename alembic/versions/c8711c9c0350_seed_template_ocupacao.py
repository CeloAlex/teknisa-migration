"""seed template ocupacao

Cadastra o template "Ocupação" — duas tabelas (GPE_OCUPACAOM/H), ambas com PK sequencial
via Key Resolution Service, sem FK e sem bloco condicional. Dicionário de dados e template
de script extraídos diretamente de "docs/planilhas-originais/02_Ocupação_v07.xlsx" (aba
Script, linha 2 = cabeçalho/template, linha 3 = primeira linha real).

Revision ID: c8711c9c0350
Revises: 06d5b9d23be9
Create Date: 2026-07-15 20:56:28.580344

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8711c9c0350'
down_revision: Union[str, None] = '06d5b9d23be9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "OCUPACAO"

# Texto extraído verbatim da célula Q2 da planilha real, com a mesma troca do operador
# técnico fixo '000000099991' por @USUARIO_TECNICO@ (Seção 13.3) já aplicada em Agências e
# Estrutura.
TEMPLATE_SQL = (
    "INSERT INTO GPE_OCUPACAOM (NRORG, NROCUPACAOM, NRTIPOOCUPACAO, DTINIVIGENCIA, "
    "DTFIMVIGENCIA, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO) VALUES (@NRORG@, "
    "@NROCUPACAOM@, @NRTIPOOCUPACAO@, '@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', SYSDATE, "
    "@NRORG@, '@USUARIO_TECNICO@'); INSERT INTO GPE_OCUPACAOH (NRORG, NROCUPACAOH, "
    "NROCUPACAOM, DTMESCOMPETENC, NMOCUPACAOH, CDINTEGRACAO, NRCBO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO) VALUES (@NRORG@, @NROCUPACAOH@, @NROCUPACAOM@, "
    "'@COMPETENCIA@', '@NMOCUPACAOH@', '@CDINTEGRACAO@', @NRCBO@, SYSDATE, @NRORG@, "
    "'@USUARIO_TECNICO@' );"
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
            "nome": "Ocupação",
            "versao": "7",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Script",
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
        # Marcada obrigatória (diferente da checagem original da planilha, que não validava
        # este campo): usada sem aspas no template (posição numérica) — vazia geraria SQL
        # inválido. Ver Seção 13.2/26.4 sobre robustecer o gerador de script.
        campo(ordem=1, origem="A", rotulo="tp ocupação", campo="NRTIPOOCUPACAO",
              marcador="@NRTIPOOCUPACAO@", destino_tabela="GPE_OCUPACAOM", destino_coluna="NRTIPOOCUPACAO",
              tipo="numerico", obrigatorio=True),
        campo(ordem=2, origem="B", rotulo="Início Vigência", campo="DTINIVIGENCIA",
              marcador="@DTINIVIGENCIA@", destino_tabela="GPE_OCUPACAOM", destino_coluna="DTINIVIGENCIA",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=3, origem="C", rotulo="Fim Vigência", campo="DTFIMVIGENCIA",
              marcador="@DTFIMVIGENCIA@", destino_tabela="GPE_OCUPACAOM", destino_coluna="DTFIMVIGENCIA",
              tipo="data", regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Nr Ocupacao (código de integração)", campo="CDINTEGRACAO",
              marcador="@CDINTEGRACAO@", destino_tabela="GPE_OCUPACAOH", destino_coluna="CDINTEGRACAO",
              tipo="texto", obrigatorio=True, regra_conversao="trim"),
        campo(ordem=5, origem="E", rotulo="Competência", campo="COMPETENCIA",
              marcador="@COMPETENCIA@", destino_tabela="GPE_OCUPACAOH", destino_coluna="DTMESCOMPETENC",
              tipo="data", obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=6, origem="F", rotulo="Descrição", campo="NMOCUPACAOH", marcador="@NMOCUPACAOH@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="NMOCUPACAOH", tipo="texto",
              tamanho_maximo=100, obrigatorio=True, regra_conversao="remover_aspas_e_comercial"),
        campo(ordem=7, origem="G", rotulo="CBO", campo="NRCBO", marcador="@NRCBO@",
              destino_tabela="GPE_OCUPACAOH", destino_coluna="NRCBO", tipo="numerico",
              tamanho_maximo=6, regra_conversao="cbo"),
        # --- campos com PK sequencial (Key Resolution Service — Seção 6.1) ---
        campo(ordem=8, origem="(gerado)", rotulo="Nº GPE_OCUPACAOM (gerado)", campo="NROCUPACAOM",
              marcador="@NROCUPACAOM@", destino_tabela="GPE_OCUPACAOM", destino_coluna="NROCUPACAOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_OCUPACAOM", gerador_pk_seed=0),
        campo(ordem=9, origem="(gerado)", rotulo="Nº GPE_OCUPACAOH (gerado)", campo="NROCUPACAOH",
              marcador="@NROCUPACAOH@", destino_tabela="GPE_OCUPACAOH", destino_coluna="NROCUPACAOH",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_OCUPACAOH", gerador_pk_seed=0),
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
                "DELETE FROM GPE_OCUPACAOH WHERE NRORG = @NRORG@ AND NROCUPACAOH = @NROCUPACAOH@; "
                "DELETE FROM GPE_OCUPACAOM WHERE NRORG = @NRORG@ AND NROCUPACAOM = @NROCUPACAOM@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
