from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CampoMetadata:
    """Contrato de um campo do dicionário de dados (Seção 6 / Anexo E), já resolvido do banco
    de metadados — usado por ingestion/transformation/validation/scripts sem nenhum
    conhecimento do template concreto a que pertence."""

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
    valor_padrao: str | None
    regra_conversao: str | None
    eh_pk: bool
    gerador_pk: bool

    @property
    def vem_do_contexto(self) -> bool:
        """True quando o valor não vem do arquivo, e sim de um parâmetro de execução da
        migração (ex.: NRORG) — ver Seção 13.3."""
        return self.origem.startswith("parametro_execucao.")

    @property
    def chave_contexto(self) -> str:
        return self.origem.removeprefix("parametro_execucao.")


@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    operacao: str
    dialeto_banco: str
    template_sql: str
    template_rollback: str | None


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """Contrato completo de um template resolvido (Seção 5.2) — dicionário de dados +
    template(s) de script, prontos para o motor genérico consumir."""

    codigo: str
    nome: str
    versao: str
    sheet_name: str | None
    header_row: int | None
    data_start_row: int | None
    campos: list[CampoMetadata]
    scripts: dict[str, ScriptMetadata] = field(default_factory=dict)
