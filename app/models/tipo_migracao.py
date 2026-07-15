from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TipoMigracao(Base):
    """Configuração reutilizável de um "pacote" de templates a migrar (Seção 5.1)."""

    __tablename__ = "tipo_migracao"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    banco_destino: Mapped[str] = mapped_column(String(20))
    permite_concorrencia: Mapped[bool] = mapped_column(Boolean, default=False)
    modo_aplicacao: Mapped[str] = mapped_column(String(20), default="SCRIPT")
    sequencia_obrigatoria: Mapped[bool] = mapped_column(Boolean, default=False)

    templates: Mapped[list["TipoMigracaoTemplate"]] = relationship(
        back_populates="tipo_migracao",
        order_by="TipoMigracaoTemplate.ordem",
        cascade="all, delete-orphan",
    )


class TipoMigracaoTemplate(Base):
    """Associação ordenada entre um tipo de migração e os templates que ele compõe (Seção 14)."""

    __tablename__ = "tipo_migracao_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_migracao_id: Mapped[int] = mapped_column(ForeignKey("tipo_migracao.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True)

    tipo_migracao: Mapped["TipoMigracao"] = relationship(back_populates="templates")
    template: Mapped["Template"] = relationship()  # noqa: F821 (referência a app.models.template.Template)
