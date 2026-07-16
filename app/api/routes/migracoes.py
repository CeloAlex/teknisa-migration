from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile
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
from app.db.session import get_db
from app.migracoes import acoes
from app.models.migracao import Migracao, MigracaoEvento, MigracaoTemplateStatus
from app.models.organizacao import Organizacao
from app.models.staging import ScriptGerado, StagingBruto, StagingNormalizado, ValidacaoResultado
from app.validation.classificacao import Classificacao

router = APIRouter(prefix="/migracoes", tags=["migracoes"])


# --- helpers de serialização (só a API JSON usa; o portal web monta seu próprio contexto
# de template diretamente a partir dos objetos ORM) -----------------------------------------


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


async def _migracao_to_response(db: AsyncSession, migracao) -> MigracaoResponse:
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


# --- criação e consulta ----------------------------------------------------------------------


@router.post("", response_model=MigracaoResponse, status_code=201)
async def criar_migracao(body: MigracaoCriarRequest, db: AsyncSession = Depends(get_db)) -> MigracaoResponse:
    migracao = await acoes.criar_migracao(db, body.nr_org, body.tipo_migracao_codigo, body.operador)
    return await _migracao_to_response(db, migracao)


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
    migracao = await acoes.carregar_migracao(db, migracao_id)
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
    migracao = await acoes.carregar_migracao(db, migracao_id)
    acoes.cancelar_migracao(db, migracao, body.usuario)
    return await _migracao_to_response(db, migracao)


@router.post("/{migracao_id}/reverter", response_model=MigracaoResponse)
async def reverter_migracao(
    migracao_id: int, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoResponse:
    migracao = await acoes.carregar_migracao(db, migracao_id)
    acoes.reverter_migracao(db, migracao, body.usuario)
    return await _migracao_to_response(db, migracao)


# --- por template: importação, pausa, validações -----------------------------------------------


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
    """`atraso_lote_ms` é um ajuste fino opcional (usado em testes de pausa/retomada) sobre a
    cessão de controle entre lotes — não precisa ser informado em uso normal."""
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    conteudo = await arquivo.read()
    await acoes.importar_arquivo(
        db, migracao, mts, arquivo.filename, conteudo, usuario, tamanho_lote, atraso_lote_ms
    )
    return _mts_to_response(mts)


@router.get("/{migracao_id}/templates/{template_codigo}", response_model=MigracaoTemplateStatusResponse)
async def obter_status_template(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    """Consulta de progresso — feita via polling pelo operador durante o processamento em
    chunks (`total_linhas`/`linhas_processadas`/`pausado`)."""
    _, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/pausar", response_model=MigracaoTemplateStatusResponse)
async def pausar_processamento(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    _, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    acoes.pausar(mts)
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/continuar", response_model=MigracaoTemplateStatusResponse)
async def continuar_processamento(
    migracao_id: int,
    template_codigo: str,
    tamanho_lote: int | None = None,
    atraso_lote_ms: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> MigracaoTemplateStatusResponse:
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    await acoes.continuar(db, migracao, mts, tamanho_lote, atraso_lote_ms)
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
    _, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
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


# --- por template: aprovação de dados, script, aprovação técnica, aplicação ---------------------


@router.post(
    "/{migracao_id}/templates/{template_codigo}/aprovar-dados",
    response_model=MigracaoTemplateStatusResponse,
)
async def aprovar_dados(
    migracao_id: int, template_codigo: str, body: AcaoComUsuarioRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    acoes.aprovar_dados(db, migracao, mts, body.usuario)
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
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    await acoes.gerar_script(db, migracao, mts, body.usuario, operacao)
    return _mts_to_response(mts)


@router.get("/{migracao_id}/templates/{template_codigo}/script")
async def baixar_script(
    migracao_id: int, template_codigo: str, db: AsyncSession = Depends(get_db)
) -> Response:
    _, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    stmt = (
        select(ScriptGerado)
        .where(ScriptGerado.migracao_template_status_id == mts.id)
        .order_by(ScriptGerado.dt_geracao.desc())
    )
    script = (await db.execute(stmt)).scalars().first()
    if script is None:
        raise acoes.AcaoInvalida("Nenhum script gerado ainda para este template.", status_code=404)
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
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    acoes.aprovar_script(db, migracao, mts, body.usuario)
    return _mts_to_response(mts)


@router.post("/{migracao_id}/templates/{template_codigo}/aplicar", response_model=MigracaoTemplateStatusResponse)
async def aplicar_script(
    migracao_id: int, template_codigo: str, body: AplicarRequest, db: AsyncSession = Depends(get_db)
) -> MigracaoTemplateStatusResponse:
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, template_codigo)
    acoes.aplicar(db, migracao, mts, body.usuario, body.sucesso, body.detalhe_erro)
    return _mts_to_response(mts)
