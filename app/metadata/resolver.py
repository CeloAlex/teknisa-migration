from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.metadata.schemas import CampoMetadata, ScriptMetadata, TemplateMetadata
from app.models.template import Template


class TemplateNaoEncontrado(Exception):
    pass


async def resolver_template(session: AsyncSession, codigo: str) -> TemplateMetadata:
    """Metadata Resolver (Anexo A): carrega o template, seu dicionário de dados e seus
    blocos de script do banco de metadados, decorando o contrato que o restante do motor
    (ingestion/transformation/validation/scripts) consome — nenhuma lógica de contexto
    específico vive em código, apenas nesta configuração."""
    stmt = (
        select(Template)
        .where(Template.codigo == codigo, Template.ativo.is_(True))
        .options(selectinload(Template.campos), selectinload(Template.scripts))
    )
    resultado = await session.execute(stmt)
    template = resultado.scalar_one_or_none()
    if template is None:
        raise TemplateNaoEncontrado(f'Template "{codigo}" não encontrado ou inativo.')

    campos = [
        CampoMetadata(
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
            valor_padrao=c.valor_padrao,
            regra_conversao=c.regra_conversao,
            eh_pk=c.eh_pk,
            gerador_pk=c.gerador_pk,
            gerador_pk_contador=c.gerador_pk_contador,
            gerador_pk_seed=c.gerador_pk_seed,
        )
        for c in template.campos
    ]

    scripts: dict[str, list[ScriptMetadata]] = defaultdict(list)
    for s in template.scripts:
        scripts[s.operacao].append(
            ScriptMetadata(
                operacao=s.operacao,
                dialeto_banco=s.dialeto_banco,
                ordem=s.ordem,
                condicao_campo=s.condicao_campo,
                template_sql=s.template_sql,
                template_rollback=s.template_rollback,
            )
        )

    return TemplateMetadata(
        codigo=template.codigo,
        nome=template.nome,
        versao=template.versao,
        sheet_name=template.sheet_name,
        header_row=template.header_row,
        data_start_row=template.data_start_row,
        campos=campos,
        scripts=dict(scripts),
    )
