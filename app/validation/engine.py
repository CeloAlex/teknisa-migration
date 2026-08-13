from collections import defaultdict
from typing import Any

from app.metadata.schemas import TemplateMetadata
from app.validation.classificacao import Classificacao
from app.validation.schemas import ResultadoValidacao


def validar_linha(
    campos: dict[str, Any],
    template: TemplateMetadata,
    valores_fk: dict[str, set[str]] | None = None,
) -> list[ResultadoValidacao]:
    """Validation Engine (Anexo A / Anexo G) — cobre validação estrutural de obrigatoriedade
    (erro impeditivo), de tamanho máximo (alerta) e, quando `valores_fk` é passado,
    validação relacional local (Seção 7.4): um campo com `fk_template_codigo`/`fk_campo`
    configurado precisa ter seu valor entre os já importados no campo referenciado do outro
    template, dentro da mesma migração — antecipa uma FK resolvida por subquery
    (`SELECT ... WHERE CDMATRICULA = '@X@'`) que retornaria NULL só na hora de aplicar o
    script. `valores_fk` é opcional e mantém a assinatura compatível com quem só quer
    validação estrutural (ex.: os testes do endpoint standalone de geração de script, Fase
    2-4, que nunca tiveram acesso a outros templates da mesma migração)."""
    valores_fk = valores_fk or {}
    resultados: list[ResultadoValidacao] = []
    for campo_meta in template.campos:
        if campo_meta.gerador_pk or campo_meta.eh_derivado:
            continue

        # Campos vindos de parâmetro de execução (ex.: NRORG) não têm coluna/caminho de
        # origem no arquivo — não faz sentido apontar uma origem para eles.
        origem = None if campo_meta.vem_do_contexto else campo_meta.origem

        valor = campos.get(campo_meta.campo)
        vazio = valor is None or str(valor).strip() == ""

        if campo_meta.obrigatorio and vazio:
            resultados.append(
                ResultadoValidacao(
                    campo=campo_meta.campo,
                    regra="obrigatoriedade",
                    classificacao=Classificacao.ERRO_IMPEDITIVO,
                    valor_recebido="(vazio)",
                    valor_esperado=campo_meta.rotulo,
                    orientacao=f'Preencha o campo "{campo_meta.rotulo}".',
                    origem=origem,
                )
            )
            continue

        if campo_meta.fk_template_codigo and not vazio:
            # `campo_meta.campo` (não `fk_campo`) é a chave usada em `valores_fk` — o
            # conjunto já vem indexado pelo campo QUE REFERENCIA, não pelo campo referenciado
            # (múltiplos campos podem referenciar o mesmo template/campo com listas diferentes).
            candidatos = valores_fk.get(campo_meta.campo)
            if candidatos is not None and str(valor).strip() not in candidatos:
                resultados.append(
                    ResultadoValidacao(
                        campo=campo_meta.campo,
                        regra="fk_nao_encontrada",
                        classificacao=Classificacao.ERRO_IMPEDITIVO,
                        valor_recebido=str(valor),
                        valor_esperado=f'valor já importado em "{campo_meta.fk_template_codigo}"',
                        orientacao=(
                            f'O valor "{valor}" de "{campo_meta.rotulo}" não foi encontrado entre os '
                            f'códigos já importados no template "{campo_meta.fk_template_codigo}" — '
                            "confira se não há divergência de digitação/formatação."
                        ),
                        origem=origem,
                    )
                )
                continue

        if campo_meta.tamanho_maximo and not vazio and len(str(valor)) > campo_meta.tamanho_maximo:
            resultados.append(
                ResultadoValidacao(
                    campo=campo_meta.campo,
                    regra="tamanho_maximo",
                    classificacao=Classificacao.ALERTA,
                    valor_recebido=str(valor),
                    valor_esperado=f"até {campo_meta.tamanho_maximo} caracteres",
                    orientacao=f'Confira o valor de "{campo_meta.rotulo}".',
                    origem=origem,
                )
            )

        if campo_meta.dominio_valores and not vazio:
            validos = {v.strip() for v in campo_meta.dominio_valores.split(",") if v.strip()}
            if str(valor).strip() not in validos:
                resultados.append(
                    ResultadoValidacao(
                        campo=campo_meta.campo,
                        regra="fora_do_dominio",
                        classificacao=Classificacao.ALERTA,
                        valor_recebido=str(valor),
                        valor_esperado=f'um dos valores do domínio de "{campo_meta.rotulo}"',
                        orientacao=(
                            f'O valor "{valor}" de "{campo_meta.rotulo}" não está no domínio '
                            "de valores conhecido — confira se não é erro de digitação ou se "
                            "é um valor novo que precisa ser cadastrado no domínio."
                        ),
                        origem=origem,
                    )
                )

        if campo_meta.alerta_se_vazio_quando_campo and vazio:
            gatilho = campos.get(campo_meta.alerta_se_vazio_quando_campo)
            valores_gatilho = {
                v.strip() for v in (campo_meta.alerta_se_vazio_quando_valores or "").split(",") if v.strip()
            }
            if gatilho is not None and str(gatilho).strip() in valores_gatilho:
                resultados.append(
                    ResultadoValidacao(
                        campo=campo_meta.campo,
                        regra="ausencia_condicional",
                        classificacao=Classificacao.ALERTA,
                        valor_recebido="(vazio)",
                        valor_esperado=campo_meta.rotulo,
                        orientacao=(
                            f'O campo "{campo_meta.rotulo}" está vazio, o que gera pendência '
                            "para as áreas responsáveis resolverem — não impede a importação."
                        ),
                        origem=origem,
                    )
                )
    return resultados


def verificar_duplicatas_lote(
    linhas: list[tuple[int, dict[str, Any]]], template: TemplateMetadata
) -> dict[int, list[ResultadoValidacao]]:
    """Checagem de duplicidade dentro do mesmo lote importado (Seção 7.3) — diferente de
    `validar_linha`, que só enxerga uma linha por vez, esta função recebe todas as linhas já
    normalizadas de um template/migração de uma vez, já que duplicidade é uma propriedade do
    conjunto, não de uma linha isolada. `linhas` é uma lista de pares
    (staging_normalizado_id, dados_json); o retorno é indexado pelo mesmo id para quem chamar
    conseguir persistir junto com os resultados de `validar_linha`."""
    resultados_por_linha: dict[int, list[ResultadoValidacao]] = defaultdict(list)
    for campo_meta in template.campos:
        if not campo_meta.duplicata_no_lote:
            continue
        classificacao = (
            Classificacao.ERRO_IMPEDITIVO if campo_meta.duplicata_no_lote == "erro_impeditivo" else Classificacao.ALERTA
        )
        grupos: dict[tuple[Any, str], list[int]] = defaultdict(list)
        for staging_id, dados in linhas:
            valor = dados.get(campo_meta.campo)
            if valor is None or str(valor).strip() == "":
                continue
            chave_grupo = None
            if campo_meta.duplicata_agrupado_por:
                chave_grupo = dados.get(campo_meta.duplicata_agrupado_por)
            grupos[(chave_grupo, str(valor).strip())].append(staging_id)

        for (chave_grupo, valor), ids in grupos.items():
            if len(ids) < 2:
                continue
            if campo_meta.duplicata_agrupado_por:
                orientacao = (
                    f'O valor "{valor}" de "{campo_meta.rotulo}" se repete em mais de uma '
                    f'linha desta importação com o mesmo "{campo_meta.duplicata_agrupado_por}" '
                    f'("{chave_grupo}").'
                )
            else:
                orientacao = f'O valor "{valor}" de "{campo_meta.rotulo}" se repete em mais de uma linha desta importação.'
            for staging_id in ids:
                resultados_por_linha[staging_id].append(
                    ResultadoValidacao(
                        campo=campo_meta.campo,
                        regra="duplicata_no_lote",
                        classificacao=classificacao,
                        valor_recebido=valor,
                        valor_esperado="valor único nesta importação",
                        orientacao=orientacao,
                        origem=None,
                    )
                )
    return resultados_por_linha
