from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
import app.models.catalogo_destino  # noqa: F401 — registra CatalogoColuna para a FK abaixo


class Template(Base):
    """Um contexto migrável (Seção 5.2) — ex.: Agências Bancárias, Estrutura, Vínculo."""

    __tablename__ = "template"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    versao: Mapped[str] = mapped_column(String(20), default="1.0")
    formatos_aceitos: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    sheet_name: Mapped[str | None] = mapped_column(String(100))
    header_row: Mapped[int | None] = mapped_column(Integer)
    data_start_row: Mapped[int | None] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Distingue template de dados transacionais (padrão) de template de catálogo/
    # parametrização compartilhada pela organização, que outros templates apenas consultam
    # por FK — ex. Eventos de Folha (Seção 26.4).
    eh_catalogo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Pré-requisito externo à migração (Seção 26.2/26.4): um dado que precisa existir
    # previamente no destino, criado por um processo de negócio fora da plataforma (ex.
    # Ficha Financeira depende de um "cálculo de folha" já existente). Texto livre exibido
    # ao operador antes da geração do script — não é (ainda) uma consulta de verificação
    # executada de fato, pois isso depende da integração com o banco de destino.
    pre_requisito_externo: Mapped[str | None] = mapped_column(Text)
    # Fase 7 (eSocial): XPath (relativo à raiz, após remoção de namespace) que seleciona
    # o(s) nó(s) "linha" no XML — nulo significa "o documento inteiro é uma linha só", o
    # caso da maioria dos eventos eSocial (um XML = um evento). Só usado quando
    # `formatos_aceitos` inclui "XML"; templates XLSX deixam isso nulo.
    xml_registro_xpath: Mapped[str | None] = mapped_column(String(300))

    campos: Mapped[list["TemplateCampo"]] = relationship(
        back_populates="template", order_by="TemplateCampo.ordem", cascade="all, delete-orphan"
    )
    scripts: Mapped[list["TemplateScript"]] = relationship(
        back_populates="template", order_by="TemplateScript.ordem", cascade="all, delete-orphan"
    )


class TemplateCampo(Base):
    """Um campo do dicionário de dados de um template (Seção 6 / Anexo E)."""

    __tablename__ = "template_campo"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    # 100 bastava para referências de coluna XLSX ("A", "campo:X,Y"); XPath eSocial (Fase
    # 7), especialmente com união de inclusão/alteração, passa disso facilmente.
    origem: Mapped[str] = mapped_column(String(300))
    rotulo: Mapped[str] = mapped_column(String(200))
    campo: Mapped[str] = mapped_column(String(100))
    marcador: Mapped[str | None] = mapped_column(String(100))
    destino_tabela: Mapped[str] = mapped_column(String(100))
    destino_coluna: Mapped[str] = mapped_column(String(100))
    # Opcional: quando o operador escolhe tabela/coluna a partir do catálogo importado de
    # DDL (em vez de digitar destino_tabela/destino_coluna à mão), a escolha também fica
    # registrada aqui como FK real. Nullable de propósito — os ~24 templates seedados antes
    # da existência do catálogo continuam com isto NULL e seguem funcionando normalmente
    # pelo texto livre (nunca lido pelo motor, só exibido).
    destino_coluna_catalogo_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalogo_destino_coluna.id"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(String(20))
    tamanho_maximo: Mapped[int | None] = mapped_column(Integer)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=False)
    valor_padrao: Mapped[str | None] = mapped_column(String(200))
    regra_conversao: Mapped[str | None] = mapped_column(String(50))
    regra_validacao: Mapped[str | None] = mapped_column(Text)
    eh_pk: Mapped[bool] = mapped_column(Boolean, default=False)
    gerador_pk: Mapped[bool] = mapped_column(Boolean, default=False)
    # Preenchidos apenas quando gerador_pk=True: nome do contador e semente iniciais usados
    # pelo Key Resolution Service (Seção 6.1) — equivalente ao par (CDCONTADOR, seed) que o
    # protótipo declara por campo em pkGeracao.
    gerador_pk_contador: Mapped[str | None] = mapped_column(String(100))
    gerador_pk_seed: Mapped[int | None] = mapped_column(Integer)
    # Validação relacional local (Seção 7.4): quando preenchidos, o valor deste campo
    # precisa aparecer entre os valores já importados no campo `fk_campo` do template
    # `fk_template_codigo`, dentro da mesma migração — antecipa uma FK que resolveria para
    # NULL na aplicação real (ex.: código de Estrutura com typo entre dois uploads).
    fk_template_codigo: Mapped[str | None] = mapped_column(String(50))
    fk_campo: Mapped[str | None] = mapped_column(String(100))
    # Validação de domínio (Seção 7.3): lista de valores aceitos, separada por vírgula.
    # Quando preenchido e o campo não está vazio, um valor fora da lista vira alerta (não
    # bloqueia) — o domínio de negócio às vezes cresce por organização (ex.: tipo de
    # estrutura), então isto é feedback pro operador resolver, não uma trava rígida.
    dominio_valores: Mapped[str | None] = mapped_column(Text)
    # Duplicidade dentro do mesmo lote importado: "erro_impeditivo" ou "alerta". Quando
    # preenchido, valores repetidos deste campo entre linhas do mesmo template/migração geram
    # esse resultado em cada linha duplicada (ver `verificar_duplicatas_lote`).
    duplicata_no_lote: Mapped[str | None] = mapped_column(String(20))
    # Opcional: nome de outro `campo` do mesmo template. Quando presente, duas linhas só
    # contam como duplicata se também compartilharem o valor deste campo (ex.: CNPJ
    # duplicado só é alerta entre estruturas do mesmo NRTPESTRUTURA).
    duplicata_agrupado_por: Mapped[str | None] = mapped_column(String(100))
    # Obrigatoriedade condicional, classificada como alerta (não erro): quando este campo
    # está vazio E o valor do campo `alerta_se_vazio_quando_campo` está entre os valores
    # (separados por vírgula) de `alerta_se_vazio_quando_valores`, gera alerta de ausência.
    alerta_se_vazio_quando_campo: Mapped[str | None] = mapped_column(String(100))
    alerta_se_vazio_quando_valores: Mapped[str | None] = mapped_column(String(300))

    template: Mapped["Template"] = relationship(back_populates="campos")


class TemplateScript(Base):
    """Bloco de template de script com marcadores @CAMPO@, por operação e dialeto de banco
    (Seção 6.2 / 10). Um template pode ter mais de um bloco para a mesma operação — cada
    linha aprovada gera um INSERT por bloco, na ordem declarada, pulando blocos cuja
    `condicao_campo` (um campo booleano do dicionário) resolver como falso/vazio — o padrão
    de "bloco condicional" identificado na Seção 26.4 (ex.: endereço de Estrutura só é
    inserido se tipo de endereço e logradouro estiverem preenchidos)."""

    __tablename__ = "template_script"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"), index=True)
    operacao: Mapped[str] = mapped_column(String(20))
    dialeto_banco: Mapped[str] = mapped_column(String(20))
    ordem: Mapped[int] = mapped_column(Integer, default=1)
    condicao_campo: Mapped[str | None] = mapped_column(String(100))
    template_sql: Mapped[str] = mapped_column(Text)
    template_rollback: Mapped[str | None] = mapped_column(Text)

    template: Mapped["Template"] = relationship(back_populates="scripts")
