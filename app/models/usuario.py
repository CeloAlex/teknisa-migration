from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Papel(str, Enum):
    """Perfis mínimos de RBAC (Seção 12.1) — a segregação de função é o ponto central: a
    mesma migração sensível nunca deve ter aprovação de dados e aprovação técnica feitas
    pelo mesmo perfil."""

    OPERADOR = "operador"
    APROVADOR_FUNCIONAL = "aprovador_funcional"
    APROVADOR_TECNICO = "aprovador_tecnico"
    EXECUTOR_DBA = "executor_dba"
    ADMINISTRADOR = "administrador"
    AUDITOR = "auditor"


class Usuario(Base):
    """Usuário do portal (Fase 6) — login local por enquanto; a Seção 3.3 menciona SSO
    corporativo como integração futura, fora do escopo desta fase. `nr_org` nulo significa
    que o usuário enxerga/atua em todas as organizações (típico de Administrador/Auditor);
    preenchido, fica restrito a uma organização só (espelha o `orgId` fixo do protótipo)."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    cargo: Mapped[str | None] = mapped_column(String(200))
    papel: Mapped[str] = mapped_column(String(30))
    nr_org: Mapped[int | None] = mapped_column(ForeignKey("organizacao.nr_org"), index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    dt_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
