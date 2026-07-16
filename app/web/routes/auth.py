from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_senha, verificar_senha
from app.db.session import get_db
from app.models.usuario import Papel, Usuario
from app.web.deps import existe_algum_usuario, usuario_logado
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration", tags=["portal-auth"])


@router.get("/login")
async def tela_login(request: Request, db: AsyncSession = Depends(get_db)):
    if await usuario_logado(request, db) is not None:
        return RedirectResponse(url="/portal-migration/", status_code=303)
    if not await existe_algum_usuario(db):
        return RedirectResponse(url="/portal-migration/primeiro-acesso", status_code=303)
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
async def fazer_login(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    usuario = (await db.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none()
    if usuario is None or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
        return templates.TemplateResponse(
            request, "login.html", {"erro": "E-mail ou senha inválidos."}, status_code=401
        )
    request.session["usuario_id"] = usuario.id
    return RedirectResponse(url="/portal-migration/", status_code=303)


@router.post("/logout")
async def fazer_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/portal-migration/login", status_code=303)


@router.get("/primeiro-acesso")
async def tela_primeiro_acesso(request: Request, db: AsyncSession = Depends(get_db)):
    if await existe_algum_usuario(db):
        return RedirectResponse(url="/portal-migration/login", status_code=303)
    return templates.TemplateResponse(request, "primeiro_acesso.html", {})


@router.post("/primeiro-acesso")
async def criar_primeiro_administrador(
    request: Request,
    nome: str = Form(...),
    cargo: str = Form(""),
    email: str = Form(...),
    senha: str = Form(...),
    confirmar_senha: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if await existe_algum_usuario(db):
        return RedirectResponse(url="/portal-migration/login", status_code=303)
    if senha != confirmar_senha:
        return templates.TemplateResponse(
            request, "primeiro_acesso.html", {"erro": "As senhas não coincidem."}, status_code=400
        )
    if len(senha) < 8:
        return templates.TemplateResponse(
            request, "primeiro_acesso.html", {"erro": "A senha precisa ter ao menos 8 caracteres."}, status_code=400
        )

    usuario = Usuario(
        nome=nome,
        email=email,
        cargo=cargo or None,
        papel=Papel.ADMINISTRADOR.value,
        nr_org=None,
        senha_hash=hash_senha(senha),
    )
    db.add(usuario)
    await db.flush()
    request.session["usuario_id"] = usuario.id
    return RedirectResponse(url="/portal-migration/", status_code=303)
