from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook

TEMPLATE_CODIGO = "AGENCIAS_BANCARIAS"


def _xlsx_agencias() -> bytes:
    """Monta um XLSX em memória no mesmo layout do arquivo real
    (docs/planilhas-originais/00_Agencias_Bancarias.xlsx): aba única, cabeçalho na linha 1,
    dados a partir da linha 2, colunas A=Banco, B=Cd. Agência, C=Agência.

    Linha 2: válida.
    Linha 3: CDBANCO vazio -> erro impeditivo (obrigatoriedade).
    Linha 4: CDBANCO com 5 dígitos (> tamanho_maximo=3) -> alerta, mas válida.
    Linha 5: totalmente vazia -> ignorada pelo adapter de ingestão.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    ws.append(["001", "0019", "Agência Sede"])
    ws.append(["", "0051", "Agência Norte"])
    ws.append(["12345", "0125", "Agência Sul"])
    ws.append(["", "", ""])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def test_obter_dicionario_de_dados(client: AsyncClient) -> None:
    response = await client.get(f"/templates/{TEMPLATE_CODIGO}")
    assert response.status_code == 200
    body = response.json()
    assert body["codigo"] == TEMPLATE_CODIGO
    assert body["sheet_name"] == "Sheet1"
    assert body["data_start_row"] == 2
    campos_por_nome = {c["campo"]: c for c in body["campos"]}
    assert campos_por_nome["CDBANCO"]["obrigatorio"] is True
    assert campos_por_nome["CDBANCO"]["tamanho_maximo"] == 3
    assert campos_por_nome["NRORG"]["origem"] == "parametro_execucao.NRORG"


async def test_template_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.get("/templates/NAO_EXISTE")
    assert response.status_code == 404


async def test_preview_classifica_linhas_corretamente(client: AsyncClient) -> None:
    arquivo = _xlsx_agencias()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/preview",
        files={"arquivo": ("00_Agencias_Bancarias.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "1410"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_linhas"] == 3  # a linha totalmente vazia não é lida
    assert body["validos"] == 2
    assert body["rejeitados"] == 1
    assert body["alertas"] == 1

    linha_rejeitada = next(l for l in body["linhas"] if l["linha"] == 3)
    assert any(v["regra"] == "obrigatoriedade" and v["campo"] == "CDBANCO" for v in linha_rejeitada["validacoes"])

    linha_com_alerta = next(l for l in body["linhas"] if l["linha"] == 4)
    assert any(v["regra"] == "tamanho_maximo" and v["classificacao"] == "alerta" for v in linha_com_alerta["validacoes"])

    linha_valida = next(l for l in body["linhas"] if l["linha"] == 2)
    assert linha_valida["validacoes"] == []
    assert linha_valida["campos"]["NRORG"] == 1410


async def test_gerar_script_inclui_apenas_linhas_validas(client: AsyncClient) -> None:
    arquivo = _xlsx_agencias()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/gerar-script",
        files={"arquivo": ("00_Agencias_Bancarias.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "1410"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/sql")
    assert "attachment" in response.headers["content-disposition"]

    sql = response.text
    assert sql.count("INSERT INTO AGENCIA") == 2
    assert "'001', '0019', 'Agência Sede'" in sql
    assert "'12345', '0125', 'Agência Sul'" in sql
    assert "Agência Norte" not in sql  # linha rejeitada não entra no script
    assert "1410" in sql
    assert "'000000099991'" in sql
    assert sql.strip().endswith("COMMIT;")


async def test_gerar_script_sem_linhas_validas_retorna_422(client: AsyncClient) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["Banco", "Cd. Agência", "Agência"])
    ws.append(["", "", "Sem banco nem agência"])
    buffer = BytesIO()
    wb.save(buffer)

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/gerar-script",
        files={"arquivo": ("vazio.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "1410"},
    )

    assert response.status_code == 422
