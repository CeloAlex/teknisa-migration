from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.usuario import Papel
from tests.conftest import login


async def _login_admin(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)


async def _apagar_usuario(email: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM usuario WHERE email = :email"), {"email": email})
        await session.commit()


async def test_operador_criado_pelo_admin_deve_trocar_senha_no_primeiro_acesso(
    client: AsyncClient, usuario_teste, nr_org_teste: int
) -> None:
    await _login_admin(client, usuario_teste)
    email = "operador.trocar.senha@example.com"

    try:
        criar = await client.post(
            "/portal-migration/admin/operadores/novo",
            data={
                "nome": "Operador Novo",
                "email": email,
                "papel": Papel.OPERADOR.value,
                "nr_org": nr_org_teste,
                "senha": "senha-definida-pelo-admin",
            },
            follow_redirects=False,
        )
        assert criar.status_code == 303

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as operador_client:
            await login(operador_client, email, "senha-definida-pelo-admin")

            bloqueado = await operador_client.get("/portal-migration/", follow_redirects=False)
            assert bloqueado.status_code == 303
            assert bloqueado.headers["location"] == "/portal-migration/trocar-senha"

            form = await operador_client.get("/portal-migration/trocar-senha")
            assert form.status_code == 200
            assert "Troca de senha obrigatória" in form.text

            senha_atual_errada = await operador_client.post(
                "/portal-migration/trocar-senha",
                data={
                    "senha_atual": "senha-errada",
                    "nova_senha": "senha-nova-do-operador",
                    "confirmar_senha": "senha-nova-do-operador",
                },
            )
            assert senha_atual_errada.status_code == 400
            assert "Senha atual incorreta" in senha_atual_errada.text

            trocar = await operador_client.post(
                "/portal-migration/trocar-senha",
                data={
                    "senha_atual": "senha-definida-pelo-admin",
                    "nova_senha": "senha-nova-do-operador",
                    "confirmar_senha": "senha-nova-do-operador",
                },
                follow_redirects=False,
            )
            assert trocar.status_code == 303
            assert trocar.headers["location"] == "/portal-migration/"

            liberado = await operador_client.get("/portal-migration/", follow_redirects=False)
            assert liberado.status_code == 200
    finally:
        await _apagar_usuario(email)
