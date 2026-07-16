import re
import unicodedata
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from openpyxl.utils.datetime import from_excel

from app.metadata.schemas import CampoMetadata

ConversaoFn = Callable[[Any, CampoMetadata], Any]


def _trim(valor: Any, campo: CampoMetadata) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _remover_mascara(valor: Any, campo: CampoMetadata) -> str:
    if valor is None:
        return ""
    return re.sub(r"[\s\-./\\_,]", "", str(valor))


def _remover_aspas_e_comercial(valor: Any, campo: CampoMetadata) -> str:
    """trim + remoção de aspas simples e "&" (Seção 13.2 — nomes/razões sociais que
    alimentam templates de script com o valor entre aspas simples)."""
    return _trim(valor, campo).replace("'", "").replace("&", "")


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
    if isinstance(valor, (int, float)):
        # Nem toda célula de data do XLSX chega como datetime — quando o formato de
        # número da célula não é reconhecido como data pelo openpyxl (inconsistência comum
        # nas planilhas reais, ex. 02_Ocupação), o valor chega como serial numérico puro
        # (ex. 33022 = 29/05/1990). Equivalente ao XLSX.SSF.parse_date_code do protótipo.
        return from_excel(valor).strftime("%d/%m/%Y")
    texto = str(valor)
    partes = re.split(r"[/-]", texto)
    if len(partes) == 3:
        dia, mes, ano = partes
        if len(ano) == 2:
            ano = "20" + ano
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
    return texto


def _data_iso(valor: Any, campo: CampoMetadata) -> str:
    """Datas do eSocial vêm em ISO 8601 ("AAAA-MM-DD" ou, para campos de competência,
    "AAAA-MM") — sintaxe diferente da planilha (`data_br` espera DD/MM/AAAA e quebraria
    silenciosamente com um ISO, invertendo dia/ano). "AAAA-MM" vira o primeiro dia do mês,
    mesmo critério que o parser de origem já usa para competência."""
    if valor in (None, ""):
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d/%m/%Y")
    texto = str(valor).strip()
    partes = texto.split("-")
    if len(partes) == 3:
        ano, mes, dia = partes
        return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
    if len(partes) == 2:
        ano, mes = partes
        return f"01/{mes.zfill(2)}/{ano}"
    return texto


def _codigo_igual_15(valor: Any, campo: CampoMetadata) -> bool:
    """Regra de campo derivado usada só para rotear o evento eSocial S-2230 (Afastamento
    Temporário): o código de motivo de afastamento eSocial "15" é Férias — o restante dos
    códigos é afastamento/Situação Funcional (Seção 26.2 do material eSocial fornecido)."""
    valores = valor if isinstance(valor, list) else [valor]
    return any(str(v).strip() == "15" for v in valores if v is not None)


def _codigo_diferente_15(valor: Any, campo: CampoMetadata) -> bool:
    """Inverso de `codigo_igual_15` — usado como `condicao_campo` do bloco oposto."""
    return not _codigo_igual_15(valor, campo)


def _numero_decimal(valor: Any, campo: CampoMetadata) -> str | None:
    if valor in (None, ""):
        return None
    return str(valor).replace(",", ".")


def _vazio_para_n(valor: Any, campo: CampoMetadata) -> str:
    texto = _trim(valor, campo)
    return texto if texto else "N"


def _nenhum_vazio(valor: Any, campo: CampoMetadata) -> bool:
    """Regra de campo derivado (Seção 7.6/26.4, "preenchimento condicional"): recebe a lista
    de valores dos campos referenciados em `origem="campo:A,B"` e responde se todos estão
    preenchidos — usado para condicionar blocos de INSERT (ex.: só inserir endereço se tipo
    de endereço E logradouro estiverem preenchidos)."""
    valores = valor if isinstance(valor, list) else [valor]
    return all(v not in (None, "") for v in valores)


def _primeiro_nao_vazio(valor: Any, campo: CampoMetadata) -> str:
    """Regra de campo derivado: recebe a lista de valores dos campos referenciados em
    `origem="campo:A,B,C"` e devolve o primeiro não vazio (ex.: nome do parceiro de negócio
    de Estrutura = Razão Social, senão Nome Fantasia, senão Nome da Estrutura)."""
    valores = valor if isinstance(valor, list) else [valor]
    for v in valores:
        if v not in (None, ""):
            return str(v)
    return ""


def _esta_vazio(valor: Any, campo: CampoMetadata) -> bool:
    """Regra de campo derivado — o inverso de `nenhum_vazio`: recebe a lista de valores dos
    campos referenciados em `origem="campo:A"` e responde se o (único) campo está vazio.
    Usado no padrão "catálogo/de-para" de Eventos (Seção 26.4): se o código do evento já
    existente no HCM não foi informado, o evento é novo e o bloco de INSERT correspondente
    é disparado."""
    valores = valor if isinstance(valor, list) else [valor]
    return any(v in (None, "") for v in valores)


def _cbo(valor: Any, campo: CampoMetadata) -> str:
    """CBO (Seção 13.2): sem validação de formato hoje, mas precisa virar o literal `NULL`
    quando vazio, pois o marcador é usado sem aspas no template de script (posição
    numérica) — equivalente a "vazio => NULL; senão remove espaço/./,/-/_ e tab"."""
    texto = _remover_mascara(valor, campo)
    return texto if texto else "NULL"


def _numero_ou_null(valor: Any, campo: CampoMetadata) -> str:
    """Mesma ideia do `cbo`, generalizada para qualquer campo numérico opcional usado sem
    aspas no template de script (ex. VRREFFOLHA da Ficha Financeira): vazio vira o literal
    `NULL` em vez de string vazia, que quebraria a posição numérica do INSERT."""
    if valor in (None, ""):
        return "NULL"
    return str(valor).replace(",", ".")


def _cpf(valor: Any, campo: CampoMetadata) -> str:
    """Vínculo (Seção 26.2): equivalente à fórmula real
    `TEXT(MIG_NORMA.NÚMERICO(J3),"00000000000")` — extrai só dígitos e completa com zeros
    à esquerda até 11 posições."""
    apenas_digitos = re.sub(r"\D", "", str(valor)) if valor is not None else ""
    return apenas_digitos.zfill(11) if apenas_digitos else ""


def _ctps(valor: Any, campo: CampoMetadata) -> str:
    """Mesma ideia do `cpf`, para CTPS — fórmula real usa 7 posições."""
    apenas_digitos = re.sub(r"\D", "", str(valor)) if valor is not None else ""
    return apenas_digitos.zfill(7) if apenas_digitos else ""


def _truncar(valor: Any, campo: CampoMetadata) -> str:
    """trim + corta no `tamanho_maximo` do campo (ex. Vínculo: NRCERTRESE, fórmula real
    `MID(TRIM(AA3),1,20)`) — ao contrário de `tamanho_maximo` sozinho (que só gera alerta na
    validação), esta regra efetivamente corta o valor antes de ir para o script."""
    texto = _trim(valor, campo)
    return texto[: campo.tamanho_maximo] if campo.tamanho_maximo else texto


def _situfuncm_por_rescisao(valor: Any, campo: CampoMetadata) -> str:
    """Campo derivado do Vínculo: a coluna "Situ. Funcional" da planilha real não é
    preenchida manualmente — é uma fórmula (`=IF(DTRESCISAO="",1,13)`). Direcionado pelo
    usuário: com data de rescisão preenchida, código 13; sem rescisão, código 1."""
    valores = valor if isinstance(valor, list) else [valor]
    dt_rescisao = valores[0] if valores else None
    return "13" if dt_rescisao not in (None, "") else "1"


def _tipo_logradouro(valor: Any, campo: CampoMetadata) -> str:
    """Vínculo (endereço): fórmula real extrai os 4 primeiros caracteres do logradouro já
    maiúsculo e sem acento (ex. "Rua" -> "RUA", "Avenida" -> "AVEN") para casar com o
    domínio `CDLOGRADOURO` do destino."""
    return _upper_sem_acento(valor, campo)[:4]


def _agencia_bancaria(valor: Any, campo: CampoMetadata) -> str:
    """Vínculo: fórmula real remove hífen, maiusculiza e mantém só os 5 primeiros
    caracteres (`UPPER(MID(SUBSTITUTE(TRIM(AK3),"-",""),1,5))`)."""
    texto = _trim(valor, campo).replace("-", "").upper()
    return texto[:5]


def _conta_corrente(valor: Any, campo: CampoMetadata) -> str:
    """Vínculo: fórmula real remove hífen e maiusculiza
    (`UPPER(SUBSTITUTE(TRIM(AL3),"-",""))`), sem limite de tamanho."""
    return _trim(valor, campo).replace("-", "").upper()


# Registro nomeado de regras de conversão (equivalente às fórmulas TRIM/SUBSTITUTE/TEXT das
# planilhas — Seção 6/7.2) — o dicionário de dados referencia estas chaves por nome, nunca
# por código específico de template.
CONVERSOES: dict[str, ConversaoFn] = {
    "trim": _trim,
    "remover_mascara": _remover_mascara,
    "remover_aspas_e_comercial": _remover_aspas_e_comercial,
    "upper_sem_acento": _upper_sem_acento,
    "zero_esquerda": _zero_esquerda,
    "data_br": _data_br,
    "data_iso": _data_iso,
    "codigo_igual_15": _codigo_igual_15,
    "codigo_diferente_15": _codigo_diferente_15,
    "numero_decimal": _numero_decimal,
    "vazio_para_n": _vazio_para_n,
    "nenhum_vazio": _nenhum_vazio,
    "esta_vazio": _esta_vazio,
    "primeiro_nao_vazio": _primeiro_nao_vazio,
    "cbo": _cbo,
    "numero_ou_null": _numero_ou_null,
    "cpf": _cpf,
    "ctps": _ctps,
    "truncar": _truncar,
    "situfuncm_por_rescisao": _situfuncm_por_rescisao,
    "tipo_logradouro": _tipo_logradouro,
    "agencia_bancaria": _agencia_bancaria,
    "conta_corrente": _conta_corrente,
}


def aplicar_conversao(valor: Any, campo: CampoMetadata) -> Any:
    if not campo.regra_conversao:
        return "" if valor is None else valor
    fn = CONVERSOES.get(campo.regra_conversao)
    if fn is None:
        return valor
    return fn(valor, campo)
