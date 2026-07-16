import uuid

from app.db.session import AsyncSessionLocal
from app.keys.service import reservar_proximo_codigo


async def test_reservar_proximo_codigo_incrementa_a_partir_do_seed() -> None:
    contador = f"TESTE_{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as session:
        try:
            primeiro = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador, seed=100)
            segundo = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador, seed=100)
            terceiro = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador, seed=100)
            await session.commit()
        finally:
            await session.rollback()

    assert (primeiro, segundo, terceiro) == (101, 102, 103)


async def test_contadores_diferentes_nao_interferem_entre_si() -> None:
    contador_a = f"TESTE_A_{uuid.uuid4().hex}"
    contador_b = f"TESTE_B_{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as session:
        try:
            a1 = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador_a, seed=0)
            b1 = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador_b, seed=50)
            a2 = await reservar_proximo_codigo(session, nr_org=9999, cd_contador=contador_a, seed=0)
            await session.commit()
        finally:
            await session.rollback()

    assert (a1, a2) == (1, 2)
    assert b1 == 51


async def test_organizacoes_diferentes_tem_contadores_independentes() -> None:
    contador = f"TESTE_ORG_{uuid.uuid4().hex}"
    async with AsyncSessionLocal() as session:
        try:
            org1 = await reservar_proximo_codigo(session, nr_org=1111, cd_contador=contador, seed=0)
            org2 = await reservar_proximo_codigo(session, nr_org=2222, cd_contador=contador, seed=0)
            await session.commit()
        finally:
            await session.rollback()

    assert org1 == 1
    assert org2 == 1
