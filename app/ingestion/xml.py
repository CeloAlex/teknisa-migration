from typing import Any

from lxml import etree

from app.ingestion.xlsx import LINHA_PLANILHA, ArquivoInvalido
from app.metadata.schemas import TemplateMetadata


def _remover_namespaces(raiz: etree._Element) -> None:
    """eSocial usa um namespace por versão de evento (`.../evtAdmissao/v_S_01_02_00`) —
    remover o prefixo de todas as tags evita que o XPath do dicionário de dados precise
    conhecer/hardcodar a URI exata de cada versão de schema."""
    for elemento in raiz.iter():
        if isinstance(elemento.tag, str) and "}" in elemento.tag:
            elemento.tag = elemento.tag.split("}", 1)[1]
    etree.cleanup_namespaces(raiz)


def ler_xml(conteudo: bytes, template: TemplateMetadata) -> list[dict[str, Any]]:
    """Adapter de Ingestão XML (Anexo A / Anexo F): mesmo contrato de `ler_xlsx` — uma
    linha por registro, mapeada por `origem` (aqui um XPath relativo ao nó-linha, em vez
    de uma letra de coluna). `template.xml_registro_xpath` seleciona o(s) nó(s)-linha; se
    nulo, o documento inteiro é tratado como uma linha só (a maioria dos eventos eSocial:
    um XML = um evento)."""
    try:
        raiz = etree.fromstring(conteudo)
    except etree.XMLSyntaxError as exc:
        raise ArquivoInvalido(f"Não foi possível ler o arquivo XML: {exc}") from exc

    _remover_namespaces(raiz)

    origens = sorted(
        {
            c.origem
            for c in template.campos
            if not c.vem_do_contexto and not c.eh_derivado and not c.gerador_pk
        }
    )

    nos = raiz.xpath(template.xml_registro_xpath) if template.xml_registro_xpath else [raiz]

    linhas: list[dict[str, Any]] = []
    for indice, no in enumerate(nos, start=1):
        valores: dict[str, Any] = {}
        for origem in origens:
            encontrados = no.xpath(origem)
            if not encontrados:
                valores[origem] = None
            else:
                achado = encontrados[0]
                valores[origem] = achado.text if hasattr(achado, "text") else str(achado)
        if all(v is None or str(v).strip() == "" for v in valores.values()):
            continue
        valores[LINHA_PLANILHA] = indice
        linhas.append(valores)
    return linhas
