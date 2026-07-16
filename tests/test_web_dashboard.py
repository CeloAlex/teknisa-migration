from httpx import AsyncClient

from app.models.usuario import Papel
from tests.conftest import login

TIPO_AGENCIAS = "MIG_AGENCIAS_INDIVIDUAL"


async def test_dashboard_renderiza_para_usuario_logado(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)

    resposta = await client.get("/portal/")
    assert resposta.status_code == 200
    assert "Painel de Migrações" in resposta.text
    assert "Nova migração" in resposta.text


async def test_dashboard_filtro_por_status_nao_quebra(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)

    resposta = await client.get("/portal/", params={"status": "criada", "incluir_concluidas": "true"})
    assert resposta.status_code == 200


async def test_criar_migracao_via_portal(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    usuario, senha = await usuario_teste(Papel.OPERADOR.value, nr_org=nr_org_teste)
    await login(client, usuario.email, senha)

    form = await client.get("/portal/migracoes/nova")
    assert form.status_code == 200
    assert str(nr_org_teste) in form.text

    criar = await client.post(
        "/portal/migracoes/nova",
        data={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS},
        follow_redirects=False,
    )
    assert criar.status_code == 303
    assert criar.headers["location"].startswith("/portal/migracoes/")

    detalhe = await client.get(criar.headers["location"])
    assert detalhe.status_code == 200
    assert usuario.nome in detalhe.text


async def test_auditor_nao_pode_abrir_form_de_nova_migracao(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    usuario, senha = await usuario_teste(Papel.AUDITOR.value)
    await login(client, usuario.email, senha)

    resposta = await client.get("/portal/migracoes/nova")
    assert resposta.status_code == 403
