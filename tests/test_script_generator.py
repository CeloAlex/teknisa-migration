import pytest

from app.metadata.schemas import CampoMetadata, ScriptMetadata, TemplateMetadata
from app.scripts.generator import ContextoExecucao, ScriptNaoConfigurado, gerar_script


def _template(com_script: bool = True) -> TemplateMetadata:
    campos = [
        CampoMetadata(
            ordem=1, origem="A", rotulo="Banco", campo="CDBANCO", marcador="@CDBANCO@",
            destino_tabela="AGENCIA", destino_coluna="CDBANCO", tipo="texto",
            tamanho_maximo=3, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=True, gerador_pk=False,
        ),
        CampoMetadata(
            ordem=2, origem="B", rotulo="Cd. Agência", campo="CDAGENCIA", marcador="@CDAGENCIA@",
            destino_tabela="AGENCIA", destino_coluna="CDAGENCIA", tipo="texto",
            tamanho_maximo=4, obrigatorio=True, valor_padrao=None, regra_conversao="trim",
            eh_pk=True, gerador_pk=False,
        ),
        CampoMetadata(
            ordem=3, origem="parametro_execucao.NRORG", rotulo="Organização", campo="NRORG",
            marcador="@NRORG@", destino_tabela="AGENCIA", destino_coluna="NRORG",
            tipo="numerico", tamanho_maximo=None, obrigatorio=True, valor_padrao=None,
            regra_conversao=None, eh_pk=False, gerador_pk=False,
        ),
    ]
    scripts = {}
    if com_script:
        scripts["INCLUSAO"] = ScriptMetadata(
            operacao="INCLUSAO",
            dialeto_banco="ORACLE",
            template_sql=(
                "INSERT INTO AGENCIA ( CDBANCO, CDAGENCIA, NRORG, CDOPERINCLUSAO ) "
                "VALUES ( '@CDBANCO@', '@CDAGENCIA@', @NRORG@, '@USUARIO_TECNICO@' );"
            ),
            template_rollback="DELETE FROM AGENCIA WHERE NRORG = @NRORG@ AND CDBANCO = '@CDBANCO@';",
        )
    return TemplateMetadata(
        codigo="AGENCIAS_BANCARIAS", nome="Agências Bancárias", versao="1.0",
        sheet_name="Sheet1", header_row=1, data_start_row=2, campos=campos, scripts=scripts,
    )


def test_gera_um_insert_por_linha_com_marcadores_substituidos() -> None:
    template = _template()
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")
    linhas = [
        {"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410},
        {"CDBANCO": "033", "CDAGENCIA": "0125", "NRORG": 1410},
    ]

    script = gerar_script(linhas, template, contexto)

    assert script.count("INSERT INTO AGENCIA") == 2
    assert "'001', '0019', 1410, '000000099991'" in script
    assert "'033', '0125', 1410, '000000099991'" in script
    assert "@" not in script.replace("COMMIT;", "")  # nenhum marcador sobrou sem substituir
    assert script.strip().endswith("COMMIT;")


def test_script_de_linhas_vazias_gera_apenas_commit() -> None:
    template = _template()
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")

    script = gerar_script([], template, contexto)

    assert script.strip() == "COMMIT;"


def test_operacao_sem_script_configurado_leva_a_erro_explicito() -> None:
    template = _template(com_script=False)
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")

    with pytest.raises(ScriptNaoConfigurado):
        gerar_script([{"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410}], template, contexto)
