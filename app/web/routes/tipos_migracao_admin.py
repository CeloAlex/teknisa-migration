from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.template import Template
from app.models.tipo_migracao import TipoMigracao, TipoMigracaoTemplate, TipoMigracaoTemplateDependencia
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration/admin/tipos-migracao", tags=["portal-admin-tipos-migracao"])


async def _carregar_tipo(db: AsyncSession, codigo: str) -> TipoMigracao | None:
    stmt = (
        select(TipoMigracao)
        .where(TipoMigracao.codigo == codigo)
        .options(
            selectinload(TipoMigracao.templates).selectinload(TipoMigracaoTemplate.template),
            selectinload(TipoMigracao.templates)
            .selectinload(TipoMigracaoTemplate.dependencias)
            .selectinload(TipoMigracaoTemplateDependencia.depende_de_template),
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


@router.get("")
async def listar(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    tipos = (await db.execute(select(TipoMigracao).options(selectinload(TipoMigracao.templates)))).scalars().all()
    return templates.TemplateResponse(request, "tipos_migracao/list.html", {"usuario": usuario, "tipos": tipos})


@router.get("/novo")
async def form_novo(request: Request, usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR))):
    return templates.TemplateResponse(request, "tipos_migracao/form.html", {"usuario": usuario})


@router.post("/novo")
async def criar(
    request: Request,
    codigo: str = Form(...),
    nome: str = Form(...),
    banco_destino: str = Form(...),
    modo_aplicacao: str = Form("SCRIPT"),
    permite_concorrencia: bool = Form(False),
    sequencia_obrigatoria: bool = Form(False),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    existente = await _carregar_tipo(db, codigo)
    if existente is not None:
        return templates.TemplateResponse(
            request,
            "tipos_migracao/form.html",
            {"usuario": usuario, "erro": f'Já existe um tipo de migração com o código "{codigo}".'},
            status_code=400,
        )
    db.add(
        TipoMigracao(
            codigo=codigo,
            nome=nome,
            banco_destino=banco_destino,
            modo_aplicacao=modo_aplicacao,
            permite_concorrencia=permite_concorrencia,
            sequencia_obrigatoria=sequencia_obrigatoria,
        )
    )
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)


@router.get("/{codigo}")
async def detalhe(
    request: Request,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    tipo = await _carregar_tipo(db, codigo)
    ids_no_tipo = {tmt.template_id for tmt in tipo.templates}
    todos_templates = (await db.execute(select(Template).order_by(Template.nome))).scalars().all()
    templates_disponiveis = [t for t in todos_templates if t.id not in ids_no_tipo]
    return templates.TemplateResponse(
        request,
        "tipos_migracao/detalhe.html",
        {"usuario": usuario, "tipo": tipo, "templates_disponiveis": templates_disponiveis},
    )


@router.post("/{codigo}/templates/adicionar")
async def adicionar_template(
    codigo: str,
    template_id: int = Form(...),
    ordem: int = Form(...),
    obrigatorio: bool = Form(True),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    tipo = await _carregar_tipo(db, codigo)
    db.add(
        TipoMigracaoTemplate(
            tipo_migracao_id=tipo.id, template_id=template_id, ordem=ordem, obrigatorio=obrigatorio
        )
    )
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)


@router.post("/{codigo}/templates/{tmt_id}/editar")
async def editar_template_do_tipo(
    codigo: str,
    tmt_id: int,
    ordem: int = Form(...),
    obrigatorio: bool = Form(False),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TipoMigracaoTemplate, tmt_id)
    if alvo is not None:
        alvo.ordem = ordem
        alvo.obrigatorio = obrigatorio
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)


@router.post("/{codigo}/templates/{tmt_id}/remover")
async def remover_template_do_tipo(
    codigo: str,
    tmt_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TipoMigracaoTemplate, tmt_id)
    if alvo is not None:
        await db.delete(alvo)
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)


@router.post("/{codigo}/dependencias/adicionar")
async def adicionar_dependencia(
    codigo: str,
    tipo_migracao_template_id: int = Form(...),
    depende_de_template_id: int = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    db.add(
        TipoMigracaoTemplateDependencia(
            tipo_migracao_template_id=tipo_migracao_template_id,
            depende_de_template_id=depende_de_template_id,
        )
    )
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)


@router.post("/{codigo}/dependencias/{dep_id}/remover")
async def remover_dependencia(
    codigo: str,
    dep_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TipoMigracaoTemplateDependencia, dep_id)
    if alvo is not None:
        await db.delete(alvo)
    return RedirectResponse(url=f"/portal-migration/admin/tipos-migracao/{codigo}", status_code=303)
