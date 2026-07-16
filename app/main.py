from fastapi import FastAPI

from app.api.routes import health, templates, tipos_migracao


def create_app() -> FastAPI:
    app = FastAPI(
        title="Plataforma de Migração de Dados ERP/HCM",
        description="Motor genérico de migração orientado por metadados — upload, validação, geração de SQL, aprovação e aplicação.",
        version="0.1.0",
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(templates.router)
    app.include_router(tipos_migracao.router)
    return app


app = create_app()
