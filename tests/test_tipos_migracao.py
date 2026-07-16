from httpx import AsyncClient


async def test_listar_tipos_migracao_inclui_os_integrais(client: AsyncClient) -> None:
    response = await client.get("/tipos-migracao")
    assert response.status_code == 200
    codigos = {item["codigo"] for item in response.json()}
    assert "MIG_INTEGRAL_INDIVIDUAL" in codigos
    assert "MIG_INTEGRAL_ONBOARDING" in codigos


async def test_tipo_individual_nao_tem_sequencia_obrigatoria(client: AsyncClient) -> None:
    response = await client.get("/tipos-migracao/MIG_INTEGRAL_INDIVIDUAL")
    assert response.status_code == 200
    body = response.json()
    assert body["sequencia_obrigatoria"] is False
    assert len(body["templates"]) == 13
    # nenhum template obrigatório nem com dependência travada neste tipo
    assert all(t["obrigatorio"] is False for t in body["templates"])
    assert all(t["depende_de"] == [] for t in body["templates"])


async def test_tipo_onboarding_aplica_grafo_de_dependencias_da_secao_26_3(client: AsyncClient) -> None:
    response = await client.get("/tipos-migracao/MIG_INTEGRAL_ONBOARDING")
    assert response.status_code == 200
    body = response.json()
    assert body["sequencia_obrigatoria"] is True

    por_codigo = {t["template_codigo"]: t for t in body["templates"]}
    assert set(por_codigo["VINCULO"]["depende_de"]) == {
        "AGENCIAS_BANCARIAS", "ESTRUTURA", "OCUPACAO", "ESCALA",
    }
    assert por_codigo["ALTERACAO_SALARIAL"]["depende_de"] == ["VINCULO"]
    assert set(por_codigo["ALTERACAO_ESCALA"]["depende_de"]) == {"VINCULO", "ESCALA"}
    assert set(por_codigo["FICHA_FINANCEIRA"]["depende_de"]) == {"VINCULO", "EVENTOS"}
    assert por_codigo["AGENCIAS_BANCARIAS"]["depende_de"] == []


async def test_tipo_migracao_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.get("/tipos-migracao/NAO_EXISTE")
    assert response.status_code == 404
