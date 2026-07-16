import random

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.organizacao import Organizacao


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def nr_org_teste() -> int:
    """Organização descartável, com número aleatório — evita que testes de concorrência
    (bloqueio de migração ativa por organização) fiquem acoplados a estado deixado por
    execuções anteriores da suíte, já que o banco de testes não é resetado entre execuções."""
    nr_org = random.randint(10_000_000, 99_999_999)
    async with AsyncSessionLocal() as session:
        session.add(Organizacao(nr_org=nr_org, nome=f"Organização de Teste {nr_org}"))
        await session.commit()
    return nr_org
