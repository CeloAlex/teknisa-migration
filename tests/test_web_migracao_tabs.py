import asyncio
import random
from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.organizacao import Organizacao
from app.models.usuario import Papel
from tests.conftest import login

TIPO_AGENCIAS = "MIG_AGENCIAS_INDIVIDUAL"


def _xlsx_agencias(n: int) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    for i in range(n):
        ws.append(["001", f"{i:04d}", f"Agência {i:04d}"])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def test_fluxo_completo_pelas_8_abas_do_portal(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    """Caminho feliz completo — criar, subir arquivo, aprovar dados, gerar script, aprovar
    tecnicamente e aplicar — tudo via rotas do portal (não da API JSON), usando um
    Administrador (que tem todos os papéis liberados) para não misturar RBAC com o teste de
    fluxo em si (RBAC tem cobertura própria em test_auth.py)."""
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)

    criar = await client.post(
        "/portal-migration/migracoes/nova",
        data={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS},
        follow_redirects=False,
    )
    assert criar.status_code == 303
    migracao_url = criar.headers["location"]
    migracao_id = int(migracao_url.rstrip("/").split("/")[-1])

    for aba in [
        "templates",
        "validacao",
        "aprovacao_dados",
        "scripts",
        "aprovacao_tecnica",
        "execucao",
        "relatorio",
        "downloads",
    ]:
        resposta = await client.get(migracao_url, params={"aba": aba})
        assert resposta.status_code == 200, f"aba {aba} falhou: {resposta.text[:300]}"

    upload = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={
            "arquivo": (
                "agencias.xlsx",
                _xlsx_agencias(5),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=False,
    )
    assert upload.status_code == 303

    for _ in range(50):
        status = await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")
        if status.json()["status"] == "validado":
            break
        await asyncio.sleep(0.05)
    else:
        raise AssertionError("Processamento não concluiu a tempo")

    aprovar_dados = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", follow_redirects=False
    )
    assert aprovar_dados.status_code == 303
    tab_aprovacao = await client.get(migracao_url, params={"aba": "aprovacao_dados"})
    assert "Dados aprovados por" in tab_aprovacao.text

    gerar_script = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script",
        data={"operacao": "INCLUSAO"},
        follow_redirects=False,
    )
    assert gerar_script.status_code == 303
    tab_scripts = await client.get(migracao_url, params={"aba": "scripts"})
    assert "codebox" in tab_scripts.text

    aprovar_script = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", follow_redirects=False
    )
    assert aprovar_script.status_code == 303
    tab_tecnica = await client.get(migracao_url, params={"aba": "aprovacao_tecnica"})
    assert "aprovado tecnicamente por" in tab_tecnica.text

    aplicar = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar",
        data={"sucesso": "true"},
        follow_redirects=False,
    )
    assert aplicar.status_code == 303
    tab_execucao = await client.get(migracao_url, params={"aba": "execucao"})
    assert "Aplicado" in tab_execucao.text

    tab_relatorio = await client.get(migracao_url, params={"aba": "relatorio"})
    assert "concluída" in tab_relatorio.text

    tab_downloads = await client.get(migracao_url, params={"aba": "downloads"})
    assert "Baixar .sql" in tab_downloads.text


async def test_usuario_de_outra_organizacao_nao_acessa_migracao(
    client: AsyncClient, usuario_teste, nr_org_teste: int
) -> None:
    admin, senha_admin = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, admin.email, senha_admin)
    criar = await client.post(
        "/portal-migration/migracoes/nova",
        data={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS},
        follow_redirects=False,
    )
    migracao_url = criar.headers["location"]
    await client.post("/portal-migration/logout")

    outro_nr_org = random.randint(10_000_000, 99_999_999)
    async with AsyncSessionLocal() as session:
        session.add(Organizacao(nr_org=outro_nr_org, nome=f"Outra Organização {outro_nr_org}"))
        await session.commit()
    operador, senha_operador = await usuario_teste(Papel.OPERADOR.value, nr_org=outro_nr_org)
    await login(client, operador.email, senha_operador)

    resposta = await client.get(migracao_url)
    assert resposta.status_code == 403

    # Apaga o usuário desta organização antes da própria organização — o teardown da
    # fábrica `usuario_teste` só roda depois que a função de teste retornar, então não dá
    # para contar com ele para liberar a FK a tempo aqui dentro do corpo do teste.
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM usuario WHERE nr_org = :nr_org"), {"nr_org": outro_nr_org})
        await session.execute(text("DELETE FROM organizacao WHERE nr_org = :nr_org"), {"nr_org": outro_nr_org})
        await session.commit()
