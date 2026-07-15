from dataclasses import dataclass

from app.validation.classificacao import Classificacao


@dataclass(frozen=True, slots=True)
class ResultadoValidacao:
    """Um resultado de validação sobre um campo de uma linha (Seção 14 — VALIDACAO_RESULTADO,
    formato de mensagem detalhado na Seção 23)."""

    campo: str
    regra: str
    classificacao: Classificacao
    valor_recebido: str
    valor_esperado: str
    orientacao: str
