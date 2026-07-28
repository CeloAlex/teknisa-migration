import oracledb

from app.execution.engine import ResultadoExecucao, executar_script


class _FakeCursor:
    def __init__(self, falhar_em: set[str] | None = None) -> None:
        self.executados: list[str] = []
        self.closed = False
        self._falhar_em = falhar_em or set()

    async def execute(self, comando: str) -> None:
        if comando in self._falhar_em:
            raise oracledb.Error(f"erro simulado: {comando}")
        self.executados.append(comando)

    def close(self) -> None:
        self.closed = True


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return self._cursor

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def close(self) -> None:
        self.closed = True


async def test_commita_em_cada_marcador_de_commit(monkeypatch) -> None:
    cursor = _FakeCursor()
    conexao = _FakeConnection(cursor)

    async def _fake_conectar():
        return conexao

    monkeypatch.setattr("app.execution.engine.conectar", _fake_conectar)

    sql = "INSERT INTO A VALUES (1);\nCOMMIT;\nINSERT INTO A VALUES (2);\nCOMMIT;"
    resultado = await executar_script(sql)

    assert resultado == ResultadoExecucao(sucesso=True, comandos_executados=2)
    assert cursor.executados == ["INSERT INTO A VALUES (1)", "INSERT INTO A VALUES (2)"]
    assert conexao.commits == 2  # um por marcador COMMIT do script — nenhum commit extra.
    assert conexao.rollbacks == 0
    assert cursor.closed is True
    assert conexao.closed is True


async def test_erro_nao_desfaz_lotes_ja_commitados(monkeypatch) -> None:
    """Reproduz o cenário do pedido do usuário: com COMMIT a cada linha, uma falha na
    linha 3 não deve desfazer as linhas 1 e 2, já commitadas antes dela."""
    cursor = _FakeCursor(falhar_em={"INSERT INTO A VALUES (3)"})
    conexao = _FakeConnection(cursor)

    async def _fake_conectar():
        return conexao

    monkeypatch.setattr("app.execution.engine.conectar", _fake_conectar)

    sql = (
        "INSERT INTO A VALUES (1);\nCOMMIT;\n"
        "INSERT INTO A VALUES (2);\nCOMMIT;\n"
        "INSERT INTO A VALUES (3);\nCOMMIT;"
    )
    resultado = await executar_script(sql)

    assert resultado.sucesso is False
    assert resultado.comandos_executados == 2  # linhas 1 e 2 tiveram sucesso.
    assert "INSERT INTO A VALUES (3)" in resultado.detalhe_erro
    assert cursor.executados == ["INSERT INTO A VALUES (1)", "INSERT INTO A VALUES (2)"]
    assert conexao.commits == 3  # os 3 marcadores COMMIT do script rodam normalmente.
    assert conexao.rollbacks == 0  # ninguém é revertido — Oracle não invalida a transação
    #                                 por uma falha de statement isolado, ao contrário do Postgres.
    assert cursor.closed is True
    assert conexao.closed is True


async def test_continua_apos_erro_e_acumula_todos_os_erros(monkeypatch) -> None:
    """Pedido explícito do usuário: em vez de parar no primeiro problema, a execução deve
    seguir pros comandos seguintes e devolver TODOS os erros encontrados, não só o
    primeiro — dá o diagnóstico completo numa passada só, sem precisar de tentativa após
    tentativa corrigindo um erro de cada vez."""
    cursor = _FakeCursor(falhar_em={"INSERT INTO A VALUES (2)", "INSERT INTO A VALUES (4)"})
    conexao = _FakeConnection(cursor)

    async def _fake_conectar():
        return conexao

    monkeypatch.setattr("app.execution.engine.conectar", _fake_conectar)

    sql = (
        "INSERT INTO A VALUES (1);\n"
        "INSERT INTO A VALUES (2);\n"
        "INSERT INTO A VALUES (3);\n"
        "INSERT INTO A VALUES (4);\n"
        "COMMIT;"
    )
    resultado = await executar_script(sql)

    assert resultado.sucesso is False
    assert resultado.comandos_executados == 2  # linhas 1 e 3, as únicas sem erro.
    assert cursor.executados == ["INSERT INTO A VALUES (1)", "INSERT INTO A VALUES (3)"]
    assert [e.indice for e in resultado.erros] == [2, 4]
    assert resultado.erros[0].comando == "INSERT INTO A VALUES (2)"
    assert "INSERT INTO A VALUES (2)" in resultado.erros[0].mensagem
    assert resultado.erros[1].comando == "INSERT INTO A VALUES (4)"
    assert resultado.detalhe_erro == resultado.erros[0].mensagem  # compatibilidade: 1º erro
    assert conexao.commits == 1  # o único marcador COMMIT do script, com o que sobrou.
