from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.template import Template, TemplateCampo, TemplateScript
from app.models.usuario import Papel, Usuario
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal/admin/templates", tags=["portal-admin-templates"])


async def _carregar_template(db: AsyncSession, codigo: str) -> Template | None:
    stmt = (
        select(Template)
        .where(Template.codigo == codigo)
        .options(selectinload(Template.campos), selectinload(Template.scripts))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


@router.get("")
async def listar(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    tpls = (await db.execute(select(Template).order_by(Template.nome))).scalars().all()
    return templates.TemplateResponse(request, "templates_admin/list.html", {"usuario": usuario, "templates": tpls})


@router.get("/novo")
async def form_novo(request: Request, usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR))):
    return templates.TemplateResponse(request, "templates_admin/form.html", {"usuario": usuario})


@router.post("/novo")
async def criar(
    request: Request,
    codigo: str = Form(...),
    nome: str = Form(...),
    versao: str = Form("1.0"),
    formatos_aceitos: str = Form("XLSX"),
    sheet_name: str = Form(""),
    header_row: int | None = Form(None),
    data_start_row: int | None = Form(None),
    eh_catalogo: bool = Form(False),
    pre_requisito_externo: str = Form(""),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    existente = await _carregar_template(db, codigo)
    if existente is not None:
        return templates.TemplateResponse(
            request,
            "templates_admin/form.html",
            {"usuario": usuario, "erro": f'Já existe um template com o código "{codigo}".'},
            status_code=400,
        )
    db.add(
        Template(
            codigo=codigo,
            nome=nome,
            versao=versao,
            formatos_aceitos=[f.strip().upper() for f in formatos_aceitos.split(",") if f.strip()],
            sheet_name=sheet_name or None,
            header_row=header_row,
            data_start_row=data_start_row,
            eh_catalogo=eh_catalogo,
            pre_requisito_externo=pre_requisito_externo or None,
        )
    )
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


@router.get("/{codigo}")
async def detalhe(
    request: Request,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    template = await _carregar_template(db, codigo)
    return templates.TemplateResponse(request, "templates_admin/detalhe.html", {"usuario": usuario, "template": template})


# --- campos do dicionário de dados -----------------------------------------------------------


@router.get("/{codigo}/campos/novo")
async def form_novo_campo(
    request: Request, codigo: str, usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR))
):
    return templates.TemplateResponse(
        request, "templates_admin/campo_form.html", {"usuario": usuario, "codigo": codigo, "campo": None}
    )


@router.post("/{codigo}/campos/novo")
async def criar_campo(
    codigo: str,
    ordem: int = Form(...),
    origem: str = Form(...),
    rotulo: str = Form(...),
    campo: str = Form(...),
    marcador: str = Form(""),
    destino_tabela: str = Form(...),
    destino_coluna: str = Form(...),
    tipo: str = Form(...),
    tamanho_maximo: int | None = Form(None),
    obrigatorio: bool = Form(False),
    valor_padrao: str = Form(""),
    regra_conversao: str = Form(""),
    regra_validacao: str = Form(""),
    eh_pk: bool = Form(False),
    gerador_pk: bool = Form(False),
    gerador_pk_contador: str = Form(""),
    gerador_pk_seed: int | None = Form(None),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    template = await _carregar_template(db, codigo)
    db.add(
        TemplateCampo(
            template_id=template.id,
            ordem=ordem,
            origem=origem,
            rotulo=rotulo,
            campo=campo,
            marcador=marcador or None,
            destino_tabela=destino_tabela,
            destino_coluna=destino_coluna,
            tipo=tipo,
            tamanho_maximo=tamanho_maximo,
            obrigatorio=obrigatorio,
            valor_padrao=valor_padrao or None,
            regra_conversao=regra_conversao or None,
            regra_validacao=regra_validacao or None,
            eh_pk=eh_pk,
            gerador_pk=gerador_pk,
            gerador_pk_contador=gerador_pk_contador or None,
            gerador_pk_seed=gerador_pk_seed,
        )
    )
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


@router.get("/{codigo}/campos/{campo_id}/editar")
async def form_editar_campo(
    request: Request,
    codigo: str,
    campo_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    campo = await db.get(TemplateCampo, campo_id)
    return templates.TemplateResponse(
        request, "templates_admin/campo_form.html", {"usuario": usuario, "codigo": codigo, "campo": campo}
    )


@router.post("/{codigo}/campos/{campo_id}/editar")
async def editar_campo(
    codigo: str,
    campo_id: int,
    ordem: int = Form(...),
    origem: str = Form(...),
    rotulo: str = Form(...),
    campo: str = Form(...),
    marcador: str = Form(""),
    destino_tabela: str = Form(...),
    destino_coluna: str = Form(...),
    tipo: str = Form(...),
    tamanho_maximo: int | None = Form(None),
    obrigatorio: bool = Form(False),
    valor_padrao: str = Form(""),
    regra_conversao: str = Form(""),
    regra_validacao: str = Form(""),
    eh_pk: bool = Form(False),
    gerador_pk: bool = Form(False),
    gerador_pk_contador: str = Form(""),
    gerador_pk_seed: int | None = Form(None),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TemplateCampo, campo_id)
    alvo.ordem = ordem
    alvo.origem = origem
    alvo.rotulo = rotulo
    alvo.campo = campo
    alvo.marcador = marcador or None
    alvo.destino_tabela = destino_tabela
    alvo.destino_coluna = destino_coluna
    alvo.tipo = tipo
    alvo.tamanho_maximo = tamanho_maximo
    alvo.obrigatorio = obrigatorio
    alvo.valor_padrao = valor_padrao or None
    alvo.regra_conversao = regra_conversao or None
    alvo.regra_validacao = regra_validacao or None
    alvo.eh_pk = eh_pk
    alvo.gerador_pk = gerador_pk
    alvo.gerador_pk_contador = gerador_pk_contador or None
    alvo.gerador_pk_seed = gerador_pk_seed
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


@router.post("/{codigo}/campos/{campo_id}/excluir")
async def excluir_campo(
    codigo: str,
    campo_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TemplateCampo, campo_id)
    if alvo is not None:
        await db.delete(alvo)
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


# --- blocos de script (@CAMPO@) ----------------------------------------------------------------


@router.get("/{codigo}/scripts/novo")
async def form_novo_script(
    request: Request, codigo: str, usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR))
):
    return templates.TemplateResponse(
        request, "templates_admin/script_form.html", {"usuario": usuario, "codigo": codigo, "script": None}
    )


@router.post("/{codigo}/scripts/novo")
async def criar_script(
    codigo: str,
    operacao: str = Form(...),
    dialeto_banco: str = Form("ORACLE"),
    ordem: int = Form(1),
    condicao_campo: str = Form(""),
    template_sql: str = Form(...),
    template_rollback: str = Form(""),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    template = await _carregar_template(db, codigo)
    db.add(
        TemplateScript(
            template_id=template.id,
            operacao=operacao,
            dialeto_banco=dialeto_banco,
            ordem=ordem,
            condicao_campo=condicao_campo or None,
            template_sql=template_sql,
            template_rollback=template_rollback or None,
        )
    )
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


@router.get("/{codigo}/scripts/{script_id}/editar")
async def form_editar_script(
    request: Request,
    codigo: str,
    script_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    script = await db.get(TemplateScript, script_id)
    return templates.TemplateResponse(
        request, "templates_admin/script_form.html", {"usuario": usuario, "codigo": codigo, "script": script}
    )


@router.post("/{codigo}/scripts/{script_id}/editar")
async def editar_script(
    codigo: str,
    script_id: int,
    operacao: str = Form(...),
    dialeto_banco: str = Form("ORACLE"),
    ordem: int = Form(1),
    condicao_campo: str = Form(""),
    template_sql: str = Form(...),
    template_rollback: str = Form(""),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TemplateScript, script_id)
    alvo.operacao = operacao
    alvo.dialeto_banco = dialeto_banco
    alvo.ordem = ordem
    alvo.condicao_campo = condicao_campo or None
    alvo.template_sql = template_sql
    alvo.template_rollback = template_rollback or None
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)


@router.post("/{codigo}/scripts/{script_id}/excluir")
async def excluir_script(
    codigo: str,
    script_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    alvo = await db.get(TemplateScript, script_id)
    if alvo is not None:
        await db.delete(alvo)
    return RedirectResponse(url=f"/portal/admin/templates/{codigo}", status_code=303)
