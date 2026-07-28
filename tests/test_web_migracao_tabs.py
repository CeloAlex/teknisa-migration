import asyncio
import random
from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.execution.engine import ErroComando, ResultadoExecucao
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


async def test_fluxo_completo_pelas_8_abas_do_portal(
    client: AsyncClient, usuario_teste, nr_org_teste: int, monkeypatch
) -> None:
    """Caminho feliz completo — criar, subir arquivo, aprovar dados, gerar script, aprovar
    tecnicamente e aplicar — tudo via rotas do portal (não da API JSON), usando um
    Administrador (que tem todos os papéis liberados) para não misturar RBAC com o teste de
    fluxo em si (RBAC tem cobertura própria em test_auth.py)."""

    async def _fake_executar_script(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(sucesso=True, comandos_executados=1)

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script)

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
        follow_redirects=False,
    )
    assert aplicar.status_code == 303
    tab_execucao = await client.get(migracao_url, params={"aba": "execucao"})
    assert "Aplicado" in tab_execucao.text

    tab_relatorio = await client.get(migracao_url, params={"aba": "relatorio"})
    assert "concluída" in tab_relatorio.text

    tab_downloads = await client.get(migracao_url, params={"aba": "downloads"})
    assert "Baixar .sql" in tab_downloads.text


async def test_falha_ao_aplicar_mostra_erro_na_aba_execucao_e_permite_tentar_de_novo(
    client: AsyncClient, usuario_teste, nr_org_teste: int, monkeypatch
) -> None:
    """Reproduz o caso relatado: erro real do Oracle (ex.: ORA-00001 unique constraint)
    precisa aparecer na própria aba Execução, não só na Trilha completa — e o operador
    precisa conseguir tentar de novo sem sair da tela."""
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)

    criar = await client.post(
        "/portal-migration/migracoes/nova",
        data={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS},
        follow_redirects=False,
    )
    migracao_url = criar.headers["location"]
    migracao_id = int(migracao_url.rstrip("/").split("/")[-1])

    await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={
            "arquivo": (
                "agencias.xlsx", _xlsx_agencias(1),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=False,
    )
    for _ in range(50):
        status = await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")
        if status.json()["status"] == "validado":
            break
        await asyncio.sleep(0.05)
    else:
        raise AssertionError("Processamento não concluiu a tempo")

    await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados",
        follow_redirects=False,
    )
    await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script",
        data={"operacao": "INCLUSAO"}, follow_redirects=False,
    )
    await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script",
        follow_redirects=False,
    )

    mensagem_oracle = "ORA-00001: unique constraint (FOLHA.PK_AGENCIA) violated"

    async def _fake_falha(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(
            sucesso=False,
            comandos_executados=0,
            detalhe_erro=mensagem_oracle,
            erros=[ErroComando(indice=1, comando="INSERT INTO GPE_AGENCIA VALUES (...)", mensagem=mensagem_oracle)],
        )

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_falha)
    aplicar_falha = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar",
        follow_redirects=False,
    )
    assert aplicar_falha.status_code == 303

    tab_execucao = await client.get(migracao_url, params={"aba": "execucao"})
    assert mensagem_oracle in tab_execucao.text
    assert "Tentar novamente" in tab_execucao.text
    assert "não são desfeitos" in tab_execucao.text
    assert "Baixar log" in tab_execucao.text
    assert f"/migracoes/{migracao_id}/erros-execucao.xlsx" in tab_execucao.text

    log_xlsx = await client.get(f"/migracoes/{migracao_id}/erros-execucao.xlsx")
    assert log_xlsx.status_code == 200
    assert log_xlsx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    async def _fake_sucesso(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(sucesso=True, comandos_executados=1)

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_sucesso)
    aplicar_retry = await client.post(
        f"/portal-migration/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar",
        follow_redirects=False,
    )
    assert aplicar_retry.status_code == 303

    # a mensagem de erro continua na trilha completa (histórico, correto ficar lá), mas o
    # card de execução do template não mostra mais o banner de falha nem "Tentar novamente"
    # — só o card correspondente ao AGENCIAS_BANCARIAS deixou de ter aplicado_com_erro.
    tab_execucao_ok = await client.get(migracao_url, params={"aba": "execucao"})
    assert "Tentar novamente" not in tab_execucao_ok.text
    assert "Aplicado (1 comando" in tab_execucao_ok.text


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
