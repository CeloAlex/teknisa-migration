from dataclasses import dataclass

from app.models.migracao import ESTADOS_TERMINAIS, MigracaoStatus, TemplateStatus


@dataclass(frozen=True, slots=True)
class ResumoTemplate:
    """Retrato mínimo de um `MigracaoTemplateStatus`, só com o que a máquina de estados
    precisa — mantém `recalcular_status` testável sem precisar de sessão de banco."""

    obrigatorio: bool
    status: str
    dados_aprovados: bool
    script_gerado: bool
    script_aprovado: bool
    aplicado: bool
    aplicado_com_erro: bool
    teve_alerta: bool


def recalcular_status(status_atual: str, templates: list[ResumoTemplate]) -> MigracaoStatus:
    """Deriva o status da migração (Seção 9.1/9.2) a partir do estado de cada template
    obrigatório. Estados terminais (cancelada/revertida) nunca são recalculados
    automaticamente — só uma ação explícita os altera."""
    if status_atual in {e.value for e in ESTADOS_TERMINAIS}:
        return MigracaoStatus(status_atual)

    obrigatorios = [t for t in templates if t.obrigatorio]
    if not obrigatorios:
        # Tipo de migração sem nenhum template obrigatório (ex.: pacote de eventos eSocial,
        # onde o operador escolhe livremente quais processar) — cai para os templates que
        # já foram tocados (status != PENDENTE); os nunca tocados são ignorados, mesmo
        # critério já usado para templates não-obrigatórios quando existe um obrigatório.
        obrigatorios = [t for t in templates if t.status != TemplateStatus.PENDENTE.value]
        if not obrigatorios:
            return MigracaoStatus.AGUARDANDO_ARQUIVOS

    if all(t.status == TemplateStatus.PENDENTE.value for t in obrigatorios):
        return MigracaoStatus.AGUARDANDO_ARQUIVOS

    if any(
        t.status in (TemplateStatus.PENDENTE.value, TemplateStatus.EM_IMPORTACAO.value, TemplateStatus.EM_VALIDACAO.value)
        for t in obrigatorios
    ):
        return MigracaoStatus.EM_VALIDACAO

    if any(t.status == TemplateStatus.COM_INCONSISTENCIAS.value for t in obrigatorios):
        return MigracaoStatus.AGUARDANDO_CORRECAO

    # A partir daqui, todos os templates obrigatórios estão VALIDADO.
    if not all(t.dados_aprovados for t in obrigatorios):
        return MigracaoStatus.AGUARDANDO_APROVACAO

    if not all(t.script_gerado for t in obrigatorios):
        return MigracaoStatus.PRONTA_PARA_GERACAO_SCRIPTS

    if not all(t.script_aprovado for t in obrigatorios):
        return MigracaoStatus.SCRIPTS_GERADOS

    if any(t.aplicado_com_erro for t in obrigatorios):
        return MigracaoStatus.COM_ERRO

    aplicados = [t for t in obrigatorios if t.aplicado]
    if not aplicados:
        return MigracaoStatus.AGUARDANDO_APLICACAO
    if len(aplicados) < len(obrigatorios):
        return MigracaoStatus.EM_EXECUCAO

    if any(t.teve_alerta for t in obrigatorios):
        return MigracaoStatus.CONCLUIDA_COM_ALERTAS

    return MigracaoStatus.CONCLUIDA
