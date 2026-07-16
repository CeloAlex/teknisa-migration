from app.metadata.schemas import CampoMetadata
from app.transformation.conversions import aplicar_conversao


def _campo(**overrides) -> CampoMetadata:
    base = dict(
        ordem=1,
        origem="A",
        rotulo="Campo",
        campo="CAMPO",
        marcador="@CAMPO@",
        destino_tabela="TABELA",
        destino_coluna="CAMPO",
        tipo="texto",
        tamanho_maximo=None,
        obrigatorio=False,
        valor_padrao=None,
        regra_conversao=None,
        eh_pk=False,
        gerador_pk=False,
    )
    base.update(overrides)
    return CampoMetadata(**base)


def test_trim_remove_espacos_nas_bordas() -> None:
    campo = _campo(regra_conversao="trim")
    assert aplicar_conversao("  0019  ", campo) == "0019"


def test_trim_com_none_vira_string_vazia() -> None:
    campo = _campo(regra_conversao="trim")
    assert aplicar_conversao(None, campo) == ""


def test_remover_mascara_remove_pontuacao_de_cnpj() -> None:
    campo = _campo(regra_conversao="remover_mascara")
    assert aplicar_conversao("03.801.629/0002-00", campo) == "03801629000200"


def test_remover_mascara_remove_virgula_e_underscore() -> None:
    campo = _campo(regra_conversao="remover_mascara")
    assert aplicar_conversao("414,110_", campo) == "414110"


def test_remover_aspas_e_comercial() -> None:
    campo = _campo(regra_conversao="remover_aspas_e_comercial")
    # replica o comportamento original das planilhas: apenas remove os caracteres ' e &,
    # sem recolher espaços duplos que sobrem no lugar do '&' removido.
    assert aplicar_conversao(" D'Ávila & Cia ", campo) == "DÁvila  Cia"


def test_upper_sem_acento() -> None:
    campo = _campo(regra_conversao="upper_sem_acento")
    assert aplicar_conversao(" varginha ", campo) == "VARGINHA"


def test_zero_esquerda_respeita_tamanho_maximo() -> None:
    campo = _campo(regra_conversao="zero_esquerda", tamanho_maximo=4)
    assert aplicar_conversao("55", campo) == "0055"


def test_data_br_normaliza_ano_de_dois_digitos() -> None:
    campo = _campo(regra_conversao="data_br")
    assert aplicar_conversao("7/1/09", campo) == "07/01/2009"


def test_data_br_converte_serial_numerico_do_excel() -> None:
    # Algumas planilhas reais (ex. 02_Ocupação) têm células de data cujo formato de número
    # não é reconhecido como data pelo openpyxl, chegando como inteiro puro.
    campo = _campo(regra_conversao="data_br")
    assert aplicar_conversao(33022, campo) == "29/05/1990"


def test_numero_decimal_troca_virgula_por_ponto() -> None:
    campo = _campo(regra_conversao="numero_decimal")
    assert aplicar_conversao("7,3333", campo) == "7.3333"


def test_numero_decimal_vazio_vira_none() -> None:
    campo = _campo(regra_conversao="numero_decimal")
    assert aplicar_conversao("", campo) is None


def test_vazio_para_n() -> None:
    campo = _campo(regra_conversao="vazio_para_n")
    assert aplicar_conversao("", campo) == "N"
    assert aplicar_conversao("S", campo) == "S"


def test_sem_regra_de_conversao_retorna_valor_original() -> None:
    campo = _campo(regra_conversao=None)
    assert aplicar_conversao(42, campo) == 42
    assert aplicar_conversao(None, campo) == ""


def test_nenhum_vazio_true_quando_todos_preenchidos() -> None:
    campo = _campo(regra_conversao="nenhum_vazio")
    assert aplicar_conversao(["OUTROS", "AV"], campo) is True


def test_nenhum_vazio_false_quando_algum_vazio() -> None:
    campo = _campo(regra_conversao="nenhum_vazio")
    assert aplicar_conversao(["OUTROS", ""], campo) is False


def test_primeiro_nao_vazio_pula_valores_vazios() -> None:
    campo = _campo(regra_conversao="primeiro_nao_vazio")
    assert aplicar_conversao(["", None, "Nome Fantasia", "Razão Social"], campo) == "Nome Fantasia"


def test_primeiro_nao_vazio_todos_vazios_retorna_vazio() -> None:
    campo = _campo(regra_conversao="primeiro_nao_vazio")
    assert aplicar_conversao(["", None], campo) == ""


def test_cbo_remove_pontuacao() -> None:
    campo = _campo(regra_conversao="cbo")
    assert aplicar_conversao("414.110", campo) == "414110"


def test_cbo_vazio_vira_literal_null() -> None:
    campo = _campo(regra_conversao="cbo")
    assert aplicar_conversao("", campo) == "NULL"
