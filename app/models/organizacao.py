from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organizacao(Base):
    """Organização/cliente cujos dados estão sendo migrados (Seção 14) — chave NRORG usada
    como parâmetro de execução em todo o motor genérico desde a Fase 2."""

    __tablename__ = "organizacao"

    nr_org: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
