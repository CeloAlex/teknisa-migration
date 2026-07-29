from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import health, migracoes, templates, tipos_migracao
from app.core.config import get_settings
from app.migracoes.acoes import AcaoInvalida
from app.web.deps import NaoAutenticado, SemPermissao, SenhaTrocaObrigatoria
from app.web.routes import auth as web_auth
from app.web.routes import dashboard as web_dashboard
from app.web.routes import migracao as web_migracao
from app.web.routes import novocodigo_admin as web_novocodigo_admin
from app.web.routes import operadores as web_operadores
from app.web.routes import organizacoes as web_organizacoes
from app.web.routes import templates_admin as web_templates_admin
from app.web.routes import tipos_migracao_admin as web_tipos_migracao_admin
from app.web.routes import trocar_senha as web_trocar_senha
from app.web.templates_env import BASE_DIR as WEB_BASE_DIR
from app.web.templates_env import templates as web_templates


def create_app() -> FastAPI:
    app = FastAPI(
        title="Plataforma de Migração de Dados - Teknisa",
        description="Motor genérico de migração orientado por metadados — upload, validação, geração de SQL, aprovação e aplicação.",
        version="0.1.0",
    )
    settings = get_settings()
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site="lax",
        https_only=settings.environment == "production",
    )

    @app.middleware("http")
    async def _sem_cache_paginas_dinamicas(request: Request, call_next):
        """Sem isso, o navegador pode reaproveitar do cache heurístico uma resposta antiga
        do portal (dashboard, detalhe de migração etc.) sem revalidar — depois de uma ação
        que muda dado no servidor (ex.: "Regerar script"), o redirect PRG pode acabar
        mostrando a versão em cache em vez do conteúdo recém-atualizado. Os arquivos
        estáticos (`/static`) ficam de fora — esses já têm cache-busting próprio via
        `?v=<mtime>` em `static_version()`, então cache agressivo neles é desejável."""
        response = await call_next(request)
        if not request.url.path.startswith("/portal-migration/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(health.router, tags=["health"])
    app.include_router(templates.router)
    app.include_router(tipos_migracao.router)
    app.include_router(migracoes.router)

    app.include_router(web_auth.router)
    app.include_router(web_dashboard.router)
    app.include_router(web_migracao.router)
    app.include_router(web_novocodigo_admin.router)
    app.include_router(web_operadores.router)
    app.include_router(web_organizacoes.router)
    app.include_router(web_templates_admin.router)
    app.include_router(web_templates_admin.router_catalogo)
    app.include_router(web_tipos_migracao_admin.router)
    app.include_router(web_trocar_senha.router)
    app.mount("/portal-migration/static", StaticFiles(directory=str(WEB_BASE_DIR / "static")), name="portal-static")

    @app.exception_handler(AcaoInvalida)
    async def _acao_invalida(request: Request, exc: AcaoInvalida) -> JSONResponse:
        """Handler global — usado pela API JSON, que deixa `AcaoInvalida` propagar sem
        try/except em cada rota (mesmo formato de resposta que o `HTTPException` de antes
        da extração de app/migracoes/acoes.py). O portal web captura essa exceção
        localmente em vez de deixá-la chegar aqui, para renderizar uma página com mensagem
        de erro em vez de um JSON cru."""
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensagem})

    @app.exception_handler(NaoAutenticado)
    async def _redirecionar_login(request: Request, exc: NaoAutenticado) -> RedirectResponse:
        return RedirectResponse(url="/portal-migration/login", status_code=303)

    @app.exception_handler(SemPermissao)
    async def _sem_permissao(request: Request, exc: SemPermissao):
        return web_templates.TemplateResponse(request, "errors/403.html", {"mensagem": exc.mensagem}, status_code=403)

    @app.exception_handler(SenhaTrocaObrigatoria)
    async def _senha_troca_obrigatoria(request: Request, exc: SenhaTrocaObrigatoria) -> RedirectResponse:
        return RedirectResponse(url="/portal-migration/trocar-senha", status_code=303)

    return app


app = create_app()
