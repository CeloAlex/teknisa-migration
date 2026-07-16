from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CatalogoTabela(Base):
    """Tabela de destino Oracle catalogada a partir de um script de DDL importado (Anexo
    `docs/especificação/base_vazia.txt`) — usada como FK-guia por `TemplateCampo`, não como
    schema de fato aplicado no Oracle (o motor nunca executa DDL)."""

    __tablename__ = "catalogo_destino_tabela"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_tabela: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    colunas: Mapped[list["CatalogoColuna"]] = relationship(
        back_populates="tabela", order_by="CatalogoColuna.nome_coluna", cascade="all, delete-orphan"
    )


class CatalogoColuna(Base):
    """Coluna de uma `CatalogoTabela`, extraída do `CREATE TABLE` do script de DDL —
    tipo/tamanho/obrigatoriedade só para referência do operador ao cadastrar um
    `TemplateCampo`; nenhuma regra de validação do motor depende disso."""

    __tablename__ = "catalogo_destino_coluna"
    __table_args__ = (UniqueConstraint("tabela_id", "nome_coluna"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tabela_id: Mapped[int] = mapped_column(ForeignKey("catalogo_destino_tabela.id"), index=True)
    nome_coluna: Mapped[str] = mapped_column(String(128))
    tipo_dado: Mapped[str | None] = mapped_column(String(50))
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=False)

    tabela: Mapped["CatalogoTabela"] = relationship(back_populates="colunas")
