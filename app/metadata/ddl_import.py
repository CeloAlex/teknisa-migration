import re
from dataclasses import dataclass, field


@dataclass
class ColunaImportada:
    nome_coluna: str
    tipo_dado: str | None
    obrigatoria: bool = False


@dataclass
class TabelaImportada:
    nome_tabela: str
    colunas: list[ColunaImportada] = field(default_factory=list)


_RE_CREATE_TABLE = re.compile(r'CREATE TABLE\s+"[^"]+"\."([^"]+)"', re.IGNORECASE)
_RE_MODIFY_NOT_NULL = re.compile(
    r'ALTER TABLE\s+"[^"]+"\."([^"]+)"\s+MODIFY\s*\(([^;]*?)\)\s*;', re.IGNORECASE | re.DOTALL
)
_RE_NOME_COLUNA = re.compile(r'^\s*"([A-Za-z0-9_#$]+)"\s*(.*)$', re.DOTALL)


def _extrair_bloco_parenteses(texto: str, inicio: int) -> str:
    """A partir do primeiro '(' em `texto[inicio:]`, devolve o conteúdo até seu fechamento
    correspondente, respeitando parênteses aninhados (ex. `NUMBER(10,2)`)."""
    abre = texto.index("(", inicio)
    profundidade = 0
    for i in range(abre, len(texto)):
        if texto[i] == "(":
            profundidade += 1
        elif texto[i] == ")":
            profundidade -= 1
            if profundidade == 0:
                return texto[abre + 1 : i]
    raise ValueError("Parêntese não fechado no DDL")


def _dividir_colunas(bloco: str) -> list[str]:
    """Divide o conteúdo de um `CREATE TABLE (...)` pelas vírgulas de topo, sem quebrar
    dentro de parênteses aninhados."""
    partes: list[str] = []
    profundidade = 0
    atual: list[str] = []
    for ch in bloco:
        if ch == "(":
            profundidade += 1
        elif ch == ")":
            profundidade -= 1
        if ch == "," and profundidade == 0:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(ch)
    if atual:
        partes.append("".join(atual))
    return partes


def _parse_coluna(texto: str) -> ColunaImportada | None:
    texto = texto.strip()
    if not texto:
        return None
    m = _RE_NOME_COLUNA.match(texto)
    if not m:
        # Não começa com um identificador entre aspas — não é uma coluna (ex. uma
        # CONSTRAINT inline, formato que este parser não precisa cobrir).
        return None
    nome_coluna, resto = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
    obrigatoria = bool(re.search(r"\bNOT NULL\b", resto, re.IGNORECASE))
    tipo_dado = re.split(r"\bDEFAULT\b|\bNOT NULL\b|\bENABLE\b", resto, flags=re.IGNORECASE)[0].strip()
    return ColunaImportada(nome_coluna=nome_coluna, tipo_dado=tipo_dado or None, obrigatoria=obrigatoria)


def parse_ddl_oracle(conteudo: str) -> list[TabelaImportada]:
    """Extrai tabelas e colunas (nome, tipo, obrigatoriedade) de um script de exportação de
    DDL Oracle (formato `docs/especificação/base_vazia.txt` — saída de
    `dbms_metadata.get_ddl` ou equivalente) para popular o catálogo de destino usado como
    FK-guia por `TemplateCampo`.

    `CREATE INDEX` e `ALTER TABLE ... ADD CONSTRAINT` (PK/FK/CHECK) são deliberadamente
    ignorados — não fazem parte do dicionário de campos, e este importador nunca aplica o
    DDL de fato contra um Oracle (o motor de migração nunca executa DDL), então a ordem de
    dependência entre constraints não é um problema a resolver aqui."""
    tabelas: dict[str, TabelaImportada] = {}

    for match in _RE_CREATE_TABLE.finditer(conteudo):
        nome_tabela = match.group(1)
        bloco = _extrair_bloco_parenteses(conteudo, match.end())
        tabela = tabelas.setdefault(nome_tabela, TabelaImportada(nome_tabela=nome_tabela))
        for parte in _dividir_colunas(bloco):
            coluna = _parse_coluna(parte)
            if coluna is not None:
                tabela.colunas.append(coluna)

    for match in _RE_MODIFY_NOT_NULL.finditer(conteudo):
        nome_tabela, corpo = match.group(1), match.group(2)
        tabela = tabelas.get(nome_tabela)
        if tabela is None:
            continue
        for nome_coluna in re.findall(r'"([A-Za-z0-9_#$]+)"\s+NOT NULL', corpo, re.IGNORECASE):
            for coluna in tabela.colunas:
                if coluna.nome_coluna == nome_coluna:
                    coluna.obrigatoria = True

    return list(tabelas.values())
