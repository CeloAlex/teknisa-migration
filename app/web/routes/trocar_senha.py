from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_senha, verificar_senha
from app.db.session import get_db
from app.models.usuario import Usuario
from app.web.deps import exigir_login
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration", tags=["portal-trocar-senha"])


@router.get("/trocar-senha")
async def form_trocar_senha(request: Request, usuario: Usuario = Depends(exigir_login)):
    return templates.TemplateResponse(request, "trocar_senha.html", {"usuario": usuario})


@router.post("/trocar-senha")
async def trocar_senha(
    request: Request,
    senha_atual: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...),
    cdoperador: str = Form(""),
    usuario: Usuario = Depends(exigir_login),
    db: AsyncSession = Depends(get_db),
):
    if not verificar_senha(senha_atual, usuario.senha_hash):
        return templates.TemplateResponse(
            request,
            "trocar_senha.html",
            {"usuario": usuario, "erro": "Senha atual incorreta."},
            status_code=400,
        )
    if nova_senha != confirmar_senha:
        return templates.TemplateResponse(
            request,
            "trocar_senha.html",
            {"usuario": usuario, "erro": "As senhas não coincidem."},
            status_code=400,
        )
    if len(nova_senha) < 8:
        return templates.TemplateResponse(
            request,
            "trocar_senha.html",
            {"usuario": usuario, "erro": "A senha precisa ter ao menos 8 caracteres."},
            status_code=400,
        )

    usuario.senha_hash = hash_senha(nova_senha)
    usuario.deve_trocar_senha = False
    usuario.cdoperador = cdoperador.strip() or usuario.cdoperador
    return RedirectResponse(url="/portal-migration/", status_code=303)
