from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.keys.service import reservar_proximo_codigo
from app.metadata.schemas import TemplateMetadata


class ScriptNaoConfigurado(Exception):
    pass


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
) -> str:
    """Script Generator (Anexo A / Anexo H / Seção 10) — para cada linha aprovada: reserva as
    PKs sequenciais declaradas no dicionário via Key Resolution Service, depois substitui os
    marcadores @CAMPO@ de cada bloco de script configurado para a operação, pulando blocos
    cuja `condicao_campo` resolver como falsa (Seção 26.4). Um único COMMIT encerra o lote
    inteiro (Seção 10.1 propõe tornar o commit configurável por lote, em vez de por linha
    como nas planilhas atuais; o controle fino de tamanho de lote chega na Fase 5)."""
    blocos = template.scripts.get(operacao)
    if not blocos:
        raise ScriptNaoConfigurado(
            f'Template "{template.codigo}" não tem script configurado para a operação "{operacao}".'
        )

    campos_geradores_pk = [c for c in template.campos if c.gerador_pk]

    comandos: list[str] = []
    for campos_linha in linhas_validas:
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
            comandos.append(_substituir_marcadores(bloco.template_sql, campos_com_pk, template, contexto))

    comandos.append("COMMIT;")
    return "\n".join(comandos)
