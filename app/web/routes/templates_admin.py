from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.metadata.ddl_import import parse_ddl_oracle
from app.models.catalogo_destino import CatalogoColuna, CatalogoTabela
from app.models.template import Template, TemplateCampo, TemplateScript
from app.models.usuario import Papel, Usuario
from app.transformation.conversions import CONVERSOES
from app.web.deps import exigir_papel
from app.web.templates_env import templates

router = APIRouter(prefix="/portal-migration/admin/templates", tags=["portal-admin-templates"])
router_catalogo = APIRouter(prefix="/portal-migration/admin/catalogo-destino", tags=["portal-admin-catalogo-destino"])


def _flash_catalogo(request: Request, mensagem: str, tipo: str = "ok") -> None:
    request.session["_flash_catalogo"] = {"tipo": tipo, "mensagem": mensagem}


async def _carregar_template(db: AsyncSession, codigo: str) -> Template | None:
    stmt = (
        select(Template)
        .where(Template.codigo == codigo)
        .options(selectinload(Template.campos), selectinload(Template.scripts))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _formatos_conhecidos(db: AsyncSession) -> list[str]:
    """Valores individuais de `formatos_aceitos` já usados em algum template, para
    autocomplete no formulário de criação — o campo aceita uma lista separada por vírgula,
    então sugerimos os tokens conhecidos em vez da combinação completa."""
    subq = select(func.unnest(Template.formatos_aceitos).label("formato")).subquery()
    stmt = select(subq.c.formato).distinct().order_by(subq.c.formato)
    return [linha[0] for linha in (await db.execute(stmt)).all()]


async def _valores_distintos_campo(db: AsyncSession, coluna) -> list[str]:
    """Valores distintos e não vazios de uma coluna de `TemplateCampo`, para autocomplete —
    reúne o que já foi digitado em outros templates/campos do dicionário de dados."""
    stmt = select(coluna).where(coluna.is_not(None), coluna != "").distinct().order_by(coluna)
    return [linha[0] for linha in (await db.execute(stmt)).all()]


async def _nomes_campos_do_template(db: AsyncSession, codigo: str) -> list[str]:
    """Nomes de `campo` já cadastrados no mesmo template — autocomplete para
    `duplicata_agrupado_por`/`alerta_se_vazio_quando_campo`, que sempre referenciam outro
    campo do próprio dicionário (nunca de outro template)."""
    stmt = (
        select(TemplateCampo.campo)
        .join(Template, Template.id == TemplateCampo.template_id)
        .where(Template.codigo == codigo)
        .order_by(TemplateCampo.campo)
    )
    return [linha[0] for linha in (await db.execute(stmt)).all()]


async def _sugestoes_campo(db: AsyncSession) -> dict[str, list[str]]:
    tipos = await _valores_distintos_campo(db, TemplateCampo.tipo)
    valores_padrao = await _valores_distintos_campo(db, TemplateCampo.valor_padrao)
    regras_db = await _valores_distintos_campo(db, TemplateCampo.regra_conversao)
    # Une com o registro de conversões válidas (`CONVERSOES`) — a lista de campos já
    # preenchidos pode não cobrir toda regra existente, e uma regra que não está em
    # `CONVERSOES` é ignorada silenciosamente por `aplicar_conversao`.
    regras_conversao = sorted(set(CONVERSOES.keys()) | set(regras_db))
    return {"tipos": tipos, "valores_padrao": valores_padrao, "regras_conversao": regras_conversao}


@router.get("")
async def listar(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    tpls = (await db.execute(select(Template).order_by(Template.nome))).scalars().all()
    return templates.TemplateResponse(request, "templates_admin/list.html", {"usuario": usuario, "templates": tpls})


@router.get("/novo")
async def form_novo(
    request: Request,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    return templates.TemplateResponse(
        request,
        "templates_admin/form.html",
        {"usuario": usuario, "formatos_conhecidos": await _formatos_conhecidos(db)},
    )


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
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


@router.get("/{codigo}")
async def detalhe(
    request: Request,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    template = await _carregar_template(db, codigo)
    catalogo_tabelas = (await db.execute(select(CatalogoTabela).order_by(CatalogoTabela.nome_tabela))).scalars().all()
    return templates.TemplateResponse(
        request,
        "templates_admin/detalhe.html",
        {
            "usuario": usuario,
            "template": template,
            "catalogo_tabelas": catalogo_tabelas,
            "flash_catalogo": request.session.pop("_flash_catalogo", None),
        },
    )


# --- campos do dicionário de dados -----------------------------------------------------------


@router.get("/{codigo}/campos/novo")
async def form_novo_campo(
    request: Request,
    codigo: str,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    catalogo_tabelas = (await db.execute(select(CatalogoTabela).order_by(CatalogoTabela.nome_tabela))).scalars().all()
    return templates.TemplateResponse(
        request,
        "templates_admin/campo_form.html",
        {
            "usuario": usuario,
            "codigo": codigo,
            "campo": None,
            "catalogo_tabelas": catalogo_tabelas,
            "nomes_campos": await _nomes_campos_do_template(db, codigo),
            **(await _sugestoes_campo(db)),
        },
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
    destino_coluna_catalogo_id: int | None = Form(None),
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
    dominio_valores: str = Form(""),
    duplicata_no_lote: str = Form(""),
    duplicata_agrupado_por: str = Form(""),
    alerta_se_vazio_quando_campo: str = Form(""),
    alerta_se_vazio_quando_valores: str = Form(""),
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
            destino_coluna_catalogo_id=destino_coluna_catalogo_id,
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
            dominio_valores=dominio_valores or None,
            duplicata_no_lote=duplicata_no_lote or None,
            duplicata_agrupado_por=duplicata_agrupado_por or None,
            alerta_se_vazio_quando_campo=alerta_se_vazio_quando_campo or None,
            alerta_se_vazio_quando_valores=alerta_se_vazio_quando_valores or None,
        )
    )
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


@router.get("/{codigo}/campos/{campo_id}/editar")
async def form_editar_campo(
    request: Request,
    codigo: str,
    campo_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    campo = await db.get(TemplateCampo, campo_id)
    catalogo_tabelas = (await db.execute(select(CatalogoTabela).order_by(CatalogoTabela.nome_tabela))).scalars().all()
    return templates.TemplateResponse(
        request,
        "templates_admin/campo_form.html",
        {
            "usuario": usuario,
            "codigo": codigo,
            "campo": campo,
            "catalogo_tabelas": catalogo_tabelas,
            "nomes_campos": await _nomes_campos_do_template(db, codigo),
            **(await _sugestoes_campo(db)),
        },
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
    destino_coluna_catalogo_id: int | None = Form(None),
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
    dominio_valores: str = Form(""),
    duplicata_no_lote: str = Form(""),
    duplicata_agrupado_por: str = Form(""),
    alerta_se_vazio_quando_campo: str = Form(""),
    alerta_se_vazio_quando_valores: str = Form(""),
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
    alvo.destino_coluna_catalogo_id = destino_coluna_catalogo_id
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
    alvo.dominio_valores = dominio_valores or None
    alvo.duplicata_no_lote = duplicata_no_lote or None
    alvo.duplicata_agrupado_por = duplicata_agrupado_por or None
    alvo.alerta_se_vazio_quando_campo = alerta_se_vazio_quando_campo or None
    alvo.alerta_se_vazio_quando_valores = alerta_se_vazio_quando_valores or None
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


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
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


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
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


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
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


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
    return RedirectResponse(url=f"/portal-migration/admin/templates/{codigo}", status_code=303)


# --- catálogo de destino (importador de DDL Oracle) -----------------------------------------


@router_catalogo.post("/importar")
async def importar_ddl(
    request: Request,
    arquivo: UploadFile,
    voltar: str = Form(""),
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    conteudo_bruto = await arquivo.read()
    try:
        conteudo = conteudo_bruto.decode("utf-8")
    except UnicodeDecodeError:
        conteudo = conteudo_bruto.decode("latin-1")

    tabelas_importadas = parse_ddl_oracle(conteudo)
    if not tabelas_importadas:
        _flash_catalogo(request, "Nenhum CREATE TABLE encontrado no arquivo enviado.", tipo="block")
    else:
        nr_tabelas = 0
        nr_colunas = 0
        for tabela_ddl in tabelas_importadas:
            tabela = (
                await db.execute(select(CatalogoTabela).where(CatalogoTabela.nome_tabela == tabela_ddl.nome_tabela))
            ).scalar_one_or_none()
            if tabela is None:
                tabela = CatalogoTabela(nome_tabela=tabela_ddl.nome_tabela)
                db.add(tabela)
                await db.flush()
            nr_tabelas += 1

            colunas_existentes = {
                c.nome_coluna: c
                for c in (
                    await db.execute(select(CatalogoColuna).where(CatalogoColuna.tabela_id == tabela.id))
                ).scalars()
            }
            for coluna_ddl in tabela_ddl.colunas:
                coluna = colunas_existentes.get(coluna_ddl.nome_coluna)
                if coluna is None:
                    db.add(
                        CatalogoColuna(
                            tabela_id=tabela.id,
                            nome_coluna=coluna_ddl.nome_coluna,
                            tipo_dado=coluna_ddl.tipo_dado,
                            obrigatoria=coluna_ddl.obrigatoria,
                        )
                    )
                else:
                    coluna.tipo_dado = coluna_ddl.tipo_dado
                    coluna.obrigatoria = coluna_ddl.obrigatoria
                nr_colunas += 1

        _flash_catalogo(request, f"{nr_tabelas} tabela(s) e {nr_colunas} coluna(s) importadas do DDL.")

    if voltar:
        return RedirectResponse(url=f"/portal-migration/admin/templates/{voltar}", status_code=303)
    return RedirectResponse(url="/portal-migration/admin/templates", status_code=303)


@router_catalogo.get("/{tabela_id}/colunas", response_class=HTMLResponse)
async def colunas_da_tabela(
    tabela_id: int,
    usuario: Usuario = Depends(exigir_papel(Papel.ADMINISTRADOR)),
    db: AsyncSession = Depends(get_db),
):
    """Fragmento HTML (`<option>`s) para popular o select de coluna via htmx, em cascata a
    partir do select de tabela — mesmo padrão server-rendered do resto do portal."""
    colunas = (
        await db.execute(select(CatalogoColuna).where(CatalogoColuna.tabela_id == tabela_id).order_by(CatalogoColuna.nome_coluna))
    ).scalars().all()
    opcoes = ['<option value="">— selecione —</option>']
    for c in colunas:
        rotulo = c.nome_coluna + (f" ({c.tipo_dado})" if c.tipo_dado else "")
        opcoes.append(f'<option value="{c.id}" data-nome="{c.nome_coluna}">{rotulo}</option>')
    return HTMLResponse("".join(opcoes))
