from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.migracoes import acoes
from app.migracoes.acoes import AcaoInvalida
from app.models.migracao import Migracao, MigracaoTemplateStatus, TemplateStatus
from app.models.staging import ScriptGerado, StagingBruto, StagingNormalizado, ValidacaoResultado
from app.models.tipo_migracao import TipoMigracaoTemplate
from app.models.usuario import Papel, Usuario
from app.validation.classificacao import Classificacao
from app.web.deps import SemPermissao, exigir_login, exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal", tags=["portal-migracao"])


def _verificar_org(usuario: Usuario, migracao: Migracao) -> None:
    """Operador/aprovadores/executor (nr_org preenchido) só podem ver/agir sobre migrações
    da própria organização — administrador/auditor (nr_org nulo) enxergam todas (Seção
    12.1). Sem esta checagem, um usuário restrito a uma organização poderia acessar/agir
    sobre a migração de outra só sabendo o id na URL."""
    if usuario.nr_org is not None and usuario.nr_org != migracao.nr_org:
        raise SemPermissao("Você não tem acesso a migrações de outra organização.")


async def _carregar(db: AsyncSession, migracao_id: int, usuario: Usuario) -> Migracao:
    migracao = await acoes.carregar_migracao(db, migracao_id)
    _verificar_org(usuario, migracao)
    return migracao


async def _carregar_com_mts(
    db: AsyncSession, migracao_id: int, codigo: str, usuario: Usuario
) -> tuple[Migracao, MigracaoTemplateStatus]:
    migracao, mts = await acoes.carregar_migracao_e_mts(db, migracao_id, codigo)
    _verificar_org(usuario, migracao)
    return migracao, mts

ABAS = [
    ("templates", "Templates & Upload"),
    ("validacao", "Validação"),
    ("aprovacao_dados", "Aprovação de Dados"),
    ("scripts", "Geração de Scripts"),
    ("aprovacao_tecnica", "Aprovação Técnica"),
    ("execucao", "Execução"),
    ("relatorio", "Relatório"),
    ("downloads", "Downloads"),
]


async def _templates_ordenados(db: AsyncSession, migracao: Migracao) -> list[MigracaoTemplateStatus]:
    stmt = (
        select(TipoMigracaoTemplate.template_id)
        .where(TipoMigracaoTemplate.tipo_migracao_id == migracao.tipo_migracao_id)
        .order_by(TipoMigracaoTemplate.ordem)
    )
    ordem_ids = (await db.execute(stmt)).scalars().all()
    por_template_id = {mts.template_id: mts for mts in migracao.templates_status}
    return [por_template_id[tid] for tid in ordem_ids if tid in por_template_id]


async def _contagem_validacoes(db: AsyncSession, mts_id: int) -> dict[str, int]:
    total_stmt = (
        select(func.count())
        .select_from(StagingNormalizado)
        .join(StagingBruto, StagingBruto.id == StagingNormalizado.staging_bruto_id)
        .where(StagingBruto.migracao_template_status_id == mts_id)
    )
    total = (await db.execute(total_stmt)).scalar_one()

    class_stmt = (
        select(ValidacaoResultado.classificacao, func.count())
        .join(StagingNormalizado, StagingNormalizado.id == ValidacaoResultado.staging_normalizado_id)
        .join(StagingBruto, StagingBruto.id == StagingNormalizado.staging_bruto_id)
        .where(StagingBruto.migracao_template_status_id == mts_id)
        .group_by(ValidacaoResultado.classificacao)
    )
    contagens = dict((await db.execute(class_stmt)).all())

    erros = contagens.get(Classificacao.ERRO_IMPEDITIVO.value, 0)
    alertas = contagens.get(Classificacao.ALERTA.value, 0)
    return {
        "recebidos": total,
        "validos": total - erros,
        "rejeitados": erros,
        "alertas": alertas,
    }


@router.get("/migracoes/{migracao_id}")
async def detalhe_migracao(
    request: Request,
    migracao_id: int,
    aba: str = "templates",
    usuario: Usuario = Depends(exigir_login),
    db: AsyncSession = Depends(get_db),
):
    migracao = await _carregar(db, migracao_id, usuario)
    if aba not in dict(ABAS):
        aba = "templates"

    templates_ordenados = await _templates_ordenados(db, migracao)
    contexto: dict = {
        "usuario": usuario,
        "migracao": migracao,
        "abas": ABAS,
        "aba": aba,
        "templates_ordenados": templates_ordenados,
        "template_status": TemplateStatus,
        "erro": request.session.pop("_flash_erro", None),
    }

    if aba in ("validacao", "aprovacao_dados", "relatorio"):
        contagens = {}
        for mts in templates_ordenados:
            contagens[mts.template.codigo] = await _contagem_validacoes(db, mts.id)
        contexto["contagens"] = contagens

    if aba == "validacao":
        ocorrencias = {}
        for mts in templates_ordenados:
            stmt = (
                select(StagingBruto.linha, ValidacaoResultado)
                .join(StagingNormalizado, StagingNormalizado.staging_bruto_id == StagingBruto.id)
                .join(ValidacaoResultado, ValidacaoResultado.staging_normalizado_id == StagingNormalizado.id)
                .where(StagingBruto.migracao_template_status_id == mts.id)
                .order_by(StagingBruto.linha)
                .limit(200)
            )
            ocorrencias[mts.template.codigo] = (await db.execute(stmt)).all()
        contexto["ocorrencias"] = ocorrencias

    if aba == "scripts" or aba == "downloads":
        scripts = {}
        for mts in templates_ordenados:
            stmt = (
                select(ScriptGerado)
                .where(ScriptGerado.migracao_template_status_id == mts.id)
                .order_by(ScriptGerado.dt_geracao.desc())
            )
            scripts[mts.template.codigo] = (await db.execute(stmt)).scalars().first()
        contexto["scripts"] = scripts

    if aba == "aprovacao_tecnica":
        scripts = {}
        for mts in templates_ordenados:
            stmt = (
                select(ScriptGerado)
                .where(ScriptGerado.migracao_template_status_id == mts.id)
                .order_by(ScriptGerado.dt_geracao.desc())
            )
            scripts[mts.template.codigo] = (await db.execute(stmt)).scalars().first()
        contexto["scripts"] = scripts

    return templates.TemplateResponse(request, "migracao_detalhe.html", contexto)


def _redirect_aba(migracao_id: int, aba: str) -> RedirectResponse:
    return RedirectResponse(url=f"/portal/migracoes/{migracao_id}?aba={aba}", status_code=303)


def _flash_erro(request: Request, mensagem: str) -> None:
    """Mensagem de erro de uma ação que redireciona (PRG) — lida e descartada na próxima
    renderização de `detalhe_migracao` (`request.session.pop`)."""
    request.session["_flash_erro"] = mensagem


@router.post("/migracoes/{migracao_id}/cancelar")
async def cancelar(
    request: Request,
    migracao_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao = await _carregar(db, migracao_id, usuario)
    try:
        acoes.cancelar_migracao(db, migracao, usuario.nome)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "relatorio")


@router.post("/migracoes/{migracao_id}/reverter")
async def reverter(
    request: Request,
    migracao_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao = await _carregar(db, migracao_id, usuario)
    try:
        acoes.reverter_migracao(db, migracao, usuario.nome)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "relatorio")


@router.post("/migracoes/{migracao_id}/templates/{codigo}/arquivo")
async def upload_arquivo(
    request: Request,
    migracao_id: int,
    codigo: str,
    arquivo: UploadFile,
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    conteudo = await arquivo.read()
    try:
        await acoes.importar_arquivo(db, migracao, mts, arquivo.filename, conteudo, usuario.nome)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "templates")


@router.get("/migracoes/{migracao_id}/templates/{codigo}/progresso")
async def progresso_template(
    request: Request,
    migracao_id: int,
    codigo: str,
    usuario: Usuario = Depends(exigir_login),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    return templates.TemplateResponse(
        request, "_template_progress.html", {"migracao_id": migracao_id, "mts": mts, "usuario": usuario}
    )


@router.post("/migracoes/{migracao_id}/templates/{codigo}/pausar")
async def pausar(
    request: Request,
    migracao_id: int,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    erro = None
    try:
        acoes.pausar(mts)
    except AcaoInvalida as exc:
        erro = exc.mensagem
    return templates.TemplateResponse(
        request, "_template_progress.html", {"migracao_id": migracao_id, "mts": mts, "usuario": usuario, "erro": erro}
    )


@router.post("/migracoes/{migracao_id}/templates/{codigo}/continuar")
async def continuar(
    request: Request,
    migracao_id: int,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    erro = None
    try:
        await acoes.continuar(db, migracao, mts)
    except AcaoInvalida as exc:
        erro = exc.mensagem
    return templates.TemplateResponse(
        request, "_template_progress.html", {"migracao_id": migracao_id, "mts": mts, "usuario": usuario, "erro": erro}
    )


@router.post("/migracoes/{migracao_id}/templates/{codigo}/aprovar-dados")
async def aprovar_dados(
    request: Request,
    migracao_id: int,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.APROVADOR_FUNCIONAL, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    try:
        acoes.aprovar_dados(db, migracao, mts, usuario.nome)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "aprovacao_dados")


@router.post("/migracoes/{migracao_id}/templates/{codigo}/gerar-script")
async def gerar_script(
    request: Request,
    migracao_id: int,
    codigo: str,
    operacao: Annotated[str, Form()] = "INCLUSAO",
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.APROVADOR_FUNCIONAL, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    try:
        await acoes.gerar_script(db, migracao, mts, usuario.nome, operacao)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "scripts")


@router.post("/migracoes/{migracao_id}/templates/{codigo}/aprovar-script")
async def aprovar_script(
    request: Request,
    migracao_id: int,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.APROVADOR_TECNICO, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    try:
        acoes.aprovar_script(db, migracao, mts, usuario.nome)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "aprovacao_tecnica")


@router.post("/migracoes/{migracao_id}/templates/{codigo}/aplicar")
async def aplicar(
    request: Request,
    migracao_id: int,
    codigo: str,
    sucesso: Annotated[bool, Form()] = True,
    detalhe_erro: Annotated[str | None, Form()] = None,
    usuario: Usuario = Depends(exigir_papel(Papel.EXECUTOR_DBA, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    migracao, mts = await _carregar_com_mts(db, migracao_id, codigo, usuario)
    try:
        acoes.aplicar(db, migracao, mts, usuario.nome, sucesso, detalhe_erro)
    except AcaoInvalida as exc:
        _flash_erro(request, exc.mensagem)
    return _redirect_aba(migracao_id, "execucao")
