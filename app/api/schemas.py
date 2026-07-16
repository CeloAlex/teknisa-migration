from datetime import datetime

from pydantic import BaseModel


class CampoDicionarioResponse(BaseModel):
    ordem: int
    origem: str
    rotulo: str
    campo: str
    marcador: str | None
    destino_tabela: str
    destino_coluna: str
    tipo: str
    tamanho_maximo: int | None
    obrigatorio: bool
    regra_conversao: str | None
    eh_pk: bool
    gerador_pk: bool


class TemplateResponse(BaseModel):
    codigo: str
    nome: str
    versao: str
    sheet_name: str | None
    header_row: int | None
    data_start_row: int | None
    eh_catalogo: bool
    pre_requisito_externo: str | None
    campos: list[CampoDicionarioResponse]


class ValidacaoResponse(BaseModel):
    campo: str
    regra: str
    classificacao: str
    valor_recebido: str
    valor_esperado: str
    orientacao: str


class LinhaResultadoResponse(BaseModel):
    linha: int | None
    campos: dict[str, str | bool | int | float | None]
    validacoes: list[ValidacaoResponse]


class PreviewResponse(BaseModel):
    template_codigo: str
    nr_org: int
    total_linhas: int
    validos: int
    rejeitados: int
    alertas: int
    linhas: list[LinhaResultadoResponse]


class TipoMigracaoListItemResponse(BaseModel):
    codigo: str
    nome: str
    banco_destino: str
    sequencia_obrigatoria: bool
    permite_concorrencia: bool
    total_templates: int


class TipoMigracaoTemplateResponse(BaseModel):
    ordem: int
    template_codigo: str
    template_nome: str
    obrigatorio: bool
    depende_de: list[str]


class TipoMigracaoResponse(BaseModel):
    codigo: str
    nome: str
    banco_destino: str
    modo_aplicacao: str
    sequencia_obrigatoria: bool
    permite_concorrencia: bool
    templates: list[TipoMigracaoTemplateResponse]


# --- Fase 5: máquina de estados da migração ---------------------------------------------


class MigracaoCriarRequest(BaseModel):
    nr_org: int
    tipo_migracao_codigo: str
    operador: str


class MigracaoTemplateStatusResponse(BaseModel):
    template_codigo: str
    template_nome: str
    obrigatorio: bool
    status: str
    total_linhas: int
    linhas_processadas: int
    pausado: bool
    teve_alerta: bool
    dados_aprovados: bool
    script_gerado: bool
    script_aprovado: bool
    aplicado: bool
    aplicado_com_erro: bool


class MigracaoEventoResponse(BaseModel):
    evento: str
    usuario: str
    dt_evento: datetime


class MigracaoResponse(BaseModel):
    id: int
    nr_org: int
    organizacao_nome: str
    tipo_migracao_codigo: str
    operador: str
    status: str
    dt_criacao: datetime
    dt_conclusao: datetime | None
    templates: list[MigracaoTemplateStatusResponse]


class MigracaoDetalheResponse(MigracaoResponse):
    eventos: list[MigracaoEventoResponse]


class MigracaoListItemResponse(BaseModel):
    id: int
    nr_org: int
    organizacao_nome: str
    tipo_migracao_codigo: str
    operador: str
    status: str
    dt_criacao: datetime


class ValidacaoPersistidaResponse(BaseModel):
    linha: int
    campo: str
    regra: str
    classificacao: str
    valor_recebido: str
    valor_esperado: str
    orientacao: str


class AcaoComUsuarioRequest(BaseModel):
    usuario: str


class AplicarRequest(BaseModel):
    usuario: str
    sucesso: bool = True
    detalhe_erro: str | None = None
