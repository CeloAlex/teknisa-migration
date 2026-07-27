import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.keys.service import reservar_proximo_codigo
from app.metadata.schemas import TemplateMetadata


class ScriptNaoConfigurado(Exception):
    pass


# Um bloco de `template_sql` pode conter mais de uma instrução SQL, separadas só por "); "
# sem quebra de linha — ex.: o bloco principal de Estrutura tem PARCNEGOCIO + ESTRUTURAM +
# ESTRUTURAH juntos, extraído verbatim de uma única célula da planilha original (mesmo
# padrão em Ocupação: GPE_OCUPACAOM+H, e Escala: GPE_ESCALATRABM+H). Sem dividir isso em
# comandos separados, dois problemas: (1) fica quase invisível numa checagem visual do
# .sql — a 2ª/3ª instrução do bloco parece "sumida", enterrada no meio da linha da 1ª; e
# (2) pior, o Oracle não executa múltiplas instruções separadas por `;` num único
# `cursor.execute()` — a Execution Engine quebraria com erro de sintaxe ao tentar rodar o
# bloco inteiro como se fosse um comando só.
_RE_FIM_INSTRUCAO = re.compile(r"(\);)\s+(?=[A-Z])")


def _dividir_comandos(texto: str) -> list[str]:
    quebrado = _RE_FIM_INSTRUCAO.sub(r"\1\n", texto)
    return [linha.strip() for linha in quebrado.splitlines() if linha.strip()]


@dataclass(frozen=True, slots=True)
class ContextoExecucao:
    """Parâmetros de execução da migração que não vêm do arquivo (Seção 13.3): organização e
    usuário técnico, hoje fixos nas planilhas e aqui configuráveis por ambiente/execução."""

    nr_org: int
    usuario_tecnico: str


def _substituir_marcadores(
    texto: str, campos: dict[str, Any], template: TemplateMetadata, contexto: ContextoExecucao
) -> str:
    resultado = texto
    for campo_meta in template.campos:
        if not campo_meta.marcador:
            continue
        valor = campos.get(campo_meta.campo)
        resultado = resultado.replace(campo_meta.marcador, "" if valor is None else str(valor))
    resultado = resultado.replace("@NRORG@", str(contexto.nr_org))
    resultado = resultado.replace("@USUARIO_TECNICO@", contexto.usuario_tecnico)
    return resultado


async def gerar_script(
    session: AsyncSession,
    linhas_validas: list[dict[str, Any]],
    template: TemplateMetadata,
    contexto: ContextoExecucao,
    operacao: str = "INCLUSAO",
    linhas_por_commit: int = 1,
) -> str:
    """Script Generator (Anexo A / Anexo H / Seção 10) — para cada linha aprovada: reserva as
    PKs sequenciais declaradas no dicionário via Key Resolution Service, depois substitui os
    marcadores @CAMPO@ de cada bloco de script configurado para a operação, pulando blocos
    cuja `condicao_campo` resolver como falsa (Seção 26.4). Um COMMIT é emitido a cada
    `linhas_por_commit` linhas processadas (Seção 10.1 — antes um único COMMIT encerrava o
    lote inteiro; agora configurável, com default igual ao comportamento das planilhas
    atuais: um COMMIT por linha)."""
    if linhas_por_commit < 1:
        raise ValueError("linhas_por_commit deve ser pelo menos 1.")

    blocos = template.scripts.get(operacao)
    if not blocos:
        raise ScriptNaoConfigurado(
            f'Template "{template.codigo}" não tem script configurado para a operação "{operacao}".'
        )

    campos_geradores_pk = [c for c in template.campos if c.gerador_pk]

    comandos: list[str] = []
    for indice, campos_linha in enumerate(linhas_validas, start=1):
        campos_com_pk = dict(campos_linha)
        for campo_meta in campos_geradores_pk:
            campos_com_pk[campo_meta.campo] = await reservar_proximo_codigo(
                session,
                contexto.nr_org,
                campo_meta.gerador_pk_contador or campo_meta.campo,
                campo_meta.gerador_pk_seed or 0,
            )

        for bloco in blocos:
            if bloco.condicao_campo and not campos_com_pk.get(bloco.condicao_campo):
                continue
            texto = _substituir_marcadores(bloco.template_sql, campos_com_pk, template, contexto)
            comandos.extend(_dividir_comandos(texto))

        if indice % linhas_por_commit == 0:
            comandos.append("COMMIT;")

    if not comandos or comandos[-1] != "COMMIT;":
        comandos.append("COMMIT;")

    return "\n".join(comandos)
