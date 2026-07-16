import random
from io import BytesIO

from httpx import AsyncClient
from openpyxl import Workbook
from openpyxl.utils import column_index_from_string

TEMPLATE_CODIGO = "VINCULO"

# Linha completa: dispara todos os blocos condicionais (conta corrente, telefone
# principal/celular, e-mail, endereço, estrutura legal/gerencial/sindical).
LINHA_COMPLETA = {
    "A": "01/03/2020", "B": "", "C": "V100", "E": "ESC01", "G": "S",
    "H": "Denise da Cunha Nascimento", "I": "SOLTEIRO", "J": "933.137.642-15",
    "K": "1234567", "L": "0021", "M": "SP", "N": "01/01/2010", "O": "12034567890",
    "P": "01/01/2010", "Q": "53.786.86-x", "R": "SSP", "S": "SP", "T": "01/02/2010",
    "U": "123456789012", "V": "0010", "W": "0055", "X": "12345678900", "Y": "01/01/2030",
    "Z": "AB", "AA": "12345678901234567890EXTRA", "AB": "1", "AC": "1", "AD": "BR",
    "AE": "SP", "AF": "São Paulo", "AG": "29/05/1990", "AH": "F", "AI": "1",
    "AJ": "341", "AK": "1234-5", "AL": "98765-4", "AM": "1", "AN": "10",
    "AO": "1", "AP": "MATRIZ", "AQ": "GERDIR", "AR": "1058", "AS": "SP",
    "AT": "São Paulo", "AU": "Avenida Paulista", "AV": "Avenida Paulista",
    "AW": "1000", "AX": "Bela Vista", "AY": "Ap 10", "AZ": "01310-100",
    "BA": "1", "BB": "1", "BC": "01/01/2020", "BD": "", "BE": "01/03/2020",
    "BF": "OCUP01", "BG": "N", "BH": "1", "BI": "", "BJ": "",
    "BK": "", "BM": "", "BN": "1", "BO": "1", "BP": "01/03/2020",
    "BQ": "2", "BR": "1", "BS": "1", "BT": "3", "BU": "SIND01",
    "BV": "90", "BW": "0", "BX": "01/02/2020", "BY": "",
    "CC": "1", "CD": "33334444", "CE": "denise@teste.com", "CI": "011", "CJ": "011",
    "CK": "988887777",
}

# Linha mínima: só os campos obrigatórios preenchidos — nenhum bloco condicional deve
# disparar (sem conta corrente, sem telefones, sem e-mail, sem endereço, sem estruturas).
LINHA_MINIMA = {
    "A": "01/03/2020", "C": "V101", "H": "Fulano de Tal", "J": "111.222.333-44",
}


def _escrever_linha(ws, linha_num: int, valores: dict) -> None:
    for col_letra, valor in valores.items():
        ws.cell(row=linha_num, column=column_index_from_string(col_letra), value=valor)


def _xlsx_vinculo() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    _escrever_linha(ws, 3, LINHA_COMPLETA)
    _escrever_linha(ws, 4, LINHA_MINIMA)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def test_vinculo_expoe_dicionario_completo(client: AsyncClient) -> None:
    response = await client.get(f"/templates/{TEMPLATE_CODIGO}")
    assert response.status_code == 200
    campos = {c["campo"] for c in response.json()["campos"]}
    # Amostra representativa: diretos, derivados e gerados — não a lista inteira (evita
    # um teste frágil a qualquer ajuste fino de rótulo/ordem).
    assert {
        "DTADMISSAO", "CDMATRICULA", "NOMEVINC", "CPF", "CTPS",
        "NRSITUFUNCM", "DTINISITUFUNC", "_TEM_CONTA", "_TEM_ENDERECO",
        "_TEM_ESTRUTLEGAL", "_TEM_ESTRUTGEREN", "_TEM_ESTRUTSIND",
        "NRVINCULOM", "NRVINCULOH", "NRPESSOA", "NRPESSOAH",
        "NRCOMUNICAPARC", "NRCOMUNICAPARC2", "NRCOMUNICAPARC3",
    } <= campos


async def test_vinculo_preview_duas_linhas_validas(client: AsyncClient) -> None:
    arquivo = _xlsx_vinculo()
    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/preview",
        files={"arquivo": ("vinculo.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": "3260"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_linhas"] == 2
    assert body["validos"] == 2
    assert body["rejeitados"] == 0

    linha1, linha2 = body["linhas"]
    assert linha1["campos"]["CPF"] == "93313764215"
    assert linha1["campos"]["_TEM_CONTA"] is True
    assert linha1["campos"]["_TEM_ENDERECO"] is True
    assert linha1["campos"]["_TEM_ESTRUTLEGAL"] is True
    assert linha1["campos"]["_TEM_ESTRUTGEREN"] is True
    assert linha1["campos"]["_TEM_ESTRUTSIND"] is True
    # sem data de rescisão -> situação funcional 1 (Decisão 3 do usuário)
    assert linha1["campos"]["NRSITUFUNCM"] == "1"

    assert linha2["campos"]["_TEM_CONTA"] is False
    assert linha2["campos"]["_TEM_TELPRI"] is False
    assert linha2["campos"]["_TEM_TELCEL"] is False
    assert linha2["campos"]["_TEM_EMAIL"] is False
    assert linha2["campos"]["_TEM_ENDERECO"] is False
    assert linha2["campos"]["_TEM_ESTRUTLEGAL"] is False
    assert linha2["campos"]["_TEM_ESTRUTGEREN"] is False
    assert linha2["campos"]["_TEM_ESTRUTSIND"] is False


async def test_vinculo_gerar_script_blocos_sempre_gerados_e_condicionais(client: AsyncClient) -> None:
    arquivo = _xlsx_vinculo()
    nr_org = random.randint(1_000_000, 9_999_999)

    response = await client.post(
        f"/templates/{TEMPLATE_CODIGO}/gerar-script",
        files={"arquivo": ("vinculo.xlsx", arquivo, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"nr_org": str(nr_org)},
    )
    assert response.status_code == 200
    sql = response.text

    # Blocos sempre gerados (2 linhas cada): PARCNEGOCIO, GPE_PESSOA, GPE_PESSOAH,
    # GPE_VINCULOM, GPE_ALTESITUFUNC e os 3 blocos de GPE_VINCULOH (ano corrente + as 2
    # cópias via INSERT...SELECT).
    assert sql.count("INSERT INTO PARCNEGOCIO (") == 2
    assert sql.count("INSERT INTO GPE_PESSOA (") == 2
    assert sql.count("INSERT INTO GPE_PESSOAH (") == 2
    assert sql.count("INSERT INTO GPE_VINCULOM (") == 2
    assert sql.count("INSERT INTO GPE_ALTESITUFUNC (") == 2
    assert sql.count("INSERT INTO GPE_VINCULOH (") == 6

    # A triplicação de GPE_VINCULOH usa aritmética simples sobre o mesmo marcador (Decisão
    # 2 do usuário) e datas relativas calculadas no Oracle, não valores fixos.
    assert "TRUNC(SYSDATE,'YYYY')" in sql
    assert "ADD_MONTHS(TRUNC(SYSDATE,'YYYY'),-12)" in sql
    assert "ADD_MONTHS(TRUNC(SYSDATE,'YYYY'),-24)" in sql
    # Aritmética +1/+2 aparece 1x por linha processada (2 linhas no fixture).
    assert sql.count("+1, NRVINCULOM") == 2
    assert sql.count("+2, NRVINCULOM") == 2

    # Blocos condicionais: só a primeira linha (LINHA_COMPLETA) os dispara.
    assert sql.count("INSERT INTO CONTCORRPARC (") == 1
    assert sql.count("INSERT INTO COMUNICAPARC (") == 3  # telpri + telcel + email, só na 1ª linha
    assert sql.count("INSERT INTO ENDERECOPARC (") == 1
    assert sql.count("INSERT INTO GPE_MOVIMENTACAO (") == 3  # legal + gerencial + sindical, só na 1ª linha

    assert "Avenida Paulista" in sql
    assert "denise@teste.com" in sql
    assert sql.strip().endswith("COMMIT;")
