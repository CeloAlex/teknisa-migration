from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MigracaoStatus(str, Enum):
    """Máquina de estados da migração (Seção 9.1). "Com inconsistências" é um estado
    transitório de sistema (Seção 9.2, "relatório de erros publicado") que não fica
    persistido isoladamente — a migração já chega direto em AGUARDANDO_CORRECAO, o próximo
    estado observável/acionável pelo operador."""

    CRIADA = "criada"
    AGUARDANDO_ARQUIVOS = "aguardando_arquivos"
    EM_VALIDACAO = "em_validacao"
    AGUARDANDO_CORRECAO = "aguardando_correcao"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    PRONTA_PARA_GERACAO_SCRIPTS = "pronta_para_geracao_scripts"
    SCRIPTS_GERADOS = "scripts_gerados"
    AGUARDANDO_APLICACAO = "aguardando_aplicacao"
    EM_EXECUCAO = "em_execucao"
    CONCLUIDA = "concluida"
    CONCLUIDA_COM_ALERTAS = "concluida_com_alertas"
    COM_ERRO = "com_erro"
    REVERTIDA = "revertida"
    CANCELADA = "cancelada"


# Estados considerados "ativos" para efeito do bloqueio de concorrência por organização
# (Seção 4.1) — qualquer estado entre criada e aguardando aplicação, inclusive.
ESTADOS_ATIVOS = {
    MigracaoStatus.CRIADA,
    MigracaoStatus.AGUARDANDO_ARQUIVOS,
    MigracaoStatus.EM_VALIDACAO,
    MigracaoStatus.AGUARDANDO_CORRECAO,
    MigracaoStatus.AGUARDANDO_APROVACAO,
    MigracaoStatus.PRONTA_PARA_GERACAO_SCRIPTS,
    MigracaoStatus.SCRIPTS_GERADOS,
    MigracaoStatus.AGUARDANDO_APLICACAO,
}

# Estados terminais: a máquina de estados nunca recalcula automaticamente a partir daqui.
ESTADOS_TERMINAIS = {
    MigracaoStatus.CANCELADA,
    MigracaoStatus.REVERTIDA,
}


class TemplateStatus(str, Enum):
    """Status de um template dentro de uma migração específica."""

    PENDENTE = "pendente"
    EM_IMPORTACAO = "em_importacao"
    EM_VALIDACAO = "em_validacao"
    COM_INCONSISTENCIAS = "com_inconsistencias"
    VALIDADO = "validado"


class Migracao(Base):
    """Uma execução de migração para uma organização (Seção 14/9) — o "MIGRACAO" da Seção 14."""

    __tablename__ = "migracao"

    id: Mapped[int] = mapped_column(primary_key=True)
    nr_org: Mapped[int] = mapped_column(ForeignKey("organizacao.nr_org"), index=True)
    tipo_migracao_id: Mapped[int] = mapped_column(ForeignKey("tipo_migracao.id"), index=True)
    operador: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default=MigracaoStatus.CRIADA.value)
    dt_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dt_conclusao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tipo_migracao = relationship("TipoMigracao")
    templates_status: Mapped[list["MigracaoTemplateStatus"]] = relationship(
        back_populates="migracao", cascade="all, delete-orphan"
    )
    eventos: Mapped[list["MigracaoEvento"]] = relationship(
        back_populates="migracao", cascade="all, delete-orphan", order_by="MigracaoEvento.dt_evento"
    )


class MigracaoTemplateStatus(Base):
    """Progresso de um template dentro de uma migração (Seção 14 — MIGRACAO_TEMPLATE_STATUS),
    incluindo os flags de aprovação por template (Fase 5 — não existe aprovação única para
    todos os templates de uma migração)."""

    __tablename__ = "migracao_template_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    migracao_id: Mapped[int] = mapped_column(ForeignKey("migracao.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"), index=True)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True)

    status: Mapped[str] = mapped_column(String(30), default=TemplateStatus.PENDENTE.value)
    arquivo_origem: Mapped[str | None] = mapped_column(String(300))
    hash_arquivo: Mapped[str | None] = mapped_column(String(64))
    total_linhas: Mapped[int] = mapped_column(Integer, default=0)
    linhas_processadas: Mapped[int] = mapped_column(Integer, default=0)
    pausado: Mapped[bool] = mapped_column(Boolean, default=False)
    teve_alerta: Mapped[bool] = mapped_column(Boolean, default=False)

    dados_aprovados: Mapped[bool] = mapped_column(Boolean, default=False)
    aprovado_dados_por: Mapped[str | None] = mapped_column(String(200))

    script_gerado: Mapped[bool] = mapped_column(Boolean, default=False)
    script_aprovado: Mapped[bool] = mapped_column(Boolean, default=False)
    aprovado_script_por: Mapped[str | None] = mapped_column(String(200))

    aplicado: Mapped[bool] = mapped_column(Boolean, default=False)
    aplicado_com_erro: Mapped[bool] = mapped_column(Boolean, default=False)

    dt_importacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    migracao: Mapped["Migracao"] = relationship(back_populates="templates_status")
    template = relationship("Template")


class MigracaoEvento(Base):
    """Trilha de eventos de uma migração (equivalente à `trilha` do protótipo) — um registro
    simples de linha do tempo; não é o motor de auditoria completo da Seção 12.4 (hash de
    arquivo, request/response de API etc.), que fica para uma fase futura."""

    __tablename__ = "migracao_evento"

    id: Mapped[int] = mapped_column(primary_key=True)
    migracao_id: Mapped[int] = mapped_column(ForeignKey("migracao.id"), index=True)
    evento: Mapped[str] = mapped_column(String(300))
    usuario: Mapped[str] = mapped_column(String(200))
    dt_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    migracao: Mapped["Migracao"] = relationship(back_populates="eventos")
