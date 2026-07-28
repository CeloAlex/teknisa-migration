from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.execution.engine import ErroComando, ResultadoExecucao
from app.models.migracao import MigracaoTemplateStatus
from app.models.staging import ExecucaoErro
from app.models.template import Template

TIPO_AGENCIAS = "MIG_AGENCIAS_INDIVIDUAL"


def _xlsx_agencias_valida() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    ws.append(["001", "0019", "Agência Sede"])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def _criar_migracao(client: AsyncClient, nr_org: int, tipo_codigo: str = TIPO_AGENCIAS, operador: str = "Operador Teste") -> dict:
    response = await client.post(
        "/migracoes", json={"nr_org": nr_org, "tipo_migracao_codigo": tipo_codigo, "operador": operador}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _mts_id(migracao_id: int, template_codigo: str) -> int:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(MigracaoTemplateStatus.id)
            .join(Template, Template.id == MigracaoTemplateStatus.template_id)
            .where(
                MigracaoTemplateStatus.migracao_id == migracao_id,
                Template.codigo == template_codigo,
            )
        )
        return (await session.execute(stmt)).scalar_one()


async def test_criar_migracao_com_organizacao_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.post(
        "/migracoes", json={"nr_org": 999_999_999, "tipo_migracao_codigo": TIPO_AGENCIAS, "operador": "X"}
    )
    assert response.status_code == 404


async def test_criar_migracao_com_tipo_inexistente_retorna_404(client: AsyncClient, nr_org_teste: int) -> None:
    response = await client.post(
        "/migracoes", json={"nr_org": nr_org_teste, "tipo_migracao_codigo": "NAO_EXISTE", "operador": "X"}
    )
    assert response.status_code == 404


async def test_criar_migracao_inicia_aguardando_arquivos_com_templates_pendentes(
    client: AsyncClient, nr_org_teste: int
) -> None:
    migracao = await _criar_migracao(client, nr_org_teste)
    assert migracao["status"] == "aguardando_arquivos"
    assert len(migracao["templates"]) == 1
    assert migracao["templates"][0]["template_codigo"] == "AGENCIAS_BANCARIAS"
    assert migracao["templates"][0]["status"] == "pendente"


async def test_bloqueia_segunda_migracao_ativa_para_mesma_organizacao(
    client: AsyncClient, nr_org_teste: int
) -> None:
    await _criar_migracao(client, nr_org_teste)
    response = await client.post(
        "/migracoes",
        json={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS, "operador": "Outro Operador"},
    )
    assert response.status_code == 409


async def test_ciclo_de_vida_completo_ate_concluida(client: AsyncClient, nr_org_teste: int, monkeypatch) -> None:
    async def _fake_executar_script(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(sucesso=True, comandos_executados=1)

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script)

    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    upload = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", _xlsx_agencias_valida(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    assert upload.status_code == 202

    # o processamento roda em uma task assíncrona própria — aguarda concluir.
    status = await _aguardar_status_template(client, migracao_id, "AGENCIAS_BANCARIAS", {"validado", "com_inconsistencias"})
    assert status["status"] == "validado"
    assert status["total_linhas"] == 1

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "aguardando_aprovacao"

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 200
    assert aprovar.json()["dados_aprovados"] is True

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "pronta_para_geracao_scripts"

    gerar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"}
    )
    assert gerar.status_code == 200
    assert gerar.json()["script_gerado"] is True

    script = await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/script")
    assert script.status_code == 200
    assert "INSERT INTO AGENCIA" in script.text

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "scripts_gerados"

    aprovar_script = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"}
    )
    assert aprovar_script.status_code == 200

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "aguardando_aplicacao"

    aplicar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego"}
    )
    assert aplicar.status_code == 200
    assert aplicar.json()["aplicado"] is True

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "concluida"
    assert detalhe["dt_conclusao"] is not None

    # organização liberada para uma nova migração ativa (Seção 4.1).
    nova = await client.post(
        "/migracoes",
        json={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS, "operador": "Beatriz Nunes"},
    )
    assert nova.status_code == 201


async def test_aplicar_com_falha_leva_a_com_erro_e_permite_reverter(
    client: AsyncClient, nr_org_teste: int, monkeypatch
) -> None:
    erros_simulados = [
        ErroComando(indice=1, comando="INSERT INTO X VALUES (1)", mensagem="violação de FK"),
        ErroComando(indice=3, comando="INSERT INTO X VALUES (3)", mensagem="ORA-01843: not a valid month"),
    ]

    async def _fake_executar_script(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(
            sucesso=False,
            comandos_executados=1,
            detalhe_erro="violação de FK",
            erros=erros_simulados,
        )

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script)

    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", _xlsx_agencias_valida(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    await _aguardar_status_template(client, migracao_id, "AGENCIAS_BANCARIAS", {"validado", "com_inconsistencias"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"})

    aplicar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego"}
    )
    assert aplicar.status_code == 200
    resposta_aplicar = aplicar.json()
    assert resposta_aplicar["aplicado_com_erro"] is True
    mts_id = await _mts_id(migracao_id, "AGENCIAS_BANCARIAS")

    async with AsyncSessionLocal() as session:
        persistidos = (
            await session.execute(
                select(ExecucaoErro)
                .where(ExecucaoErro.migracao_template_status_id == mts_id)
                .order_by(ExecucaoErro.indice_comando)
            )
        ).scalars().all()
    assert [e.indice_comando for e in persistidos] == [1, 3]
    assert persistidos[0].mensagem_erro == "violação de FK"
    assert persistidos[1].mensagem_erro == "ORA-01843: not a valid month"

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "com_erro"

    reverter = await client.post(f"/migracoes/{migracao_id}/reverter", json={"usuario": "Diego"})
    assert reverter.status_code == 200
    assert reverter.json()["status"] == "revertida"


async def test_aplicar_com_sucesso_limpa_log_de_erros_da_tentativa_anterior(
    client: AsyncClient, nr_org_teste: int, monkeypatch
) -> None:
    """Pedido do usuário: o log de erros reflete sempre a última execução, não um
    histórico acumulado — uma tentativa que corrige o problema não deve deixar lixo de
    tentativas anteriores na entidade de erros."""

    async def _fake_executar_script_falha(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(
            sucesso=False,
            comandos_executados=0,
            detalhe_erro="ORA-01843: not a valid month",
            erros=[ErroComando(indice=1, comando="INSERT INTO X VALUES (1)", mensagem="ORA-01843: not a valid month")],
        )

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script_falha)

    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", _xlsx_agencias_valida(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    await _aguardar_status_template(client, migracao_id, "AGENCIAS_BANCARIAS", {"validado", "com_inconsistencias"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"})

    aplicar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego"}
    )
    mts_id = await _mts_id(migracao_id, "AGENCIAS_BANCARIAS")

    async with AsyncSessionLocal() as session:
        persistidos = (
            await session.execute(
                select(ExecucaoErro).where(ExecucaoErro.migracao_template_status_id == mts_id)
            )
        ).scalars().all()
    assert len(persistidos) == 1

    async def _fake_executar_script_sucesso(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(sucesso=True, comandos_executados=1)

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script_sucesso)
    retry = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego"}
    )
    assert retry.status_code == 200
    assert retry.json()["aplicado"] is True

    async with AsyncSessionLocal() as session:
        restantes = (
            await session.execute(
                select(ExecucaoErro).where(ExecucaoErro.migracao_template_status_id == mts_id)
            )
        ).scalars().all()
    assert restantes == []


async def test_regerar_script_reseta_aprovacao_tecnica_ja_feita(client: AsyncClient, nr_org_teste: int) -> None:
    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", _xlsx_agencias_valida(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    await _aguardar_status_template(client, migracao_id, "AGENCIAS_BANCARIAS", {"validado", "com_inconsistencias"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"})
    aprovar_script = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"}
    )
    assert aprovar_script.json()["script_aprovado"] is True

    # regerar (ex.: com outro linhas_por_commit) invalida a aprovação técnica anterior —
    # o conteúdo mudou, precisa de revisão nova.
    regerar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script?linhas_por_commit=1",
        json={"usuario": "Carlos"},
    )
    assert regerar.status_code == 200
    assert regerar.json()["script_gerado"] is True
    assert regerar.json()["script_aprovado"] is False


async def test_gerar_script_apos_aplicado_e_bloqueado(client: AsyncClient, nr_org_teste: int, monkeypatch) -> None:
    async def _fake_executar_script(sql: str) -> ResultadoExecucao:
        return ResultadoExecucao(sucesso=True, comandos_executados=1)

    monkeypatch.setattr("app.migracoes.acoes.executar_script", _fake_executar_script)

    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", _xlsx_agencias_valida(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    await _aguardar_status_template(client, migracao_id, "AGENCIAS_BANCARIAS", {"validado", "com_inconsistencias"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"})
    aplicar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego"}
    )
    assert aplicar.json()["aplicado"] is True

    regerar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"}
    )
    assert regerar.status_code == 409


async def test_cancelar_migracao_libera_organizacao(client: AsyncClient, nr_org_teste: int) -> None:
    migracao = await _criar_migracao(client, nr_org_teste)
    cancelar = await client.post(f"/migracoes/{migracao['id']}/cancelar", json={"usuario": "Fernanda"})
    assert cancelar.status_code == 200
    assert cancelar.json()["status"] == "cancelada"

    nova = await client.post(
        "/migracoes",
        json={"nr_org": nr_org_teste, "tipo_migracao_codigo": TIPO_AGENCIAS, "operador": "Fernanda"},
    )
    assert nova.status_code == 201


async def _aguardar_status_template(
    client: AsyncClient, migracao_id: int, template_codigo: str, status_esperados: set[str], tentativas: int = 50
) -> dict:
    import asyncio

    for _ in range(tentativas):
        resposta = await client.get(f"/migracoes/{migracao_id}/templates/{template_codigo}")
        corpo = resposta.json()
        if corpo["status"] in status_esperados:
            return corpo
        await asyncio.sleep(0.02)
    raise AssertionError(f"Template não atingiu {status_esperados} a tempo — status atual: {corpo['status']}")
