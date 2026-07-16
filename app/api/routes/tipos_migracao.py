from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    TipoMigracaoListItemResponse,
    TipoMigracaoResponse,
    TipoMigracaoTemplateResponse,
)
from app.db.session import get_db
from app.models.tipo_migracao import (
    TipoMigracao,
    TipoMigracaoTemplate,
    TipoMigracaoTemplateDependencia,
)

router = APIRouter(prefix="/tipos-migracao", tags=["tipos-migracao"])


@router.get("", response_model=list[TipoMigracaoListItemResponse])
async def listar_tipos_migracao(db: AsyncSession = Depends(get_db)) -> list[TipoMigracaoListItemResponse]:
    """Cadastro de tipos de migração (Seção 5.1) — cada um define quais templates compõem o
    "pacote", em que ordem, e se a sequência é travada por dependência (Seção 26.3)."""
    resultado = await db.execute(select(TipoMigracao).options(selectinload(TipoMigracao.templates)))
    tipos = resultado.scalars().all()
    return [
        TipoMigracaoListItemResponse(
            codigo=t.codigo,
            nome=t.nome,
            banco_destino=t.banco_destino,
            sequencia_obrigatoria=t.sequencia_obrigatoria,
            permite_concorrencia=t.permite_concorrencia,
            total_templates=len(t.templates),
        )
        for t in tipos
    ]


@router.get("/{codigo}", response_model=TipoMigracaoResponse)
async def obter_tipo_migracao(codigo: str, db: AsyncSession = Depends(get_db)) -> TipoMigracaoResponse:
    """Detalhe de um tipo de migração: templates na ordem configurada e, quando a sequência é
    travada, de quais outros templates cada um depende (Seção 26.3 — grafo de dependências)."""
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
    resultado = await db.execute(stmt)
    tipo = resultado.scalar_one_or_none()
    if tipo is None:
        raise HTTPException(status_code=404, detail=f'Tipo de migração "{codigo}" não encontrado.')

    return TipoMigracaoResponse(
        codigo=tipo.codigo,
        nome=tipo.nome,
        banco_destino=tipo.banco_destino,
        modo_aplicacao=tipo.modo_aplicacao,
        sequencia_obrigatoria=tipo.sequencia_obrigatoria,
        permite_concorrencia=tipo.permite_concorrencia,
        templates=[
            TipoMigracaoTemplateResponse(
                ordem=tmt.ordem,
                template_codigo=tmt.template.codigo,
                template_nome=tmt.template.nome,
                obrigatorio=tmt.obrigatorio,
                depende_de=[d.depende_de_template.codigo for d in tmt.dependencias],
            )
            for tmt in tipo.templates
        ],
    )
