import re
import unicodedata
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from app.metadata.schemas import CampoMetadata

ConversaoFn = Callable[[Any, CampoMetadata], Any]


def _trim(valor: Any, campo: CampoMetadata) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _remover_mascara(valor: Any, campo: CampoMetadata) -> str:
    if valor is None:
        return ""
    return re.sub(r"[\s\-./\\]", "", str(valor))


def _upper_sem_acento(valor: Any, campo: CampoMetadata) -> str:
    texto = _trim(valor, campo).upper()
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def _zero_esquerda(valor: Any, campo: CampoMetadata) -> str:
    texto = _trim(valor, campo)
    tamanho = campo.tamanho_maximo or len(texto)
    return texto.zfill(tamanho)


def _data_br(valor: Any, campo: CampoMetadata) -> str:
    if valor in (None, ""):
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    texto = str(valor)
    partes = re.split(r"[/-]", texto)
    if len(partes) == 3:
        dia, mes, ano = partes
        if len(ano) == 2:
            ano = "20" + ano
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
    return texto


def _numero_decimal(valor: Any, campo: CampoMetadata) -> str | None:
    if valor in (None, ""):
        return None
    return str(valor).replace(",", ".")


def _vazio_para_n(valor: Any, campo: CampoMetadata) -> str:
    texto = _trim(valor, campo)
    return texto if texto else "N"


# Registro nomeado de regras de conversão (equivalente às fórmulas TRIM/SUBSTITUTE/TEXT das
# planilhas — Seção 6/7.2) — o dicionário de dados referencia estas chaves por nome, nunca
# por código específico de template.
CONVERSOES: dict[str, ConversaoFn] = {
    "trim": _trim,
    "remover_mascara": _remover_mascara,
    "upper_sem_acento": _upper_sem_acento,
    "zero_esquerda": _zero_esquerda,
    "data_br": _data_br,
    "numero_decimal": _numero_decimal,
    "vazio_para_n": _vazio_para_n,
}


def aplicar_conversao(valor: Any, campo: CampoMetadata) -> Any:
    if not campo.regra_conversao:
        return "" if valor is None else valor
    fn = CONVERSOES.get(campo.regra_conversao)
    if fn is None:
        return valor
    return fn(valor, campo)
