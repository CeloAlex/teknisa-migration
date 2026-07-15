from dataclasses import dataclass
from typing import Any

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


def gerar_script(
    linhas_validas: list[dict[str, Any]],
    template: TemplateMetadata,
    contexto: ContextoExecucao,
    operacao: str = "INCLUSAO",
) -> str:
    """Script Generator (Anexo A / Anexo H / Seção 10) — substitui os marcadores @CAMPO@ do
    template de script cadastrado no metadado pelos valores já transformados e validados de
    cada linha aprovada, um INSERT por linha, seguido de um único COMMIT ao final do lote
    (Seção 10.1 propõe justamente tornar o commit configurável por lote, em vez de por linha
    como nas planilhas atuais; o controle fino de tamanho de lote chega na Fase 5)."""
    script_meta = template.scripts.get(operacao)
    if script_meta is None:
        raise ScriptNaoConfigurado(
            f'Template "{template.codigo}" não tem script configurado para a operação "{operacao}".'
        )

    comandos = [
        _substituir_marcadores(script_meta.template_sql, campos, template, contexto)
        for campos in linhas_validas
    ]
    comandos.append("COMMIT;")
    return "\n".join(comandos)
