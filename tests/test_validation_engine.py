from app.metadata.schemas import CampoMetadata, TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.engine import validar_linha, verificar_duplicatas_lote


def _template() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="A", rotulo="Banco", campo="CDBANCO", marcador="@CDBANCO@",
            destino_tabela="AGENCIA", destino_coluna="CDBANCO", tipo="texto",
            tamanho_maximo=3, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=True, gerador_pk=False,
        ),
        CampoMetadata(
            ordem=2, origem="C", rotulo="Agência", campo="NMAGENCIA", marcador="@NMAGENCIA@",
            destino_tabela="AGENCIA", destino_coluna="NMAGENCIA", tipo="texto",
            tamanho_maximo=60, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=False, gerador_pk=False,
        ),
    ]
    return TemplateMetadata(
        codigo="TESTE", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_campo_obrigatorio_vazio_gera_erro_impeditivo() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "", "NMAGENCIA": "Agência Centro"}, template)
    assert len(resultados) == 1
    assert resultados[0].campo == "CDBANCO"
    assert resultados[0].regra == "obrigatoriedade"
    assert resultados[0].classificacao == Classificacao.ERRO_IMPEDITIVO


def test_campo_acima_do_tamanho_maximo_gera_alerta_nao_bloqueante() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "ABCD", "NMAGENCIA": "Agência Centro"}, template)
    assert len(resultados) == 1
    assert resultados[0].campo == "CDBANCO"
    assert resultados[0].regra == "tamanho_maximo"
    assert resultados[0].classificacao == Classificacao.ALERTA


def test_campo_obrigatorio_vazio_nao_avalia_tamanho_do_mesmo_campo() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "", "NMAGENCIA": "Agência Centro"}, template)
    regras = [r.regra for r in resultados if r.campo == "CDBANCO"]
    assert regras == ["obrigatoriedade"]


def test_linha_valida_nao_gera_nenhum_resultado() -> None:
    template = _template()
    resultados = validar_linha({"CDBANCO": "001", "NMAGENCIA": "Agência Centro"}, template)
    assert resultados == []


def _template_com_fk() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="D", rotulo="Nr Estrutura", campo="NRESTRUTURAM", marcador="@NRESTRUTURAM@",
            destino_tabela="GPE_MOVIMENTACAO", destino_coluna="NRESTRUTURAM", tipo="texto",
            tamanho_maximo=None, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=False, gerador_pk=False, fk_template_codigo="ESTRUTURA", fk_campo="NRESTRUTURA",
        ),
    ]
    return TemplateMetadata(
        codigo="MOVIMENTACOES_ESTRUTURA", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_fk_nao_encontrada_no_template_referenciado_gera_erro_impeditivo() -> None:
    """Reproduz o caso relatado pelo usuário: Estrutura tem "9272000000001_001", mas
    Movimentações referencia "9272000000001001" (sem o "_") — a subquery do script
    resolveria pra NULL só na hora de aplicar; a validação antecipa isso."""
    template = _template_com_fk()
    valores_fk = {"NRESTRUTURAM": {"9272000000001_001"}}

    resultados = validar_linha({"NRESTRUTURAM": "9272000000001001"}, template, valores_fk)

    assert len(resultados) == 1
    assert resultados[0].regra == "fk_nao_encontrada"
    assert resultados[0].classificacao == Classificacao.ERRO_IMPEDITIVO
    assert "ESTRUTURA" in resultados[0].valor_esperado


def test_fk_encontrada_no_template_referenciado_nao_gera_erro() -> None:
    template = _template_com_fk()
    valores_fk = {"NRESTRUTURAM": {"9272000000001_001"}}

    resultados = validar_linha({"NRESTRUTURAM": "9272000000001_001"}, template, valores_fk)

    assert resultados == []


def test_fk_sem_dado_de_comparacao_nao_bloqueia() -> None:
    """Template referenciado sem nenhuma linha importada nesta migração (FK aponta pra dado
    que já existia no Oracle antes desta migração) — sem dado local pra comparar, a
    validação não deveria reprovar a linha."""
    template = _template_com_fk()

    resultados = validar_linha({"NRESTRUTURAM": "qualquer-coisa"}, template, valores_fk={})
    assert resultados == []

    resultados_sem_fk = validar_linha({"NRESTRUTURAM": "qualquer-coisa"}, template)
    assert resultados_sem_fk == []


def _template_com_dominio() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="A", rotulo="Tipo de Estrutura", campo="NRTPESTRUTURA",
            marcador="@NRTPESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="NRTIPOESTRUTURA",
            tipo="numerico", tamanho_maximo=None, obrigatorio=True, valor_padrao=None,
            regra_conversao=None, eh_pk=False, gerador_pk=False, dominio_valores="1,2,3",
        ),
    ]
    return TemplateMetadata(
        codigo="ESTRUTURA", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_valor_fora_do_dominio_gera_alerta_nao_bloqueante() -> None:
    """Reproduz o feedback do piloto NUTRIBEM-TOTAL: tipo de estrutura 75 não existe no
    domínio conhecido — deve alertar, não bloquear (a equipe pode cadastrar um tipo novo)."""
    template = _template_com_dominio()
    resultados = validar_linha({"NRTPESTRUTURA": "75"}, template)
    assert len(resultados) == 1
    assert resultados[0].regra == "fora_do_dominio"
    assert resultados[0].classificacao == Classificacao.ALERTA


def test_valor_dentro_do_dominio_nao_gera_alerta() -> None:
    template = _template_com_dominio()
    resultados = validar_linha({"NRTPESTRUTURA": "2"}, template)
    assert resultados == []


def _template_com_ausencia_condicional() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="A", rotulo="Tipo de Estrutura", campo="NRTPESTRUTURA",
            marcador="@NRTPESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="NRTIPOESTRUTURA",
            tipo="numerico", tamanho_maximo=None, obrigatorio=True, valor_padrao=None,
            regra_conversao=None, eh_pk=False, gerador_pk=False,
        ),
        CampoMetadata(
            ordem=2, origem="F", rotulo="CNPJ", campo="CNPJ", marcador="@CNPJ@",
            destino_tabela="ESTRUTURAH", destino_coluna="CDCNPJESTRUT", tipo="texto",
            tamanho_maximo=14, obrigatorio=False, valor_padrao=None, regra_conversao=None,
            eh_pk=False, gerador_pk=False,
            alerta_se_vazio_quando_campo="NRTPESTRUTURA", alerta_se_vazio_quando_valores="1,2,20",
        ),
    ]
    return TemplateMetadata(
        codigo="ESTRUTURA", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_ausencia_condicional_gera_alerta_quando_gatilho_presente() -> None:
    """CNPJ vazio numa estrutura tipo 1 (empresa) gera responsabilidade pras áreas
    resolverem, mas não impede a importação (Seção 1 do feedback do piloto)."""
    template = _template_com_ausencia_condicional()
    resultados = validar_linha({"NRTPESTRUTURA": "1", "CNPJ": ""}, template)
    assert len(resultados) == 1
    assert resultados[0].campo == "CNPJ"
    assert resultados[0].regra == "ausencia_condicional"
    assert resultados[0].classificacao == Classificacao.ALERTA


def test_ausencia_condicional_nao_dispara_fora_do_gatilho() -> None:
    template = _template_com_ausencia_condicional()
    resultados = validar_linha({"NRTPESTRUTURA": "6", "CNPJ": ""}, template)
    assert resultados == []


def test_ausencia_condicional_nao_dispara_quando_campo_preenchido() -> None:
    template = _template_com_ausencia_condicional()
    resultados = validar_linha({"NRTPESTRUTURA": "1", "CNPJ": "12345678000199"}, template)
    assert resultados == []


def _template_com_duplicata() -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="D", rotulo="Nº Estrutura", campo="NRESTRUTURA", marcador="@NRESTRUTURA@",
            destino_tabela="ESTRUTURAM", destino_coluna="CDINTESTRUTURA", tipo="texto",
            tamanho_maximo=None, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=False, gerador_pk=False, duplicata_no_lote="erro_impeditivo",
        ),
        CampoMetadata(
            ordem=2, origem="F", rotulo="CNPJ", campo="CNPJ", marcador="@CNPJ@",
            destino_tabela="ESTRUTURAH", destino_coluna="CDCNPJESTRUT", tipo="texto",
            tamanho_maximo=14, obrigatorio=False, valor_padrao=None, regra_conversao=None,
            eh_pk=False, gerador_pk=False,
            duplicata_no_lote="alerta", duplicata_agrupado_por="NRTPESTRUTURA",
        ),
        CampoMetadata(
            ordem=3, origem="A", rotulo="Tipo de Estrutura", campo="NRTPESTRUTURA",
            marcador="@NRTPESTRUTURA@", destino_tabela="ESTRUTURAM", destino_coluna="NRTIPOESTRUTURA",
            tipo="numerico", tamanho_maximo=None, obrigatorio=True, valor_padrao=None,
            regra_conversao=None, eh_pk=False, gerador_pk=False,
        ),
    ]
    return TemplateMetadata(
        codigo="ESTRUTURA", nome="Teste", versao="1.0", sheet_name="Dados",
        header_row=1, data_start_row=2, campos=campos,
    )


def test_duplicata_no_lote_sem_agrupamento_gera_erro_impeditivo_nas_duas_linhas() -> None:
    """Reproduz o feedback do piloto: NRESTRUTURA repetido quebra a integração com
    Vínculo/Movimentações, que usam esse valor como chave — precisa ser rejeitado."""
    template = _template_com_duplicata()
    linhas = [
        (1, {"NRESTRUTURA": "9272", "CNPJ": "111", "NRTPESTRUTURA": "10"}),
        (2, {"NRESTRUTURA": "9272", "CNPJ": "222", "NRTPESTRUTURA": "20"}),
        (3, {"NRESTRUTURA": "9273", "CNPJ": "333", "NRTPESTRUTURA": "10"}),
    ]

    resultados = verificar_duplicatas_lote(linhas, template)

    assert set(resultados.keys()) == {1, 2}
    for staging_id in (1, 2):
        assert len(resultados[staging_id]) == 1
        assert resultados[staging_id][0].regra == "duplicata_no_lote"
        assert resultados[staging_id][0].classificacao == Classificacao.ERRO_IMPEDITIVO
    assert 3 not in resultados


def test_duplicata_no_lote_agrupada_so_conta_com_mesmo_valor_do_agrupador() -> None:
    """CNPJ duplicado só é alerta quando as duas linhas têm o mesmo NRTPESTRUTURA — CNPJ
    repetido entre tipos diferentes de estrutura não é anômalo (confirmado pelo usuário)."""
    template = _template_com_duplicata()
    linhas = [
        (1, {"NRESTRUTURA": "A", "CNPJ": "999", "NRTPESTRUTURA": "10"}),
        (2, {"NRESTRUTURA": "B", "CNPJ": "999", "NRTPESTRUTURA": "10"}),
        (3, {"NRESTRUTURA": "C", "CNPJ": "999", "NRTPESTRUTURA": "20"}),
    ]

    resultados = verificar_duplicatas_lote(linhas, template)

    assert set(resultados.keys()) == {1, 2}
    for staging_id in (1, 2):
        assert resultados[staging_id][0].classificacao == Classificacao.ALERTA
    assert 3 not in resultados


def test_duplicata_no_lote_ignora_valores_vazios() -> None:
    template = _template_com_duplicata()
    linhas = [
        (1, {"NRESTRUTURA": "", "CNPJ": "", "NRTPESTRUTURA": "10"}),
        (2, {"NRESTRUTURA": "", "CNPJ": "", "NRTPESTRUTURA": "10"}),
    ]

    resultados = verificar_duplicatas_lote(linhas, template)

    assert resultados == {}
