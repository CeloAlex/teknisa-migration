import random

from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.usuario import Papel
from tests.conftest import login


async def _login_admin(client: AsyncClient, usuario_teste) -> None:
    usuario, senha = await usuario_teste(Papel.ADMINISTRADOR.value)
    await login(client, usuario.email, senha)


async def _apagar_organizacao(nr_org: int) -> None:
    """Este teste cria a organização direto pela tela de admin (não pelo fixture
    `nr_org_teste`), então precisa apagar por conta própria ao final."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM organizacao WHERE nr_org = :nr_org"), {"nr_org": nr_org})
        await session.commit()


async def _apagar_tipo_migracao(codigo: str) -> None:
    """Este teste cria o tipo de migração pela tela de admin, então precisa apagar por
    conta própria ao final — mesmo motivo do `_apagar_organizacao`/`_apagar_template`."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM tipo_migracao WHERE codigo = :codigo"), {"codigo": codigo})
        await session.commit()


async def _apagar_template(codigo: str) -> None:
    """Os testes de admin de template criam pela tela (não por uma migração Alembic), então
    precisam apagar por conta própria ao final — mesmo motivo do `_apagar_organizacao`.
    Ordem de FK: template_campo/template_script antes de template."""
    async with AsyncSessionLocal() as session:
        template_id = (
            await session.execute(text("SELECT id FROM template WHERE codigo = :codigo"), {"codigo": codigo})
        ).scalar_one_or_none()
        if template_id is None:
            return
        await session.execute(text("DELETE FROM template_campo WHERE template_id = :id"), {"id": template_id})
        await session.execute(text("DELETE FROM template_script WHERE template_id = :id"), {"id": template_id})
        await session.execute(text("DELETE FROM template WHERE id = :id"), {"id": template_id})
        await session.commit()


async def test_criar_e_listar_operador(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    await _login_admin(client, usuario_teste)
    email = f"novo{random.randint(1000, 9999)}@example.com"

    criar = await client.post(
        "/portal-migration/admin/operadores/novo",
        data={
            "nome": "Operador De Teste",
            "email": email,
            "cargo": "QA",
            "papel": Papel.OPERADOR.value,
            "nr_org": nr_org_teste,
            "senha": "senha-teste-123",
        },
        follow_redirects=False,
    )
    assert criar.status_code == 303

    listagem = await client.get("/portal-migration/admin/operadores")
    assert listagem.status_code == 200
    assert "Operador De Teste" in listagem.text


async def test_criar_operador_com_email_duplicado_falha(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    await _login_admin(client, usuario_teste)
    existente, _ = await usuario_teste(Papel.OPERADOR.value, nr_org=nr_org_teste)

    resposta = await client.post(
        "/portal-migration/admin/operadores/novo",
        data={
            "nome": "Duplicado",
            "email": existente.email,
            "papel": Papel.OPERADOR.value,
            "nr_org": nr_org_teste,
            "senha": "senha-teste-123",
        },
    )
    assert resposta.status_code == 400
    assert "Já existe um operador" in resposta.text


async def test_criar_e_listar_organizacao(client: AsyncClient, usuario_teste) -> None:
    await _login_admin(client, usuario_teste)
    nr_org = random.randint(10_000_000, 99_999_999)

    criar = await client.post(
        "/portal-migration/admin/organizacoes/nova",
        data={"nr_org": nr_org, "nome": "Organização Admin Teste"},
        follow_redirects=False,
    )
    assert criar.status_code == 303

    listagem = await client.get("/portal-migration/admin/organizacoes")
    assert "Organização Admin Teste" in listagem.text

    desativar = await client.post(f"/portal-migration/admin/organizacoes/{nr_org}/toggle-ativo", follow_redirects=False)
    assert desativar.status_code == 303
    listagem2 = await client.get("/portal-migration/admin/organizacoes")
    assert "Inativa" in listagem2.text

    await _apagar_organizacao(nr_org)


async def test_criar_template_e_adicionar_campo_e_script(client: AsyncClient, usuario_teste) -> None:
    await _login_admin(client, usuario_teste)
    codigo = f"TESTE_{random.randint(1000, 9999)}"

    criar = await client.post(
        "/portal-migration/admin/templates/novo",
        data={
            "codigo": codigo,
            "nome": "Template de Teste",
            "versao": "1.0",
            "formatos_aceitos": "XLSX",
            "sheet_name": "Sheet1",
            "header_row": 1,
            "data_start_row": 2,
        },
        follow_redirects=False,
    )
    assert criar.status_code == 303
    assert criar.headers["location"] == f"/portal-migration/admin/templates/{codigo}"

    adicionar_campo = await client.post(
        f"/portal-migration/admin/templates/{codigo}/campos/novo",
        data={
            "ordem": 1,
            "origem": "A",
            "rotulo": "Campo Teste",
            "campo": "CAMPOTESTE",
            "destino_tabela": "TABELA_TESTE",
            "destino_coluna": "COLUNA_TESTE",
            "tipo": "texto",
        },
        follow_redirects=False,
    )
    assert adicionar_campo.status_code == 303

    adicionar_script = await client.post(
        f"/portal-migration/admin/templates/{codigo}/scripts/novo",
        data={
            "operacao": "INCLUSAO",
            "dialeto_banco": "ORACLE",
            "ordem": 1,
            "template_sql": "INSERT INTO TABELA_TESTE (COLUNA_TESTE) VALUES (@CAMPOTESTE@);",
        },
        follow_redirects=False,
    )
    assert adicionar_script.status_code == 303

    detalhe = await client.get(f"/portal-migration/admin/templates/{codigo}")
    assert detalhe.status_code == 200
    assert "Campo Teste" in detalhe.text
    assert "INSERT INTO TABELA_TESTE" in detalhe.text

    await _apagar_template(codigo)


async def test_importar_ddl_popula_catalogo_e_alimenta_select_de_colunas(
    client: AsyncClient, usuario_teste
) -> None:
    await _login_admin(client, usuario_teste)
    codigo = f"TESTE_{random.randint(1000, 9999)}"
    nome_tabela = f"TAB_TESTE_{random.randint(100000, 999999)}"

    await client.post(
        "/portal-migration/admin/templates/novo",
        data={"codigo": codigo, "nome": "Template DDL", "versao": "1.0", "formatos_aceitos": "XLSX"},
    )

    ddl = f"""
      CREATE TABLE "FOLHA"."{nome_tabela}"
       (	"NRORG" NUMBER DEFAULT 1,
	"NRCHAVE" NUMBER,
	"DSNOME" VARCHAR2(60 BYTE)
       ) SEGMENT CREATION IMMEDIATE TABLESPACE "FOLHA" ;
      ALTER TABLE "FOLHA"."{nome_tabela}" MODIFY ("NRCHAVE" NOT NULL ENABLE);
    """.encode("utf-8")

    importar = await client.post(
        "/portal-migration/admin/catalogo-destino/importar",
        files={"arquivo": ("schema.sql", ddl, "text/plain")},
        data={"voltar": codigo},
        follow_redirects=False,
    )
    assert importar.status_code == 303
    assert importar.headers["location"] == f"/portal-migration/admin/templates/{codigo}"

    detalhe = await client.get(f"/portal-migration/admin/templates/{codigo}")
    assert detalhe.status_code == 200
    assert "1 tabela(s) e 3 coluna(s) importadas" in detalhe.text

    form_novo_campo = await client.get(f"/portal-migration/admin/templates/{codigo}/campos/novo")
    assert form_novo_campo.status_code == 200
    assert nome_tabela in form_novo_campo.text

    import re

    m = re.search(rf'<option value="(\d+)"[^>]*>{nome_tabela}</option>', form_novo_campo.text)
    assert m, "opção da tabela recém-importada não encontrada no select"
    tabela_id = m.group(1)

    colunas = await client.get(f"/portal-migration/admin/catalogo-destino/{tabela_id}/colunas")
    assert colunas.status_code == 200
    assert "NRCHAVE" in colunas.text
    assert "DSNOME" in colunas.text
    assert "NRORG" in colunas.text

    await _apagar_template(codigo)
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM catalogo_destino_coluna WHERE tabela_id = :id"), {"id": int(tabela_id)})
        await session.execute(text("DELETE FROM catalogo_destino_tabela WHERE id = :id"), {"id": int(tabela_id)})
        await session.commit()


async def test_criar_tipo_migracao_e_adicionar_template_e_dependencia(client: AsyncClient, usuario_teste) -> None:
    await _login_admin(client, usuario_teste)
    codigo_tipo = f"TIPO_TESTE_{random.randint(1000, 9999)}"

    criar_tipo = await client.post(
        "/portal-migration/admin/tipos-migracao/novo",
        data={"codigo": codigo_tipo, "nome": "Tipo de Teste", "banco_destino": "ORACLE", "modo_aplicacao": "SCRIPT"},
        follow_redirects=False,
    )
    assert criar_tipo.status_code == 303

    detalhe = await client.get(f"/portal-migration/admin/tipos-migracao/{codigo_tipo}")
    assert detalhe.status_code == 200
    assert "Tipo de Teste" in detalhe.text

    await _apagar_tipo_migracao(codigo_tipo)


async def test_operador_bloqueado_em_todas_as_telas_admin(client: AsyncClient, usuario_teste, nr_org_teste: int) -> None:
    usuario, senha = await usuario_teste(Papel.OPERADOR.value, nr_org=nr_org_teste)
    await login(client, usuario.email, senha)

    for caminho in [
        "/portal-migration/admin/operadores",
        "/portal-migration/admin/organizacoes",
        "/portal-migration/admin/templates",
        "/portal-migration/admin/tipos-migracao",
    ]:
        resposta = await client.get(caminho)
        assert resposta.status_code == 403, f"{caminho} deveria bloquear Operador"
