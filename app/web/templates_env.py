import re
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mapas cor/rótulo de badge — mesmo papel do STATUS_META/SEV_META do protótipo de
# referência, só que consultados do lado do servidor (Jinja), não em JS no navegador.
STATUS_MIGRACAO_META = {
    "criada": ("gray", "Criada"),
    "aguardando_arquivos": ("gray", "Aguardando arquivos"),
    "em_validacao": ("blue", "Em validação"),
    "aguardando_correcao": ("orange", "Aguardando correção"),
    "aguardando_aprovacao": ("purple", "Aguardando aprovação"),
    "pronta_para_geracao_scripts": ("blue", "Pronta para gerar scripts"),
    "scripts_gerados": ("teal", "Scripts gerados"),
    "aguardando_aplicacao": ("teal", "Aguardando aplicação"),
    "em_execucao": ("blue", "Em execução"),
    "concluida": ("green", "Concluída"),
    "concluida_com_alertas": ("orange", "Concluída com alertas"),
    "com_erro": ("red", "Com erro"),
    "revertida": ("gray", "Revertida"),
    "cancelada": ("gray", "Cancelada"),
}

STATUS_TEMPLATE_META = {
    "pendente": ("gray", "Pendente"),
    "em_importacao": ("blue", "Em importação"),
    "em_validacao": ("blue", "Em validação"),
    "com_inconsistencias": ("red", "Com inconsistências"),
    "validado": ("green", "Validado"),
}

SEVERIDADE_META = {
    "erro_impeditivo": ("red", "Erro impeditivo"),
    "alerta": ("orange", "Alerta"),
    "recomendacao": ("blue", "Recomendação"),
    "ajuste_automatico": ("teal", "Ajuste automático"),
    "informacao": ("gray", "Informação"),
}

PAPEL_META = {
    "operador": "Operador",
    "aprovador_funcional": "Aprovador Funcional",
    "aprovador_tecnico": "Aprovador Técnico",
    "executor_dba": "Executor/DBA",
    "administrador": "Administrador",
    "auditor": "Auditor (somente leitura)",
}


def status_migracao_meta(status: str) -> tuple[str, str]:
    return STATUS_MIGRACAO_META.get(status, ("gray", status))


def status_template_meta(status: str) -> tuple[str, str]:
    return STATUS_TEMPLATE_META.get(status, ("gray", status))


def severidade_meta(severidade: str) -> tuple[str, str]:
    return SEVERIDADE_META.get(severidade, ("gray", severidade))


def papel_rotulo(papel: str) -> str:
    return PAPEL_META.get(papel, papel)


def formatar_data(valor) -> str:
    if valor is None:
        return "—"
    return valor.strftime("%d/%m/%Y %H:%M")


_RE_FIM_INSTRUCAO = re.compile(r"(\);)\s+(?=[A-Z])")


def sql_legivel(template_sql: str) -> str:
    """Só para exibição no preview de admin (Seção 6.2) — um `TemplateScript.template_sql`
    pode conter mais de uma instrução (ex.: INSERT em GPE_ESCALATRABM seguido de INSERT em
    GPE_ESCALATRABH, separados só por `); `). Sem quebra de linha, blocos com 2-3 instruções
    parecem ter só a primeira dentro da caixa de preview de altura fixa — quebra cada `);`
    de fechamento em uma linha nova, sem alterar o texto armazenado usado de fato na geração
    do script real."""
    return _RE_FIM_INSTRUCAO.sub(r"\1\n", template_sql)


templates.env.globals["status_migracao_meta"] = status_migracao_meta
templates.env.globals["status_template_meta"] = status_template_meta
templates.env.globals["severidade_meta"] = severidade_meta
templates.env.globals["papel_rotulo"] = papel_rotulo
templates.env.globals["papel_opcoes"] = list(PAPEL_META.items())
templates.env.filters["data_br"] = formatar_data
templates.env.filters["sql_legivel"] = sql_legivel
