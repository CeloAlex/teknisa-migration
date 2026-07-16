"""Adapters de Ingestão (Anexo A) — um adapter por formato (XLSX, XML, API...), saída tabular normalizada."""

from typing import Any

from app.ingestion.xlsx import ler_xlsx
from app.ingestion.xml import ler_xml
from app.metadata.schemas import TemplateMetadata


def ler_arquivo(conteudo: bytes, template: TemplateMetadata) -> list[dict[str, Any]]:
    """Ponto único de despacho por formato — escolhe o adapter certo a partir de
    `template.formatos_aceitos`, para que os call sites (staging, preview da API) não
    precisem conhecer XLSX/XML diretamente."""
    if "XML" in template.formatos_aceitos:
        return ler_xml(conteudo, template)
    return ler_xlsx(conteudo, template)
