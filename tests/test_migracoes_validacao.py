import asyncio
from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook

TIPO_AGENCIAS = "MIG_AGENCIAS_INDIVIDUAL"


def _xlsx(linhas: list[tuple[str, str, str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    for linha in linhas:
        ws.append(list(linha))
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def _criar_migracao(client: AsyncClient, nr_org: int) -> dict:
    response = await client.post(
        "/migracoes", json={"nr_org": nr_org, "tipo_migracao_codigo": TIPO_AGENCIAS, "operador": "Operador Teste"}
    )
    assert response.status_code == 201
    return response.json()


async def _upload_e_aguardar(client: AsyncClient, migracao_id: int, conteudo: bytes, status_esperados: set[str]) -> dict:
    upload = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={"arquivo": ("agencias.xlsx", conteudo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"usuario": "Beatriz Nunes"},
    )
    assert upload.status_code == 202
    for _ in range(100):
        resposta = (await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")).json()
        if resposta["status"] in status_esperados:
            return resposta
        await asyncio.sleep(0.02)
    raise AssertionError(f"Status não atingiu {status_esperados}: {resposta}")


async def test_erro_impeditivo_bloqueia_aprovacao_e_migracao_fica_aguardando_correcao(
    client: AsyncClient, nr_org_teste: int
) -> None:
    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    conteudo = _xlsx([("001", "0019", "Agência Válida"), ("", "0020", "Agência Sem Banco")])
    status = await _upload_e_aguardar(client, migracao_id, conteudo, {"validado", "com_inconsistencias"})
    assert status["status"] == "com_inconsistencias"

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "aguardando_correcao"

    aprovar = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"}
    )
    assert aprovar.status_code == 400

    validacoes = await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/validacoes")
    assert validacoes.status_code == 200
    erros = [v for v in validacoes.json() if v["classificacao"] == "erro_impeditivo"]
    assert len(erros) == 1
    assert erros[0]["campo"] == "CDBANCO"
    assert erros[0]["linha"] == 3

    # reenvio corrigido (Seção 8 — reprocessamento) substitui o staging anterior.
    conteudo_corrigido = _xlsx([("001", "0019", "Agência Válida")])
    status_corrigido = await _upload_e_aguardar(client, migracao_id, conteudo_corrigido, {"validado", "com_inconsistencias"})
    assert status_corrigido["status"] == "validado"
    assert status_corrigido["total_linhas"] == 1

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "aguardando_aprovacao"


async def test_alerta_nao_bloqueia_e_migracao_conclui_com_alertas(client: AsyncClient, nr_org_teste: int) -> None:
    migracao = await _criar_migracao(client, nr_org_teste)
    migracao_id = migracao["id"]

    # CDBANCO com 4 dígitos excede o tamanho_maximo=3 -> alerta, não erro.
    conteudo = _xlsx([("0011", "0019", "Agência Com Alerta")])
    status = await _upload_e_aguardar(client, migracao_id, conteudo, {"validado", "com_inconsistencias"})
    assert status["status"] == "validado"
    assert status["teve_alerta"] is True

    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-dados", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/gerar-script", json={"usuario": "Carlos"})
    await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aprovar-script", json={"usuario": "Ana"})
    await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/aplicar", json={"usuario": "Diego", "sucesso": True}
    )

    detalhe = (await client.get(f"/migracoes/{migracao_id}")).json()
    assert detalhe["status"] == "concluida_com_alertas"
