from typing import Any

from app.metadata.schemas import TemplateMetadata
from app.transformation.conversions import aplicar_conversao


def aplicar_transformacoes(
    linha_bruta: dict[str, Any], template: TemplateMetadata, contexto: dict[str, Any]
) -> dict[str, Any]:
    """Transformation Engine (Anexo A): aplica a regra de conversão de cada campo do
    dicionário de dados sobre o valor bruto lido da linha (equivalente às fórmulas
    TRIM/SUBSTITUTE/TEXT das planilhas), resolvendo campos vindos de parâmetro de execução
    (ex.: NRORG) a partir do contexto em vez do arquivo. Roda em duas passagens: primeiro os
    campos diretos (arquivo/contexto), depois os campos derivados de outros campos já
    calculados desta mesma linha (ex.: um flag condicional de bloco de script — Seção 26.4).
    Campos com PK gerada (gerador_pk=True) não são lidos aqui — seu valor só existe na
    geração do script, via Key Resolution Service."""
    campos: dict[str, Any] = {}

    diretos = [c for c in template.campos if not c.gerador_pk and not c.eh_derivado]
    derivados = [c for c in template.campos if not c.gerador_pk and c.eh_derivado]

    for campo_meta in diretos:
        if campo_meta.vem_do_contexto:
            valor_bruto = contexto.get(campo_meta.origem.removeprefix("parametro_execucao."))
        else:
            valor_bruto = linha_bruta.get(campo_meta.origem)
        valor = aplicar_conversao(valor_bruto, campo_meta)
        if (valor is None or valor == "") and campo_meta.valor_padrao is not None:
            valor = campo_meta.valor_padrao
        campos[campo_meta.campo] = valor

    for campo_meta in derivados:
        valores_referenciados = [campos.get(nome) for nome in campo_meta.campos_referenciados]
        campos[campo_meta.campo] = aplicar_conversao(valores_referenciados, campo_meta)

    return campos
