from typing import Any

from app.metadata.schemas import TemplateMetadata
from app.transformation.conversions import aplicar_conversao


def aplicar_transformacoes(
    linha_bruta: dict[str, Any], template: TemplateMetadata, contexto: dict[str, Any]
) -> dict[str, Any]:
    """Transformation Engine (Anexo A): aplica a regra de conversão de cada campo do
    dicionário de dados sobre o valor bruto lido da linha (equivalente às fórmulas
    TRIM/SUBSTITUTE/TEXT das planilhas), resolvendo campos vindos de parâmetro de execução
    (ex.: NRORG) a partir do contexto em vez do arquivo."""
    campos: dict[str, Any] = {}
    for campo_meta in template.campos:
        if campo_meta.vem_do_contexto:
            valor_bruto = contexto.get(campo_meta.chave_contexto)
        else:
            valor_bruto = linha_bruta.get(campo_meta.origem)
        campos[campo_meta.campo] = aplicar_conversao(valor_bruto, campo_meta)
    return campos
