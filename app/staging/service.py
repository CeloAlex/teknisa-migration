import asyncio
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.ingestion import ler_arquivo
from app.ingestion.xlsx import LINHA_PLANILHA, ArquivoInvalido
from app.metadata.resolver import resolver_template
from app.metadata.schemas import TemplateMetadata
from app.migracoes.estado import ResumoTemplate, recalcular_status
from app.models.migracao import Migracao, MigracaoStatus, MigracaoTemplateStatus, TemplateStatus
from app.models.staging import ScriptGerado, StagingBruto, StagingNormalizado, ValidacaoResultado
from app.models.template import Template
from app.transformation.engine import aplicar_transformacoes
from app.validation.classificacao import Classificacao
from app.validation.engine import validar_linha


def _json_seguro(valor: Any) -> Any:
    """Converte valores que o openpyxl pode devolver (datetime/date) para algo
    serializável em JSONB — o resto (str/int/float/bool/None) já passa direto."""
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def _linha_bruta_para_json(linha: dict[str, Any]) -> dict[str, Any]:
    return {chave: _json_seguro(valor) for chave, valor in linha.items() if chave != LINHA_PLANILHA}


async def resetar_para_reprocessamento(session: AsyncSession, mts: MigracaoTemplateStatus) -> None:
    """Limpa todo staging/script anterior de um template antes de uma nova importação —
    tanto a primeira quanto um reenvio após correção (Seção 8 — "correção ou
    reprocessamento"). A exclusão de `staging_bruto` cascateia (ON DELETE CASCADE) para
    `staging_normalizado` e `validacao_resultado`."""
    await session.execute(delete(StagingBruto).where(StagingBruto.migracao_template_status_id == mts.id))
    await session.execute(delete(ScriptGerado).where(ScriptGerado.migracao_template_status_id == mts.id))
    mts.status = TemplateStatus.PENDENTE.value
    mts.total_linhas = 0
    mts.linhas_processadas = 0
    mts.pausado = False
    mts.teve_alerta = False
    mts.dados_aprovados = False
    mts.aprovado_dados_por = None
    mts.script_gerado = False
    mts.script_aprovado = False
    mts.aprovado_script_por = None
    mts.aplicado = False
    mts.aplicado_com_erro = False
    mts.dt_importacao = None


async def _processar_lote(
    session: AsyncSession,
    mts: MigracaoTemplateStatus,
    template_meta: TemplateMetadata,
    contexto: dict[str, Any],
    tamanho_lote: int,
) -> int:
    """Processa até `tamanho_lote` linhas ainda não transformadas (Transformation Engine) —
    equivalente a `processarProximoLote` do protótipo, mas persistido em banco em vez de em
    memória, para sobreviver a uma pausa entre requisições."""
    stmt = (
        select(StagingBruto)
        .where(StagingBruto.migracao_template_status_id == mts.id, StagingBruto.processado.is_(False))
        .order_by(StagingBruto.linha)
        .limit(tamanho_lote)
    )
    pendentes = (await session.execute(stmt)).scalars().all()
    for staging_bruto in pendentes:
        campos = aplicar_transformacoes(staging_bruto.dados_json, template_meta, contexto)
        session.add(StagingNormalizado(staging_bruto_id=staging_bruto.id, dados_json=campos))
        staging_bruto.processado = True
        mts.linhas_processadas += 1
    return len(pendentes)


async def _executar_validacao(session: AsyncSession, mts: MigracaoTemplateStatus, template_meta: TemplateMetadata) -> None:
    """Validation Engine (Fase 2+) aplicado a todas as linhas já normalizadas de um template,
    persistindo cada resultado — equivalente a `executarValidacao` do protótipo."""
    stmt = select(StagingNormalizado).join(StagingBruto).where(
        StagingBruto.migracao_template_status_id == mts.id
    )
    normalizados = (await session.execute(stmt)).scalars().all()

    tem_erro = False
    tem_alerta = False
    for staging_normalizado in normalizados:
        for resultado in validar_linha(staging_normalizado.dados_json, template_meta):
            session.add(
                ValidacaoResultado(
                    staging_normalizado_id=staging_normalizado.id,
                    campo=resultado.campo,
                    regra=resultado.regra,
                    classificacao=resultado.classificacao.value,
                    valor_recebido=resultado.valor_recebido,
                    valor_esperado=resultado.valor_esperado,
                    mensagem=resultado.orientacao,
                )
            )
            if resultado.classificacao == Classificacao.ERRO_IMPEDITIVO:
                tem_erro = True
            elif resultado.classificacao == Classificacao.ALERTA:
                tem_alerta = True

    mts.status = TemplateStatus.COM_INCONSISTENCIAS.value if tem_erro else TemplateStatus.VALIDADO.value
    mts.teve_alerta = tem_alerta
    mts.dt_importacao = datetime.now(timezone.utc)


async def _atualizar_status_migracao(session: AsyncSession, migracao_id: int) -> None:
    """Recalcula e persiste o status da migração (Seção 9) depois que um template termina
    de processar em background — sem isso, `Migracao.status` só mudaria na próxima vez que
    alguma rota da API tocasse a migração, o que deixaria o status visivelmente "atrasado"
    para quem estivesse só consultando `GET /migracoes/{id}`."""
    migracao = await session.get(Migracao, migracao_id)
    stmt = select(MigracaoTemplateStatus).where(MigracaoTemplateStatus.migracao_id == migracao_id)
    templates_status = (await session.execute(stmt)).scalars().all()

    resumo = [
        ResumoTemplate(
            obrigatorio=t.obrigatorio,
            status=t.status,
            dados_aprovados=t.dados_aprovados,
            script_gerado=t.script_gerado,
            script_aprovado=t.script_aprovado,
            aplicado=t.aplicado,
            aplicado_com_erro=t.aplicado_com_erro,
            teve_alerta=t.teve_alerta,
        )
        for t in templates_status
    ]
    novo_status = recalcular_status(migracao.status, resumo)
    migracao.status = novo_status.value
    concluida = {MigracaoStatus.CONCLUIDA, MigracaoStatus.CONCLUIDA_COM_ALERTAS}
    if novo_status in concluida and migracao.dt_conclusao is None:
        migracao.dt_conclusao = datetime.now(timezone.utc)


async def _processar_pendentes_ate_o_fim(
    session: AsyncSession,
    mts: MigracaoTemplateStatus,
    template_meta: TemplateMetadata,
    nr_org: int,
    tamanho_lote: int,
    atraso_por_lote: float = 0.001,
) -> None:
    """Loop retomável de transformação em chunks + validação final — compartilhado entre a
    primeira importação e um "continuar" após pausa, já que ambos só precisam operar sobre
    `staging_bruto` já persistido, nunca sobre o arquivo original de novo."""
    contexto = {"NRORG": nr_org}
    while True:
        await session.refresh(mts)
        if mts.pausado:
            return
        processados = await _processar_lote(session, mts, template_meta, contexto, tamanho_lote)
        await session.commit()
        if processados == 0:
            break
        # Cede o loop de eventos entre lotes — não é só cortesia: em arquivos grandes
        # (Escala de Trabalho real tem 3.587 linhas), sem essa pausa a task dominaria o
        # loop de eventos por muito tempo seguido, atrasando outras requisições
        # concorrentes (inclusive um pedido de "pausar"). O valor é configurável (usado nos
        # testes de pause/resume para abrir uma janela confiável) mas pequeno o bastante por
        # padrão para não pesar no throughput total.
        await asyncio.sleep(atraso_por_lote)

    mts.status = TemplateStatus.EM_VALIDACAO.value
    await session.commit()

    await _executar_validacao(session, mts, template_meta)
    await _atualizar_status_migracao(session, mts.migracao_id)
    await session.commit()


async def processar_arquivo_em_background(
    mts_id: int, template_id: int, conteudo: bytes, nr_org: int, tamanho_lote: int, atraso_por_lote: float = 0.001
) -> None:
    """Ingestão (uma vez) + transformação em chunks + validação de um arquivo recém-
    importado. Roda como uma task assíncrona independente da requisição HTTP que a disparou
    (Seção 11 do documento / stack: "BackgroundTasks do FastAPI + progresso persistido em
    banco" — aqui via `asyncio.create_task`, para que pausar/continuar funcionem de forma
    determinística mesmo sob o transporte ASGI usado nos testes)."""
    async with AsyncSessionLocal() as session:
        mts = await session.get(MigracaoTemplateStatus, mts_id)
        template_row = await session.get(Template, template_id)
        template_meta = await resolver_template(session, template_row.codigo)

        try:
            linhas_brutas = ler_arquivo(conteudo, template_meta)
        except ArquivoInvalido:
            mts.status = TemplateStatus.COM_INCONSISTENCIAS.value
            await _atualizar_status_migracao(session, mts.migracao_id)
            await session.commit()
            return

        mts.total_linhas = len(linhas_brutas)
        mts.status = TemplateStatus.EM_IMPORTACAO.value
        session.add_all(
            [
                StagingBruto(
                    migracao_template_status_id=mts.id,
                    linha=linha.get(LINHA_PLANILHA) or 0,
                    dados_json=_linha_bruta_para_json(linha),
                )
                for linha in linhas_brutas
            ]
        )
        await session.commit()

        await _processar_pendentes_ate_o_fim(session, mts, template_meta, nr_org, tamanho_lote, atraso_por_lote)


async def retomar_processamento_em_background(
    mts_id: int, template_id: int, nr_org: int, tamanho_lote: int, atraso_por_lote: float = 0.001
) -> None:
    """Retoma o processamento de um template pausado — usado por "continuar" (Fase 5).
    Não precisa do arquivo original: `staging_bruto` já está persistido desde a primeira
    importação, só resta transformar+validar as linhas com `processado = false`."""
    async with AsyncSessionLocal() as session:
        mts = await session.get(MigracaoTemplateStatus, mts_id)
        template_row = await session.get(Template, template_id)
        template_meta = await resolver_template(session, template_row.codigo)
        await _processar_pendentes_ate_o_fim(session, mts, template_meta, nr_org, tamanho_lote, atraso_por_lote)


async def buscar_linhas_validas(session: AsyncSession, mts_id: int) -> list[dict[str, Any]]:
    """Linhas normalizadas sem nenhum erro impeditivo — as únicas que entram no Script
    Generator (Seção 7.7: erro impeditivo bloqueia aprovação/geração de script)."""
    subquery_invalidas = select(ValidacaoResultado.staging_normalizado_id).where(
        ValidacaoResultado.classificacao == Classificacao.ERRO_IMPEDITIVO.value
    )
    stmt = (
        select(StagingNormalizado.dados_json)
        .join(StagingBruto, StagingBruto.id == StagingNormalizado.staging_bruto_id)
        .where(StagingBruto.migracao_template_status_id == mts_id)
        .where(StagingNormalizado.id.not_in(subquery_invalidas))
        .order_by(StagingBruto.linha)
    )
    resultado = await session.execute(stmt)
    return [linha for (linha,) in resultado.all()]
