from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente / arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # Banco de staging/controle da plataforma (PostgreSQL).
    database_url: str = "postgresql+asyncpg://migracao_app:changeme@localhost:5432/migracao_platform"

    # Identificador do usuário técnico de migração (Seção 13.3) — hoje hardcoded como
    # '000000099991' em todos os templates SQL das planilhas; aqui é configurável por
    # ambiente/organização, não mais fixo em código.
    usuario_tecnico_padrao: str = "000000099991"

    # Reservado para a camada de integração de destino (Oracle) — usado a partir da Fase 3+.
    oracle_dsn: str | None = None
    oracle_user: str | None = None
    oracle_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
