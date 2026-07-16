import asyncio
from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook

TIPO_AGENCIAS = "MIG_AGENCIAS_INDIVIDUAL"
TIPO_ONBOARDING = "MIG_INTEGRAL_ONBOARDING"


def _xlsx_agencias_com_n_linhas(n: int) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    for i in range(n):
        ws.append(["001", f"{i:04d}", f"Agência {i:04d}"])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def _criar_migracao(client: AsyncClient, nr_org: int, tipo_codigo: str) -> dict:
    response = await client.post(
        "/migracoes", json={"nr_org": nr_org, "tipo_migracao_codigo": tipo_codigo, "operador": "Operador Teste"}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_pausar_interrompe_processamento_e_continuar_retoma_ate_o_fim(
    client: AsyncClient, nr_org_teste: int
) -> None:
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_AGENCIAS)
    migracao_id = migracao["id"]

    total_linhas = 30
    upload = await client.post(
        f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/arquivo",
        files={
            "arquivo": (
                "agencias.xlsx",
                _xlsx_agencias_com_n_linhas(total_linhas),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        # atraso_lote_ms força uma janela larga e confiável entre lotes (30 linhas em lotes
        # de 3 = 10 chunks x 30ms = ao menos 300ms de processamento) — sem isso, o
        # processamento de um arquivo pequeno pode terminar rápido demais para o teste
        # conseguir pausar no meio. A espera abaixo (0.3s) também cobre o custo de abrir a
        # primeira conexão nova com o Postgres para a sessão da task em background, que por
        # si só já consome uma fração relevante desse tempo.
        data={"usuario": "Beatriz Nunes", "tamanho_lote": "3", "atraso_lote_ms": "30"},
    )
    assert upload.status_code == 202

    await asyncio.sleep(0.3)
    pausar = await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/pausar")
    assert pausar.status_code == 200

    await asyncio.sleep(0.1)  # garante que a task realmente parou (não só que o pedido foi aceito)
    status_pausado = (await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")).json()
    assert status_pausado["pausado"] is True
    assert 0 < status_pausado["linhas_processadas"] < total_linhas
    linhas_ao_pausar = status_pausado["linhas_processadas"]

    # confirma que realmente parou: espera mais um pouco e vê que não avançou sozinho.
    await asyncio.sleep(0.05)
    status_ainda_pausado = (await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")).json()
    assert status_ainda_pausado["linhas_processadas"] == linhas_ao_pausar

    continuar = await client.post(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS/continuar")
    assert continuar.status_code == 200
    assert continuar.json()["pausado"] is False

    for _ in range(100):
        status_final = (await client.get(f"/migracoes/{migracao_id}/templates/AGENCIAS_BANCARIAS")).json()
        if status_final["status"] == "validado":
            break
        await asyncio.sleep(0.02)
    else:
        raise AssertionError(f"Processamento não concluiu a tempo: {status_final}")

    assert status_final["linhas_processadas"] == total_linhas
    assert status_final["total_linhas"] == total_linhas


async def test_pausar_template_que_nao_esta_em_importacao_retorna_400(
    client: AsyncClient, nr_org_teste: int
) -> None:
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_AGENCIAS)
    response = await client.post(
        f"/migracoes/{migracao['id']}/templates/AGENCIAS_BANCARIAS/pausar"
    )
    assert response.status_code == 400


async def test_continuar_template_que_nao_esta_pausado_retorna_400(
    client: AsyncClient, nr_org_teste: int
) -> None:
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_AGENCIAS)
    response = await client.post(
        f"/migracoes/{migracao['id']}/templates/AGENCIAS_BANCARIAS/continuar"
    )
    assert response.status_code == 400


async def test_sequencia_travada_bloqueia_upload_fora_de_ordem(client: AsyncClient, nr_org_teste: int) -> None:
    """No tipo ONBOARDING, Vínculo depende de Agências/Estrutura/Ocupação/Escala (Seção
    26.3) — subir o arquivo de Vínculo antes desses quatro estarem validados deve falhar."""
    migracao = await _criar_migracao(client, nr_org_teste, TIPO_ONBOARDING)
    migracao_id = migracao["id"]

    response = await client.post(
        f"/migracoes/{migracao_id}/templates/VINCULO/arquivo",
        files={
            "arquivo": (
                "vinculo.xlsx",
                _xlsx_agencias_com_n_linhas(1),  # conteúdo irrelevante, a checagem é anterior à leitura
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"usuario": "Beatriz Nunes"},
    )
    assert response.status_code == 409
    assert "AGENCIAS_BANCARIAS" in response.text
