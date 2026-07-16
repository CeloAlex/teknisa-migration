from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


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
    origem: Mapped[str] = mapped_column(String(100))
    rotulo: Mapped[str] = mapped_column(String(200))
    campo: Mapped[str] = mapped_column(String(100))
    marcador: Mapped[str | None] = mapped_column(String(100))
    destino_tabela: Mapped[str] = mapped_column(String(100))
    destino_coluna: Mapped[str] = mapped_column(String(100))
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
