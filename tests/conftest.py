import random
from typing import Callable, Coroutine

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.security import hash_senha
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.organizacao import Organizacao
from app.models.usuario import Usuario


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def nr_org_teste() -> int:
    """Organização descartável, com número aleatório — evita que testes de concorrência
    (bloqueio de migração ativa por organização) fiquem acoplados a estado deixado por
    execuções anteriores da suíte. Ao final do teste, apaga a própria organização e tudo
    que ficou pendurado nela (usuários, migrações e suas dependências) — o banco de testes
    não é resetado entre execuções, então sem essa limpeza o volume só cresce."""
    nr_org = random.randint(10_000_000, 99_999_999)
    async with AsyncSessionLocal() as session:
        session.add(Organizacao(nr_org=nr_org, nome=f"Organização de Teste {nr_org}"))
        await session.commit()

    yield nr_org

    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM usuario WHERE nr_org = :nr_org"), {"nr_org": nr_org})
        await session.execute(
            text(
                "DELETE FROM migracao_template_status WHERE migracao_id IN "
                "(SELECT id FROM migracao WHERE nr_org = :nr_org)"
            ),
            {"nr_org": nr_org},
        )
        await session.execute(
            text("DELETE FROM migracao_evento WHERE migracao_id IN (SELECT id FROM migracao WHERE nr_org = :nr_org)"),
            {"nr_org": nr_org},
        )
        await session.execute(text("DELETE FROM migracao WHERE nr_org = :nr_org"), {"nr_org": nr_org})
        await session.execute(text("DELETE FROM organizacao WHERE nr_org = :nr_org"), {"nr_org": nr_org})
        await session.commit()


SENHA_PADRAO_TESTE = "senha-teste-123"


@pytest.fixture
async def usuario_teste() -> Callable[..., Coroutine[None, None, tuple[Usuario, str]]]:
    """Fábrica de usuário do portal descartável, com e-mail aleatório. Ao final do teste,
    apaga todos os usuários criados por essa fábrica — mesmo motivo do `nr_org_teste`
    (efeito colateral independente: cobre usuários criados sem organização, ou cujo
    `nr_org` não veio de `nr_org_teste`)."""
    criados: list[int] = []

    async def _criar(papel: str, nr_org: int | None = None, senha: str = SENHA_PADRAO_TESTE) -> tuple[Usuario, str]:
        sufixo = random.randint(1_000_000, 9_999_999)
        async with AsyncSessionLocal() as session:
            usuario = Usuario(
                nome=f"Usuário Teste {sufixo}",
                email=f"teste{sufixo}@example.com",
                papel=papel,
                nr_org=nr_org,
                senha_hash=hash_senha(senha),
            )
            session.add(usuario)
            await session.commit()
            await session.refresh(usuario)
        criados.append(usuario.id)
        return usuario, senha

    yield _criar

    if criados:
        async with AsyncSessionLocal() as session:
            for usuario_id in criados:
                await session.execute(text("DELETE FROM usuario WHERE id = :id"), {"id": usuario_id})
            await session.commit()


async def login(client: AsyncClient, email: str, senha: str) -> None:
    resposta = await client.post("/portal-migration/login", data={"email": email, "senha": senha})
    assert resposta.status_code == 303, resposta.text
