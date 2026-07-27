from dataclasses import dataclass
from typing import Literal

import oracledb

from app.destination.oracle import conectar


@dataclass(frozen=True, slots=True)
class ResultadoExecucao:
    """Resultado de rodar um script gerado (Script Generator) contra o Oracle de destino."""

    sucesso: bool
    comandos_executados: int
    detalhe_erro: str | None = None


_COMMIT = "COMMIT"


def _comandos(sql: str) -> list[str | Literal["COMMIT"]]:
    """O Script Generator emite um comando por linha, terminado em `;`, com um `COMMIT;`
    a cada N linhas (Seção 10.1) — cada ocorrência vira um marcador de fronteira de commit,
    executado como `connection.commit()` real no lugar em que aparece, em vez de descartada."""
    comandos: list[str] = []
    for linha in sql.splitlines():
        comando = linha.strip()
        if not comando:
            continue
        comandos.append(_COMMIT if comando.upper() == "COMMIT;" else comando.rstrip(";"))
    return comandos


async def executar_script(sql: str) -> ResultadoExecucao:
    """Execution Engine, Modo Script (Anexo A / Seção 11): roda cada comando do script,
    respeitando os pontos de COMMIT definidos pelo Script Generator. Diferente de uma
    transação única: um erro NÃO desfaz lotes já commitados antes dele — só o lote em
    andamento no momento da falha é revertido (mesma semântica de "COMMIT a cada N linhas"
    das planilhas atuais, Seção 10.1)."""
    comandos = _comandos(sql)
    conexao = await conectar()
    try:
        cursor = conexao.cursor()
        executados = 0
        try:
            for comando in comandos:
                if comando == _COMMIT:
                    await conexao.commit()
                    continue
                await cursor.execute(comando)
                executados += 1
        except oracledb.Error as exc:
            await conexao.rollback()
            return ResultadoExecucao(sucesso=False, comandos_executados=executados, detalhe_erro=str(exc))
        finally:
            cursor.close()
        # Sem commit extra aqui: `gerar_script` garante que o script sempre termina em
        # COMMIT (Seção 10.1), então o último marcador do loop já cobriu tudo.
        return ResultadoExecucao(sucesso=True, comandos_executados=executados)
    finally:
        await conexao.close()
