from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    CampoDicionarioResponse,
    LinhaResultadoResponse,
    PreviewResponse,
    TemplateResponse,
    ValidacaoResponse,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.ingestion.xlsx import LINHA_PLANILHA, ArquivoInvalido, ler_xlsx
from app.metadata.resolver import TemplateNaoEncontrado, resolver_template
from app.metadata.schemas import TemplateMetadata
from app.scripts.generator import ContextoExecucao, ScriptNaoConfigurado, gerar_script
from app.transformation.engine import aplicar_transformacoes
from app.validation.classificacao import Classificacao
from app.validation.engine import validar_linha
from app.validation.schemas import ResultadoValidacao

router = APIRouter(prefix="/templates", tags=["templates"])

LinhaProcessada = tuple[int | None, dict[str, Any], list[ResultadoValidacao], bool]


async def _carregar_template(codigo: str, db: AsyncSession) -> TemplateMetadata:
    try:
        return await resolver_template(db, codigo)
    except TemplateNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _processar_arquivo(
    conteudo: bytes, template: TemplateMetadata, nr_org: int
) -> tuple[list[LinhaProcessada], list[dict[str, Any]]]:
    """Orquestra ingestion → transformation → validation para cada linha do arquivo — a
    camada de API/Orquestração (Anexo A) reunindo o motor genérico, sem lógica de contexto
    específico de template embutida aqui."""
    try:
        linhas_brutas = ler_xlsx(conteudo, template)
    except ArquivoInvalido as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    contexto_campos = {"NRORG": nr_org}
    resultados: list[LinhaProcessada] = []
    linhas_validas: list[dict[str, Any]] = []
    for linha_bruta in linhas_brutas:
        numero_linha = linha_bruta.get(LINHA_PLANILHA)
        campos = aplicar_transformacoes(linha_bruta, template, contexto_campos)
        validacoes = validar_linha(campos, template)
        tem_erro = any(v.classificacao == Classificacao.ERRO_IMPEDITIVO for v in validacoes)
        resultados.append((numero_linha, campos, validacoes, tem_erro))
        if not tem_erro:
            linhas_validas.append(campos)
    return resultados, linhas_validas


@router.get("/{codigo}", response_model=TemplateResponse)
async def obter_template(codigo: str, db: AsyncSession = Depends(get_db)) -> TemplateResponse:
    """Dicionário de dados de um template — mapeamento coluna de origem → tabela.campo de
    destino, usado tanto pela tela de configuração de metadados (Fase 6) quanto para
    conferência manual."""
    template = await _carregar_template(codigo, db)
    return TemplateResponse(
        codigo=template.codigo,
        nome=template.nome,
        versao=template.versao,
        sheet_name=template.sheet_name,
        header_row=template.header_row,
        data_start_row=template.data_start_row,
        campos=[
            CampoDicionarioResponse(
                ordem=c.ordem,
                origem=c.origem,
                rotulo=c.rotulo,
                campo=c.campo,
                marcador=c.marcador,
                destino_tabela=c.destino_tabela,
                destino_coluna=c.destino_coluna,
                tipo=c.tipo,
                tamanho_maximo=c.tamanho_maximo,
                obrigatorio=c.obrigatorio,
                regra_conversao=c.regra_conversao,
                eh_pk=c.eh_pk,
                gerador_pk=c.gerador_pk,
            )
            for c in template.campos
        ],
    )


@router.post("/{codigo}/preview", response_model=PreviewResponse)
async def preview_importacao(
    codigo: str,
    arquivo: UploadFile,
    nr_org: Annotated[int, Form()],
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    """Upload de XLSX → leitura via dicionário → validação de obrigatoriedade/tamanho —
    devolve o relatório linha a linha sem gerar script (equivalente à aba de Validação)."""
    template = await _carregar_template(codigo, db)
    conteudo = await arquivo.read()
    resultados, linhas_validas = _processar_arquivo(conteudo, template, nr_org)

    rejeitados = sum(1 for _, _, _, tem_erro in resultados if tem_erro)
    alertas = sum(
        1
        for _, _, validacoes, _ in resultados
        for v in validacoes
        if v.classificacao == Classificacao.ALERTA
    )

    return PreviewResponse(
        template_codigo=template.codigo,
        nr_org=nr_org,
        total_linhas=len(resultados),
        validos=len(linhas_validas),
        rejeitados=rejeitados,
        alertas=alertas,
        linhas=[
            LinhaResultadoResponse(
                linha=numero_linha,
                campos=campos,
                validacoes=[
                    ValidacaoResponse(
                        campo=v.campo,
                        regra=v.regra,
                        classificacao=v.classificacao.value,
                        valor_recebido=v.valor_recebido,
                        valor_esperado=v.valor_esperado,
                        orientacao=v.orientacao,
                    )
                    for v in validacoes
                ],
            )
            for numero_linha, campos, validacoes, _ in resultados
        ],
    )


@router.post("/{codigo}/gerar-script")
async def gerar_script_importacao(
    codigo: str,
    arquivo: UploadFile,
    nr_org: Annotated[int, Form()],
    operacao: Annotated[str, Form()] = "INCLUSAO",
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Upload de XLSX → leitura → validação → geração de INSERT → download do .sql — só as
    linhas sem erro impeditivo entram no script gerado."""
    template = await _carregar_template(codigo, db)
    conteudo = await arquivo.read()
    _, linhas_validas = _processar_arquivo(conteudo, template, nr_org)

    if not linhas_validas:
        raise HTTPException(
            status_code=422,
            detail="Nenhuma linha válida para gerar script — corrija os erros impeditivos e tente novamente.",
        )

    settings = get_settings()
    contexto = ContextoExecucao(nr_org=nr_org, usuario_tecnico=settings.usuario_tecnico_padrao)
    try:
        script_sql = await gerar_script(db, linhas_validas, template, contexto, operacao=operacao)
    except ScriptNaoConfigurado as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    nome_arquivo = f"{template.codigo.lower()}_{operacao.lower()}.sql"
    return Response(
        content=script_sql,
        media_type="application/sql",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
