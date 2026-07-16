"""seed template ficha financeira

Cadastra o template "Ficha Financeira" (Seção 26.2) — a dependência mais crítica do
conjunto de treze: cada INSERT em FPA_ITECALCFOLHA depende de um "cálculo de folha"
(FPA_CALCULOFOLHA) já existente no destino para a mesma organização, tipo de movimento e
competência — um registro que não é criado por nenhuma das treze planilhas, e sim por um
processo de folha de pagamento externo à migração. Como ainda não há integração com o banco
de destino (Oracle) para executar uma consulta de verificação de fato, o pré-requisito é
registrado como texto livre em `pre_requisito_externo`, exibido ao operador via
GET /templates/{codigo} — não é (ainda) uma checagem em tempo de execução (Seção 26.4).
PK sequencial, FK a Vínculo (matrícula) e a MIG_MIGRAMDEPARA (evento, populada pelo template
Eventos). A planilha real oferece 4 variantes de template (vínculo por matrícula ou por
número interno; evento por de-para ou por número interno); esta migração cadastra apenas a
variante mais comum (matrícula + de-para), como o próprio protótipo de referência já havia
optado. Dicionário e template de script extraídos diretamente de
"docs/planilhas-originais/13_FichaFinanceira_v15.xlsx".

Revision ID: 157982505200
Revises: e5513421e14a
Create Date: 2026-07-16 07:25:19.240560

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '157982505200'
down_revision: Union[str, None] = 'e5513421e14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "FICHA_FINANCEIRA"

PRE_REQUISITO_EXTERNO = (
    "Depende de um registro em FPA_CALCULOFOLHA já existente no destino para a mesma "
    "organização, tipo de movimento (NRTIPOMOVIMENT) e competência (DTOCORRENCIA) de cada "
    "linha — criado por um processo de folha de pagamento externo à migração, não por esta "
    "plataforma. Confirme com a equipe de folha que o cálculo já foi gerado antes de aplicar "
    "o script; caso contrário, a subquery de NRCALCULOFOLHA retorna NULL e o INSERT falha "
    "silenciosamente ou grava um item órfão (Seção 26.2/26.4)."
)

# Texto extraído verbatim da célula U2 do arquivo real (variante matrícula + de-para).
TEMPLATE_SQL = (
    "INSERT INTO FPA_ITECALCFOLHA ( NRITEMCALCFOLHA, NRCALCULOFOLHA, NRVINCULOM, NREVENTOM, "
    "NRORG, IDEVENDEMONCALC, VRREFFOLHA, VREVENTOFOLHA, IDREFEVALORCALC, DTINCLUSAO, "
    "DTOCORRENCIA, DSITEMCALCFOLHA, QTOCORPROXPERI ) VALUES ( @NRO@, ( SELECT "
    "MAX(NRCALCULOFOLHA) FROM FPA_CALCULOFOLHA WHERE NRORG = @NRORG@ AND NRTIPOMOVIMENT = "
    "@NRTIPOMOVIMENT@ AND DTOCORRENCIA = '@DTMESCOMPETENC@' AND NRTPMODALIDCAL = 1 AND "
    "NROCORRECAL = 1 ), ( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE NRORG = "
    "@NRORG@ AND CDMATRICULA = '@CDMATRICULA@' ), ( SELECT MAX(NRPARA) FROM "
    "MIG_MIGRAMDEPARA WHERE NRORG = @NRORG@ AND NRDE = '@NREVENTO@' ), @NRORG@, 'N', "
    "@VRREFFOLHA@, @VREVENTOFOLHA@, 'REFERENCIA_VALOR', SYSDATE, '@DTOCORRENCIA@', "
    "'@DSITEMCALCFOLHA@', 1 );"
)


def upgrade() -> None:
    conn = op.get_bind()

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO template (codigo, nome, versao, formatos_aceitos, sheet_name,
                                   header_row, data_start_row, ativo, pre_requisito_externo)
            VALUES (:codigo, :nome, :versao, :formatos_aceitos, :sheet_name,
                    :header_row, :data_start_row, true, :pre_requisito_externo)
            RETURNING id
            """
        ),
        {
            "codigo": TEMPLATE_CODIGO,
            "nome": "Ficha Financeira (histórico de proventos/descontos)",
            "versao": "15",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Dados",
            "header_row": 2,
            "data_start_row": 3,
            "pre_requisito_externo": PRE_REQUISITO_EXTERNO,
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
        # Bare/sem aspas no script — obrigatório para não gerar SQL inválido.
        campo(ordem=1, origem="A", rotulo="Tp Movimento", campo="NRTIPOMOVIMENT", marcador="@NRTIPOMOVIMENT@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="NRTIPOMOVIMENT", tipo="numerico",
              obrigatorio=True),
        campo(ordem=2, origem="B", rotulo="Nr. Vínculo", campo="CDMATRICULA", marcador="@CDMATRICULA@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="NRVINCULOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="C", rotulo="Competência", campo="DTMESCOMPETENC", marcador="@DTMESCOMPETENC@",
              destino_tabela="FPA_CALCULOFOLHA", destino_coluna="DTOCORRENCIA", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=4, origem="D", rotulo="Nr. Evento", campo="NREVENTO", marcador="@NREVENTO@",
              destino_tabela="MIG_MIGRAMDEPARA", destino_coluna="NRDE", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        # Bare/sem aspas — obrigatório.
        campo(ordem=5, origem="E", rotulo="Valor", campo="VREVENTOFOLHA", marcador="@VREVENTOFOLHA@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="VREVENTOFOLHA", tipo="monetario",
              obrigatorio=True, regra_conversao="numero_decimal"),
        campo(ordem=6, origem="F", rotulo="Descrição do Cálculo", campo="DSITEMCALCFOLHA",
              marcador="@DSITEMCALCFOLHA@", destino_tabela="FPA_ITECALCFOLHA", destino_coluna="DSITEMCALCFOLHA",
              tipo="texto", regra_conversao="trim"),
        campo(ordem=7, origem="G", rotulo="Data de Ocorrência", campo="DTOCORRENCIA", marcador="@DTOCORRENCIA@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="DTOCORRENCIA", tipo="data",
              regra_conversao="data_br"),
        # Bare/sem aspas e opcional — vazio precisa virar o literal NULL.
        campo(ordem=8, origem="H", rotulo="Valor de Referencia", campo="VRREFFOLHA", marcador="@VRREFFOLHA@",
              destino_tabela="FPA_ITECALCFOLHA", destino_coluna="VRREFFOLHA", tipo="numerico",
              regra_conversao="numero_ou_null"),
        campo(ordem=9, origem="(gerado)", rotulo="Nº sequencial do item (gerado)", campo="NRO",
              marcador="@NRO@", destino_tabela="FPA_ITECALCFOLHA", destino_coluna="NRITEMCALCFOLHA",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_ITECALCFOLHA", gerador_pk_seed=0),
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
                "DELETE FROM FPA_ITECALCFOLHA WHERE NRORG = @NRORG@ AND NRITEMCALCFOLHA = @NRO@;"
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
