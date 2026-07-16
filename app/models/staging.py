from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class StagingBruto(Base):
    """Dado bruto, exatamente como veio do arquivo, sem qualquer transformação (Seção 14/16
    requisito 5) — uma linha por registro, chave por letra de coluna. `processado` marca se
    já passou pela Transformation Engine (usado para resumir o processamento em chunks após
    uma pausa: a próxima leva de trabalho são as linhas com `processado = false`)."""

    __tablename__ = "staging_bruto"

    id: Mapped[int] = mapped_column(primary_key=True)
    migracao_template_status_id: Mapped[int] = mapped_column(
        ForeignKey("migracao_template_status.id", ondelete="CASCADE"), index=True
    )
    linha: Mapped[int] = mapped_column(Integer)
    dados_json: Mapped[dict] = mapped_column(JSONB)
    processado: Mapped[bool] = mapped_column(Boolean, default=False)

    normalizado: Mapped["StagingNormalizado | None"] = relationship(
        back_populates="staging_bruto", cascade="all, delete-orphan", uselist=False
    )


class StagingNormalizado(Base):
    """Dado após a Transformation Engine (Seção 14) — os `campo: valor` já convertidos,
    prontos para validação e, mais tarde, para virar marcador substituído no script."""

    __tablename__ = "staging_normalizado"

    id: Mapped[int] = mapped_column(primary_key=True)
    staging_bruto_id: Mapped[int] = mapped_column(
        ForeignKey("staging_bruto.id", ondelete="CASCADE"), unique=True, index=True
    )
    dados_json: Mapped[dict] = mapped_column(JSONB)
    dt_processamento: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    staging_bruto: Mapped["StagingBruto"] = relationship(back_populates="normalizado")
    validacoes: Mapped[list["ValidacaoResultado"]] = relationship(
        back_populates="staging_normalizado", cascade="all, delete-orphan"
    )


class ValidacaoResultado(Base):
    """Um resultado de validação persistido (Seção 14/23) — mesma classificação do Validation
    Engine em memória (Fase 2+), agora durável entre a importação e a aprovação."""

    __tablename__ = "validacao_resultado"

    id: Mapped[int] = mapped_column(primary_key=True)
    staging_normalizado_id: Mapped[int] = mapped_column(
        ForeignKey("staging_normalizado.id", ondelete="CASCADE"), index=True
    )
    campo: Mapped[str] = mapped_column(String(100))
    regra: Mapped[str] = mapped_column(String(100))
    classificacao: Mapped[str] = mapped_column(String(30))
    valor_recebido: Mapped[str] = mapped_column(Text)
    valor_esperado: Mapped[str] = mapped_column(Text)
    mensagem: Mapped[str] = mapped_column(Text)

    staging_normalizado: Mapped["StagingNormalizado"] = relationship(back_populates="validacoes")


class ScriptGerado(Base):
    """Script gerado e persistido para um template dentro de uma migração (Seção 14) — a
    versão "stateful" do que a Fase 2-4 devolvia direto na resposta HTTP."""

    __tablename__ = "script_gerado"

    id: Mapped[int] = mapped_column(primary_key=True)
    migracao_template_status_id: Mapped[int] = mapped_column(
        ForeignKey("migracao_template_status.id", ondelete="CASCADE"), index=True
    )
    operacao: Mapped[str] = mapped_column(String(20))
    conteudo_sql: Mapped[str] = mapped_column(Text)
    dt_geracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
