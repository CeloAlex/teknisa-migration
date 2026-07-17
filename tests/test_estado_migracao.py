from app.migracoes.estado import ResumoTemplate, recalcular_status
from app.models.migracao import MigracaoStatus, TemplateStatus


def _template(**overrides) -> ResumoTemplate:
    base = dict(
        obrigatorio=True, status=TemplateStatus.PENDENTE.value, dados_aprovados=False,
        script_gerado=False, script_aprovado=False, aplicado=False, aplicado_com_erro=False,
        teve_alerta=False,
    )
    base.update(overrides)
    return ResumoTemplate(**base)


def test_todos_pendentes_fica_aguardando_arquivos() -> None:
    templates = [_template(), _template()]
    assert recalcular_status(MigracaoStatus.CRIADA.value, templates) == MigracaoStatus.AGUARDANDO_ARQUIVOS


def test_algum_em_validacao_fica_em_validacao() -> None:
    templates = [
        _template(status=TemplateStatus.VALIDADO.value, dados_aprovados=False),
        _template(status=TemplateStatus.EM_VALIDACAO.value),
    ]
    assert recalcular_status(MigracaoStatus.EM_VALIDACAO.value, templates) == MigracaoStatus.EM_VALIDACAO


def test_algum_com_inconsistencias_fica_aguardando_correcao() -> None:
    templates = [
        _template(status=TemplateStatus.VALIDADO.value),
        _template(status=TemplateStatus.COM_INCONSISTENCIAS.value),
    ]
    assert recalcular_status(MigracaoStatus.EM_VALIDACAO.value, templates) == MigracaoStatus.AGUARDANDO_CORRECAO


def test_todos_validados_mas_nem_todos_aprovados_fica_aguardando_aprovacao() -> None:
    templates = [
        _template(status=TemplateStatus.VALIDADO.value, dados_aprovados=True),
        _template(status=TemplateStatus.VALIDADO.value, dados_aprovados=False),
    ]
    assert recalcular_status(MigracaoStatus.EM_VALIDACAO.value, templates) == MigracaoStatus.AGUARDANDO_APROVACAO


def test_dados_aprovados_mas_sem_script_fica_pronta_para_geracao_scripts() -> None:
    templates = [_template(status=TemplateStatus.VALIDADO.value, dados_aprovados=True)]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APROVACAO.value, templates) == MigracaoStatus.PRONTA_PARA_GERACAO_SCRIPTS


def test_script_gerado_mas_nao_aprovado_fica_scripts_gerados() -> None:
    templates = [_template(status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True)]
    assert recalcular_status(MigracaoStatus.PRONTA_PARA_GERACAO_SCRIPTS.value, templates) == MigracaoStatus.SCRIPTS_GERADOS


def test_script_aprovado_fica_aguardando_aplicacao() -> None:
    templates = [
        _template(status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True, script_aprovado=True)
    ]
    assert recalcular_status(MigracaoStatus.SCRIPTS_GERADOS.value, templates) == MigracaoStatus.AGUARDANDO_APLICACAO


def test_aplicacao_parcial_fica_em_execucao() -> None:
    aprovado = dict(status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True, script_aprovado=True)
    templates = [_template(**aprovado, aplicado=True), _template(**aprovado, aplicado=False)]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.EM_EXECUCAO


def test_aplicado_com_erro_fica_com_erro() -> None:
    templates = [
        _template(
            status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True,
            script_aprovado=True, aplicado_com_erro=True,
        )
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.COM_ERRO


def test_todos_aplicados_sem_alerta_fica_concluida() -> None:
    templates = [
        _template(
            status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True,
            script_aprovado=True, aplicado=True,
        )
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.CONCLUIDA


def test_todos_aplicados_com_alerta_fica_concluida_com_alertas() -> None:
    templates = [
        _template(
            status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True,
            script_aprovado=True, aplicado=True, teve_alerta=True,
        )
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.CONCLUIDA_COM_ALERTAS


def test_templates_nao_obrigatorios_sao_ignorados_no_calculo() -> None:
    templates = [
        _template(status=TemplateStatus.VALIDADO.value, dados_aprovados=True, script_gerado=True, script_aprovado=True, aplicado=True),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.CONCLUIDA


def test_estado_terminal_nunca_e_recalculado() -> None:
    templates = [_template(status=TemplateStatus.PENDENTE.value)]
    assert recalcular_status(MigracaoStatus.CANCELADA.value, templates) == MigracaoStatus.CANCELADA


# --- tipo de migração sem NENHUM template obrigatório (ex.: pacote de eventos eSocial —
# Seção "consolidação eSocial") — o operador escolhe livremente quais templates processar;
# os nunca tocados (PENDENTE) não podem travar a migração para sempre. ---


def test_todos_opcionais_todos_pendentes_fica_aguardando_arquivos() -> None:
    templates = [
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
    ]
    assert recalcular_status(MigracaoStatus.CRIADA.value, templates) == MigracaoStatus.AGUARDANDO_ARQUIVOS


def test_todos_opcionais_um_concluido_e_outros_intocados_fica_concluida() -> None:
    templates = [
        _template(
            obrigatorio=False, status=TemplateStatus.VALIDADO.value, dados_aprovados=True,
            script_gerado=True, script_aprovado=True, aplicado=True,
        ),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.CONCLUIDA


def test_todos_opcionais_um_ainda_em_validacao_nao_conclui() -> None:
    concluido = dict(
        obrigatorio=False, status=TemplateStatus.VALIDADO.value, dados_aprovados=True,
        script_gerado=True, script_aprovado=True, aplicado=True,
    )
    templates = [
        _template(**concluido),
        _template(obrigatorio=False, status=TemplateStatus.EM_VALIDACAO.value),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
    ]
    assert recalcular_status(MigracaoStatus.EM_VALIDACAO.value, templates) == MigracaoStatus.EM_VALIDACAO


def test_todos_opcionais_um_com_erro_de_aplicacao_fica_com_erro() -> None:
    templates = [
        _template(
            obrigatorio=False, status=TemplateStatus.VALIDADO.value, dados_aprovados=True,
            script_gerado=True, script_aprovado=True, aplicado_com_erro=True,
        ),
        _template(obrigatorio=False, status=TemplateStatus.PENDENTE.value),
    ]
    assert recalcular_status(MigracaoStatus.AGUARDANDO_APLICACAO.value, templates) == MigracaoStatus.COM_ERRO
