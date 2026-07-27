from app.metadata.schemas import CampoMetadata, TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.engine import validar_linha


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
