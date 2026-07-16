from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_senha
from app.db.session import get_db
from app.models.organizacao import Organizacao
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration/admin/operadores", tags=["portal-admin-operadores"])

PAPEIS_SEM_ORGANIZACAO = {Papel.ADMINISTRADOR.value, Papel.AUDITOR.value}


async def _organizacoes_ativas(db: AsyncSession) -> list[Organizacao]:
    return (await db.execute(select(Organizacao).where(Organizacao.ativo.is_(True)).order_by(Organizacao.nome))).scalars().all()


@router.get("")
async def listar(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    operadores = (await db.execute(select(Usuario).order_by(Usuario.nome))).scalars().all()
    orgs = (await db.execute(select(Organizacao))).scalars().all()
    organizacoes_nome = {o.nr_org: o.nome for o in orgs}
    return templates.TemplateResponse(
        request,
        "operadores/list.html",
        {"usuario": usuario, "operadores": operadores, "organizacoes_nome": organizacoes_nome},
    )


@router.get("/novo")
async def form_novo(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    organizacoes = await _organizacoes_ativas(db)
    return templates.TemplateResponse(
        request, "operadores/form.html", {"usuario": usuario, "organizacoes": organizacoes, "operador": None}
    )


@router.post("/novo")
async def criar(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    cargo: str = Form(""),
    papel: str = Form(...),
    nr_org: int | None = Form(None),
    senha: str = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    existente = (await db.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
    if existente is not None:
        organizacoes = await _organizacoes_ativas(db)
        return templates.TemplateResponse(
            request,
            "operadores/form.html",
            {
                "usuario": usuario,
                "organizacoes": organizacoes,
                "operador": None,
                "erro": f'Já existe um operador com o e-mail "{email}".',
            },
            status_code=400,
        )

    novo = Usuario(
        nome=nome,
        email=email,
        cargo=cargo or None,
        papel=papel,
        nr_org=None if papel in PAPEIS_SEM_ORGANIZACAO else nr_org,
        senha_hash=hash_senha(senha),
    )
    db.add(novo)
    return RedirectResponse(url="/portal-migration/admin/operadores", status_code=303)


@router.get("/{operador_id}/editar")
async def form_editar(
    request: Request,
    operador_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(Usuario, operador_id)
    organizacoes = await _organizacoes_ativas(db)
    return templates.TemplateResponse(
        request, "operadores/form.html", {"usuario": usuario, "organizacoes": organizacoes, "operador": alvo}
    )


@router.post("/{operador_id}/editar")
async def editar(
    request: Request,
    operador_id: int,
    nome: str = Form(...),
    email: str = Form(...),
    cargo: str = Form(""),
    papel: str = Form(...),
    nr_org: int | None = Form(None),
    senha: str = Form(""),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(Usuario, operador_id)
    duplicado = (
        await db.execute(select(Usuario).where(Usuario.email == email, Usuario.id != operador_id))
    ).scalar_one_or_none()
    if duplicado is not None:
        organizacoes = await _organizacoes_ativas(db)
        return templates.TemplateResponse(
            request,
            "operadores/form.html",
            {
                "usuario": usuario,
                "organizacoes": organizacoes,
                "operador": alvo,
                "erro": f'Já existe um operador com o e-mail "{email}".',
            },
            status_code=400,
        )

    alvo.nome = nome
    alvo.email = email
    alvo.cargo = cargo or None
    alvo.papel = papel
    alvo.nr_org = None if papel in PAPEIS_SEM_ORGANIZACAO else nr_org
    if senha:
        alvo.senha_hash = hash_senha(senha)
    return RedirectResponse(url="/portal-migration/admin/operadores", status_code=303)


@router.post("/{operador_id}/toggle-ativo")
async def alternar_ativo(
    operador_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(Usuario, operador_id)
    if alvo is not None:
        alvo.ativo = not alvo.ativo
    return RedirectResponse(url="/portal-migration/admin/operadores", status_code=303)
