from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.migracoes import acoes
from app.migracoes.acoes import AcaoInvalida
from app.models.migracao import Migracao, MigracaoStatus
from app.models.organizacao import Organizacao
from app.models.tipo_migracao import TipoMigracao
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_login, exigir_papel
from app.web.templates_env import STATUS_MIGRACAO_META, templates

router = APIRouter(prefix="/portal", tags=["portal-dashboard"])

ESTADOS_FINALIZADOS = {
    MigracaoStatus.CONCLUIDA.value,
    MigracaoStatus.CONCLUIDA_COM_ALERTAS.value,
    MigracaoStatus.CANCELADA.value,
    MigracaoStatus.REVERTIDA.value,
}


@router.get("/")
async def dashboard(
    request: Request,
    status: str = "",
    operador: str = "",
    banco: str = "",
    data_ini: str = "",
    data_fim: str = "",
    incluir_concluidas: bool = False,
    usuario: Usuario = Depends(exigir_login),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Migracao).options(selectinload(Migracao.tipo_migracao)).order_by(Migracao.dt_criacao.desc())

    # Operador/aprovadores/executor enxergam só a própria organização (Seção 12.1);
    # administrador e auditor (nr_org nulo) enxergam todas.
    if usuario.nr_org is not None:
        stmt = stmt.where(Migracao.nr_org == usuario.nr_org)
    if status:
        stmt = stmt.where(Migracao.status == status)
    if operador:
        stmt = stmt.where(Migracao.operador.ilike(f"%{operador}%"))
    if banco:
        stmt = stmt.where(Migracao.tipo_migracao.has(TipoMigracao.banco_destino == banco))
    if data_ini:
        stmt = stmt.where(Migracao.dt_criacao >= datetime.fromisoformat(data_ini))
    if data_fim:
        stmt = stmt.where(Migracao.dt_criacao < datetime.fromisoformat(data_fim) + timedelta(days=1))
    if not incluir_concluidas:
        stmt = stmt.where(Migracao.status.not_in(ESTADOS_FINALIZADOS))

    migracoes = (await db.execute(stmt)).scalars().all()

    organizacoes_nome: dict[int, str] = {}
    nr_orgs = {m.nr_org for m in migracoes}
    if nr_orgs:
        orgs = (await db.execute(select(Organizacao).where(Organizacao.nr_org.in_(nr_orgs)))).scalars().all()
        organizacoes_nome = {o.nr_org: o.nome for o in orgs}

    bancos = sorted({t.banco_destino for t in (await db.execute(select(TipoMigracao))).scalars().all()})

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "usuario": usuario,
            "migracoes": migracoes,
            "organizacoes_nome": organizacoes_nome,
            "bancos": bancos,
            "status_opcoes": list(STATUS_MIGRACAO_META.items()),
            "filtros": {
                "status": status,
                "operador": operador,
                "banco": banco,
                "data_ini": data_ini,
                "data_fim": data_fim,
                "incluir_concluidas": incluir_concluidas,
            },
        },
    )


@router.get("/migracoes/nova")
async def tela_nova_migracao(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    organizacoes = (await db.execute(select(Organizacao).where(Organizacao.ativo.is_(True)))).scalars().all()
    tipos = (await db.execute(select(TipoMigracao))).scalars().all()
    return templates.TemplateResponse(
        request, "migracao_nova.html", {"usuario": usuario, "organizacoes": organizacoes, "tipos": tipos}
    )


@router.post("/migracoes/nova")
async def criar_nova_migracao(
    request: Request,
    nr_org: int = Form(...),
    tipo_migracao_codigo: str = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.OPERADOR, Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    try:
        migracao = await acoes.criar_migracao(db, nr_org, tipo_migracao_codigo, usuario.nome)
    except AcaoInvalida as exc:
        organizacoes = (await db.execute(select(Organizacao).where(Organizacao.ativo.is_(True)))).scalars().all()
        tipos = (await db.execute(select(TipoMigracao))).scalars().all()
        return templates.TemplateResponse(
            request,
            "migracao_nova.html",
            {"usuario": usuario, "organizacoes": organizacoes, "tipos": tipos, "erro": exc.mensagem},
            status_code=exc.status_code,
        )
    return RedirectResponse(url=f"/portal/migracoes/{migracao.id}", status_code=303)
