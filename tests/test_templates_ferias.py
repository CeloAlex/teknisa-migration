from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from openpyxl.utils import column_index_from_string

TEMPLATE_CODIGO = "FERIAS"

LINHA_COM_GOZO = {
    "A": "V001", "B": "01/01/2020", "C": "31/12/2020", "E": "GOZADO_INTEGRAL",
    "G": "01/06/2021", "H": "20/06/2021", "I": "21/06/2021", "J": "5", "K": "0",
}
LINHA_SEM_GOZO = {
    "A": "V002", "B": "01/02/2020", "C": "31/01/2021", "E": "PENDENTE",
}


def _escrever_linha(ws, linha_num: int, valores: dict) -> None:
    for col_letra, valor in valores.items():
        ws.cell(row=linha_num, column=column_index_from_string(col_letra), value=valor)


def _xlsx_ferias() -> bytes:
    """Monta um XLSX no layout real (aba Dados, cabeçalho na linha 2, dados a partir da
    linha 3): uma linha com período de gozo preenchido (dispara o bloco condicional de
    FPA_GOZOFERIAS) e uma linha só com o período aquisitivo."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    _escrever_linha(ws, 3, LINHA_COM_GOZO)
    _escrever_linha(ws, 4, LINHA_SEM_GOZO)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def test_preview_ferias_calcula_flag_de_gozo_por_linha(client: AsyncClient) -> None:
    arquivo = _xlsx_ferias()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/preview",
        files={"arquivo": ("ferias.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "1456"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_linhas"] == 2
    assert body["validos"] == 2

    linha1, linha2 = body["linhas"]
    assert linha1["campos"]["_TEM_GOZO"] is True
    assert linha2["campos"]["_TEM_GOZO"] is False


async def test_gerar_script_ferias_gera_gozo_apenas_quando_preenchido(client: AsyncClient) -> None:
    arquivo = _xlsx_ferias()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/gerar-script",
        files={"arquivo": ("ferias.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "1456"},
    )

    assert response.status_code == 200
    sql = response.text

    # As duas linhas sempre geram o período aquisitivo (bloco 1, incondicional).
    assert sql.count("INSERT INTO FPA_FERIAS (") == 2
    # Só a primeira linha (com data de início de gozo) gera o bloco condicional.
    assert sql.count("INSERT INTO FPA_GOZOFERIAS (") == 1
    assert "'01/06/2021'" in sql
    assert sql.strip().endswith("COMMIT;")
