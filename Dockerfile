FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Camada de dependências separada do código: só reconstrói se pyproject.toml/uv.lock
# mudarem, não a cada alteração de código-fonte.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Roda as migrações (schema + seed do dicionário de dados) antes de subir o servidor —
# Railway injeta $PORT dinamicamente; --proxy-headers confia no X-Forwarded-Proto do edge
# TLS do Railway, necessário para o cookie de sessão "Secure" funcionar em produção.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
