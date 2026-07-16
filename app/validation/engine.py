from typing import Any

from app.metadata.schemas import TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.schemas import ResultadoValidacao


def validar_linha(campos: dict[str, Any], template: TemplateMetadata) -> list[ResultadoValidacao]:
    """Validation Engine (Anexo A / Anexo G) — nesta fase cobre validação estrutural de
    obrigatoriedade (erro impeditivo) e de tamanho máximo (alerta) por campo do dicionário de
    dados (Seção 7.1/7.2), na mesma ordem do pseudocódigo de referência: um campo com erro de
    obrigatoriedade não chega a ser avaliado quanto ao tamanho. Campos com PK gerada
    (gerador_pk) e campos derivados internos (eh_derivado — flags de condição de bloco de
    script, não colunas de destino reais) não são validados. Validações relacionais,
    temporais e de negócio (Seção 7.4-7.6) chegam nas próximas fases, junto da integração
    com o banco de destino."""
    resultados: list[ResultadoValidacao] = []
    for campo_meta in template.campos:
        if campo_meta.gerador_pk or campo_meta.eh_derivado:
            continue

        valor = campos.get(campo_meta.campo)
        vazio = valor is None or str(valor).strip() == ""

        if campo_meta.obrigatorio and vazio:
            resultados.append(
                ResultadoValidacao(
                    campo=campo_meta.campo,
                    regra="obrigatoriedade",
                    classificacao=Classificacao.ERRO_IMPEDITIVO,
                    valor_recebido="(vazio)",
                    valor_esperado=campo_meta.rotulo,
                    orientacao=f'Preencha o campo "{campo_meta.rotulo}".',
                )
            )
            continue

        if campo_meta.tamanho_maximo and not vazio and len(str(valor)) > campo_meta.tamanho_maximo:
            resultados.append(
                ResultadoValidacao(
                    campo=campo_meta.campo,
                    regra="tamanho_maximo",
                    classificacao=Classificacao.ALERTA,
                    valor_recebido=str(valor),
                    valor_esperado=f"até {campo_meta.tamanho_maximo} caracteres",
                    orientacao=f'Confira o valor de "{campo_meta.rotulo}".',
                )
            )
    return resultados
