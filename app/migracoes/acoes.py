import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Coroutine

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.metadata.resolver import resolver_template
from app.migracoes.estado import ResumoTemplate, recalcular_status
from app.models.migracao import (
    ESTADOS_ATIVOS,
    Migracao,
    MigracaoEvento,
    MigracaoStatus,
    MigracaoTemplateStatus,
    TemplateStatus,
)
from app.models.organizacao import Organizacao
from app.models.staging import ScriptGerado
from app.models.tipo_migracao import TipoMigracao, TipoMigracaoTemplate
from app.scripts.generator import ContextoExecucao, ScriptNaoConfigurado
from app.scripts.generator import gerar_script as _gerar_script_sql
from app.staging.service import (
    buscar_linhas_validas,
    processar_arquivo_em_background,
    resetar_para_reprocessamento,
    retomar_processamento_em_background,
)

__all__ = [
    "AcaoInvalida",
    "carregar_migracao",
    "buscar_mts",
    "carregar_migracao_e_mts",
    "registrar_evento",
    "atualizar_status_migracao",
    "criar_migracao",
    "cancelar_migracao",
    "reverter_migracao",
    "importar_arquivo",
    "pausar",
    "continuar",
    "aprovar_dados",
    "gerar_script",
    "aprovar_script",
    "aplicar",
]


class AcaoInvalida(Exception):
    """Pré-condição de negócio não satisfeita para a ação pedida. Cada camada de
    apresentação traduz isso pro formato que fizer sentido: a API JSON deixa isso propagar
    até o exception handler global (app/main.py), que responde com
    `{"detail": mensagem}` no `status_code` dado — igual ao `HTTPException` que existia
    antes desta extração; o portal web captura localmente e renderiza a página atual com
    uma mensagem de erro."""

    def __init__(self, mensagem: str, status_code: int = 400) -> None:
        self.mensagem = mensagem
        self.status_code = status_code
        super().__init__(mensagem)


# asyncio só mantém uma referência fraca à Task criada por create_task() — se nada mais
# segurar o objeto, ela pode ser descartada pelo coletor de lixo antes do loop de eventos
# chegar a rodar seu corpo. Compartilhado entre a API JSON e o portal web, já que ambos
# disparam o mesmo processamento em background.
_tarefas_em_background: set[asyncio.Task] = set()


def _disparar_em_background(coro: Coroutine[Any, Any, None]) -> asyncio.Task:
    tarefa = asyncio.create_task(coro)
    _tarefas_em_background.add(tarefa)
    tarefa.add_done_callback(_tarefas_em_background.discard)
    return tarefa


# --- carregamento --------------------------------------------------------------------------


async def carregar_migracao(db: AsyncSession, migracao_id: int) -> Migracao:
    stmt = (
        select(Migracao)
        .where(Migracao.id == migracao_id)
        .options(
            selectinload(Migracao.templates_status).selectinload(MigracaoTemplateStatus.template),
            selectinload(Migracao.tipo_migracao),
            selectinload(Migracao.eventos),
        )
    )
    migracao = (await db.execute(stmt)).scalar_one_or_none()
    if migracao is None:
        raise AcaoInvalida(f"Migração {migracao_id} não encontrada.", status_code=404)
    return migracao


def buscar_mts(migracao: Migracao, template_codigo: str) -> MigracaoTemplateStatus:
    for mts in migracao.templates_status:
        if mts.template.codigo == template_codigo:
            return mts
    raise AcaoInvalida(
        f'Template "{template_codigo}" não faz parte do tipo de migração desta migração.', status_code=404
    )


async def carregar_migracao_e_mts(
    db: AsyncSession, migracao_id: int, template_codigo: str
) -> tuple[Migracao, MigracaoTemplateStatus]:
    migracao = await carregar_migracao(db, migracao_id)
    return migracao, buscar_mts(migracao, template_codigo)


# --- estado ---------------------------------------------------------------------------------


def registrar_evento(db: AsyncSession, migracao_id: int, evento: str, usuario: str) -> None:
    db.add(MigracaoEvento(migracao_id=migracao_id, evento=evento, usuario=usuario))


def _status_recalculado(migracao: Migracao) -> str:
    resumo = [
        ResumoTemplate(
            obrigatorio=mts.obrigatorio,
            status=mts.status,
            dados_aprovados=mts.dados_aprovados,
            script_gerado=mts.script_gerado,
            script_aprovado=mts.script_aprovado,
            aplicado=mts.aplicado,
            aplicado_com_erro=mts.aplicado_com_erro,
            teve_alerta=mts.teve_alerta,
        )
        for mts in migracao.templates_status
    ]
    return recalcular_status(migracao.status, resumo).value


def atualizar_status_migracao(migracao: Migracao) -> None:
    novo_status = _status_recalculado(migracao)
    migracao.status = novo_status
    concluida = {MigracaoStatus.CONCLUIDA.value, MigracaoStatus.CONCLUIDA_COM_ALERTAS.value}
    if novo_status in concluida and migracao.dt_conclusao is None:
        migracao.dt_conclusao = datetime.now(timezone.utc)


# --- ciclo de vida da migração ----------------------------------------------------------------


async def criar_migracao(db: AsyncSession, nr_org: int, tipo_migracao_codigo: str, operador: str) -> Migracao:
    """Cria uma migração (Seção 4, passos 1-5): valida organização e tipo de migração,
    bloqueia se a organização já tiver uma migração ativa (Seção 4.1), e cria um
    `MigracaoTemplateStatus` "pendente" para cada template do tipo escolhido."""
    organizacao = await db.get(Organizacao, nr_org)
    if organizacao is None:
        raise AcaoInvalida(f"Organização {nr_org} não encontrada.", status_code=404)

    tipo_stmt = (
        select(TipoMigracao)
        .where(TipoMigracao.codigo == tipo_migracao_codigo)
        .options(selectinload(TipoMigracao.templates))
    )
    tipo_migracao = (await db.execute(tipo_stmt)).scalar_one_or_none()
    if tipo_migracao is None:
        raise AcaoInvalida(f'Tipo de migração "{tipo_migracao_codigo}" não encontrado.', status_code=404)

    if not tipo_migracao.permite_concorrencia:
        stmt_ativas = select(Migracao.id).where(
            Migracao.nr_org == nr_org,
            Migracao.status.in_([e.value for e in ESTADOS_ATIVOS]),
        )
        if (await db.execute(stmt_ativas)).first() is not None:
            raise AcaoInvalida(
                f"Organização {nr_org} já possui uma migração ativa — não é possível criar "
                "outra simultaneamente (Seção 4.1).",
                status_code=409,
            )

    migracao = Migracao(
        nr_org=nr_org, tipo_migracao_id=tipo_migracao.id, operador=operador, status=MigracaoStatus.CRIADA.value
    )
    db.add(migracao)
    await db.flush()

    for tmt in tipo_migracao.templates:
        db.add(
            MigracaoTemplateStatus(migracao_id=migracao.id, template_id=tmt.template_id, obrigatorio=tmt.obrigatorio)
        )
    await db.flush()

    migracao_completa = await carregar_migracao(db, migracao.id)
    atualizar_status_migracao(migracao_completa)
    registrar_evento(db, migracao_completa.id, "Migração criada", operador)
    return migracao_completa


def cancelar_migracao(db: AsyncSession, migracao: Migracao, usuario: str) -> None:
    """Cancelamento manual (Seção 9.2 — "qualquer estado ativo -> cancelada")."""
    if migracao.status in (
        MigracaoStatus.CONCLUIDA.value,
        MigracaoStatus.CONCLUIDA_COM_ALERTAS.value,
        MigracaoStatus.CANCELADA.value,
        MigracaoStatus.REVERTIDA.value,
    ):
        raise AcaoInvalida(f'Migração em estado "{migracao.status}" não pode ser cancelada.')
    migracao.status = MigracaoStatus.CANCELADA.value
    registrar_evento(db, migracao.id, "Migração cancelada", usuario)


def reverter_migracao(db: AsyncSession, migracao: Migracao, usuario: str) -> None:
    """Confirmação manual de rollback (Seção 9.2 — "com erro -> revertida"). A reversão em
    si é executada fora da plataforma (sem integração com o Oracle de destino ainda); este
    endpoint só registra que ela foi concluída."""
    if migracao.status != MigracaoStatus.COM_ERRO.value:
        raise AcaoInvalida('Só é possível reverter uma migração em estado "com_erro".')
    migracao.status = MigracaoStatus.REVERTIDA.value
    registrar_evento(db, migracao.id, "Rollback confirmado — migração revertida", usuario)


# --- ações por template -----------------------------------------------------------------------


async def importar_arquivo(
    db: AsyncSession,
    migracao: Migracao,
    mts: MigracaoTemplateStatus,
    arquivo_nome: str | None,
    conteudo: bytes,
    usuario: str,
    tamanho_lote: int | None = None,
    atraso_lote_ms: int | None = None,
) -> None:
    """Upload de XLSX para um template desta migração — dispara processamento assíncrono em
    chunks (Seção 11/Fase 5). Aceita reenvio (Seção 8, "correção ou reprocessamento"): o
    staging anterior desse template é descartado antes de recomeçar."""
    if migracao.status in (MigracaoStatus.CANCELADA.value, MigracaoStatus.REVERTIDA.value):
        raise AcaoInvalida(
            f'Migração está em estado terminal ("{migracao.status}") — não aceita novos arquivos.'
        )

    if migracao.tipo_migracao.sequencia_obrigatoria:
        tmt_stmt = (
            select(TipoMigracaoTemplate)
            .where(
                TipoMigracaoTemplate.tipo_migracao_id == migracao.tipo_migracao_id,
                TipoMigracaoTemplate.template_id == mts.template_id,
            )
            .options(selectinload(TipoMigracaoTemplate.dependencias))
        )
        tmt = (await db.execute(tmt_stmt)).scalar_one()
        ids_dependencias = {d.depende_de_template_id for d in tmt.dependencias}
        if ids_dependencias:
            pendentes = [
                m.template.codigo
                for m in migracao.templates_status
                if m.template_id in ids_dependencias and m.status != TemplateStatus.VALIDADO.value
            ]
            if pendentes:
                raise AcaoInvalida(
                    f'Template "{mts.template.codigo}" depende de {", ".join(pendentes)} já '
                    "estar(em) validado(s) antes (sequência travada — Seção 26.3).",
                    status_code=409,
                )

    await resetar_para_reprocessamento(db, mts)
    mts.arquivo_origem = arquivo_nome
    mts.hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    await db.flush()

    lote = tamanho_lote or get_settings().tamanho_lote_processamento
    atraso = (atraso_lote_ms / 1000) if atraso_lote_ms is not None else 0.001
    _disparar_em_background(
        processar_arquivo_em_background(mts.id, mts.template_id, conteudo, migracao.nr_org, lote, atraso)
    )

    registrar_evento(db, migracao.id, f"Arquivo importado — {mts.template.codigo}", usuario)
    atualizar_status_migracao(migracao)


def pausar(mts: MigracaoTemplateStatus) -> None:
    if mts.status != TemplateStatus.EM_IMPORTACAO.value:
        raise AcaoInvalida("Só é possível pausar um template que está em importação.")
    mts.pausado = True


async def continuar(
    db: AsyncSession,
    migracao: Migracao,
    mts: MigracaoTemplateStatus,
    tamanho_lote: int | None = None,
    atraso_lote_ms: int | None = None,
) -> None:
    if not mts.pausado:
        raise AcaoInvalida("Este template não está pausado.")
    mts.pausado = False
    await db.flush()

    lote = tamanho_lote or get_settings().tamanho_lote_processamento
    atraso = (atraso_lote_ms / 1000) if atraso_lote_ms is not None else 0.001
    _disparar_em_background(
        retomar_processamento_em_background(mts.id, mts.template_id, migracao.nr_org, lote, atraso)
    )


def aprovar_dados(db: AsyncSession, migracao: Migracao, mts: MigracaoTemplateStatus, usuario: str) -> None:
    """Aprovação de dados POR TEMPLATE (não existe um botão único para todos os templates de
    uma migração — requisito explícito da Fase 5, corrigindo a inconsistência identificada
    no protótipo)."""
    if mts.status != TemplateStatus.VALIDADO.value:
        raise AcaoInvalida("Só é possível aprovar dados de um template sem erros impeditivos pendentes.")
    mts.dados_aprovados = True
    mts.aprovado_dados_por = usuario
    atualizar_status_migracao(migracao)
    registrar_evento(db, migracao.id, f"Dados aprovados — {mts.template.codigo}", usuario)


async def gerar_script(
    db: AsyncSession, migracao: Migracao, mts: MigracaoTemplateStatus, usuario: str, operacao: str = "INCLUSAO"
) -> None:
    if not mts.dados_aprovados:
        raise AcaoInvalida("Aprove os dados deste template antes de gerar o script.")

    template_meta = await resolver_template(db, mts.template.codigo)
    linhas_validas = await buscar_linhas_validas(db, mts.id)
    if not linhas_validas:
        raise AcaoInvalida("Nenhuma linha válida para gerar script.", status_code=422)

    settings = get_settings()
    contexto = ContextoExecucao(nr_org=migracao.nr_org, usuario_tecnico=settings.usuario_tecnico_padrao)
    try:
        sql = await _gerar_script_sql(db, linhas_validas, template_meta, contexto, operacao=operacao)
    except ScriptNaoConfigurado as exc:
        raise AcaoInvalida(str(exc)) from exc

    db.add(ScriptGerado(migracao_template_status_id=mts.id, operacao=operacao, conteudo_sql=sql))
    mts.script_gerado = True
    atualizar_status_migracao(migracao)
    registrar_evento(db, migracao.id, f"Script gerado — {mts.template.codigo}", usuario)


def aprovar_script(db: AsyncSession, migracao: Migracao, mts: MigracaoTemplateStatus, usuario: str) -> None:
    """Aprovação técnica POR TEMPLATE — perfil segregado do aprovador de dados (Seção 10.3),
    também individual por template (mesmo requisito explícito da Fase 5)."""
    if not mts.script_gerado:
        raise AcaoInvalida("Gere o script deste template antes de aprová-lo tecnicamente.")
    mts.script_aprovado = True
    mts.aprovado_script_por = usuario
    atualizar_status_migracao(migracao)
    registrar_evento(db, migracao.id, f"Script aprovado — {mts.template.codigo}", usuario)


def aplicar(
    db: AsyncSession,
    migracao: Migracao,
    mts: MigracaoTemplateStatus,
    usuario: str,
    sucesso: bool,
    detalhe_erro: str | None = None,
) -> None:
    """Confirmação de aplicação do script (Anexo J — MVP aplica o `.sql` manualmente fora da
    plataforma; este endpoint registra o resultado dessa aplicação manual, não executa nada
    no Oracle diretamente, já que essa integração ainda não existe)."""
    if not mts.script_aprovado:
        raise AcaoInvalida("Aprove tecnicamente o script antes de aplicá-lo.")

    if sucesso:
        mts.aplicado = True
        mts.aplicado_com_erro = False
        evento = f"Script aplicado — {mts.template.codigo}"
    else:
        mts.aplicado_com_erro = True
        evento = f"Falha ao aplicar script — {mts.template.codigo}: {detalhe_erro or 'sem detalhe informado'}"

    atualizar_status_migracao(migracao)
    registrar_evento(db, migracao.id, evento, usuario)
