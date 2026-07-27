import oracledb

from app.core.config import get_settings


class OracleNaoConfigurado(Exception):
    """ORACLE_DSN/ORACLE_USER/ORACLE_PASSWORD não configurados neste ambiente (.env)."""


async def conectar() -> oracledb.AsyncConnection:
    """Abre uma conexão com o Oracle de destino (thin mode — sem Instant Client), usando as
    credenciais de `Settings`. Chamado a cada execução em vez de manter um pool: a
    Execution Engine roda em lotes esporádicos (por template aprovado), não em alta
    frequência, e uma conexão nova por lote evita lidar com conexões obsoletas."""
    settings = get_settings()
    if not settings.oracle_dsn or not settings.oracle_user or not settings.oracle_password:
        raise OracleNaoConfigurado(
            "Conexão com o Oracle de destino não configurada — preencha ORACLE_DSN, "
            "ORACLE_USER e ORACLE_PASSWORD no .env."
        )
    return await oracledb.connect_async(
        dsn=settings.oracle_dsn, user=settings.oracle_user, password=settings.oracle_password
    )
