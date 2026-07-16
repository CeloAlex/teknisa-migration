from app.metadata.schemas import CampoMetadata, TemplateMetadata
from app.transformation.engine import aplicar_transformacoes


def _campo(**overrides) -> CampoMetadata:
    base = dict(
        ordem=1, origem="A", rotulo="Campo", campo="CAMPO", marcador="@CAMPO@",
        destino_tabela="TABELA", destino_coluna="CAMPO", tipo="texto", tamanho_maximo=None,
        obrigatorio=False, valor_padrao=None, regra_conversao=None, eh_pk=False,
        gerador_pk=False, gerador_pk_contador=None, gerador_pk_seed=None,
    )
    base.update(overrides)
    return CampoMetadata(**base)


def _template(campos: list[CampoMetadata]) -> TemplateMetadata:
    return TemplateMetadata(
        codigo="TESTE", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=2, data_start_row=3, campos=campos,
    )


def test_valor_padrao_aplicado_quando_campo_vazio() -> None:
    template = _template([_campo(origem="C", campo="NROCORRENCIA", valor_padrao="1")])
    resultado = aplicar_transformacoes({"C": ""}, template, {})
    assert resultado["NROCORRENCIA"] == "1"


def test_valor_padrao_nao_sobrescreve_valor_presente() -> None:
    template = _template([_campo(origem="C", campo="NROCORRENCIA", valor_padrao="1")])
    resultado = aplicar_transformacoes({"C": "3"}, template, {})
    assert resultado["NROCORRENCIA"] == "3"


def test_campo_derivado_usa_valores_ja_calculados_na_primeira_passagem() -> None:
    template = _template(
        [
            _campo(origem="P", campo="IDENDERECO", regra_conversao="trim"),
            _campo(origem="T", campo="LOGRADOURO", regra_conversao="trim"),
            _campo(
                origem="campo:IDENDERECO,LOGRADOURO", campo="_TEM_ENDERECO",
                marcador=None, regra_conversao="nenhum_vazio",
            ),
        ]
    )
    resultado = aplicar_transformacoes({"P": "OUTROS", "T": "AV"}, template, {})
    assert resultado["_TEM_ENDERECO"] is True

    resultado_sem = aplicar_transformacoes({"P": "OUTROS", "T": ""}, template, {})
    assert resultado_sem["_TEM_ENDERECO"] is False
