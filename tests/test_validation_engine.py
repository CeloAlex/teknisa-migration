from app.metadata.schemas import CampoMetadata, TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.engine import validar_linha


def _template() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="A", rotulo="Banco", campo="CDBANCO", marcador="@CDBANCO@",
            destino_tabela="AGENCIA", destino_coluna="CDBANCO", tipo="texto",
            tamanho_maximo=3, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=True, gerador_pk=False,
        ),
        CampoMetadata(
            ordem=2, origem="C", rotulo="Agência", campo="NMAGENCIA", marcador="@NMAGENCIA@",
            destino_tabela="AGENCIA", destino_coluna="NMAGENCIA", tipo="texto",
            tamanho_maximo=60, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=False, gerador_pk=False,
        ),
    ]
    return TemplateMetadata(
        codigo="TESTE", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_campo_obrigatorio_vazio_gera_erro_impeditivo() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "", "NMAGENCIA": "Agência Centro"}, template)
    assert len(resultados) == 1
    assert resultados[0].campo == "CDBANCO"
    assert resultados[0].regra == "obrigatoriedade"
    assert resultados[0].classificacao == Classificacao.ERRO_IMPEDITIVO


def test_campo_acima_do_tamanho_maximo_gera_alerta_nao_bloqueante() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "ABCD", "NMAGENCIA": "Agência Centro"}, template)
    assert len(resultados) == 1
    assert resultados[0].campo == "CDBANCO"
    assert resultados[0].regra == "tamanho_maximo"
    assert resultados[0].classificacao == Classificacao.ALERTA


def test_campo_obrigatorio_vazio_nao_avalia_tamanho_do_mesmo_campo() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "", "NMAGENCIA": "Agência Centro"}, template)
    regras = [r.regra for r in resultados if r.campo == "CDBANCO"]
    assert regras == ["obrigatoriedade"]


def test_linha_valida_nao_gera_nenhum_resultado() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "001", "NMAGENCIA": "Agência Centro"}, template)
    assert resultados == []
