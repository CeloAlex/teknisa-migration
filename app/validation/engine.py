from typing import Any

from app.metadata.schemas import TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.schemas import ResultadoValidacao


def validar_linha(campos: dict[str, Any], template: TemplateMetadata) -> list[ResultadoValidacao]:
    """Validation Engine (Anexo A / Anexo G) — nesta fase cobre validação estrutural de
    obrigatoriedade (erro impeditivo) e de tamanho máximo (alerta) por campo do dicionário de
    dados (Seção 7.1/7.2), na mesma ordem do pseudocódigo de referência: um campo com erro de
    obrigatoriedade não chega a ser avaliado quanto ao tamanho. Validações relacionais,
    temporais e de negócio (Seção 7.4-7.6) chegam nas próximas fases, junto do Key Resolution
    Service e da integração com o banco de destino."""
    resultados: list[ResultadoValidacao] = []
    for campo_meta in template.campos:
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
