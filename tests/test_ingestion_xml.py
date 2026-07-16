import pytest

from app.ingestion.xlsx import ArquivoInvalido
from app.ingestion.xml import ler_xml
from app.metadata.schemas import CampoMetadata, TemplateMetadata


def _campo(**kw) -> CampoMetadata:
    base = {
        "ordem": 1, "rotulo": "campo", "marcador": None, "destino_tabela": "T",
        "destino_coluna": "C", "tipo": "texto", "tamanho_maximo": None, "obrigatorio": False,
        "valor_padrao": None, "regra_conversao": None, "eh_pk": False, "gerador_pk": False,
    }
    base.update(kw)
    return CampoMetadata(**base)


def _template(campos: list[CampoMetadata], xml_registro_xpath: str | None = None) -> TemplateMetadata:
    return TemplateMetadata(
        codigo="TESTE_XML",
        nome="Teste XML",
        versao="1",
        sheet_name=None,
        header_row=None,
        data_start_row=None,
        campos=campos,
        formatos_aceitos=["XML"],
        xml_registro_xpath=xml_registro_xpath,
    )


def test_documento_com_registro_unico_vira_uma_linha() -> None:
    template = _template([_campo(campo="NOME", origem="pessoa/nome")])
    xml = b"<raiz><pessoa><nome>Maria</nome></pessoa></raiz>"
    linhas = ler_xml(xml, template)
    assert len(linhas) == 1
    assert linhas[0]["pessoa/nome"] == "Maria"


def test_namespace_e_removido_antes_do_xpath() -> None:
    template = _template([_campo(campo="NOME", origem="pessoa/nome")])
    xml = b'<raiz xmlns="http://exemplo.com/evt/v1"><pessoa><nome>Maria</nome></pessoa></raiz>'
    linhas = ler_xml(xml, template)
    assert len(linhas) == 1
    assert linhas[0]["pessoa/nome"] == "Maria"


def test_xml_registro_xpath_seleciona_nos_repetidos() -> None:
    template = _template(
        [_campo(campo="CODIGO", origem="codigo"), _campo(campo="MATRICULA", origem="../matricula")],
        xml_registro_xpath="lote/item",
    )
    xml = (
        b"<raiz><lote><matricula>111</matricula>"
        b"<item><codigo>A</codigo></item><item><codigo>B</codigo></item>"
        b"</lote></raiz>"
    )
    linhas = ler_xml(xml, template)
    assert len(linhas) == 2
    assert [l["codigo"] for l in linhas] == ["A", "B"]
    assert all(l["../matricula"] == "111" for l in linhas)


def test_linha_totalmente_vazia_e_descartada() -> None:
    template = _template(
        [_campo(campo="CODIGO", origem="codigo")], xml_registro_xpath="lote/item"
    )
    xml = b"<raiz><lote><item><codigo>A</codigo></item><item></item></lote></raiz>"
    linhas = ler_xml(xml, template)
    assert len(linhas) == 1
    assert linhas[0]["codigo"] == "A"


def test_xml_malformado_levanta_arquivo_invalido() -> None:
    template = _template([_campo(campo="NOME", origem="pessoa/nome")])
    with pytest.raises(ArquivoInvalido):
        ler_xml(b"<raiz><pessoa>", template)


def test_campo_com_origem_absoluta_ignora_no_de_contexto() -> None:
    template = _template(
        [
            _campo(campo="CODIGO", origem="codigo"),
            _campo(campo="COMPETENCIA", origem="/raiz/ideEvento/perApur"),
        ],
        xml_registro_xpath="lote/item",
    )
    xml = (
        b"<raiz><ideEvento><perApur>2026-06</perApur></ideEvento>"
        b"<lote><item><codigo>A</codigo></item><item><codigo>B</codigo></item></lote></raiz>"
    )
    linhas = ler_xml(xml, template)
    assert len(linhas) == 2
    assert all(l["/raiz/ideEvento/perApur"] == "2026-06" for l in linhas)
