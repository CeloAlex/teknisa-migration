from enum import Enum


class Classificacao(str, Enum):
    """Classificação do resultado de uma validação (Seção 7.7)."""

    ERRO_IMPEDITIVO = "erro_impeditivo"
    ALERTA = "alerta"
    RECOMENDACAO = "recomendacao"
    AJUSTE_AUTOMATICO = "ajuste_automatico"
    INFORMACAO = "informacao"
