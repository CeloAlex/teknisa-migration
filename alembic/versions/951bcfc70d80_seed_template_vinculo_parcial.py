"""seed template vinculo parcial

Cadastra o template "Vínculo" com fidelidade PARCIAL, deliberadamente — mesmo limite já
assumido pelo protótipo de referência (`simulacaoDisponivel:false`). É o arquivo mais
complexo dos treze (224 colunas na aba Dados, 10 blocos de script diferentes localizados
entre as colunas 147-162 e 214-223 na inspeção do arquivo real), e reconstituir seu
dicionário completo e todos os blocos de INSERT exigiria um levantamento funcional dedicado
que foge do escopo desta fase (Seção 19, risco "ordem de dependência... não documentada
formalmente"; Anexo J trata Vínculo como parte do MVP mas não detalha os 224 campos).

Cadastramos aqui apenas os três campos já validados diretamente no arquivo real e no
protótipo (matrícula, data de admissão e CPF) e a PK sequencial de GPE_VINCULOM — o
suficiente para que outros templates já cadastrados (Alteração Salarial, Alteração de
Escala, Alteração de Ocupação, Situação Funcional, Férias, Movimentações de Estrutura,
Ficha Financeira) resolvam corretamente sua FK "vínculo por matrícula" via subquery contra
GPE_VINCULOM. NÃO cadastramos um TemplateScript: gerar o script completo de Vínculo exigiria
os ~10 blocos de INSERT (GPE_VINCULOM/H, GPE_PESSOA/H, endereço, dados bancários, CTPS
etc.) que não foram extraídos com segurança nesta fase. `POST /templates/VINCULO/gerar-script`
retorna erro explícito (`ScriptNaoConfigurado`) até que esse levantamento seja concluído —
comportamento intencional, não uma falha do motor.

Um achado ao conferir o arquivo real: o protótipo mapeava CPF na coluna H, mas na versão
v26_BETA revisada o CPF está na coluna J (H contém "Nome") — corrigido aqui a partir da
inspeção direta do arquivo, não do protótipo.

Revision ID: 951bcfc70d80
Revises: 157982505200
Create Date: 2026-07-16 07:26:17.219860

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '951bcfc70d80'
down_revision: Union[str, None] = '157982505200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODIGO = "VINCULO"


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
            "nome": "Vínculo (dicionário parcial — pendente de levantamento funcional completo)",
            "versao": "26_BETA",
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
        campo(ordem=1, origem="A", rotulo="Data Admissão", campo="DTADMISSAOVINC", marcador="@DTADMISSAOVINC@",
              destino_tabela="GPE_VINCULOM", destino_coluna="DTADMISSAOVINC", tipo="data",
              obrigatorio=True, regra_conversao="data_br"),
        campo(ordem=2, origem="C", rotulo="Nr. Vínculo (matrícula)", campo="CDMATRICULA", marcador="@CDMATRICULA@",
              destino_tabela="GPE_VINCULOM", destino_coluna="CDMATRICULA", tipo="texto",
              obrigatorio=True, regra_conversao="trim"),
        campo(ordem=3, origem="J", rotulo="CPF", campo="NRCPFPESSOA", marcador="@CDCPFPESSOA@",
              destino_tabela="GPE_PESSOAH", destino_coluna="NRCPFPESSOA", tipo="texto",
              tamanho_maximo=11, obrigatorio=True, regra_conversao="remover_mascara"),
        campo(ordem=4, origem="(gerado)", rotulo="Nº sequencial de vínculo (gerado)", campo="NRVINCULOM",
              marcador="@NRVINCULOM@", destino_tabela="GPE_VINCULOM", destino_coluna="NRVINCULOM",
              tipo="numerico", eh_pk=True, gerador_pk=True, gerador_pk_contador="GPE_VINCULOM", gerador_pk_seed=949700),
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
    # Nenhum TemplateScript cadastrado — ver docstring desta revisão.


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM template WHERE codigo = :codigo"), {"codigo": TEMPLATE_CODIGO})
