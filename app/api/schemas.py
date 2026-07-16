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
