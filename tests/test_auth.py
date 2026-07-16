from httpx import AsyncClient

from app.models.usuario import Papel
from tests.conftest import login


async def test_login_com_credenciais_corretas_funciona(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    resposta = await client.post("/portal-migration/login", data={"email": usuario.email, "senha": senha})
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/portal-migration/"


async def test_login_com_senha_errada_falha(client: AsyncClient, usuario_teste) -> None:
    usuario, _ = await usuario_teste(Papel.ADMINISTRADOR.value)
    resposta = await client.post("/portal-migration/login", data={"email": usuario.email, "senha": "senha-errada"})
    assert resposta.status_code == 401


async def test_logout_limpa_sessao(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)

    logout = await client.post("/portal-migration/logout")
    assert logout.status_code == 303

    resposta = await client.get("/portal-migration/", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/portal-migration/login"


async def test_rota_sem_login_redireciona_para_login(client: AsyncClient) -> None:
    resposta = await client.get("/portal-migration/", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/portal-migration/login"


async def test_rota_que_exige_papel_bloqueia_papel_diferente(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    """Segregação de função (Seção 12.1): aprovar-script exige Aprovador Técnico ou
    Administrador — um Operador não pode."""
    usuario, senha = await usuario_teste(Papel.OPERADOR.value, nr_org=nr_org_teste)
    await login(client, usuario.email, senha)

    resposta = await client.post(f"/portal-migration/migracoes/1/templates/QUALQUER/aprovar-script")
    assert resposta.status_code == 403


async def test_primeiro_acesso_redireciona_para_login_quando_ja_existe_usuario(
    client: AsyncClient, usuario_teste
) -> None:
    await usuario_teste(Papel.ADMINISTRADOR.value)
    resposta = await client.get("/portal-migration/primeiro-acesso", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/portal-migration/login"
