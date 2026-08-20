"""seed template evento relacionado

Cadastra o template "Evento Relacionado" — um único dicionário/planilha que roteia cada
linha para UMA de três tabelas físicas diferentes conforme a coluna "Tipo Relacionamento"
(VINCULO/ESTRUTURA/OCUPACAO): FPA_VINCEVENTO, FPA_ESTRUTEVENTO ou FPA_OCUPAEVENTO
(estrutura extraída de "docs/novos_templates.txt"). Mesmo padrão de bloco condicional
decidindo a TABELA de destino já usado no eSocial S-2230 (`condicao_campo` + regra de
conversão derivada comparando um código de domínio) — aqui generalizado para 3 ramos em vez
de 2, com 3 novas regras de conversão em `app/transformation/conversions.py`
(`tipo_relacionamento_eh_vinculo`/`_eh_estrutura`/`_eh_ocupacao`).

Dicionário extraído de "docs/LEIAUTE_EVENTO_RELACIONADO.xlsx" (aba única "Planilha1"): a
linha 1 é o cabeçalho real (usado por `header_row`/`data_start_row` — o template de produção
só tem essa linha de rótulo, dados a partir da linha 2); as linhas 2 (texto de ajuda/domínio/
valor padrão) e 3 (marcação OBRIGATORIO) e as linhas 4-15 (exemplos reais) do arquivo modelo
foram usadas só para derivar `obrigatorio`/`valor_padrao`/`dominio_valores` de cada campo —
não fazem parte do layout do template cadastrado.

A coluna B ("Nr. Vínculo/Estrutura/Ocupação") é compartilhada entre os 3 ramos e resolvida
por subquery, reaproveitando os MESMOS padrões já usados por templates existentes que
resolvem a mesma FK a partir de um código de negócio (não o Nº interno):
- VINCULO: matrícula em GPE_VINCULOM (padrão de MOVIMENTACOES_ESTRUTURA/ALTERACAO_OCUPACAO).
- ESTRUTURA: código de integração (CDINTESTRUTURA) em ESTRUTURAM (padrão de
  MOVIMENTACOES_ESTRUTURA).
- OCUPACAO: código de integração (CDINTEGRACAO) em GPE_OCUPACAOH (padrão de
  ALTERACAO_OCUPACAO).

"Nr. Evento" (coluna F) referencia um evento de folha JÁ EXISTENTE no HCM (valores de
exemplo ~205239, ordem de grandeza incompatível com o seed de evento novo do template
EVENTOS, 100073312) — usado direto como NREVENTOM, sem geração de PK nem subquery.
IDATIVO (NOT NULL nas 3 tabelas, sem coluna correspondente na planilha) é gravado como
literal 'S', mesmo padrão já usado no bloco FPA_EVENTOH do template EVENTOS.

Contadores de PK novos (seed=0): nenhum outro template grava nestas 3 tabelas (grep
confirmado em alembic/versions antes de decidir).

Fora de escopo desta leva, por ausência de coluna na planilha/DDL informada: NRESTRUTURAM/
NRTIPOINCIDE/NRCONTRCONSIG/DTINICONTRCONSIG/VRSALDODEVEDOR/PRGARANTIA (campos extras só de
FPA_VINCEVENTO), DSOBSERVACAO, NRTPAGRUPACALC, IDRETREFERENCIA, DTULTATU/NRORGULTATU/
CDOPERULTATU (colunas de última atualização — este template só faz INCLUSAO). Não foi
criado nenhum `TipoMigracao` nesta leva — o template fica cadastrado (visível/testável via
admin) mas não aparece ainda em nenhuma migração do portal; decisão de wiring (tipo próprio
vs. adicionar à Migração Integral) fica para uma próxima etapa.

Revision ID: 769ec8de265b
Revises: ae5c7211f308
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '769ec8de265b'
down_revision: Union[str, None] = 'ae5c7211f308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "EVENTO_RELACIONADO"
SEM_ORIGEM = "_fixo_"

DESTINO_3_TABELAS = "FPA_VINCEVENTO/FPA_ESTRUTEVENTO/FPA_OCUPAEVENTO"

TEMPLATE_SQL_VINCULO = (
    "INSERT INTO FPA_VINCEVENTO ( NRVINCEVENTO, NRORG, NRVINCULOM, NREVENTOM, DTINIVIGENCIA, "
    "DTFIMVIGENCIA, NRVALORREFERENCIAM, VRPERCENT, VRMULTIPLIC, VRDIVIDE, VREVENTOFIXO, "
    "IDREFGERAR, VRREFFIXO, IDTIPOMOVIMENTO, VRPISOEVENTO, VRTETOEVENTO, DTINCLUSAO, "
    "NRORGINCLUSAO, CDOPERINCLUSAO, PERIODICIDADEMES, IDGERAAFASTADO, IDATIVO ) VALUES ( "
    "@NRVINCEVENTO@, @NRORG@, ( SELECT /*MAX(*/ NRVINCULOM /*)*/ FROM GPE_VINCULOM WHERE "
    "NRORG = @NRORG@ AND CDMATRICULA = '@NRRELACIONAMENTO@' ), @NREVENTOM@, "
    "'@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', @NRVALORREFERENCIAM@, @VRPERCENT@, @VRMULTIPLIC@, "
    "@VRDIVIDE@, @VREVENTOFIXO@, '@IDREFGERAR@', @VRREFFIXO@, '@IDTIPOMOVIMENTO@', "
    "@VRPISOEVENTO@, @VRTETOEVENTO@, SYSDATE, @NRORG@, '@USUARIO_TECNICO@', "
    "'@PERIODICIDADEMES@', '@IDGERAAFASTADO@', 'S' );"
)

TEMPLATE_SQL_ESTRUTURA = (
    "INSERT INTO FPA_ESTRUTEVENTO ( NRESTRUTEVENTO, NRORG, NRESTRUTURAM, NREVENTOM, "
    "DTINIVIGENCIA, DTFIMVIGENCIA, PERIODICIDADEMES, NRVALORREFERENCIAM, VRPERCENT, "
    "VRMULTIPLIC, VRDIVIDE, VREVENTOFIXO, IDREFGERAR, VRREFFIXO, IDTIPOMOVIMENTO, "
    "VRPISOEVENTO, VRTETOEVENTO, DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, IDGERAAFASTADO, "
    "IDATIVO ) VALUES ( @NRESTRUTEVENTO@, @NRORG@, ( SELECT MAX( NRESTRUTURAM ) FROM "
    "ESTRUTURAM WHERE NRORG = @NRORG@ AND CDINTESTRUTURA = '@NRRELACIONAMENTO@' ), "
    "@NREVENTOM@, '@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', '@PERIODICIDADEMES@', "
    "@NRVALORREFERENCIAM@, @VRPERCENT@, @VRMULTIPLIC@, @VRDIVIDE@, @VREVENTOFIXO@, "
    "'@IDREFGERAR@', @VRREFFIXO@, '@IDTIPOMOVIMENTO@', @VRPISOEVENTO@, @VRTETOEVENTO@, "
    "SYSDATE, @NRORG@, '@USUARIO_TECNICO@', '@IDGERAAFASTADO@', 'S' );"
)

TEMPLATE_SQL_OCUPACAO = (
    "INSERT INTO FPA_OCUPAEVENTO ( NROCUPAEVENTO, NRORG, NROCUPACAOM, NREVENTOM, "
    "DTINIVIGENCIA, DTFIMVIGENCIA, NRVALORREFERENCIAM, VRPERCENT, VRMULTIPLIC, VRDIVIDE, "
    "VREVENTOFIXO, IDREFGERAR, VRREFFIXO, IDTIPOMOVIMENTO, VRPISOEVENTO, VRTETOEVENTO, "
    "DTINCLUSAO, NRORGINCLUSAO, CDOPERINCLUSAO, PERIODICIDADEMES, IDGERAAFASTADO, IDATIVO ) "
    "VALUES ( @NROCUPAEVENTO@, @NRORG@, ( SELECT MAX(NROCUPACAOM) FROM GPE_OCUPACAOH WHERE "
    "NRORG = @NRORG@ AND CDINTEGRACAO = '@NRRELACIONAMENTO@' ), @NREVENTOM@, "
    "'@DTINIVIGENCIA@', '@DTFIMVIGENCIA@', @NRVALORREFERENCIAM@, @VRPERCENT@, @VRMULTIPLIC@, "
    "@VRDIVIDE@, @VREVENTOFIXO@, '@IDREFGERAR@', @VRREFFIXO@, '@IDTIPOMOVIMENTO@', "
    "@VRPISOEVENTO@, @VRTETOEVENTO@, SYSDATE, @NRORG@, '@USUARIO_TECNICO@', "
    "'@PERIODICIDADEMES@', '@IDGERAAFASTADO@', 'S' );"
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
            "nome": "Evento Relacionado (Vínculo/Estrutura/Ocupação)",
            "versao": "1",
            "formatos_aceitos": ["XLSX"],
            "sheet_name": "Planilha1",
            "header_row": 1,
            "data_start_row": 2,
        },
    ).scalar_one()

    def campo(**kw):
        base = {
            "template_id": template_id, "tamanho_maximo": None, "obrigatorio": False,
            "valor_padrao": None, "regra_conversao": None, "eh_pk": False,
            "gerador_pk": False, "gerador_pk_contador": None, "gerador_pk_seed": None,
            "dominio_valores": None,
        }
        base.update(kw)
        return base

    campos = [
        # --- discriminador + roteamento (Seção 26.4 — bloco condicional decide a TABELA) ---
        campo(ordem=1, origem="A", rotulo="Tipo Relacionamento", campo="TIPORELACIONAMENTO",
              marcador=None, destino_tabela="—", destino_coluna="—", tipo="texto",
              obrigatorio=True, regra_conversao="upper_sem_acento",
              dominio_valores="VINCULO,ESTRUTURA,OCUPACAO"),
        campo(ordem=2, origem="campo:TIPORELACIONAMENTO", rotulo="É Vínculo? (derivado)",
              campo="_EH_VINCULO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="tipo_relacionamento_eh_vinculo"),
        campo(ordem=3, origem="campo:TIPORELACIONAMENTO", rotulo="É Estrutura? (derivado)",
              campo="_EH_ESTRUTURA", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="tipo_relacionamento_eh_estrutura"),
        campo(ordem=4, origem="campo:TIPORELACIONAMENTO", rotulo="É Ocupação? (derivado)",
              campo="_EH_OCUPACAO", marcador=None, destino_tabela="—", destino_coluna="—",
              tipo="booleano", regra_conversao="tipo_relacionamento_eh_ocupacao"),
        # --- compartilhados pelos 3 ramos ---
        campo(ordem=5, origem="B", rotulo="Nr. Vínculo/Estrutura/Ocupação", campo="NRRELACIONAMENTO",
              marcador="@NRRELACIONAMENTO@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="NRVINCULOM/NRESTRUTURAM/NROCUPACAOM", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=6, origem="C", rotulo="Início Vigência", campo="DTINIVIGENCIA",
              marcador="@DTINIVIGENCIA@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="DTINIVIGENCIA", tipo="data", obrigatorio=True,
              valor_padrao="01/01/2000", regra_conversao="data_br"),
        campo(ordem=7, origem="D", rotulo="Fim Vigência", campo="DTFIMVIGENCIA",
              marcador="@DTFIMVIGENCIA@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="DTFIMVIGENCIA", tipo="data", regra_conversao="data_br"),
        campo(ordem=8, origem="E", rotulo="Tipo Movimento (0:TODOS 1:PRINCIPAL 2:AUXILIAR "
              "3:PRINCIPAL+13º 4:PRINCIPAL+Férias 5:FÉRIAS 6:PRINCIPAL+FÉRIAS+13º)",
              campo="IDTIPOMOVIMENTO", marcador="@IDTIPOMOVIMENTO@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="IDTIPOMOVIMENTO", tipo="texto", obrigatorio=True,
              valor_padrao="1", regra_conversao="trim", dominio_valores="0,1,2,3,4,5,6"),
        campo(ordem=9, origem="F", rotulo="Nr. Evento (já existente no HCM)", campo="NREVENTOM",
              marcador="@NREVENTOM@", destino_tabela=DESTINO_3_TABELAS, destino_coluna="NREVENTOM",
              tipo="numerico", obrigatorio=True),
        campo(ordem=10, origem="G", rotulo="Vr. Piso", campo="VRPISOEVENTO", marcador="@VRPISOEVENTO@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRPISOEVENTO", tipo="numerico",
              obrigatorio=True, valor_padrao="0", regra_conversao="numero_decimal"),
        campo(ordem=11, origem="H", rotulo="Vr. Teto", campo="VRTETOEVENTO", marcador="@VRTETOEVENTO@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRTETOEVENTO", tipo="numerico",
              obrigatorio=True, valor_padrao="999999999.99", regra_conversao="numero_decimal"),
        campo(ordem=12, origem="I", rotulo="Valor Referência", campo="NRVALORREFERENCIAM",
              marcador="@NRVALORREFERENCIAM@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="NRVALORREFERENCIAM", tipo="numerico", regra_conversao="numero_ou_null"),
        campo(ordem=13, origem="J", rotulo="Vr. Percentual", campo="VRPERCENT", marcador="@VRPERCENT@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRPERCENT", tipo="numerico",
              obrigatorio=True, valor_padrao="100", regra_conversao="numero_decimal"),
        campo(ordem=14, origem="K", rotulo="Vr. Multiplicador", campo="VRMULTIPLIC", marcador="@VRMULTIPLIC@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRMULTIPLIC", tipo="numerico",
              obrigatorio=True, valor_padrao="1", regra_conversao="numero_decimal"),
        campo(ordem=15, origem="L", rotulo="Vr. Divisor", campo="VRDIVIDE", marcador="@VRDIVIDE@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRDIVIDE", tipo="numerico",
              obrigatorio=True, valor_padrao="1", regra_conversao="numero_decimal"),
        campo(ordem=16, origem="M", rotulo="Vr. Evento Fixo", campo="VREVENTOFIXO", marcador="@VREVENTOFIXO@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VREVENTOFIXO", tipo="numerico",
              regra_conversao="numero_ou_null"),
        campo(ordem=17, origem="N", rotulo="Gerar Tp. Referência", campo="IDREFGERAR",
              marcador="@IDREFGERAR@", destino_tabela=DESTINO_3_TABELAS, destino_coluna="IDREFGERAR",
              tipo="texto", obrigatorio=True, regra_conversao="trim",
              dominio_valores="PERCENTUAL,MULTIPLICADOR,DIVISOR,NENHUM,PARCELA"),
        campo(ordem=18, origem="O", rotulo="Vr. Ref. Fixa", campo="VRREFFIXO", marcador="@VRREFFIXO@",
              destino_tabela=DESTINO_3_TABELAS, destino_coluna="VRREFFIXO", tipo="numerico",
              regra_conversao="numero_ou_null"),
        campo(ordem=19, origem="P", rotulo="Periodicidade Mês (S/N por mês, 12 posições)",
              campo="PERIODICIDADEMES", marcador="@PERIODICIDADEMES@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="PERIODICIDADEMES", tipo="texto", tamanho_maximo=12,
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=20, origem="Q", rotulo="Gera Afastados", campo="IDGERAAFASTADO",
              marcador="@IDGERAAFASTADO@", destino_tabela=DESTINO_3_TABELAS,
              destino_coluna="IDGERAAFASTADO", tipo="texto", tamanho_maximo=1,
              obrigatorio=True, regra_conversao="trim", dominio_valores="S,N"),
        # --- campos com PK sequencial (Key Resolution Service — Seção 6.1); a Script
        # Generator reserva os 3 contadores em toda linha, mas só o do ramo escolhido é de
        # fato gravado (mesmo comportamento já aceito no eSocial S-2230) ---
        campo(ordem=21, origem="(gerado)", rotulo="Nº FPA_VINCEVENTO (gerado)", campo="NRVINCEVENTO",
              marcador="@NRVINCEVENTO@", destino_tabela="FPA_VINCEVENTO", destino_coluna="NRVINCEVENTO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_VINCEVENTO", gerador_pk_seed=0),
        campo(ordem=22, origem="(gerado)", rotulo="Nº FPA_ESTRUTEVENTO (gerado)", campo="NRESTRUTEVENTO",
              marcador="@NRESTRUTEVENTO@", destino_tabela="FPA_ESTRUTEVENTO", destino_coluna="NRESTRUTEVENTO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_ESTRUTEVENTO", gerador_pk_seed=0),
        campo(ordem=23, origem="(gerado)", rotulo="Nº FPA_OCUPAEVENTO (gerado)", campo="NROCUPAEVENTO",
              marcador="@NROCUPAEVENTO@", destino_tabela="FPA_OCUPAEVENTO", destino_coluna="NROCUPAEVENTO",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="FPA_OCUPAEVENTO", gerador_pk_seed=0),
    ]

    conn.execute(
        sa.text(
            """
            INSERT INTO template_campo (template_id, ordem, origem, rotulo, campo, marcador,
                                         destino_tabela, destino_coluna, tipo, tamanho_maximo,
                                         obrigatorio, valor_padrao, regra_conversao, eh_pk,
                                         gerador_pk, gerador_pk_contador, gerador_pk_seed,
                                         dominio_valores)
            VALUES (:template_id, :ordem, :origem, :rotulo, :campo, :marcador, :destino_tabela,
                    :destino_coluna, :tipo, :tamanho_maximo, :obrigatorio, :valor_padrao,
                    :regra_conversao, :eh_pk, :gerador_pk, :gerador_pk_contador, :gerador_pk_seed,
                    :dominio_valores)
            """
        ),
        campos,
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO template_script (template_id, operacao, dialeto_banco, ordem,
                                          condicao_campo, template_sql, template_rollback)
            VALUES (:template_id, 'INCLUSAO', 'ORACLE', :ordem, :condicao_campo,
                    :template_sql, :template_rollback)
            """
        ),
        [
            {
                "template_id": template_id, "ordem": 1, "condicao_campo": "_EH_VINCULO",
                "template_sql": TEMPLATE_SQL_VINCULO,
                "template_rollback": (
                    "DELETE FROM FPA_VINCEVENTO WHERE NRORG = @NRORG@ AND NRVINCEVENTO = @NRVINCEVENTO@;"
                ),
            },
            {
                "template_id": template_id, "ordem": 2, "condicao_campo": "_EH_ESTRUTURA",
                "template_sql": TEMPLATE_SQL_ESTRUTURA,
                "template_rollback": (
                    "DELETE FROM FPA_ESTRUTEVENTO WHERE NRORG = @NRORG@ AND NRESTRUTEVENTO = @NRESTRUTEVENTO@;"
                ),
            },
            {
                "template_id": template_id, "ordem": 3, "condicao_campo": "_EH_OCUPACAO",
                "template_sql": TEMPLATE_SQL_OCUPACAO,
                "template_rollback": (
                    "DELETE FROM FPA_OCUPAEVENTO WHERE NRORG = @NRORG@ AND NROCUPAEVENTO = @NROCUPAEVENTO@;"
                ),
            },
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
