import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Annotated, Any, Coroutine

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    AcaoComUsuarioRequest,
    AplicarRequest,
    MigracaoCriarRequest,
    MigracaoDetalheResponse,
    MigracaoEventoResponse,
    MigracaoListItemResponse,
    MigracaoResponse,
    MigracaoTemplateStatusResponse,
    ValidacaoPersistidaResponse,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.migracoes.estado import ResumoTemplate, recalcular_status
from app.metadata.resolver import resolver_template
from app.models.migracao import (
    ESTADOS_ATIVOS,
    Migracao,
    MigracaoEvento,
    MigracaoStatus,
    MigracaoTemplateStatus,
    TemplateStatus,
)
from app.models.organizacao import Organizacao
from app.models.staging import ScriptGerado, StagingBruto, StagingNormalizado, ValidacaoResultado
from app.models.template import Template
from app.models.tipo_migracao import TipoMigracao, TipoMigracaoTemplate, TipoMigracaoTemplateDependencia
from app.scripts.generator import ContextoExecucao, ScriptNaoConfigurado, gerar_script
from app.staging.service import (
    buscar_linhas_validas,
    processar_arquivo_em_background,
    resetar_para_reprocessamento,
    retomar_processamento_em_background,
)
from app.validation.classificacao import Classificacao

router = APIRouter(prefix="/migracoes", tags=["migracoes"])

# asyncio só mantém uma referência fraca à Task criada por create_task() — se nada mais
# segurar o objeto, ela pode ser descartada pelo coletor de lixo antes do loop de eventos
# chegar a rodar seu corpo (é literalmente o que a documentação do asyncio recomenda evitar:
# "save a reference to the result"). Sem este conjunto, o processamento em background nunca
# chegava a executar uma única linha.
_tarefas_em_background: set[asyncio.Task] = set()


def _disparar_em_background(coro: Coroutine[Any, Any, None]) -> asyncio.Task:
    tarefa = asyncio.create_task(coro)
    _tarefas_em_background.add(tarefa)
    tarefa.add_done_callback(_tarefas_em_background.discard)
    return tarefa


# --- helpers internos ---------------------------------------------------------------------


async def _carregar_migracao(migracao_id: int, db: AsyncSession) -> Migracao:
    stmt = (
        select(Migracao)
        .where(Migracao.id == migracao_id)
        .options(
            selectinload(Migracao.templates_status).selectinload(MigracaoTemplateStatus.template),
            selectinload(Migracao.tipo_migracao),
        )
    )
    migracao = (await db.execute(stmt)).scalar_one_or_none()
    if migracao is None:
        raise HTTPException(status_code=404, detail=f"Migração {migracao_id} não encontrada.")
    return migracao


def _buscar_mts(migracao: Migracao, template_codigo: str) -> MigracaoTemplateStatus:
    for mts in migracao.templates_status:
        if mts.template.codigo == template_codigo:
            return mts
    raise HTTPException(
        status_code=404,
        detail=f'Template "{template_codigo}" não faz parte do tipo de migração desta migração.',
    )


async def _carregar_migracao_e_mts(
    migracao_id: int, template_codigo: str, db: AsyncSession
) -> tuple[Migracao, MigracaoTemplateStatus]:
    migracao = await _carregar_migracao(migracao_id, db)
    return migracao, _buscar_mts(migracao, template_codigo)


async def _organizacao_nome(db: AsyncSession, nr_org: int) -> str:
    organizacao = await db.get(Organizacao, nr_org)
    return organizacao.nome if organizacao else str(nr_org)


def _mts_to_response(mts: MigracaoTemplateStatus) -> MigracaoTemplateStatusResponse:
    return MigracaoTemplateStatusResponse(
        template_codigo=mts.template.codigo,
        template_nome=mts.template.nome,
        obrigatorio=mts.obrigatorio,
        status=mts.status,
        total_linhas=mts.total_linhas,
        linhas_processadas=mts.linhas_processadas,
        pausado=mts.pausado,
        teve_alerta=mts.teve_alerta,
        dados_aprovados=mts.dados_aprovados,
        script_gerado=mts.script_gerado,
        script_aprovado=mts.script_aprovado,
        aplicado=mts.aplicado,
        aplicado_com_erro=mts.aplicado_com_erro,
    )


async def _migracao_to_response(db: AsyncSession, migracao: Migracao) -> MigracaoResponse:
    return MigracaoResponse(
        id=migracao.id,
        nr_org=migracao.nr_org,
        organizacao_nome=await _organizacao_nome(db, migracao.nr_org),
        tipo_migracao_codigo=migracao.tipo_migracao.codigo,
        operador=migracao.operador,
        status=migracao.status,
        dt_criacao=migracao.dt_criacao,
        dt_conclusao=migracao.dt_conclusao,
        templates=[_mts_to_response(mts) for mts in migracao.templates_status],
    )


def _registrar_evento(db: AsyncSession, migracao_id: int, evento: str, usuario: str) -> None:
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


def _atualizar_status_migracao(migracao: Migracao) -> None:
    novo_status = _status_recalculado(migracao)
    migracao.status = novo_status
    concluida = {MigracaoStatus.CONCLUIDA.value, MigracaoStatus.CONCLUIDA_COM_ALERTAS.value}
    if novo_status in concluida and migracao.dt_conclusao is None:
        migracao.dt_conclusao = datetime.now(timezone.utc)


# --- criação e consulta --------------------------------------------------------------------


@router.post("", response_model=MigracaoResponse, status_code=201)
async def criar_migracao(body: MigracaoCriarRequest, db: AsyncSession = Depends(get_db)) -> MigracaoResponse:
    """Cria uma migração (Seção 4, passos 1-5): valida organização e tipo de migração,
    bloqueia se a organização já tiver uma migração ativa (Seção 4.1), e cria um
    `MigracaoTemplateStatus` "pendente" para cada template do tipo escolhido."""
    organizacao = await db.get(Organizacao, body.nr_org)
    if organizacao is None:
        raise HTTPException(status_code=404, detail=f"Organização {body.nr_org} não encontrada.")

    tipo_stmt = (
        select(TipoMigracao)
        .where(TipoMigracao.codigo == body.tipo_migracao_codigo)
        .options(selectinload(TipoMigracao.templates))
    )
    tipo_migracao = (await db.execute(tipo_stmt)).scalar_one_or_none()
    if tipo_migracao is None:
        raise HTTPException(
            status_code=404, detail=f'Tipo de migração "{body.tipo_migracao_codigo}" não encontrado.'
        )

    if not tipo_migracao.permite_concorrencia:
        stmt_ativas = select(Migracao.id).where(
            Migracao.nr_org == body.nr_org,
            Migracao.status.in_([e.value for e in ESTADOS_ATIVOS]),
        )
        if (await db.execute(stmt_ativas)).first() is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Organização {body.nr_org} já possui uma migração ativa — não é "
                    "possível criar outra simultaneamente (Seção 4.1)."
                ),
            )

    migracao = Migracao(
        nr_org=body.nr_org,
        tipo_migracao_id=tipo_migracao.id,
        operador=body.operador,
        status=MigracaoStatus.CRIADA.value,
    )
    db.add(migracao)
    await db.flush()

    for tmt in tipo_migracao.templates:
        db.add(
            MigracaoTemplateStatus(migracao_id=migracao.id, template_id=tmt.template_id, obrigatorio=tmt.obrigatorio)
        )
    await db.flush()

    migracao_completa = await _carregar_migracao(migracao.id, db)
    _atualizar_status_migracao(migracao_completa)
    _registrar_evento(db, migracao_completa.id, "Migração criada", body.operador)

    return await _migracao_to_response(db, migracao_completa)


@router.get("", response_model=list[MigracaoListItemResponse])
async def listar_migracoes(db: AsyncSession = Depends(get_db)) -> list[MigracaoListItemResponse]:
    stmt = select(Migracao).options(selectinload(Migracao.tipo_migracao)).order_by(Migracao.dt_criacao.desc())
    migracoes = (await db.execute(stmt)).scalars().all()
    return [
        MigracaoListItemResponse(
            id=m.id,
            nr_org=m.nr_org,
            organizacao_nome=await _organizacao_nome(db, m.nr_org),
            tipo_migracao_codigo=m.tipo_migracao.codigo,
            operador=m.operador,
            status=m.status,
            dt_criacao=m.dt_criacao,
        )
        for m in migracoes
    ]


@router.get("/{migracao_id}", response_model=MigracaoDetalheResponse)
async def obter_migracao(migracao_id: int, db: AsyncSession = Depends(get_db)) -> MigracaoDetalheResponse:
    migracao = await _carregar_migracao(migracao_id, db)
    eventos_stmt = (
        select(MigracaoEvento).where(MigracaoEvento.migracao_id == migracao_id).order_by(MigracaoEvento.dt_evento)
    )
    eventos = (await db.execute(eventos_stmt)).scalars().all()
    base = await _migracao_to_response(db, migracao)
    return MigracaoDetalheResponse(
        **base.model_dump(),
        eventos=[
            MigracaoEventoResponse(evento=e.evento, usuario=e.usuario, dt_evento=e.dt_evento) for e in eventos
        ],
    )


@router.post("/{migracao_id}/cancelar", response_model=MigracaoResponse)
async def cancelar_migracao(
    migracao_id: int, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoResponse:
    """Cancelamento manual (Seção 9.2 — "qualquer estado ativo -> cancelada")."""
    migracao = await _carregar_migracao(migracao_id, db)
    if migracao.status in (
        MigracaoStatus.CONCLUIDA.value,
        MigracaoStatus.CONCLUIDA_COM_ALERTAS.value,
        MigracaoStatus.CANCELADA.value,
        MigracaoStatus.REVERTIDA.value,
    ):
        raise HTTPException(status_code=400, detail=f'Migração em estado "{migracao.status}" não pode ser cancelada.')
    migracao.status = MigracaoStatus.CANCELADA.value
    _registrar_evento(db, migracao.id, "Migração cancelada", body.usuario)
    return await _migracao_to_response(db, migracao)


@router.post("/{migracao_id}/reverter", response_model=MigracaoResponse)
async def reverter_migracao(
    migracao_id: int, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoResponse:
    """Confirmação manual de rollback (Seção 9.2 — "com erro -> revertida"). Como a
    plataforma ainda não tem integração com o banco de destino (Oracle), a reversão em si é
    executada fora da plataforma; este endpoint só registra que ela foi concluída — o mesmo
    modelo de confirmação manual já usado em `/aplicar`."""
    migracao = await _carregar_migracao(migracao_id, db)
    if migracao.status != MigracaoStatus.COM_ERRO.value:
        raise HTTPException(status_code=400, detail='Só é possível reverter uma migração em estado "com_erro".')
    migracao.status = MigracaoStatus.REVERTIDA.value
    _registrar_evento(db, migracao.id, "Rollback confirmado — migração revertida", body.usuario)
    return await _migracao_to_response(db, migracao)


# --- por template: importação, pausa, validações -------------------------------------------


@router.post(
    "/{migracao_id}/templates/{template_codigo}/arquivo",
    response_model=MigracaoTemplateStatusResponse,
    status_code=202,
)
async def importar_arquivo(
    migracao_id: int,
    template_codigo: str,
    arquivo: UploadFile,
    usuario: Annotated[str, Form()],
    tamanho_lote: Annotated[int | None, Form()] = None,
    atraso_lote_ms: Annotated[int | None, Form()] = None,
    db: AsyncSession = Depends(get_db),
) -> MigracaoTemplateStatusResponse:
    """Upload de XLSX para um template desta migração — dispara processamento assíncrono em
    chunks (Seção 11/Fase 5). Aceita reenvio (Seção 8, "correção ou reprocessamento"): o
    staging anterior desse template é descartado antes de recomeçar. `atraso_lote_ms` é um
    ajuste fino opcional (usado em testes de pausa/retomada) sobre a cessão de controle
    entre lotes — não precisa ser informado em uso normal."""
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)

    if migracao.status in (MigracaoStatus.CANCELADA.value, MigracaoStatus.REVERTIDA.value):
        raise HTTPException(
            status_code=400, detail=f'Migração está em estado terminal ("{migracao.status}") — não aceita novos arquivos.'
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
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f'Template "{template_codigo}" depende de {", ".join(pendentes)} já '
                        "estar(em) validado(s) antes (sequência travada — Seção 26.3)."
                    ),
                )

    conteudo = await arquivo.read()

    await resetar_para_reprocessamento(db, mts)
    mts.arquivo_origem = arquivo.filename
    mts.hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    await db.flush()

    lote = tamanho_lote or get_settings().tamanho_lote_processamento
    atraso = (atraso_lote_ms / 1000) if atraso_lote_ms is not None else 0.001
    _disparar_em_background(
        processar_arquivo_em_background(mts.id, mts.template_id, conteudo, migracao.nr_org, lote, atraso)
    )

    _registrar_evento(db, migracao.id, f'Arquivo importado — {template_codigo}', usuario)
    _atualizar_status_migracao(migracao)

    return _mts_to_response(mts)


@router.get("/{migracao_id}/templates/{template_codigo}", response_model=MigracaoTemplateStatusResponse)
async def obter_status_template(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    """Consulta de progresso — feita via polling pelo operador durante o processamento em
    chunks (`total_linhas`/`linhas_processadas`/`pausado`)."""
    _, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/pausar", response_model=MigracaoTemplateStatusResponse)
async def pausar_processamento(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    _, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if mts.status != TemplateStatus.EM_IMPORTACAO.value:
        raise HTTPException(status_code=400, detail="Só é possível pausar um template que está em importação.")
    mts.pausado = True
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/continuar", response_model=MigracaoTemplateStatusResponse)
async def continuar_processamento(
    migracao_id: int,
    template_codigo: str,
    tamanho_lote: int | None = None,
    atraso_lote_ms: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> MigracaoTemplateStatusResponse:
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if not mts.pausado:
        raise HTTPException(status_code=400, detail="Este template não está pausado.")
    mts.pausado = False
    await db.flush()

    lote = tamanho_lote or get_settings().tamanho_lote_processamento
    atraso = (atraso_lote_ms / 1000) if atraso_lote_ms is not None else 0.001
    _disparar_em_background(
        retomar_processamento_em_background(mts.id, mts.template_id, migracao.nr_org, lote, atraso)
    )

    return _mts_to_response(mts)


@router.get(
    "/{migracao_id}/templates/{template_codigo}/validacoes",
    response_model=list[ValidacaoPersistidaResponse],
)
async def listar_validacoes(
    migracao_id: int,
    template_codigo: str,
    apenas_erros: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[ValidacaoPersistidaResponse]:
    _, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    stmt = (
        select(StagingBruto.linha, ValidacaoResultado)
        .join(StagingNormalizado, StagingNormalizado.staging_bruto_id == StagingBruto.id)
        .join(ValidacaoResultado, ValidacaoResultado.staging_normalizado_id == StagingNormalizado.id)
        .where(StagingBruto.migracao_template_status_id == mts.id)
        .order_by(StagingBruto.linha)
    )
    if apenas_erros:
        stmt = stmt.where(ValidacaoResultado.classificacao == Classificacao.ERRO_IMPEDITIVO.value)
    linhas = (await db.execute(stmt)).all()
    return [
        ValidacaoPersistidaResponse(
            linha=linha,
            campo=v.campo,
            regra=v.regra,
            classificacao=v.classificacao,
            valor_recebido=v.valor_recebido,
            valor_esperado=v.valor_esperado,
            orientacao=v.mensagem,
        )
        for linha, v in linhas
    ]


# --- por template: aprovação de dados, script, aprovação técnica, aplicação -----------------


@router.post(
    "/{migracao_id}/templates/{template_codigo}/aprovar-dados",
    response_model=MigracaoTemplateStatusResponse,
)
async def aprovar_dados(
    migracao_id: int, template_codigo: str, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    """Aprovação de dados POR TEMPLATE (não existe um botão único para todos os templates de
    uma migração — requisito explícito da Fase 5, corrigindo a inconsistência identificada
    no protótipo)."""
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if mts.status != TemplateStatus.VALIDADO.value:
        raise HTTPException(
            status_code=400, detail="Só é possível aprovar dados de um template sem erros impeditivos pendentes."
        )
    mts.dados_aprovados = True
    mts.aprovado_dados_por = body.usuario
    _atualizar_status_migracao(migracao)
    _registrar_evento(db, migracao.id, f"Dados aprovados — {template_codigo}", body.usuario)
    return _mts_to_response(mts)


@router.post(
    "/{migracao_id}/templates/{template_codigo}/gerar-script",
    response_model=MigracaoTemplateStatusResponse,
)
async def gerar_script_persistido(
    migracao_id: int,
    template_codigo: str,
    body: AcaoComUsuarioRequest,
    operacao: str = "INCLUSAO",
    db: AsyncSession = Depends(get_db),
) -> MigracaoTemplateStatusResponse:
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if not mts.dados_aprovados:
        raise HTTPException(status_code=400, detail="Aprove os dados deste template antes de gerar o script.")

    template_meta = await resolver_template(db, template_codigo)
    linhas_validas = await buscar_linhas_validas(db, mts.id)
    if not linhas_validas:
        raise HTTPException(status_code=422, detail="Nenhuma linha válida para gerar script.")

    settings = get_settings()
    contexto = ContextoExecucao(nr_org=migracao.nr_org, usuario_tecnico=settings.usuario_tecnico_padrao)
    try:
        sql = await gerar_script(db, linhas_validas, template_meta, contexto, operacao=operacao)
    except ScriptNaoConfigurado as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.add(ScriptGerado(migracao_template_status_id=mts.id, operacao=operacao, conteudo_sql=sql))
    mts.script_gerado = True
    _atualizar_status_migracao(migracao)
    _registrar_evento(db, migracao.id, f"Script gerado — {template_codigo}", body.usuario)
    return _mts_to_response(mts)


@router.get("/{migracao_id}/templates/{template_codigo}/script")
async def baixar_script(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> Response:
    _, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    stmt = (
        select(ScriptGerado)
        .where(ScriptGerado.migracao_template_status_id == mts.id)
        .order_by(ScriptGerado.dt_geracao.desc())
    )
    script = (await db.execute(stmt)).scalars().first()
    if script is None:
        raise HTTPException(status_code=404, detail="Nenhum script gerado ainda para este template.")
    nome_arquivo = f"{template_codigo.lower()}_{script.operacao.lower()}.sql"
    return Response(
        content=script.conteudo_sql,
        media_type="application/sql",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.post(
    "/{migracao_id}/templates/{template_codigo}/aprovar-script",
    response_model=MigracaoTemplateStatusResponse,
)
async def aprovar_script(
    migracao_id: int, template_codigo: str, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    """Aprovação técnica POR TEMPLATE — perfil segregado do aprovador de dados (Seção 10.3),
    também individual por template (mesmo requisito explícito da Fase 5)."""
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if not mts.script_gerado:
        raise HTTPException(status_code=400, detail="Gere o script deste template antes de aprová-lo tecnicamente.")
    mts.script_aprovado = True
    mts.aprovado_script_por = body.usuario
    _atualizar_status_migracao(migracao)
    _registrar_evento(db, migracao.id, f"Script aprovado — {template_codigo}", body.usuario)
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/aplicar", response_model=MigracaoTemplateStatusResponse)
async def aplicar_script(
    migracao_id: int, template_codigo: str, body: AplicarRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    """Confirmação de aplicação do script (Anexo J — MVP aplica o `.sql` manualmente fora da
    plataforma; este endpoint registra o resultado dessa aplicação manual, não executa nada
    no Oracle diretamente, já que essa integração ainda não existe)."""
    migracao, mts = await _carregar_migracao_e_mts(migracao_id, template_codigo, db)
    if not mts.script_aprovado:
        raise HTTPException(status_code=400, detail="Aprove tecnicamente o script antes de aplicá-lo.")

    if body.sucesso:
        mts.aplicado = True
        mts.aplicado_com_erro = False
        evento = f"Script aplicado — {template_codigo}"
    else:
        mts.aplicado_com_erro = True
        evento = f"Falha ao aplicar script — {template_codigo}: {body.detalhe_erro or 'sem detalhe informado'}"

    _atualizar_status_migracao(migracao)
    _registrar_evento(db, migracao.id, evento, body.usuario)
    return _mts_to_response(mts)
