from datetime import date, datetime, time

from app.staging.service import _json_seguro, _linha_bruta_para_json


def test_json_seguro_converte_datetime_date_e_time() -> None:
    assert _json_seguro(datetime(2026, 1, 7, 10, 30)) == "2026-01-07T10:30:00"
    assert _json_seguro(date(2026, 1, 7)) == "2026-01-07"
    assert _json_seguro(time(7, 0)) == "07:00:00"


def test_json_seguro_mantem_tipos_ja_serializaveis() -> None:
    assert _json_seguro("texto") == "texto"
    assert _json_seguro(1001) == 1001
    assert _json_seguro(None) is None


def test_linha_bruta_com_coluna_de_horario_puro_fica_serializavel() -> None:
    """Reproduz o bug real da Escala de Trabalho (achado via logs de produção): colunas de
    entrada/saída em formato de hora pura (célula Excel tipo "hora", não "data/hora") viram
    `datetime.time` no openpyxl — sem a conversão em `_json_seguro`, gravar isso em JSONB
    derrubava a task de importação em segundo plano, travando a tela em "0/0 linhas
    processadas" pra sempre."""
    linha = {
        "A": datetime(2009, 1, 7),
        "G": time(7, 0),
        "H": time(12, 0),
        "_linha_planilha": 2,
    }
    resultado = _linha_bruta_para_json(linha)
    assert resultado == {"A": "2009-01-07T00:00:00", "G": "07:00:00", "H": "12:00:00"}

    import json

    json.dumps(resultado)  # não pode levantar TypeError
