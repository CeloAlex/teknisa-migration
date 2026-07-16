from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def reservar_proximo_codigo(session: AsyncSession, nr_org: int, cd_contador: str, seed: int) -> int:
    """Key Resolution Service (Anexo A / Seção 6.1) — equivalente à tabela NOVOCODIGO e à
    fórmula "Busca de PK's livres": reserva atomicamente o próximo código disponível por
    organização e por contador.

    O UPSERT abaixo faz o papel do bloqueio otimista citado na especificação: a primeira
    reserva de um (nr_org, cd_contador) semeia o contador em `seed + 1`; toda reserva
    seguinte incrementa `nr_proximo` em uma única instrução atômica do Postgres — duas
    execuções concorrentes nunca recebem o mesmo valor, sem precisar de uma transação
    explícita mais longa ou de um SELECT ... FOR UPDATE."""
    resultado = await session.execute(
        text(
            """
            INSERT INTO novocodigo (nr_org, cd_contador, nr_proximo)
            VALUES (:nr_org, :cd_contador, :proximo_seed)
            ON CONFLICT (nr_org, cd_contador)
            DO UPDATE SET nr_proximo = novocodigo.nr_proximo + 1
            RETURNING nr_proximo
            """
        ),
        {"nr_org": nr_org, "cd_contador": cd_contador, "proximo_seed": seed + 1},
    )
    return resultado.scalar_one()
