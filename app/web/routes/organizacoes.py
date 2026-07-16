from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.organizacao import Organizacao
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration/admin/organizacoes", tags=["portal-admin-organizacoes"])


@router.get("")
async def listar(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    organizacoes = (await db.execute(select(Organizacao).order_by(Organizacao.nome))).scalars().all()
    return templates.TemplateResponse(request, "organizacoes/list.html", {"usuario": usuario, "organizacoes": organizacoes})


@router.get("/nova")
async def form_nova(
    request: Request, usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR))
):
    return templates.TemplateResponse(request, "organizacoes/form.html", {"usuario": usuario})


@router.post("/nova")
async def criar(
    request: Request,
    nr_org: int = Form(...),
    nome: str = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    existente = await db.get(Organizacao, nr_org)
    if existente is not None:
        return templates.TemplateResponse(
            request,
            "organizacoes/form.html",
            {"usuario": usuario, "erro": f"Já existe uma organização com o número {nr_org}."},
            status_code=400,
        )
    db.add(Organizacao(nr_org=nr_org, nome=nome, ativo=True))
    return RedirectResponse(url="/portal-migration/admin/organizacoes", status_code=303)


@router.post("/{nr_org}/toggle-ativo")
async def alternar_ativo(
    nr_org: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organizacao, nr_org)
    if org is not None:
        org.ativo = not org.ativo
    return RedirectResponse(url="/portal-migration/admin/organizacoes", status_code=303)
