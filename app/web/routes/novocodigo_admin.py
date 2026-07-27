from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.novocodigo import NovoCodigo
from app.models.organizacao import Organizacao
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration/admin/contadores", tags=["portal-admin-contadores"])


async def _organizacoes_nome(db: AsyncSession) -> dict[int, str]:
    orgs = (await db.execute(select(Organizacao))).scalars().all()
    return {o.nr_org: o.nome for o in orgs}


@router.get("")
async def listar(
    request: Request,
    nr_org: int | None = None,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NovoCodigo).order_by(NovoCodigo.nr_org, NovoCodigo.cd_contador)
    if nr_org is not None:
        stmt = stmt.where(NovoCodigo.nr_org == nr_org)
    contadores = (await db.execute(stmt)).scalars().all()

    nr_orgs_disponiveis = sorted(
        {row[0] for row in (await db.execute(select(NovoCodigo.nr_org).distinct())).all()}
    )

    return templates.TemplateResponse(
        request,
        "contadores/list.html",
        {
            "usuario": usuario,
            "contadores": contadores,
            "organizacoes_nome": await _organizacoes_nome(db),
            "nr_orgs_disponiveis": nr_orgs_disponiveis,
            "filtro_nr_org": nr_org,
        },
    )


@router.get("/novo")
async def form_novo(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        request, "contadores/form.html", {"usuario": usuario, "contador": None}
    )


@router.post("/novo")
async def criar(
    request: Request,
    nr_org: int = Form(...),
    cd_contador: str = Form(...),
    nr_proximo: int = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    cd_contador = cd_contador.strip().upper()
    existente = await db.get(NovoCodigo, (nr_org, cd_contador))
    if existente is not None:
        return templates.TemplateResponse(
            request,
            "contadores/form.html",
            {
                "usuario": usuario,
                "contador": None,
                "erro": f'Já existe um contador "{cd_contador}" para a organização {nr_org} — edite o existente.',
            },
            status_code=400,
        )

    db.add(NovoCodigo(nr_org=nr_org, cd_contador=cd_contador, nr_proximo=nr_proximo))
    return RedirectResponse(url="/portal-migration/admin/contadores", status_code=303)


@router.get("/{nr_org}/{cd_contador}/editar")
async def form_editar(
    request: Request,
    nr_org: int,
    cd_contador: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    contador = await db.get(NovoCodigo, (nr_org, cd_contador))
    if contador is None:
        return RedirectResponse(url="/portal-migration/admin/contadores", status_code=303)
    return templates.TemplateResponse(
        request, "contadores/form.html", {"usuario": usuario, "contador": contador}
    )


@router.post("/{nr_org}/{cd_contador}/editar")
async def editar(
    request: Request,
    nr_org: int,
    cd_contador: str,
    nr_proximo: int = Form(...),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    contador = await db.get(NovoCodigo, (nr_org, cd_contador))
    if contador is not None:
        contador.nr_proximo = nr_proximo
    return RedirectResponse(url="/portal-migration/admin/contadores", status_code=303)


@router.post("/{nr_org}/{cd_contador}/zerar")
async def zerar(
    nr_org: int,
    cd_contador: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    contador = await db.get(NovoCodigo, (nr_org, cd_contador))
    if contador is not None:
        contador.nr_proximo = 0
    return RedirectResponse(url="/portal-migration/admin/contadores", status_code=303)
