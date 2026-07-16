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
    gerador_pk_contador: str | None = None
    gerador_pk_seed: int | None = None

    @property
    def vem_do_contexto(self) -> bool:
        """True quando o valor não vem do arquivo, e sim de um parâmetro de execução da
        migração (ex.: NRORG) — ver Seção 13.3."""
        return self.origem.startswith("parametro_execucao.")

    @property
    def eh_derivado(self) -> bool:
        """True quando o valor não vem do arquivo nem do contexto, e sim de outros campos já
        transformados desta mesma linha (ex.: um flag booleano de "tem endereço?" calculado a
        partir de dois outros campos — Seção 7.6/26.4, "preenchimento condicional")."""
        return self.origem.startswith("campo:")

    @property
    def campos_referenciados(self) -> list[str]:
        return self.origem.removeprefix("campo:").split(",")


@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    """Um bloco de template de script (Seção 6.2/10) — um template pode ter vários blocos
    para a mesma operação (ex.: Estrutura gera um bloco fixo de PARCNEGOCIO/ESTRUTURAM/
    ESTRUTURAH e um bloco condicional de ENDERECOPARC, Seção 26.4)."""

    operacao: str
    dialeto_banco: str
    ordem: int
    condicao_campo: str | None
    template_sql: str
    template_rollback: str | None


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """Contrato completo de um template resolvido (Seção 5.2) — dicionário de dados +
    bloco(s) de script por operação, prontos para o motor genérico consumir."""

    codigo: str
    nome: str
    versao: str
    sheet_name: str | None
    header_row: int | None
    data_start_row: int | None
    campos: list[CampoMetadata]
    scripts: dict[str, list[ScriptMetadata]] = field(default_factory=dict)
    eh_catalogo: bool = False
    pre_requisito_externo: str | None = None
