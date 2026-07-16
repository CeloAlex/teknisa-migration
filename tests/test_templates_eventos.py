from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from openpyxl.utils import column_index_from_string

TEMPLATE_CODIGO = "EVENTOS"

LINHA_EVENTO_NOVO = {
    "A": "01/01/2000", "B": "PROVENTO", "C": "01/01/2000",
    "D": "Novo Evento Teste", "E": "", "F": "999",
}
LINHA_EVENTO_EXISTENTE = {
    "A": "01/01/2000", "B": "DESCONTO", "C": "01/01/2000",
    "D": "Evento Existente", "E": "50", "F": "998",
}


def _escrever_linha(ws, linha_num: int, valores: dict) -> None:
    for col_letra, valor in valores.items():
        ws.cell(row=linha_num, column=column_index_from_string(col_letra), value=valor)


def _xlsx_eventos() -> bytes:
    """Monta um XLSX no layout real (aba Dados, cabeçalho na linha 2, dados a partir da
    linha 3): uma linha de evento novo (Nr Evento Pebbian vazio, dispara o bloco de
    FPA_EVENTOM/H) e uma linha de evento já existente (só gera o de-para)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    _escrever_linha(ws, 3, LINHA_EVENTO_NOVO)
    _escrever_linha(ws, 4, LINHA_EVENTO_EXISTENTE)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def test_obter_template_eventos_marca_como_catalogo(client: AsyncClient) -> None:
    response = await client.get(f"/templates/{TEMPLATE_CODIGO}")
    assert response.status_code == 200
    assert response.json()["eh_catalogo"] is True


async def test_preview_eventos_calcula_flag_de_evento_novo_por_linha(client: AsyncClient) -> None:
    arquivo = _xlsx_eventos()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/preview",
        files={"arquivo": ("eventos.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "4385"},
    )

    assert response.status_code == 200
    body = response.json()
    linha1, linha2 = body["linhas"]
    assert linha1["campos"]["_EVENTO_NOVO"] is True
    assert linha2["campos"]["_EVENTO_NOVO"] is False


async def test_gerar_script_eventos_so_cria_evento_quando_novo(client: AsyncClient) -> None:
    arquivo = _xlsx_eventos()

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/gerar-script",
        files={"arquivo": ("eventos.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "4385"},
    )

    assert response.status_code == 200
    sql = response.text

    # Só a linha com "Nr Evento Pebbian" vazio dispara a criação do evento.
    assert sql.count("INSERT INTO FPA_EVENTOM (") == 1
    assert sql.count("INSERT INTO FPA_EVENTOH (") == 1
    # O de-para é sempre gerado, para as duas linhas.
    assert sql.count("INSERT INTO MIG_MIGRAMDEPARA (") == 2
    assert "Novo Evento Teste" in sql
    assert sql.strip().endswith("COMMIT;")
