from dataclasses import dataclass, field
from typing import Literal

import oracledb

from app.destination.oracle import conectar


@dataclass(frozen=True, slots=True)
class ErroComando:
    """Um comando individual que falhou durante a execução — persistido depois pelo
    chamador (Seção 7.4/11) para dar rastreabilidade completa ao operador, não só o
    primeiro erro encontrado."""

    indice: int
    comando: str
    mensagem: str


@dataclass(frozen=True, slots=True)
class ResultadoExecucao:
    """Resultado de rodar um script gerado (Script Generator) contra o Oracle de destino."""

    sucesso: bool
    comandos_executados: int
    detalhe_erro: str | None = None
    erros: list[ErroComando] = field(default_factory=list)


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
    transação única: um erro não interrompe a execução — o Oracle não invalida a
    transação por uma falha de statement isolado (ao contrário do Postgres), então o
    comando problemático é pulado (registrado em `erros`) e os seguintes continuam
    normalmente, sendo commitados junto do resto do lote. Pedido explícito do usuário: dar
    o log de erro completo em vez de parar no primeiro problema."""
    comandos = _comandos(sql)
    conexao = await conectar()
    try:
        cursor = conexao.cursor()
        try:
            executados = 0
            erros: list[ErroComando] = []
            indice = 0
            for comando in comandos:
                if comando == _COMMIT:
                    await conexao.commit()
                    continue
                indice += 1
                try:
                    await cursor.execute(comando)
                    executados += 1
                except oracledb.Error as exc:
                    erros.append(ErroComando(indice=indice, comando=comando[:8000], mensagem=str(exc)))
        finally:
            cursor.close()
        # Sem commit extra aqui: `gerar_script` garante que o script sempre termina em
        # COMMIT (Seção 10.1), então o último marcador do loop já cobriu tudo — inclusive
        # comandos que vieram depois de algum erro pulado.
        return ResultadoExecucao(
            sucesso=not erros,
            comandos_executados=executados,
            detalhe_erro=erros[0].mensagem if erros else None,
            erros=erros,
        )
    finally:
        await conexao.close()
