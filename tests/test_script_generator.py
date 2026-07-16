import pytest

from app.metadata.schemas import CampoMetadata, ScriptMetadata, TemplateMetadata
from app.scripts.generator import ContextoExecucao, ScriptNaoConfigurado, gerar_script


def _campo(**overrides) -> CampoMetadata:
    base = dict(
        ordem=1, origem="A", rotulo="Campo", campo="CAMPO", marcador="@CAMPO@",
        destino_tabela="TABELA", destino_coluna="CAMPO", tipo="texto", tamanho_maximo=None,
        obrigatorio=False, valor_padrao=None, regra_conversao=None, eh_pk=False,
        gerador_pk=False, gerador_pk_contador=None, gerador_pk_seed=None,
    )
    base.update(overrides)
    return CampoMetadata(**base)


def _template(com_script: bool = True) -> TemplateMetadata:
    campos = [
        _campo(ordem=1, origem="A", campo="CDBANCO", marcador="@CDBANCO@", tamanho_maximo=3, obrigatorio=True, regra_conversao="trim", eh_pk=True),
        _campo(ordem=2, origem="B", campo="CDAGENCIA", marcador="@CDAGENCIA@", tamanho_maximo=4, obrigatorio=True, regra_conversao="trim", eh_pk=True),
        _campo(ordem=3, origem="parametro_execucao.NRORG", campo="NRORG", marcador="@NRORG@", tipo="numerico", obrigatorio=True),
    ]
    scripts: dict[str, list[ScriptMetadata]] = {}
    if com_script:
        scripts["INCLUSAO"] = [
            ScriptMetadata(
                operacao="INCLUSAO",
                dialeto_banco="ORACLE",
                ordem=1,
                condicao_campo=None,
                template_sql=(
                    "INSERT INTO AGENCIA ( CDBANCO, CDAGENCIA, NRORG, CDOPERINCLUSAO ) "
                    "VALUES ( '@CDBANCO@', '@CDAGENCIA@', @NRORG@, '@USUARIO_TECNICO@' );"
                ),
                template_rollback="DELETE FROM AGENCIA WHERE NRORG = @NRORG@ AND CDBANCO = '@CDBANCO@';",
            )
        ]
    return TemplateMetadata(
        codigo="AGENCIAS_BANCARIAS", nome="Agências Bancárias", versao="1.0",
        sheet_name="Sheet1", header_row=1, data_start_row=2, campos=campos, scripts=scripts,
    )


async def test_gera_um_insert_por_linha_com_marcadores_substituidos() -> None:
    template = _template()
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")
    linhas = [
        {"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410},
        {"CDBANCO": "033", "CDAGENCIA": "0125", "NRORG": 1410},
    ]

    # Nenhum campo com gerador_pk=True nesta linha do dicionário: o Key Resolution Service
    # nunca é acionado, então a sessão de banco não precisa existir de verdade neste teste.
    script = await gerar_script(None, linhas, template, contexto)

    assert script.count("INSERT INTO AGENCIA") == 2
    assert "'001', '0019', 1410, '000000099991'" in script
    assert "'033', '0125', 1410, '000000099991'" in script
    assert "@" not in script.replace("COMMIT;", "")  # nenhum marcador sobrou sem substituir
    assert script.strip().endswith("COMMIT;")


async def test_script_de_linhas_vazias_gera_apenas_commit() -> None:
    template = _template()
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")

    script = await gerar_script(None, [], template, contexto)

    assert script.strip() == "COMMIT;"


async def test_operacao_sem_script_configurado_leva_a_erro_explicito() -> None:
    template = _template(com_script=False)
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")

    with pytest.raises(ScriptNaoConfigurado):
        await gerar_script(None, [{"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410}], template, contexto)


async def test_bloco_condicional_e_pulado_quando_condicao_falsa() -> None:
    template = _template()
    template.scripts["INCLUSAO"].append(
        ScriptMetadata(
            operacao="INCLUSAO",
            dialeto_banco="ORACLE",
            ordem=2,
            condicao_campo="_TEM_ENDERECO",
            template_sql="INSERT INTO ENDERECO ( CDBANCO ) VALUES ( '@CDBANCO@' );",
            template_rollback=None,
        )
    )
    contexto = ContextoExecucao(nr_org=1410, usuario_tecnico="000000099991")

    sem_endereco = await gerar_script(
        None, [{"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410, "_TEM_ENDERECO": False}], template, contexto
    )
    assert "INSERT INTO ENDERECO" not in sem_endereco

    com_endereco = await gerar_script(
        None, [{"CDBANCO": "001", "CDAGENCIA": "0019", "NRORG": 1410, "_TEM_ENDERECO": True}], template, contexto
    )
    assert "INSERT INTO ENDERECO" in com_endereco
