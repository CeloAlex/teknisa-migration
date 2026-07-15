% Plataforma Genérica de Migração de Dados para ERP/HCM
% Especificação de Solução — Teknisa
% Julho de 2026

# 1. Visão executiva da solução

A Teknisa realiza, hoje, migrações de dados de sistemas legados para o ERP/HCM através de planilhas Excel altamente sofisticadas — como as seis planilhas anexadas a este documento (Agências Bancárias, Estrutura Organizacional, Ocupação, Escala de Trabalho, Vínculo e Dependentes). Essas planilhas escondem, dentro de fórmulas de `SUBSTITUTE`, `TRIM`, `TEXT` e concatenação de texto, uma lógica de migração real e madura: normalização de dados, verificação de existência prévia contra o banco de destino, geração de chaves primárias livres, montagem de comandos `INSERT`/`MERGE` a partir de templates com placeholders (`@CAMPO@`) e controle de commit.

Essa lógica funciona, mas está presa à ferramenta errada. Cada nova migração exige um novo arquivo, novas fórmulas, novo desenvolvimento manual de templates de SQL, e o conhecimento de como validar e gerar os scripts está distribuído em fórmulas de planilha que só um punhado de pessoas sabe manter. Não há orquestração de etapas, não há controle de status, não há trilha de auditoria centralizada, não há reaproveitamento entre contextos (Estrutura, Ocupação, Escala, Vínculo e Dependentes replicam o mesmo padrão de "Busca de PK's livres" e "Atualiza Novo Código" de forma independente e ligeiramente distinta em cada planilha).

A proposta deste documento é extrair esse padrão implícito — que já é validado pela prática — e reconstruí-lo como uma **plataforma de migração genérica, orientada por metadados**, capaz de:

1. Substituir a planilha por uma aplicação com importador configurável, mantendo (e generalizando) a mesma lógica de normalização, verificação de existência, geração de PK e montagem de scripts que hoje vive nas fórmulas.
2. Tratar cada um dos seis contextos anexados (e qualquer contexto futuro) como uma configuração de metadados, não como código específico.
3. Adicionar uma camada de governança que hoje não existe: controle de status por migração, bloqueio de concorrência por organização, validações estruturadas e classificadas, staging auditável, aprovação formal antes da geração/aplicação de scripts, e rastreabilidade ponta a ponta.
4. Preparar o terreno para, no médio prazo, substituir a geração de SQL por chamadas às APIs da Teknisa, sem reescrever o motor de validação nem o modelo de metadados.

O resultado é uma ferramenta única, parametrizável, que atende hoje aos seis contextos anexados e amanhã a qualquer novo cadastro (benefícios, sindicatos, cargos, centros de custo etc.), sem novo desenvolvimento de software — apenas nova configuração de metadados.

# 2. Principais funcionalidades do sistema migrador

| Funcionalidade | Descrição |
|---|---|
| Cadastro de tipos de migração | Define quais contextos, templates, sequência e banco de destino compõem uma migração (ex.: "Migração HCM Completa" = Estrutura → Ocupação → Escala → Agências → Vínculo → Dependentes). |
| Cadastro de templates por metadados | Mapeia colunas/tags/atributos de origem para tabelas e colunas de destino, com tipo, tamanho, obrigatoriedade, valor padrão, regra de conversão, regra de validação, PK/FK. |
| Importação multi-formato | XLSX, XML e API na primeira versão; CSV, JSON e largura fixa por evolução, todos processados pelo mesmo motor via adaptadores de leitura. |
| Motor de validação estruturado | Executa validações estruturais, de dados, de domínio, relacionais, temporais e de negócio, classificando cada resultado (erro impeditivo, alerta, recomendação, ajuste automático, informação). |
| Staging area | Armazena dado bruto, dado normalizado, resultado de validação e dado aprovado em camadas distintas e rastreáveis. |
| Resolução de dependências e PKs | Reproduz e generaliza a lógica de "Busca de PK's livres" e "Atualiza Novo Código" das planilhas, como serviço central de geração de chaves (equivalente à tabela `NOVOCODIGO`). |
| Console de correção | Tela de tratamento de erros por arquivo/linha/coluna, com exportação/reimportação de planilha de pendências e correção inline. |
| Aprovação em etapas | Fluxo de aprovação formal antes da geração de scripts e antes da aplicação no banco, com segregação de papéis. |
| Gerador de scripts multi-SGBD | Gera `INSERT`/`UPDATE`/`DELETE`/`MERGE` idempotentes a partir dos metadados, parametrizados por dialeto de banco (Oracle, PostgreSQL, SQL Server, MySQL). |
| Execução controlada | Aplica os scripts em lote, com transação, rollback automático em falha, e registro de sucesso/erro por comando. |
| Motor de auditoria | Loga toda ação relevante (quem, quando, o quê, de onde, para onde) com retenção configurável. |
| Dashboard de acompanhamento | Mostra progresso, status, percentual de conclusão, contadores de válidos/rejeitados/alertas por migração. |
| Camada de evolução para API | Interface de execução plugável (script SQL vs. chamada de API) sem alterar o motor de validação nem os metadados. |

# 3. Arquitetura recomendada

## 3.1 Visão em camadas

A solução deve ser construída como uma aplicação em camadas, desacoplando o "o quê migrar" (metadados) do "como migrar" (motor de execução):

1. **Camada de apresentação (Portal de Migração)** — telas de configuração de metadados, condução do wizard de migração, console de tratamento de erros, aprovação e acompanhamento. Web, responsiva, orientada a papéis.
2. **Camada de API/Orquestração** — API REST que expõe as operações de criação de migração, upload de arquivo, execução de validação, geração de scripts, aprovação e execução. É o ponto único de entrada tanto para o portal quanto para integrações futuras (RPA, CI/CD de migração, chamadas em lote).
3. **Camada de motor (Migration Engine)**, composta por serviços especializados e independentes entre si:
   - *Adapter de Ingestão* — um adapter por formato de entrada (XLSX, XML, API, futuramente CSV/JSON/largura fixa), todos implementando a mesma interface de saída: um conjunto tabular normalizado (linhas x colunas mapeadas).
   - *Metadata Resolver* — lê a configuração de template/tipo de migração e decora cada campo recebido com seu contrato (tipo, tamanho, obrigatoriedade, regra).
   - *Transformation Engine* — aplica as regras de conversão (trim, normalização de caixa, remoção de caracteres especiais, máscaras, formatação de datas), equivalente às fórmulas `SUBSTITUTE/TRIM/TEXT` das planilhas atuais.
   - *Validation Engine* — aplica as validações estruturais, de dado, de domínio, relacionais, temporais e de negócio, e classifica o resultado.
   - *Key Resolution Service* — equivalente da tabela `NOVOCODIGO` e das fórmulas de "Busca de PK's livres": centraliza a geração/reserva de identificadores por organização e por contador, com bloqueio otimista para evitar colisão em execuções concorrentes.
   - *Script Generator* — a partir dos metadados e dos dados aprovados, monta os comandos por dialeto de banco.
   - *Execution Engine* — aplica os scripts (ou, na evolução futura, despacha chamadas de API) de forma transacional, em lote, com rollback e log por comando.
4. **Camada de staging/persistência** — banco relacional próprio da plataforma de migração (não o banco do ERP/HCM), com tabelas de controle de migração, dados brutos, dados normalizados, resultados de validação, scripts gerados e resultados de execução.
5. **Camada de integração de destino** — conexão com o banco do ERP/HCM (para aplicação de script e para consultas de "Base", equivalentes às abas `Base`/`HCM` das planilhas) e, na evolução futura, com as APIs da Teknisa.

## 3.2 Por que orientar por metadados

O ponto central da arquitetura é que **nenhuma lógica específica de contexto deve residir em código**. O que hoje é uma fórmula de planilha escrita à mão para "Estrutura" e reescrita, com pequenas variações, para "Ocupação", "Escala" e "Vínculo", deve se tornar uma única implementação de motor que lê:

- de onde vem o dado (coluna X do XLSX, tag Y do XML, campo Z da API);
- para onde vai (tabela/coluna do banco de destino);
- que forma deve assumir (tipo, tamanho, obrigatoriedade, valor padrão, conversão);
- que regras de validação e de dependência se aplicam;
- que operação é permitida (incluir, alterar, excluir).

Isso é o que a Seção 6 (Modelo de Metadados) detalha. A vantagem prática direta: um novo cadastro (por exemplo, "Sindicatos" ou "Centros de Custo") passa a ser configurado pela equipe funcional/implantação, sem intervenção de desenvolvimento, replicando exatamente o padrão das seis planilhas atuais.

## 3.3 Componentes de infraestrutura sugeridos

- Banco relacional para staging/controle (PostgreSQL é uma escolha natural, independente do banco de destino do cliente).
- Fila de mensagens (ex.: RabbitMQ/Kafka) para processamento assíncrono de importação, validação e, futuramente, chamadas de API em lote.
- Armazenamento de arquivos (blob storage) para os arquivos de origem, planilhas de inconsistência exportadas e scripts gerados, com política de retenção.
- Serviço de autenticação/autorização integrado ao IAM corporativo da Teknisa (SSO), com perfis e permissões próprios da ferramenta de migração.
- Motor de regras (rule engine) leve, para permitir que regras de validação/negócio complexas sejam parametrizadas sem deploy de código — ex.: uma DSL simples ou expressões avaliáveis (tipo "campo X obrigatório quando campo Y = tal valor").

# 4. Fluxo completo da migração

O fluxo abaixo consolida e refina a sequência proposta, com pontos de decisão e de bloqueio explícitos.

1. **Criação da migração** — usuário com perfil de operador cria uma nova migração.
2. **Seleção da organização** — sistema valida se já existe migração ativa/em processamento para essa organização; se existir, bloqueia a criação (ver regra de concorrência abaixo).
3. **Seleção do tipo de migração** — define automaticamente quais contextos/templates são obrigatórios, a ordem de importação e o banco de destino.
4. **Definição do operador responsável** — pode ser o próprio criador ou outro usuário designado; grava-se para trilha de auditoria.
5. **Identificação dos templates obrigatórios** — sistema apresenta checklist dos arquivos/fontes esperados, com status "pendente".
6. **Importação dos arquivos na ordem definida** — sistema aceita apenas o próximo template da sequência (ou libera importação livre se o tipo de migração permitir paralelismo entre contextos independentes).
7. **Leitura e armazenamento temporário (staging bruto)** — dado é lido pelo adapter correspondente e persistido como veio, sem qualquer transformação, para fins de auditoria e reprocessamento.
8. **Validação estrutural dos arquivos** — extensão, versão do template, abas obrigatórias, cabeçalhos, encoding, schema (XML/JSON), tamanho e volume.
9. **Validação dos tipos de dados** — aplica o contrato de metadados (tipo, tamanho, obrigatoriedade, máscara).
10. **Aplicação das regras de negócio** — validações de domínio e de regra específica de módulo.
11. **Validação das dependências entre arquivos** — confere se os registros referenciados em outros templates (banco/agência, estrutura, ocupação, escala) já existem no staging aprovado desta migração ou no banco de destino.
12. **Identificação de inconsistências** — consolida os resultados classificados (erro/alerta/recomendação/ajuste automático/informação) em um relatório por arquivo/linha/campo.
13. **Correção ou reprocessamento** — usuário corrige na interface, reimporta apenas os registros corrigidos, ou reprocessa arquivo/etapa.
14. **Aprovação dos dados** — usuário com perfil de aprovador confirma que o lote validado pode seguir para geração de scripts (exceções pontuais podem ser aprovadas com justificativa registrada).
15. **Geração dos scripts** — o Script Generator monta os comandos (INSERT/UPDATE/DELETE/MERGE) a partir dos dados aprovados e dos metadados, resolvendo PKs via Key Resolution Service.
16. **Revisão e aprovação final** — segundo perfil (segregação de função) revisa o conteúdo do script antes da aplicação.
17. **Geração do arquivo SQL ou execução no banco** — conforme autorização, o sistema apenas exporta o `.sql` ou já aplica diretamente, em lote controlado.
18. **Validação pós-migração** — reexecuta consultas de conferência (equivalentes às abas `Base`/`HCM`) para confirmar que os registros existem no destino com os valores esperados.
19. **Encerramento da migração** — migração é marcada como concluída (ou concluída com alertas), gera-se o relatório final, e a organização é liberada para uma nova migração.

## 4.1 Regra de concorrência por organização

Uma organização não pode ter mais de uma migração em status ativo (qualquer status entre "criada" e "aguardando aplicação", inclusive) simultaneamente. Exceção: o tipo de migração pode declarar contextos independentes como "migração paralela permitida" (ex.: Agências Bancárias, por não ter dependência com Estrutura/Vínculo, poderia rodar em paralelo com uma migração de Escala de Trabalho) — essa permissão deve ser explícita no cadastro do tipo de migração, nunca implícita. Por padrão, o sistema bloqueia.
# 5. Modelo de tipos de migração e templates

## 5.1 Tipo de migração

Um **tipo de migração** é a configuração reutilizável que descreve um "pacote" de contextos a migrar. Exemplo, baseado nos seis arquivos anexados:

| Atributo | Exemplo de valor |
|---|---|
| Código | `MIG_HCM_ONBOARDING` |
| Nome | Migração HCM — Implantação Completa |
| Banco de destino | Oracle |
| Templates obrigatórios | Agências Bancárias, Estrutura Organizacional, Ocupação, Escala de Trabalho, Vínculo, Dependentes |
| Sequência obrigatória | 1) Agências Bancárias 2) Estrutura 3) Ocupação 4) Escala de Trabalho 5) Vínculo 6) Dependentes |
| Dependências entre templates | Vínculo depende de Estrutura, Ocupação, Escala e Agências; Dependentes depende de Vínculo |
| Regras de validação aplicáveis | Conjunto de regras vinculadas a cada template (ver Seção 7) |
| Regras de transformação aplicáveis | Conjunto de regras de conversão vinculadas a cada campo |
| Operação permitida | Inclusão (padrão para migração inicial); Alteração e Exclusão habilitáveis por template |
| Mecanismo de aplicação | Geração de script SQL (fase 1) ou chamada de API (fase futura), configurável por tipo de migração |
| Permite concorrência | Não, por padrão (ver 4.1) |

## 5.2 Template

Um **template** representa um contexto migrável (uma das seis planilhas, ou qualquer cadastro futuro). Ele é a unidade de configuração de metadados e carrega:

- identificação (código, nome, versão — replicando o controle de versão que hoje aparece nos nomes dos arquivos, como "v12", "v07", "v26_BETA");
- formato(s) de entrada aceitos (XLSX, XML, API);
- estrutura esperada (aba/planilha, cabeçalhos obrigatórios, schema);
- lista de campos (o "Modelo de Metadados" da Seção 6);
- tabelas de destino (podendo ser mais de uma por template — como visto no arquivo de Estrutura, que gera `PARCNEGOCIO`, `ESTRUTURAM`, `ESTRUTURAH` e `ENDERECOPARC` a partir de uma única linha de entrada);
- consultas de "estado atual do destino" (equivalentes às abas `Base`/`HCM`/`Script`), usadas para checar existência prévia e obter o próximo código livre;
- template de geração de script (por dialeto de banco).

## 5.3 Relação entre templates identificados nos arquivos anexados

| Ordem sugerida | Template | Depende de | Gera principalmente |
|---|---|---|---|
| 1 | Agências Bancárias | — | `AGENCIA` |
| 2 | Estrutura Organizacional | — (mas referenciada por Vínculo) | `PARCNEGOCIO`, `ESTRUTURAM`, `ESTRUTURAH`, `ENDERECOPARC` |
| 3 | Ocupação | — (referenciada por Vínculo) | `GPE_OCUPACAOM`, `GPE_OCUPACAOH` |
| 4 | Escala de Trabalho | — (referenciada por Vínculo) | `GPE_ESCALATRABM`, `GPE_ESCALATRABH` |
| 5 | Vínculo | Agências, Estrutura, Ocupação, Escala | `GPE_VINCULOM`, `GPE_VINCULOH`, `GPE_PESSOA`, `GPE_PESSOAH` (inferido) |
| 6 | Dependentes | Vínculo | `PARCNEGOCIO` (pessoa), `GPE_PESSOA`, `GPE_PESSOAH`, `RELACIONAPARC`, `FPA_DEPVINCULO` |

Esta ordem é **inferida com alto grau de confiança** a partir das referências cruzadas encontradas nos scripts (por exemplo, o script de Dependentes busca `NRVINCULOM` via `SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE CDMATRICULA = '@NRVINCULOM@'`, o que exige que o Vínculo já exista no banco). A confirmação definitiva de obrigatoriedade estrita (versus apenas recomendação de ordem) deve ser validada com a equipe funcional.

# 6. Modelo de metadados

O metadado é a unidade central da plataforma: tudo que hoje está "hardcoded" em fórmula de planilha deve poder ser expresso como configuração. Cada campo de um template carrega:

| Atributo do metadado | Descrição | Equivalente observado nas planilhas |
|---|---|---|
| `origem` | Coluna/tag/atributo de origem | Coluna do XLSX (ex. coluna `D` = "Nº Estrutura") |
| `destino_tabela` | Tabela de destino | `ESTRUTURAM`, `AGENCIA`, `GPE_OCUPACAOM` etc. |
| `destino_coluna` | Coluna de destino | `NRESTRUTURA`, `CDAGENCIA`, `NROCUPACAOM` |
| `tipo` | Tipo de dado esperado | numérico, texto, data, hora, monetário, booleano |
| `tamanho_maximo` | Tamanho/precisão máxima | ex. `LEFT(...,4)` no CBO, `TEXT(...,"0000")` na agência |
| `obrigatorio` | Se o campo é obrigatório | inferido pelas fórmulas `IF(TRIM(x)="","N",...)` (tem padrão) vs. campos sem tratamento de vazio (obrigatórios) |
| `valor_padrao` | Valor aplicado quando ausente | `IF(TRIM(N3)="","N",TRIM(N3))`, `NVL(...)` nos templates SQL |
| `regra_conversao` | Transformação a aplicar | `TRIM`, `SUBSTITUTE` (remoção de espaços, pontos, hífens, barras), `TEXT(...,"DD/MM/AAAA")`, `UPPER`, remoção de acentuação |
| `regra_validacao` | Regra de validação a aplicar | checagem de duplicidade (`COUNTIF`), obrigatoriedade condicional |
| `chave_primaria` | Se compõe PK do registro de destino | `NRESTRUTURA`, `NRPARCNEGOCIO`, `NROCUPACAOM` etc. |
| `chaves_estrangeiras` | Referências a outras entidades | `NRTIPOESTRUTURA`, `CDSINDICAL`, `NRESCALATRABM` |
| `gerador_pk` | Se o valor deve ser gerado automaticamente (sequencial) | padrão `NOVOCODIGO`/"Busca de PK's livres" |
| `dependencias` | Outros templates/registros que devem existir antes | Vínculo depende de Estrutura/Ocupação/Escala/Agência |
| `operacao_permitida` | Inclusão / Alteração / Exclusão | hoje só inclusão está implementada nas planilhas (`"insere"` / `"não"`) |

## 6.1 Padrão observado: geração de chave via contador central

Todas as planilhas analisadas resolvem PK da mesma forma, o que deve virar um serviço único e não seis implementações:

1. Uma consulta ao banco de destino identifica faixas livres na sequência de códigos de uma tabela (fórmula "Busca de PK's livres": localiza lacunas entre valores mínimo/máximo usando `LEAD() OVER (ORDER BY ...)`).
2. Uma tabela de controle central, `NOVOCODIGO` (chave `NRORG` + `CDCONTADOR`), guarda o próximo número disponível por organização e por "contador" (equivalente a uma tabela/entidade).
3. Ao final da geração de scripts, um `MERGE INTO NOVOCODIGO` atualiza o próximo código disponível.
4. Antes da aplicação, uma consulta de "Validação de PK" confere se a faixa de códigos que será usada não colide com o que já existe na tabela de destino (`SELECT ... WHERE campo BETWEEN faixa_inicial AND faixa_final`).

Esse é o padrão de **Key Resolution Service** citado na arquitetura (Seção 3): ele deve ser generalizado para qualquer tabela/contador, reutilizando a própria tabela `NOVOCODIGO` já existente no HCM da Teknisa, e não recriando uma versão paralela por planilha.

## 6.2 Padrão observado: template de script com placeholders

Os seis arquivos usam a mesma técnica: um texto de template com marcadores `@CAMPO@`, armazenado em uma célula fixa, que é populado via cadeias de `SUBSTITUTE(SUBSTITUTE(...))` linha a linha. Esse é exatamente o comportamento que o **Script Generator** deve reproduzir de forma genérica: o metadado de cada campo aponta seu marcador, o motor injeta o template (armazenado por tabela/operação, não por planilha) e substitui os marcadores pelos valores já validados e transformados da linha.

# 7. Regras de validação

O motor de validação deve operar em camadas sucessivas, interrompendo o processamento de um registro assim que um erro impeditivo é encontrado nessa camada (mas continuando a processar os demais registros do lote):

## 7.1 Validações estruturais
Existência do arquivo; extensão permitida; versão do template (as planilhas já trazem esse controle informalmente no nome do arquivo — "v12", "v07", "BETA" — e isso deve virar um campo formal de metadado); aba/planilha obrigatória (`Dados`, `Script`, `Base`, conforme o padrão observado); cabeçalhos obrigatórios; colunas ausentes/duplicadas/desconhecidas; encoding; estrutura e schema válidos para XML/JSON; tamanho máximo do arquivo; quantidade máxima de registros por lote.

## 7.2 Validações de dado
Obrigatoriedade; tipo (numérico, texto, data, hora, monetário, percentual, booleano); tamanho mínimo/máximo; casas decimais; máscaras; CPF/CNPJ/CEP/e-mail/telefone; códigos oficiais (CBO, CNAE, FPAS, CAGED — todos presentes no arquivo de Estrutura); caracteres inválidos; espaços indevidos; normalização de caixa; remoção/conversão de caracteres especiais — todas essas últimas já são replicadas hoje pelas cadeias `SUBSTITUTE` das planilhas e devem ser parametrizadas como "regra de conversão" no metadado, não reescritas em fórmula a cada novo template.

## 7.3 Validações de domínio
Valores permitidos para: sexo, estado civil, tipo de vínculo, categoria, situação, tipo de dependente, tipo de jornada, tipo de conta, banco, agência, ocupação, cargo, sindicato, estabelecimento, centro de custo, lotação. Nos arquivos anexados, os domínios de sexo, estado civil, tipo de dependente e tipo de conta aparecem como códigos numéricos/textuais sem lista de valores explícita na planilha (ex. `@IDSEXO@`, `@CDESTACIVIL@`, `@NRTIPODEPENDE@`) — **isso é uma hipótese que precisa ser validada com a equipe funcional**: os domínios certamente existem como tabelas de apoio no HCM, mas não estão documentados nos arquivos anexados e precisam ser levantados por tabela para compor o metadado de "valores permitidos".

## 7.4 Validações relacionais
Existência da organização (`NRORG` aparece em todos os arquivos como parâmetro fixo de cabeçalho — identificado diretamente); existência de estrutura/ocupação/escala/banco/agência referenciados por Vínculo (inferido pelas fórmulas de busca cruzada); existência de vínculo referenciado por Dependentes (identificado diretamente no script: `SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE CDMATRICULA = '@NRVINCULOM@'`); unicidade de chaves; duplicidade dentro do arquivo, entre arquivos e no banco de destino (replicando a lógica de `COUNTIF` contra a aba `Base`); ordem correta de importação; integridade entre entidades.

## 7.5 Validações temporais
Datas futuras indevidas; data de admissão anterior à data de nascimento (aplicável ao Vínculo, que traz `Data Admissão` e, indiretamente via Dependentes, `Data de Nascimento`); data de rescisão anterior à admissão; vigências sobrepostas — **relevante e inferido com alta confiança**, pois o padrão Master/Histórico (`ESTRUTURAM/ESTRUTURAH`, `OCUPACAOM/OCUPACAOH`, `ESCALATRABM/ESCALATRABH`, `VINCULOM/VINCULOH`) é controlado por `DTINIVIGENCIA`/`DTFIMVIGENCIA` e por `DTMESCOMPETENC` (competência mensal), e sobreposição de vigência é um risco relacional clássico desse desenho; validade de documentos; histórico cronológico inconsistente.

## 7.6 Validações de negócio
Regras específicas de módulo (folha, frequência, benefícios, previdência); preenchimento condicional (ex. no arquivo de Estrutura, a inserção de endereço só ocorre "se tipo de endereço e endereço existirem" — regra identificada diretamente na fórmula `=IF(AND(AT3<>"",AY3<>""),"insere","não")`); vínculos incompatíveis; dependências entre cadastros; necessidade de cadastro prévio (ex. Município deve existir previamente, pois o script de Estrutura busca `SELECT MAX(CDMUNICIPIO) FROM MUNICIPIO WHERE UPPER(NMMUNICIPIO) = '@MUNICIPIO@'` — identificado diretamente); regras fiscais, trabalhistas, previdenciárias.

## 7.7 Classificação dos resultados
Cada validação deve produzir um resultado com uma das seguintes classificações, para orientar o comportamento subsequente do fluxo:

| Classificação | Efeito |
|---|---|
| Erro impeditivo | Bloqueia a aprovação do registro; não gera script |
| Alerta | Permite prosseguir, mas exige atenção e é reportado no relatório final |
| Recomendação | Sugestão de ajuste, não bloqueia |
| Ajuste automático | Sistema corrige o valor (ex. trim, normalização) e registra o valor original |
| Informação | Apenas contextual, sem efeito no fluxo |

# 8. Gestão de erros e inconsistências

O console de tratamento de erros deve permitir, no mínimo:

- Visualizar erros por arquivo, aba, linha e coluna, com valor recebido, valor esperado, regra violada e orientação de correção — formato de mensagem detalhado na Seção 23.
- Filtrar registros válidos/inválidos, por severidade (erro/alerta/recomendação).
- Corrigir diretamente na interface (célula a célula) ou exportar uma planilha de inconsistências, corrigir externamente e reimportar apenas os registros corrigidos (mantendo rastreabilidade de que aquela linha é uma correção da importação original, não um novo registro).
- Reprocessar um arquivo inteiro ou apenas uma etapa (por exemplo, refazer apenas a validação relacional sem reimportar o arquivo).
- Comparar versões: manter o valor original (staging bruto) e o valor ajustado (staging transformado), sempre visíveis lado a lado.
- Aprovar exceções pontuais mediante justificativa registrada — equivalente a permitir que um "alerta" ou uma "recomendação" não seja corrigida, desde que o aprovador registre o motivo.

# 9. Gestão de status e etapas

## 9.1 Máquina de estados da migração

```
[criada]
   │  (seleção de organização/tipo OK, sem migração ativa concorrente)
   ▼
[aguardando arquivos] ──(todos os templates obrigatórios enviados)──▶ [em importação]
   │                                                                        │
   │ (upload incompleto / cancelamento)                                    ▼
   ▼                                                                [em validação]
[cancelada]                                                               │
                                     ┌──────────────────────────────────┼───────────────────────┐
                                     ▼ (erros impeditivos encontrados)  ▼ (sem erros impeditivos) ▼ (falha técnica)
                              [com inconsistências]              [aguardando aprovação]      [com erro]
                                     │ (correção/reprocessamento)        │ (aprovado)
                                     ▼                                   ▼
                              [aguardando correção] ──(reenvio)──▶ [em validação]      [pronta para geração de scripts]
                                                                                              │
                                                                                              ▼
                                                                                       [scripts gerados]
                                                                                              │ (revisão/aprovação final)
                                                                                              ▼
                                                                                     [aguardando aplicação]
                                                                                              │
                                                                                              ▼
                                                                                        [em execução]
                                                                            ┌─────────────────┼─────────────────┐
                                                                            ▼                  ▼                 ▼
                                                                     [concluída]   [concluída com alertas]   [com erro]
                                                                                                                  │
                                                                                                                  ▼
                                                                                                            [revertida]
```

## 9.2 Tabela de transições e responsáveis

| De | Para | Gatilho | Perfil responsável |
|---|---|---|---|
| criada | aguardando arquivos | organização/tipo definidos, sem conflito de concorrência | Operador |
| aguardando arquivos | em importação | upload do próximo template na sequência | Operador |
| em importação | em validação | leitura/staging concluído | Sistema |
| em validação | com inconsistências | erro impeditivo identificado | Sistema |
| em validação | aguardando aprovação | nenhum erro impeditivo pendente | Sistema |
| com inconsistências | aguardando correção | relatório de erros publicado | Sistema |
| aguardando correção | em validação | reenvio/reprocessamento | Operador |
| aguardando aprovação | pronta para geração de scripts | aprovação dos dados | Aprovador |
| pronta para geração de scripts | scripts gerados | geração concluída | Sistema |
| scripts gerados | aguardando aplicação | revisão e aprovação final | Aprovador (segregado do aprovador de dados) |
| aguardando aplicação | em execução | autorização de aplicação | Executor |
| em execução | concluída | todos os comandos aplicados com sucesso | Sistema |
| em execução | concluída com alertas | aplicação concluída com pendências não bloqueantes | Sistema |
| em execução | com erro | falha na aplicação | Sistema |
| com erro | revertida | rollback executado | Sistema/Executor |
| qualquer estado ativo | cancelada | cancelamento manual | Operador/Administrador |

Qualquer estado entre "criada" e "aguardando aplicação" (inclusive) é considerado **ativo** para efeito da regra de bloqueio de concorrência por organização (Seção 4.1).
# 10. Geração e aplicação de scripts

## 10.1 Requisitos do gerador

O gerador deve produzir, por dialeto de banco selecionado (Oracle na primeira versão, por ser o observado nos arquivos anexados; PostgreSQL, SQL Server e MySQL por evolução):

- escape correto de caracteres especiais e aspas simples (as planilhas já tratam isso parcialmente com `SUBSTITUTE(texto,"'","")`, o que na verdade **remove** em vez de **escapar** — um ponto de melhoria funcional a se levar à equipe, já que remover aspas pode alterar nomes próprios legítimos; o motor genérico deve escapar corretamente, ex. dobrar aspas, em vez de eliminar caracteres);
- tratamento de valores nulos (`NVL`/`COALESCE` conforme dialeto);
- formatação de datas conforme o dialeto (`TO_DATE(...,'DD/MM/YYYY')` para Oracle, `::date` para PostgreSQL etc.) — hoje as planilhas apenas formatam como texto `DD/MM/AAAA` e confiam na conversão implícita do Oracle, o que é um risco a ser eliminado;
- tratamento de campos numéricos e monetários (separador decimal, precisão);
- uso de transações com controle de commit/rollback por lote (as planilhas já usam `COMMIT;` ao final de cada linha — o motor deve tornar esse controle configurável por tamanho de lote, não por linha);
- ordenação dos comandos respeitando dependência entre tabelas (mestre antes de detalhe/histórico, ex. `ESTRUTURAM` antes de `ESTRUTURAH`);
- scripts idempotentes — o motor deve gerar comandos que possam ser reexecutados sem duplicar dados, o que hoje é parcialmente resolvido pela checagem `COUNTIF`/`Existe?` contra a aba `Base`, e deve virar, no gerador, uma cláusula condicional (`MERGE`/`INSERT ... WHERE NOT EXISTS`) sempre que o dialeto suportar;
- validação de existência antes de inserir (equivalente ao padrão `Existe?`/`insere`/`não` observado em todos os arquivos);
- prevenção de duplicidade;
- geração de logs por comando;
- scripts de reversão (rollback script) — ausente nas planilhas atuais e que deve ser um requisito novo da plataforma: para cada `INSERT` gerado, o motor também gera o `DELETE`/`UPDATE` reverso correspondente, associado ao mesmo lote;
- separação por lote e limitação de volume por arquivo de saída, para viabilizar execução e revisão de scripts grandes (o arquivo de Vínculo, por exemplo, já traz 224 colunas e potencialmente centenas de registros).

## 10.2 Etapa final de aplicação

1. Gerar arquivo `.sql` (ou equivalente ao banco selecionado).
2. Revisar o conteúdo gerado (interface de revisão, com syntax highlighting e contagem de comandos por tipo/tabela).
3. Aprovar a execução (perfil segregado do aprovador de dados — Seção 10.3 detalha).
4. Aplicar os scripts diretamente no banco, caso autorizado, em lotes controlados.
5. Acompanhar o processamento (percentual, comandos executados, comandos pendentes).
6. Registrar sucesso ou falha de cada comando individualmente.
7. Executar rollback automático em caso de erro não tratado (usando os scripts de reversão gerados na etapa 10.1, ou `ROLLBACK` de transação quando o lote ainda não foi commitado).
8. Gerar relatório final da migração (contadores, tempo total, exceções, usuário aprovador/executor).

## 10.3 Segregação de papéis na geração/aplicação

| Ação | Perfil mínimo exigido |
|---|---|
| Importar arquivos | Operador |
| Corrigir dados em staging | Operador |
| Aprovar dados validados | Aprovador Funcional |
| Gerar scripts | Aprovador Funcional ou Operador (configurável) |
| Aprovar aplicação dos scripts | Aprovador Técnico (distinto do Aprovador Funcional) |
| Aplicar scripts no banco | Executor/DBA |
| Executar rollback | Executor/DBA ou Administrador |

# 11. Evolução para APIs e processamento em background

## 11.1 Modelo alvo

Na evolução futura, a Execution Engine (Seção 3.1) passa a ter dois modos de despacho, selecionáveis por tipo de migração ou por template, sem qualquer alteração no Metadata Resolver, no Transformation Engine ou no Validation Engine:

- **Modo Script**: gera comando SQL (estado atual proposto para a primeira versão).
- **Modo API**: para cada registro aprovado, monta um payload (a partir dos mesmos metadados que hoje montam o `@CAMPO@` do template SQL) e o envia a um endpoint de inclusão/alteração/exclusão da API da Teknisa.

O Modo API deve:

- controlar autenticação (OAuth2/client credentials) e autorização por escopo/permissão;
- processar em lotes, respeitando limites de taxa (*rate limiting*) do provedor de API;
- gerenciar filas (fila de saída por migração/template, com prioridade e reentrada);
- realizar retentativas com backoff exponencial em falhas transitórias (5xx, timeout);
- controlar idempotência — usando uma chave de idempotência por registro (ex. hash do payload + id do template + linha de origem), para permitir reprocessamento seguro sem duplicar;
- registrar request e response completos (para trilha de auditoria e depuração);
- tratar falhas parciais — lote com 100 registros pode ter 92 sucessos e 8 falhas; o sistema deve continuar processando os demais e reportar exatamente quais falharam e por quê;
- acompanhar o status de cada registro individualmente (enviado, confirmado, falhou, reenviado);
- permitir reprocessamento seletivo (apenas os registros que falharam);
- consolidar o resultado final no mesmo relatório usado para o Modo Script;
- manter rastreabilidade completa, ponta a ponta, do dado de origem até a resposta da API.

## 11.2 Comparativo de estratégias de aplicação

| Estratégia | Vantagens | Desvantagens |
|---|---|---|
| Geração de script SQL (sem aplicação automática) | Máximo controle humano antes da execução; fácil auditoria estática do que será alterado; permite execução por DBA fora da janela da plataforma | Processo manual adicional; risco de divergência entre o script revisado e o que é de fato executado se houver edição manual; não valida regras de negócio da camada de aplicação do ERP (bypassa regras que só existem na camada de serviço) |
| Aplicação direta de script no banco | Mais rápido, sem etapa manual extra; ainda permite transação/rollback | Bypassa completamente as regras de negócio da aplicação (só valida o que o banco valida via constraints); maior risco de inconsistência com lógica de domínio que vive fora do banco; mais difícil de auditar "quem decidiu aplicar o quê" se não houver aprovação formal antes |
| Integração via API | Reaproveita toda a regra de negócio e validação já existente na camada de serviço do ERP/HCM; caminho natural para evolução, sem acesso direto ao banco de produção; mais seguro em termos de superfície de ataque | Mais lento por registro; depende de disponibilidade/limite de taxa da API; exige tratamento robusto de filas, retentativas e idempotência; requer que a API cubra 100% dos casos de uso hoje resolvidos via SQL direto (pode não cobrir no início) |
| Filas e processamento assíncrono | Resiliente a picos de volume; permite retomar de onde parou; desacopla ingestão de aplicação; natural para o Modo API | Maior complexidade operacional (monitoramento de fila, dead-letter, alertas); introduz latência entre aprovação e efetivação, que precisa ser comunicada ao usuário |

**Recomendação de trajetória**: iniciar em Modo Script (fase 1, aderente ao padrão já validado nas planilhas), evoluir para aplicação direta controlada (fase 2, mesma lógica, menos manual), e migrar progressivamente contexto por contexto para o Modo API assíncrono com filas (fase 3), à medida que os endpoints de API cubram cada entidade (Estrutura, Ocupação, Escala, Vínculo, Dependentes, Agências).

# 12. Segurança, auditoria e LGPD

## 12.1 Controle de acesso
Perfis mínimos: Operador, Aprovador Funcional, Aprovador Técnico, Executor/DBA, Administrador, Auditor (somente leitura). Autorizações distintas para importar, aprovar dados, gerar scripts, aprovar aplicação e aplicar scripts — nunca um único perfil concentrando todas as etapas de uma migração sensível (segregação de função).

## 12.2 Proteção de dados
Mascaramento de dados sensíveis em tela e em log para usuários sem permissão plena (CPF, PIS, dados bancários, endereço — todos presentes no arquivo de Vínculo); criptografia em repouso e em trânsito para arquivos de origem e para o staging (que contém dados pessoais de colaboradores e dependentes, sujeitos à LGPD); exclusão segura de arquivos temporários após o prazo de retenção definido pela política da organização.

## 12.3 LGPD
Os arquivos de Vínculo e Dependentes carregam dados pessoais sensíveis (CPF, RG, título de eleitor, CNH, dados de saúde indiretos via dependentes, endereço, dados bancários). A plataforma deve:

- tratar esses dados sob base legal de execução de contrato de trabalho/obrigação legal (a ser confirmado formalmente com jurídico/DPO da organização contratante — **hipótese que precisa validação**, pois a base legal aplicável depende do contrato entre a Teknisa e cada cliente);
- registrar finalidade e base legal do tratamento por tipo de dado, quando exigido;
- oferecer expurgo dos dados de staging após a conclusão da migração, conforme política de retenção;
- restringir acesso aos dados pessoais pelo princípio de necessidade (perfis com acesso mínimo necessário);
- manter log de quem acessou/exportou dados pessoais durante o processo de migração.

## 12.4 Auditoria e trilha
Todo evento relevante deve ser registrado de forma imutável: criação/alteração de migração; upload de arquivo (hash do arquivo, usuário, timestamp); execução de validação (resultado, regras aplicadas); correções manuais (valor original × valor ajustado, autor, justificativa); aprovações (usuário, papel, timestamp, dados aprovados); geração de script (conteúdo, hash); aplicação (comando a comando, sucesso/erro); rollback. Essa trilha deve ser consultável por migração, por organização e por período, com retenção configurável e exportação para fins de auditoria externa.

# 13. Análise dos arquivos anexados

Esta seção resume os achados técnicos da inspeção direta dos seis arquivos, classificando cada conclusão conforme solicitado.

## 13.1 Padrão estrutural comum (identificado diretamente em todos os arquivos)

Todos os seis arquivos seguem o mesmo desenho: uma aba **`Dados`** (ou `Sheet1`/`Script`, no caso de Agências e Ocupação) contendo, lado a lado:

1. colunas de entrada manual (dado bruto vindo do sistema legado);
2. colunas auxiliares de normalização (fórmulas `TRIM`, `SUBSTITUTE`, `TEXT`, `UPPER`, remoção de acentos e caracteres especiais);
3. uma coluna/flag de existência prévia (`Existe?`, `insere`/`não`), calculada via `COUNTIF` contra uma aba de referência;
4. colunas de geração de chave primária sequencial (incremento sobre a linha anterior, ou busca de "faixa livre" contra o banco de destino);
5. uma célula de template de script com marcadores `@CAMPO@`;
6. uma fórmula final, por linha, que substitui os marcadores pelos valores calculados e concatena múltiplos `INSERT` seguidos de `COMMIT;`.

Uma segunda aba (**`Base`**, `HCM` ou `prototipo 3`) traz o resultado de uma consulta SQL previamente extraída do banco de destino (com parâmetros `:P_NRORG` e `:P_DTMESCOMPETENC`), usada como referência estática para os `COUNTIF` de existência. Isso confirma que o processo real hoje é: extrair manualmente uma consulta do banco, colar o resultado na aba `Base`, e só então preencher a aba `Dados`.

## 13.2 Achados por arquivo

**00_Agencias_Bancarias.xlsx** (identificado diretamente): estrutura mais simples dos seis, uma única aba, 4 linhas de exemplo. Colunas: `Banco`, `Cd. Agência`, `Agência`, célula fixa `NRORG` (`1410`). Gera um único `INSERT INTO AGENCIA (CDBANCO, CDAGENCIA, NMAGENCIA, NRORG, DTINCLUSAO, CDOPERINCLUSAO, NRORGINCLUSAO, IDATIVO)`. Não possui aba `Base`/verificação de existência prévia — **risco identificado diretamente**: reexecutar esse template pode gerar duplicidade, já que não há checagem de existência como nos demais arquivos.

**01_Estrutura_v12.xlsx**: aba `Dados` com 87 colunas e aba `Base`. Gera quatro tabelas por linha: `PARCNEGOCIO`, `ESTRUTURAM`, `ESTRUTURAH`, `ENDERECOPARC` — inserção condicional de endereço apenas se tipo de endereço e logradouro estiverem preenchidos (identificado diretamente na fórmula `IF(AND(AT3<>"",AY3<>""),"insere","não")`). Depende de tabela de apoio `MUNICIPIO` (consulta por nome + país + estado) e de um código de sindicato (`CDSINDICAL`) cujo domínio não está descrito no arquivo (hipótese a validar). Nome do arquivo evidencia controle de versão informal ("v12 [melhorias da v11]") que deveria virar um campo formal de versionamento de template na plataforma.

**02_Ocupação_v07.xlsx**: aba `Script` (nome distinto do padrão `Dados`, mas mesma função) com 10 linhas de exemplo, e aba `HCM` (equivalente à aba `Base` dos demais). Gera `GPE_OCUPACAOM` e `GPE_OCUPACAOH`, com CBO (`NRCBO`) como atributo relevante — nenhuma validação de formato de CBO aparece na planilha (7 dígitos padrão MTE), o que é uma **recomendação a incluir** no metadado de validação de domínio/máscara.

**03_EscalaTrabalho_v09.xlsx**: aba `Dados` com 221 linhas de dados reais (o maior volume de exemplo entre os arquivos) e aba `Base`. Gera `GPE_ESCALATRABM`/`GPE_ESCALATRABH`, incluindo horários de entrada/saída em texto livre `HH:MM` — a própria planilha registra um alerta manual ("As entradas e saídas devem ser texto no formato HH:MM"), o que **identificado diretamente** indica ausência de validação automática de formato de hora nesse template hoje, um ponto claro de melhoria a ser coberto pelo metadado `tipo=hora`.

**04_Vinculo_v26_BETA.xlsx**: o arquivo mais complexo, com 224 colunas na aba `Dados`, aba `Base` com 680 linhas de referência e uma terceira aba `prototipo 3` (parece um protótipo de tela ou layout alternativo — **hipótese a validar com a equipe**, pois seu conteúdo não pôde ser plenamente interpretado sem contexto funcional adicional). O sufixo "BETA" no nome do arquivo confirma que este template está em desenvolvimento ativo, reforçando a necessidade de versionamento formal de metadados. Traz dados pessoais sensíveis (CPF, PIS, título de eleitor, CNH, endereço, dados bancários) e referencia todos os demais contextos (Banco/Agência, Estrutura — via `Estrutura Trabalho`/`Estrutura Gerencial`, Ocupação, Escala de Trabalho) — confirmando a posição deste template como o mais dependente na sequência de importação.

**05_Dependentes_v12.xlsx**: aba `Dados` com 54 colunas. Gera `PARCNEGOCIO` (pessoa física do dependente), `GPE_PESSOA`/`GPE_PESSOAH`, `RELACIONAPARC` (vínculo de relacionamento entre parceiros de negócio) e `FPA_DEPVINCULO` (vínculo funcional do dependente). Depende explicitamente do Vínculo já existente no banco (`SELECT MAX(NRVINCULOM) FROM GPE_VINCULOM WHERE CDMATRICULA = '@NRVINCULOM@'` — identificado diretamente), confirmando que Dependentes deve ser o último template da sequência.

## 13.3 Elementos comuns que devem virar metadados genéricos

- Parâmetro fixo `NRORG` (organização) — presente em célula fixa em todos os arquivos, deve ser um parâmetro de execução da migração, não uma célula de planilha.
- Operador de inclusão fixo `'000000099991'` — hoje hardcoded em todos os templates SQL; deve virar o identificador do usuário técnico de migração configurado por ambiente/organização.
- Padrão Master/Histórico (`XXXM`/`XXXH`) com `DTMESCOMPETENC`, `DTINIVIGENCIA`, `DTFIMVIGENCIA` — recorrente em Estrutura, Ocupação, Escala e Vínculo; deve ser tratado como um padrão de metadado de primeira classe (um template pode declarar que gera um par mestre/histórico, com uma coluna de competência).
- Tabela `NOVOCODIGO` como serviço central de geração de código (Seção 6.1).
- Consultas de "estado atual do destino" (abas `Base`/`HCM`) — devem ser parametrizadas como parte do metadado do template ("query de existência"), e não coladas manualmente antes de cada migração.

## 13.4 Riscos de inconsistência identificados

- Ausência de checagem de existência prévia no template de Agências Bancárias (risco de duplicidade).
- Tratamento de aspas simples por remoção (`SUBSTITUTE(texto,"'","")`) em vez de escape, o que pode corromper nomes próprios legítimos (ex. "D'Ávila").
- Dependência de que o usuário cole manualmente, antes de cada execução, o resultado atualizado da consulta de referência na aba `Base`/`HCM` — sujeito a defasagem entre o momento da extração e o momento da geração do script, criando janela de corrida em ambientes com múltiplos operadores.
- Validação de formato de hora (Escala de Trabalho) e de CBO (Ocupação) dependente de disciplina manual do usuário, sem validação automática.
# 14. Modelo de dados sugerido

O modelo abaixo é o esquema de controle da **plataforma de migração** (staging/orquestração), distinto do banco de destino do ERP/HCM.

```
ORGANIZACAO (NRORG PK, NOME, ATIVO)

TIPO_MIGRACAO (ID PK, CODIGO, NOME, BANCO_DESTINO, PERMITE_CONCORRENCIA, MODO_APLICACAO)

TIPO_MIGRACAO_TEMPLATE (ID PK, TIPO_MIGRACAO_ID FK, TEMPLATE_ID FK, ORDEM, OBRIGATORIO)

TEMPLATE (ID PK, CODIGO, NOME, VERSAO, FORMATOS_ACEITOS, ATIVO)

TEMPLATE_METADADO_CAMPO (
  ID PK, TEMPLATE_ID FK, ORIGEM, DESTINO_TABELA, DESTINO_COLUNA,
  TIPO, TAMANHO_MAXIMO, OBRIGATORIO, VALOR_PADRAO,
  REGRA_CONVERSAO, REGRA_VALIDACAO, EH_PK, GERADOR_PK,
  OPERACAO_PERMITIDA
)

TEMPLATE_CAMPO_FK (ID PK, CAMPO_ID FK, TEMPLATE_REFERENCIADO_ID FK, CAMPO_REFERENCIADO)

TEMPLATE_SCRIPT (ID PK, TEMPLATE_ID FK, OPERACAO, DIALETO_BANCO, TEMPLATE_TEXTO, TEMPLATE_ROLLBACK)

TEMPLATE_QUERY_REFERENCIA (ID PK, TEMPLATE_ID FK, DESCRICAO, SQL_TEXTO, PARAMETROS)

MIGRACAO (
  ID PK, NRORG FK, TIPO_MIGRACAO_ID FK, OPERADOR_ID FK,
  DT_CRIACAO, DT_INICIO, DT_CONCLUSAO,
  STATUS, ETAPA_ATUAL, PERCENTUAL_PROGRESSO,
  QT_RECEBIDOS, QT_VALIDOS, QT_REJEITADOS, QT_ALERTAS, QT_ERROS,
  USUARIO_APROVOU_DADOS, USUARIO_APROVOU_SCRIPT, USUARIO_EXECUTOU
)

MIGRACAO_TEMPLATE_STATUS (ID PK, MIGRACAO_ID FK, TEMPLATE_ID FK, STATUS, ARQUIVO_ORIGEM, HASH_ARQUIVO, DT_IMPORTACAO)

STAGING_BRUTO (ID PK, MIGRACAO_TEMPLATE_STATUS_ID FK, LINHA, DADOS_JSON)

STAGING_NORMALIZADO (ID PK, STAGING_BRUTO_ID FK, DADOS_JSON, DT_PROCESSAMENTO)

VALIDACAO_RESULTADO (
  ID PK, STAGING_NORMALIZADO_ID FK, CAMPO, REGRA,
  CLASSIFICACAO, VALOR_RECEBIDO, VALOR_ESPERADO, MENSAGEM
)

AJUSTE_MANUAL (ID PK, STAGING_NORMALIZADO_ID FK, CAMPO, VALOR_ORIGINAL, VALOR_AJUSTADO, USUARIO, JUSTIFICATIVA, DT_AJUSTE)

CHAVE_GERADA (ID PK, NRORG, CDCONTADOR, NRSEQUENCIAL, MIGRACAO_ID FK, DT_RESERVA)

SCRIPT_GERADO (ID PK, MIGRACAO_ID FK, TEMPLATE_ID FK, ORDEM, CONTEUDO_SQL, CONTEUDO_ROLLBACK, HASH, DT_GERACAO)

EXECUCAO_COMANDO (ID PK, SCRIPT_GERADO_ID FK, SEQUENCIA, COMANDO, STATUS, ERRO, DT_EXECUCAO)

API_DESPACHO (ID PK, MIGRACAO_ID FK, STAGING_NORMALIZADO_ID FK, ENDPOINT, PAYLOAD, CHAVE_IDEMPOTENCIA, STATUS, TENTATIVAS, RESPONSE, DT_ULTIMA_TENTATIVA)

AUDITORIA_EVENTO (ID PK, MIGRACAO_ID FK, USUARIO, ACAO, ENTIDADE, ENTIDADE_ID, DETALHE_JSON, DT_EVENTO)
```

# 15. Principais entidades e relacionamentos

- **Organização** 1—N **Migração**: uma organização pode ter várias migrações ao longo do tempo, mas apenas uma ativa por vez (Seção 4.1).
- **Tipo de Migração** 1—N **Tipo de Migração x Template**: define quais templates, em que ordem, compõem o tipo.
- **Template** 1—N **Metadado de Campo**: cada template tem N campos mapeados.
- **Metadado de Campo** N—N **Template** (via **Campo FK**): um campo pode referenciar outro template (ex. campo "Banco/Agência" do Vínculo referencia o template Agências Bancárias).
- **Migração** 1—N **Migração x Template Status**: acompanha o progresso de cada template dentro da migração.
- **Migração x Template Status** 1—N **Staging Bruto** 1—1 **Staging Normalizado** 1—N **Resultado de Validação**: cadeia de rastreabilidade linha a linha.
- **Staging Normalizado** 1—N **Ajuste Manual**: histórico de correções.
- **Migração** 1—N **Script Gerado** 1—N **Execução de Comando** (Modo Script) **ou** 1—N **Despacho de API** (Modo API).
- **Migração** 1—N **Auditoria Evento**: todo evento relevante do ciclo de vida.
- **Chave Gerada**: associa a migração à reserva de código no serviço central (equivalente a `NOVOCODIGO`), evitando colisão entre migrações concorrentes de organizações distintas que usem o mesmo contador compartilhado (quando aplicável).

# 16. Requisitos funcionais

1. O sistema deve permitir cadastrar organizações, tipos de migração e templates de forma independente e reutilizável.
2. O sistema deve permitir configurar metadados de campo sem necessidade de desenvolvimento de software.
3. O sistema deve aceitar arquivos XLSX e XML, e consumo de API, como fontes de dados na primeira versão.
4. O sistema deve bloquear a criação de nova migração para uma organização que já possua migração ativa, salvo regra explícita de concorrência.
5. O sistema deve armazenar o dado bruto recebido antes de qualquer transformação.
6. O sistema deve aplicar regras de transformação configuráveis (trim, normalização, máscara, conversão de data) antes da validação.
7. O sistema deve validar estrutura, tipo, domínio, relacionamento, tempo e regra de negócio, classificando cada resultado.
8. O sistema deve permitir correção manual, reprocessamento de arquivo ou de etapa, e exportação/reimportação de planilha de inconsistências.
9. O sistema deve exigir aprovação formal dos dados antes da geração de scripts.
10. O sistema deve gerar scripts SQL parametrizados por dialeto de banco, incluindo script de reversão.
11. O sistema deve exigir uma segunda aprovação, por perfil distinto, antes da aplicação dos scripts.
12. O sistema deve registrar sucesso/erro por comando executado e permitir rollback automático em caso de falha.
13. O sistema deve manter uma máquina de estados única e consistente por migração, com histórico de todas as transições.
14. O sistema deve registrar trilha de auditoria completa (quem, quando, o quê, de onde, para onde) para toda ação relevante.
15. O sistema deve suportar, futuramente, o despacho das operações via API em substituição (ou complemento) à geração de script, sem alterar a configuração de metadados existente.
16. O sistema deve permitir consulta e reprocessamento de migrações concluídas com alerta ou com erro.

# 17. Requisitos não funcionais

1. **Desempenho**: processar arquivos de até [a definir com o cliente] linhas em até [a definir] minutos por etapa de validação.
2. **Escalabilidade**: suportar múltiplas migrações simultâneas de organizações distintas sem degradação perceptível.
3. **Disponibilidade**: a camada de API/orquestração deve ter disponibilidade compatível com SLA definido para operações críticas de RH/folha (janelas de migração costumam ser críticas para fechamento de folha).
4. **Segurança**: criptografia em trânsito (TLS) e em repouso para dados pessoais; autenticação via SSO corporativo; autorização por perfil e por ação.
5. **Auditabilidade**: toda ação deve ser reconstituível a partir dos logs, sem dependência de memória do operador.
6. **Extensibilidade**: adicionar um novo template/contexto não deve exigir alteração de código, apenas configuração de metadados.
7. **Observabilidade**: métricas de tempo por etapa, taxa de erro por template, volume processado, disponíveis em dashboard operacional.
8. **Portabilidade de banco de destino**: o gerador de scripts deve suportar múltiplos dialetos sem acoplamento a um único SGBD.
9. **Conformidade**: aderência à LGPD para dados pessoais tratados durante a migração (Seção 12.3).
10. **Usabilidade**: fluxo guiado (wizard) que não exija conhecimento de SQL do operador funcional para conduzir uma migração do início ao fim.

# 18. Critérios de aceite

1. Dado um tipo de migração configurado com N templates em sequência obrigatória, o sistema impede a importação de um template fora de ordem, salvo quando a sequência permitir paralelismo explícito.
2. Dado um arquivo XLSX com cabeçalho divergente do template configurado, o sistema rejeita a importação na validação estrutural, antes de processar qualquer linha.
3. Dado um registro com campo obrigatório vazio, o sistema classifica o resultado como erro impeditivo e impede sua aprovação, mas continua processando os demais registros do lote.
4. Dado um registro que já existe no banco de destino (mesma chave), o sistema não gera um novo `INSERT` duplicado, seguindo a mesma lógica de checagem hoje implementada via `COUNTIF`/aba `Base`.
5. Dado que uma organização possui uma migração em qualquer status ativo, o sistema impede a criação de uma nova migração para a mesma organização, exceto quando o tipo de migração permitir concorrência explicitamente.
6. Dado um lote de scripts gerado, o sistema exige aprovação de um perfil distinto do que aprovou os dados antes de liberar a aplicação.
7. Dada uma falha durante a aplicação de um comando, o sistema registra o erro específico daquele comando, interrompe o lote (ou aplica a política de rollback configurada) e não marca a migração como concluída com sucesso.
8. Dado o encerramento de uma migração, o sistema disponibiliza relatório com contadores de recebidos, válidos, rejeitados, alertas e erros, e a organização volta a poder iniciar uma nova migração.
9. Dado um campo configurado com regra de conversão (ex. remoção de caracteres especiais), o valor original permanece acessível no staging bruto mesmo após a transformação.
10. Dado um novo contexto de migração (ex. "Sindicatos"), é possível configurá-lo integralmente via metadados, sem deploy de código novo, reaproveitando o mesmo motor de validação e gerador de scripts.

# 19. Riscos técnicos e funcionais

| Risco | Tipo | Mitigação sugerida |
|---|---|---|
| Domínios de valores (sexo, estado civil, tipo de dependente, tipo de conta etc.) não estão documentados nos arquivos anexados | Funcional | Levantamento formal de tabelas de domínio junto à equipe funcional antes de configurar as validações de domínio no metadado |
| Padrão atual de "remoção" de aspas simples pode corromper nomes próprios legítimos | Técnico | Substituir por escape correto no gerador de scripts, validado com casos reais de nomes com apóstrofo |
| Dependência de extração manual da aba `Base`/`HCM` antes de cada execução, sujeita a defasagem | Funcional/Técnico | Automatizar a consulta de referência como parte do próprio motor (query de existência executada em tempo real, não colada manualmente) |
| Ausência de checagem de existência prévia no template de Agências Bancárias | Técnico | Padronizar checagem de existência como obrigatória em todo template, sem exceção |
| Ordem de dependência entre templates (Vínculo após Estrutura/Ocupação/Escala/Agências; Dependentes após Vínculo) inferida por engenharia reversa, não documentada formalmente | Funcional | Validar formalmente com a equipe de implantação/funcional antes de tornar a sequência uma regra rígida do sistema |
| Volume elevado de colunas em alguns templates (Vínculo com 224 colunas) pode gerar telas de configuração de metadado complexas | Técnico/UX | Permitir agrupamento de campos por seção temática na tela de configuração (dados pessoais, endereço, dados bancários etc.) |
| Migração de dados sensíveis (CPF, dados bancários, saúde indireta via dependentes) sob LGPD sem base legal formalmente definida | Legal/Compliance | Validar com jurídico/DPO da organização contratante antes de operar em produção com dados reais |
| Evolução para API pode não cobrir 100% dos casos hoje resolvidos via SQL direto, criando dependência híbrida por período indefinido | Técnico/Produto | Priorizar endpoints de API por contexto (começar pelos mais simples: Agências, Ocupação) e manter Modo Script como fallback documentado |
| Concorrência entre migrações de organizações distintas usando o mesmo contador central de PK (`NOVOCODIGO`) | Técnico | Implementar bloqueio otimista/transacional no Key Resolution Service, testado sob carga concorrente |

# 20. Roadmap de implementação por fases

**Fase 0 — Fundação (metadados e staging)**: modelo de dados de controle (Seção 14), cadastro de organizações/tipos de migração/templates, importador XLSX com mapeamento por metadados, staging bruto e normalizado.

**Fase 1 — Motor de validação e correção**: Validation Engine com as seis categorias de regra (Seção 7), console de tratamento de erros, exportação/reimportação de planilha de inconsistências, classificação de severidade.

**Fase 2 — Máquina de estados e governança**: implementação completa dos status (Seção 9), controle de concorrência por organização, segregação de papéis, trilha de auditoria.

**Fase 3 — Gerador de scripts (Modo Script)**: Script Generator para o dialeto prioritário (Oracle), Key Resolution Service central (substituindo `NOVOCODIGO` manual), scripts de reversão, revisão e aprovação em duas etapas.

**Fase 4 — Migração dos seis contextos anexados**: configuração dos templates Agências, Estrutura, Ocupação, Escala, Vínculo e Dependentes como metadados, validando o motor genérico contra o comportamento hoje replicado nas planilhas (testes de regressão comparando saída do motor com saída das fórmulas atuais).

**Fase 5 — Suporte a XML e múltiplos dialetos de banco**: adapter de ingestão XML, geradores de script para PostgreSQL/SQL Server/MySQL.

**Fase 6 — Execução direta e dashboard operacional**: aplicação direta autorizada no banco de destino, dashboard de acompanhamento em tempo real, relatório final consolidado.

**Fase 7 — Evolução para API**: Execution Engine em Modo API para os contextos mais simples primeiro (Agências, Ocupação), com fila, retentativa e idempotência; extensão progressiva aos demais contextos.

**Fase 8 — Formatos adicionais**: CSV, JSON, largura fixa, reaproveitando o mesmo contrato de adapter de ingestão.
# 21. Backlog inicial em épicos e histórias de usuário

**Épico 1 — Cadastro de metadados**
- Como administrador de migração, quero cadastrar um novo template com seus campos, tipos e regras, para poder migrar um novo contexto sem depender de desenvolvimento.
- Como administrador de migração, quero definir chaves primárias e estrangeiras de um template, para que o sistema resolva dependências automaticamente.
- Como administrador de migração, quero versionar um template, para manter compatibilidade com migrações já em andamento quando o template evoluir.

**Épico 2 — Tipos de migração**
- Como administrador, quero compor um tipo de migração a partir de templates existentes, definindo ordem e obrigatoriedade, para padronizar migrações recorrentes.
- Como administrador, quero definir se um tipo de migração permite concorrência entre contextos, para viabilizar paralelismo quando seguro.

**Épico 3 — Execução guiada da migração**
- Como operador, quero criar uma migração selecionando organização e tipo, para iniciar o processo controlado.
- Como operador, quero ser impedido de iniciar uma nova migração se já existir uma ativa para a mesma organização, para evitar conflito de dados.
- Como operador, quero importar os arquivos na ordem exigida, para respeitar as dependências entre contextos.

**Épico 4 — Validação e tratamento de erros**
- Como operador, quero ver os erros por arquivo, linha e coluna, com valor recebido e esperado, para corrigir rapidamente.
- Como operador, quero exportar uma planilha de inconsistências e reimportar apenas os registros corrigidos, para não reprocessar tudo.
- Como aprovador funcional, quero aprovar exceções pontuais com justificativa, para lidar com casos legítimos fora do padrão.

**Épico 5 — Geração e aplicação de scripts**
- Como aprovador funcional, quero aprovar o lote de dados validados, para autorizar a geração de scripts.
- Como aprovador técnico, quero revisar o script gerado antes da aplicação, para garantir que o conteúdo está correto.
- Como executor, quero aplicar os scripts com rollback automático em caso de erro, para garantir consistência do banco de destino.

**Épico 6 — Governança e auditoria**
- Como auditor, quero consultar a trilha completa de uma migração, para verificar conformidade do processo.
- Como administrador, quero configurar perfis e permissões por etapa, para garantir segregação de função.

**Épico 7 — Evolução para API**
- Como arquiteto, quero configurar um template para despachar via API em vez de gerar script, para reduzir dependência de acesso direto ao banco.
- Como operador, quero acompanhar o status de cada registro despachado via API, para saber o que foi confirmado e o que falhou.

# 22. Sugestão de telas e experiência do usuário

1. **Painel inicial**: lista de migrações por organização, com status, percentual de progresso e ações rápidas (continuar, corrigir, aprovar).
2. **Wizard de criação de migração**: passos sequenciais — organização → tipo de migração → operador responsável → checklist de templates obrigatórios.
3. **Tela de upload por template**: indica formato aceito, exemplo de layout esperado, e status de leitura (sucesso/erro estrutural).
4. **Console de validação**: tabela com filtro por severidade (erro/alerta/recomendação), navegável por arquivo/linha/coluna, com edição inline e botão de exportar planilha de pendências.
5. **Tela de comparação de valores**: exibe valor original (staging bruto) versus valor ajustado (staging transformado/corrigido), lado a lado.
6. **Tela de aprovação de dados**: resumo de contadores (válidos/rejeitados/alertas), botão de aprovação com campo de observação obrigatório em caso de exceção.
7. **Tela de revisão de scripts**: visualização do SQL gerado com destaque de sintaxe, contagem de comandos por tabela/operação, botão de aprovação técnica.
8. **Tela de execução**: barra de progresso em tempo real, log de comandos executados com sucesso/erro, botão de rollback manual se necessário.
9. **Relatório final**: consolidado de toda a migração, exportável em PDF/planilha, com todos os contadores e trilha resumida.
10. **Tela de configuração de metadados (perfil administrador)**: editor de template com lista de campos, tipo, regras, PK/FK — pensada para ser usada por equipe de implantação, não apenas por desenvolvimento.

# 23. Exemplos de mensagens de validação

```
[ERRO IMPEDITIVO]
Arquivo: 04_Vinculo.xlsx | Aba: Dados | Linha: 37 | Coluna: J (CPF)
Valor recebido: "123.456.789-0"
Valor esperado: CPF válido com 11 dígitos e dígito verificador correto
Regra violada: validacao_cpf
Orientação: verifique se o CPF foi digitado corretamente; dígito verificador inválido.

[ALERTA]
Arquivo: 03_EscalaTrabalho.xlsx | Aba: Dados | Linha: 112 | Coluna: G (1ª Entrada)
Valor recebido: "8:00"
Valor esperado: formato HH:MM (ex.: 08:00)
Regra violada: formato_hora
Orientação: valor foi aceito, mas recomenda-se ajustar para o formato padrão HH:MM.

[AJUSTE AUTOMÁTICO]
Arquivo: 01_Estrutura.xlsx | Aba: Dados | Linha: 5 | Coluna: H (CNPJ)
Valor original: "03.801.629/0002-00"
Valor ajustado: "03801629000200"
Regra aplicada: remocao_mascara
Orientação: máscara removida automaticamente para gravação; valor original preservado no histórico.

[ERRO IMPEDITIVO — RELACIONAL]
Arquivo: 05_Dependentes.xlsx | Aba: Dados | Linha: 21 | Coluna: B (Nr Vínculo)
Valor recebido: "949999"
Valor esperado: vínculo existente na organização (importado nesta migração ou já presente no destino)
Regra violada: existencia_vinculo
Orientação: importe/valide o template de Vínculo antes de Dependentes, ou confirme o número do vínculo.

[RECOMENDAÇÃO]
Arquivo: 02_Ocupacao.xlsx | Aba: Script | Linha: 8 | Coluna: G (CBO)
Valor recebido: "4141"
Valor esperado: código CBO com 6 dígitos
Regra violada: tamanho_dominio_cbo
Orientação: confirme se o código CBO está completo; formato usual possui 6 dígitos.
```

# 24. Exemplo de configuração de um template

Exemplo simplificado do template **Agências Bancárias**, em JSON, incluindo os pontos de melhoria identificados na Seção 13.4 (checagem de existência e uso de contador central):

```json
{
  "template": {
    "codigo": "AGENCIAS_BANCARIAS",
    "nome": "Agências Bancárias",
    "versao": "1.0",
    "formatos_aceitos": ["XLSX", "API"],
    "aba_obrigatoria": "Dados",
    "campos": [
      {
        "origem": "Banco",
        "destino_tabela": "AGENCIA",
        "destino_coluna": "CDBANCO",
        "tipo": "texto",
        "tamanho_maximo": 3,
        "obrigatorio": true,
        "regra_conversao": "trim",
        "regra_validacao": "codigo_banco_existente",
        "eh_pk": true
      },
      {
        "origem": "Cd. Agência",
        "destino_tabela": "AGENCIA",
        "destino_coluna": "CDAGENCIA",
        "tipo": "texto",
        "tamanho_maximo": 4,
        "obrigatorio": true,
        "regra_conversao": "trim_zero_esquerda",
        "regra_validacao": "duplicidade_no_arquivo,duplicidade_no_destino",
        "eh_pk": true
      },
      {
        "origem": "Agência",
        "destino_tabela": "AGENCIA",
        "destino_coluna": "NMAGENCIA",
        "tipo": "texto",
        "tamanho_maximo": 60,
        "obrigatorio": true,
        "regra_conversao": "trim"
      },
      {
        "origem": "parametro_execucao.NRORG",
        "destino_tabela": "AGENCIA",
        "destino_coluna": "NRORG",
        "tipo": "numerico",
        "obrigatorio": true,
        "valor_padrao": "@contexto.organizacao@"
      }
    ],
    "query_existencia": {
      "descricao": "Verifica se a agência já existe no destino",
      "sql": "SELECT 1 FROM AGENCIA WHERE NRORG = :P_NRORG AND CDBANCO = :CDBANCO AND CDAGENCIA = :CDAGENCIA"
    },
    "operacao_permitida": ["INCLUSAO"],
    "script": {
      "dialeto": "ORACLE",
      "operacao": "INCLUSAO",
      "template_sql": "INSERT INTO AGENCIA ( CDBANCO, CDAGENCIA, NMAGENCIA, NRORG, DTINCLUSAO, CDOPERINCLUSAO, NRORGINCLUSAO, IDATIVO ) VALUES ( '@CDBANCO@', '@CDAGENCIA@', '@NMAGENCIA@', @NRORG@, SYSDATE, '@USUARIO_TECNICO@', @NRORG@, 'S' );",
      "template_rollback": "DELETE FROM AGENCIA WHERE NRORG = @NRORG@ AND CDBANCO = '@CDBANCO@' AND CDAGENCIA = '@CDAGENCIA@';"
    }
  }
}
```

# 25. Exemplo de execução completa de uma migração

Cenário: organização 3260 (número identificado no arquivo de Dependentes anexado como referência de exemplo) inicia uma migração do tipo `MIG_HCM_ONBOARDING`.

1. Operador cria a migração para a organização 3260; sistema confirma ausência de migração ativa e move o status para `aguardando arquivos`.
2. Operador importa `00_Agencias_Bancarias.xlsx` → validação estrutural OK → validação de dado OK → sem erro impeditivo → template marcado como `validado`.
3. Operador importa `01_Estrutura_v12.xlsx` → validação relacional identifica que o código de município "VARGINHA/MG" existe na tabela de apoio → validação de negócio confirma que endereço só será inserido para linhas com tipo de endereço e logradouro preenchidos → duas linhas geram alerta de sindicato sem domínio confirmado (`CDSINDICAL` não encontrado na tabela de apoio) → migração muda para `com inconsistências`.
4. Operador corrige o código de sindicato das duas linhas em alerta na interface, reprocessa apenas a validação relacional → sem novos erros impeditivos → status volta a `em validação` e, na sequência, `aguardando aprovação` (Estrutura).
5. Processo se repete para `02_Ocupação`, `03_EscalaTrabalho` (uma linha em alerta por formato de hora fora do padrão, ajustada automaticamente) e `04_Vinculo` (motor confirma existência prévia de Banco/Agência, Estrutura, Ocupação e Escala referenciados antes de validar cada vínculo).
6. Operador importa `05_Dependentes_v12.xlsx` → motor confirma, para cada linha, que o `Nr. Vínculo` informado já existe entre os vínculos desta migração ou no destino → uma linha é rejeitada por referenciar um vínculo inexistente (erro impeditivo, relacional) → operador corrige o número do vínculo e reimporta apenas essa linha.
7. Aprovador funcional revisa os contadores finais (ex.: 812 registros recebidos, 806 válidos, 6 rejeitados, 14 alertas) e aprova os dados → status `pronta para geração de scripts`.
8. Sistema gera os scripts na ordem de dependência (Agências → Estrutura → Ocupação → Escala → Vínculo → Dependentes), resolvendo PKs via Key Resolution Service e gerando também os scripts de reversão → status `scripts gerados`.
9. Aprovador técnico revisa o conteúdo do SQL gerado (contagem de comandos por tabela, amostra de `INSERT`s) e aprova a aplicação → status `aguardando aplicação`.
10. Executor aplica os scripts em lotes de 200 comandos, com commit por lote → um lote de Vínculo falha por violação de constraint de FK em `NRESTRUTURAM` (erro impeditivo não detectado na validação relacional por mudança concorrente no destino) → sistema executa rollback do lote falho, mantém os lotes anteriores já commitados, marca a migração como `com erro`.
11. Equipe técnica investiga a causa raiz, corrige o dado de origem, reprocessa apenas o lote afetado → aplicação concluída com sucesso → status `concluída com alertas` (por conta dos ajustes automáticos e do lote reprocessado).
12. Sistema executa validação pós-migração (reexecuta a consulta de referência equivalente à aba `Base`) confirmando presença de todos os registros aprovados no destino, gera relatório final e libera a organização 3260 para uma nova migração.

---

# 26. Planilhas adicionais da migração integral do cliente

As seções anteriores documentaram os cinco templates cadastrais/estruturais originalmente analisados (Agências Bancárias, Estrutura, Ocupação, Escala de Trabalho e Vínculo). Esta seção complementa o levantamento com as oito planilhas adicionais fornecidas em uma segunda rodada, que hoje compõem, junto às cinco primeiras, o conjunto completo de treze planilhas efetivamente utilizado em uma **migração integral de um cliente**: cadastro inicial, movimentações funcionais e histórico financeiro.

## 26.1 Enquadramento no fluxo de migração integral

As oito planilhas adicionais dividem-se em três grupos funcionais, todos dependentes do cadastro inicial (Agências, Estrutura, Ocupação, Escala, Vínculo) já coberto nas seções anteriores:

1. **Movimentações funcionais do vínculo** — alterações pontuais aplicadas sobre um vínculo já existente: Alteração Salarial (06), Alteração de Escala (07), Alteração de Ocupação (08), Situação Funcional/afastamentos (09), Férias (10) e Movimentações de Estrutura/transferências (12). Todas dependem de o Vínculo (04) já estar migrado.
2. **Catálogo de eventos de folha** — Eventos (11), que não migra dados de um funcionário específico, mas sim o catálogo de rubricas de folha de pagamento (proventos/descontos) e o mapeamento "de-para" entre o código do cliente e o código interno do HCM.
3. **Histórico financeiro** — Ficha Financeira (13), que carrega o histórico de valores de proventos/descontos por competência e vínculo, e depende tanto do Vínculo quanto do catálogo de Eventos (para resolver o código de rubrica) e de um cálculo de folha (`FPA_CALCULOFOLHA`) já existente no destino.

Isso eleva o total de templates de uma migração integral de 5 para 13, e introduz, pela primeira vez no conjunto de arquivos analisados, dois padrões estruturais novos: uma planilha com **relação um-para-N** dentro da mesma linha (Férias) e uma planilha de **catálogo/de-para** que não representa um registro transacional de funcionário (Eventos).

## 26.2 Achados por arquivo

**06_AlteracaoSalarial_v12.xlsx** (identificado diretamente): aba `Dados` com colunas `Nr Vinculo`, `Dt. Alteração`, `Numero Ocorrencia`, `Tipo Alteração`, `Salário`, `Tipo Salário` e `Observação`. Gera um único `INSERT INTO GPE_ALTESALARIO`, com o vínculo resolvido por subquery em `GPE_VINCULOM` a partir da matrícula, e o campo `DSOBSERVACAO` com `NVL` para um texto padrão quando vazio. A planilha bloqueia explicitamente linhas com salário vazio ou zerado ("Verificação Sal. Zerado") e possui uma checagem de deduplicação ("mesc") contra alterações já existentes no destino — nenhuma das duas está automatizada além de fórmulas de planilha, ambas propostas como validações de metadado (obrigatoriedade de `VRSALARIO` e regra de deduplicação por vínculo+data+ocorrência).

**07_Alteracao de Escala_v10.xlsx**: o arquivo de maior volume real entre todos os treze — 3.587 linhas de dados de produção na aba `Dados`, além de abas `Base`, `Script` e `prototipo 2`. Gera `GPE_ALTEESCALA` a partir de `Nr Vinculo`, `Dt Alteracao` e `Escala` (referência direta ao código já migrado pela planilha 03). **Particularidade identificada diretamente**: a fórmula de geração do script não é uma fórmula de planilha nativa, e sim uma chamada a uma função de macro/suplemento customizado (`MIG_GERA.SCRIPT`), o que a diferencia de todas as demais planilhas do lote e confirma que o processo real, hoje, depende de um add-in do Excel específico do ambiente de migração — não apenas de fórmulas portáveis. O volume real desta planilha é a melhor evidência disponível para dimensionar o processamento em lote (Seção 22) a um caso concreto de produção.

**08_AlteracaoOcupacao_v11.xlsx**: aba `Dados` com 835 linhas reais. Gera `GPE_ALTEOCUPACAO` a partir de `Nr Vinculo`, `Dt Alteracao` e `Ocupacao` (código de integração), ambos resolvidos por subquery — vínculo em `GPE_VINCULOM`, ocupação em `GPE_OCUPACAOH` por `CDINTEGRACAO`. Validações de existência de vínculo e de ocupação, com contagem de "vínculos afetados pela ausência de ocupação" — sinal de que a ordem de carga (Ocupação antes de Alteração de Ocupação) é tratada hoje apenas por disciplina manual do operador, não por travamento automático.

**09_SituacaoFuncional_v07.xlsx**: gera `GPE_ALTESITUFUNC` (afastamentos e situações funcionais) a partir de `Nr Vinculo`, código de situação funcional, datas de início/fim e, quando aplicável, tabela e código de diagnóstico (`CDTABECDI`/`CDDIAGNOST`, ex. CID-10) — **dado de saúde sensível**, que deve ser tratado com as mesmas salvaguardas de LGPD já descritas na Seção 12 para os dados pessoais de Vínculo, e não apenas como um campo de texto genérico.

**10_Ferias_(padrão)_v07.xlsx**: a planilha estruturalmente mais distinta do lote — 2.162 linhas reais, aba `Dados` com 50 colunas. **Identificado diretamente**: cada linha pode gerar até dois `INSERT` em tabelas diferentes e relacionadas — um período aquisitivo (`FPA_FERIAS`) e, condicionalmente, um período de gozo associado (`FPA_GOZOFERIAS`, cuja PK referencia a PK recém-gerada de `FPA_FERIAS`) — com deduplicação por hash calculada separadamente para cada uma das duas tabelas, de forma a não reinserir períodos já migrados. É o único template do conjunto de treze com uma relação **um-para-N dentro da própria linha de origem**, o que não é coberto pelo modelo de metadados genérico atual (Seção 6), pensado para um template gerar um conjunto fixo de INSERTs por linha, e não uma quantidade condicional. Recomenda-se que o modelo de metadados evolua para suportar "blocos condicionais" de INSERT por template.

**11_Eventos_v08_.xlsx**: também estruturalmente distinta — não migra dados de um funcionário, e sim o catálogo de eventos de folha (proventos/descontos) e a tabela de mapeamento `MIG_MIGRAMDEPARA`, usada para traduzir o código de rubrica do cliente para o código interno do HCM. **Identificado diretamente**: a lógica é condicional por linha — se a coluna "Nr Evento Pebbian" (código já existente no HCM) estiver vazia, a planilha entende que o evento é novo e gera `INSERT` em `FPA_EVENTOM`/`FPA_EVENTOH`; se estiver preenchida, apenas o de-para é gerado, reaproveitando o evento já existente. Esta planilha é pré-requisito funcional da Ficha Financeira (13), que depende de `MIG_MIGRAMDEPARA` já povoada para resolver o código de evento de cada lançamento histórico — uma dependência que não existia entre nenhum dos demais templates analisados até aqui, pois aqui uma planilha de **catálogo/parametrização** (não de dados de funcionário) se torna pré-requisito de uma planilha de **movimentação**.

**12_MovimentacoesEstrutura_v07.xlsx**: gera `GPE_MOVIMENTACAO` (histórico de transferências de estrutura/centro de custo de um vínculo), a partir de `Nr Vínculo`, tipo e motivo de transferência, e `Nr Estrutura` (resolvido por subquery contra `ESTRUTURAM`, referenciando a planilha 01 já migrada). Depende de Vínculo e de Estrutura simultaneamente — o segundo template do lote, junto de Ficha Financeira, a depender de mais de um template cadastral ao mesmo tempo.

**13_FichaFinanceira_v15.xlsx**: a planilha com a dependência mais crítica de todo o conjunto. Gera `FPA_ITECALCFOLHA` (itens individuais de cálculo de folha — valores de proventos/descontos por competência), mas **cada INSERT depende de um "cálculo de folha" (`FPA_CALCULOFOLHA`) já existente no destino** para a mesma organização, tipo de movimento e competência — um registro que não é criado por nenhuma das treze planilhas migradas, e sim por um processo de folha de pagamento externo à migração. A própria planilha original inclui uma consulta de verificação e outra de criação desse cabeçalho (mesclando MERGE contra `NOVOCODIGO`), que hoje precisam ser executadas manualmente, fora do fluxo de scripts gerados pela planilha, antes da carga dos itens. **Risco identificado diretamente**: se a plataforma não expuser esse pré-requisito de forma explícita na tela de configuração do template (Seção 8), a aplicação do script de Ficha Financeira falhará silenciosamente ou retornará `NRCALCULOFOLHA` nulo em produção. A planilha real ainda oferece quatro variantes de template de INSERT (combinando identificação de vínculo por matrícula ou por número interno, e de evento por código de-para ou por número interno — aba `Scripts`), evidenciando que a resolução de chaves de negócio versus chaves internas é uma decisão de configuração por cliente, não uma constante do template.

## 26.3 Dependências entre as treze planilhas

O grafo de dependências completo, consolidando as cinco planilhas originais e as oito adicionais, é:

| Template | Depende de |
|---|---|
| Agências Bancárias | — |
| Estrutura | — |
| Ocupação | — |
| Escala de Trabalho | — |
| Eventos (catálogo) | — |
| Vínculo | Agências, Estrutura, Ocupação, Escala |
| Alteração Salarial | Vínculo |
| Alteração de Escala | Vínculo, Escala de Trabalho |
| Alteração de Ocupação | Vínculo, Ocupação |
| Situação Funcional | Vínculo |
| Férias | Vínculo |
| Movimentações de Estrutura | Vínculo, Estrutura |
| Ficha Financeira | Vínculo, Eventos, **cálculo de folha pré-existente (fora da migração)** |

Esta tabela é a base do tipo de migração "Migração Integral do Cliente — Implantação Completa" descrito na Seção 26.5, na variante com sequência obrigatória.

## 26.4 Padrões novos identificados (não presentes nas cinco planilhas originais)

- **Relação um-para-N por linha de origem** (Férias): uma linha da planilha pode gerar de zero a dois `INSERT`, cada um com sua própria PK e sua própria checagem de deduplicação. O modelo de metadados da Seção 6 deve evoluir para declarar, por template, quais blocos de INSERT são condicionais e qual a condição de disparo de cada um.
- **Template de catálogo/de-para** (Eventos): nem todo template representa dados de um funcionário — alguns representam parametrização compartilhada por toda a organização, que outros templates consultam por FK. O metadado de template deve distinguir explicitamente "template de dados transacionais" de "template de catálogo/parametrização".
- **Pré-requisito externo à migração** (Ficha Financeira): a primeira ocorrência, no conjunto de treze planilhas, de uma dependência que não é outro template de migração, e sim um dado que precisa existir previamente no sistema de destino por um processo de negócio diferente (fechamento de folha). O metadado de template deve permitir declarar pré-requisitos externos, com uma query de verificação associada, para que a plataforma alerte o operador antes da geração do script em vez de falhar na aplicação.
- **Geração de script via macro/suplemento customizado** (Alteração de Escala): confirma que nem todo o conhecimento de geração de script hoje está em fórmulas de planilha portáveis — parte dele está em código de suplemento do Excel específico do ambiente de migração, o que reforça a proposta da Seção 11 de migrar esse conhecimento para o motor central da plataforma.

## 26.5 Tipo de migração "Migração Integral do Cliente"

Consolidando os treze templates, dois novos tipos de migração foram definidos, seguindo o mesmo par já existente para o cadastro inicial (Seção 5.1):

- **Migração Integral do Cliente — 13 Templates (importação individual)**: sem sequência obrigatória, indicada para operação corrente pós-implantação (ex.: aplicar apenas um lote de Férias ou de Alteração Salarial, sem tocar nos demais templates).
- **Migração Integral do Cliente — Implantação Completa (sequência travada)**: aplica o grafo de dependências da Seção 26.3 como travamento de sequência, indicada para a implantação inicial de um cliente novo, quando a ordem de carga é crítica para a integridade referencial.

Ambos os tipos foram incorporados ao protótipo navegável (Seção 22), incluindo uma migração de demonstração que exercita simultaneamente as treze planilhas, com geração de SQL real (motor genérico orientado por metadados, mais fiel ao padrão observado nas planilhas originais) para as oito planilhas adicionadas nesta rodada.

# Anexo A — Proposta de arquitetura técnica

Ver Seção 3 para a descrição textual completa. Resumo em camadas:

```
┌───────────────────────────────────────────────────────────────┐
│                     Portal de Migração (Web)                  │
│  Config. de Metadados | Wizard de Migração | Console de Erros │
│  Aprovação | Dashboard de Acompanhamento                       │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTPS / REST
┌───────────────────────────────▼─────────────────────────────────┐
│                    API de Orquestração (Gateway)                │
└───────────────────────────────┬─────────────────────────────────┘
                                 │
        ┌────────────────────────┼──────────────────────────┐
        ▼                        ▼                            ▼
┌───────────────┐      ┌──────────────────┐        ┌────────────────────┐
│ Adapters de   │      │ Metadata Resolver │        │ Key Resolution     │
│ Ingestão      │      │ + Transformation  │        │ Service            │
│ XLSX/XML/API  │      │ Engine            │        │ (equiv. NOVOCODIGO)│
└───────┬───────┘      └─────────┬─────────┘        └──────────┬─────────┘
        │                        ▼                              │
        │              ┌──────────────────┐                     │
        └─────────────▶│ Validation Engine │◀────────────────────┘
                        └─────────┬─────────┘
                                  ▼
                       ┌─────────────────────┐
                       │   Staging (DB próprio)│
                       └─────────┬─────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   Script Generator     │
                     │ (multi-dialeto SQL)    │
                     └──────────┬─────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   Execution Engine     │
                     │  Modo Script | Modo API │
                     └──────────┬─────────────┘
                                 ▼
              ┌──────────────────────────────────────┐
              │   Banco de destino ERP/HCM  /  APIs   │
              └──────────────────────────────────────┘
```

Todas as camadas emitem eventos para o **Módulo de Auditoria**, persistidos de forma centralizada e imutável.

# Anexo B — Modelo conceitual de banco de dados

Ver Seção 14 para o DDL conceitual completo do esquema de staging/controle da plataforma. As entidades centrais são `MIGRACAO`, `TEMPLATE`, `TEMPLATE_METADADO_CAMPO`, `STAGING_BRUTO/NORMALIZADO`, `VALIDACAO_RESULTADO`, `SCRIPT_GERADO`/`EXECUCAO_COMANDO` e `AUDITORIA_EVENTO`, conforme detalhado na Seção 15.

# Anexo C — Sugestão de APIs

```
POST   /organizacoes
GET    /organizacoes/{nrOrg}/migracoes-ativas

POST   /tipos-migracao
POST   /tipos-migracao/{id}/templates

POST   /templates
POST   /templates/{id}/campos

POST   /migracoes                          { nrOrg, tipoMigracaoId, operadorId }
GET    /migracoes/{id}
GET    /migracoes/{id}/status
POST   /migracoes/{id}/templates/{templateId}/arquivos     (multipart upload)
POST   /migracoes/{id}/templates/{templateId}/validar
GET    /migracoes/{id}/inconsistencias
POST   /migracoes/{id}/inconsistencias/{itemId}/corrigir
POST   /migracoes/{id}/aprovar-dados
POST   /migracoes/{id}/gerar-scripts
GET    /migracoes/{id}/scripts
POST   /migracoes/{id}/aprovar-aplicacao
POST   /migracoes/{id}/aplicar
GET    /migracoes/{id}/execucao/status
POST   /migracoes/{id}/rollback
GET    /migracoes/{id}/relatorio-final
GET    /migracoes/{id}/auditoria

# Evolução — Modo API
POST   /migracoes/{id}/despacho-api/iniciar
GET    /migracoes/{id}/despacho-api/status
POST   /migracoes/{id}/despacho-api/reprocessar/{registroId}
```

# Anexo D — Máquina de estados da migração

Ver Seção 9 (diagrama completo e tabela de transições/responsáveis).

# Anexo E — Exemplo de metadados em JSON

Ver Seção 24 (template completo de Agências Bancárias). Estrutura geral do contrato de metadado, reaplicável a qualquer template:

```json
{
  "origem": "string",
  "destino_tabela": "string",
  "destino_coluna": "string",
  "tipo": "texto|numerico|data|hora|monetario|percentual|booleano",
  "tamanho_maximo": "number|null",
  "obrigatorio": "boolean",
  "valor_padrao": "any|null",
  "regra_conversao": "string|array",
  "regra_validacao": "string|array",
  "eh_pk": "boolean",
  "gerador_pk": "boolean",
  "chaves_estrangeiras": [{ "template_referenciado": "string", "campo_referenciado": "string" }],
  "operacao_permitida": ["INCLUSAO", "ALTERACAO", "EXCLUSAO"]
}
```

# Anexo F — Exemplo de mapeamento XLSX/XML para banco de dados

**XLSX** (arquivo `00_Agencias_Bancarias.xlsx`, aba `Dados`, colunas A–C):

| Coluna XLSX | Campo metadado | Tabela.Coluna destino |
|---|---|---|
| A (`Banco`) | CDBANCO | AGENCIA.CDBANCO |
| B (`Cd. Agência`) | CDAGENCIA | AGENCIA.CDAGENCIA |
| C (`Agência`) | NMAGENCIA | AGENCIA.NMAGENCIA |
| Célula fixa D1 | NRORG (parâmetro de execução) | AGENCIA.NRORG |

**XML equivalente** (formato de entrada futuro para o mesmo template):

```xml
<agencias nrOrg="1410">
  <agencia>
    <banco>001</banco>
    <codigoAgencia>0019</codigoAgencia>
    <nomeAgencia>0019</nomeAgencia>
  </agencia>
</agencias>
```

Mapeamento: `/agencias/@nrOrg` → `AGENCIA.NRORG`; `/agencias/agencia/banco` → `AGENCIA.CDBANCO`; `/agencias/agencia/codigoAgencia` → `AGENCIA.CDAGENCIA`; `/agencias/agencia/nomeAgencia` → `AGENCIA.NMAGENCIA`. O mesmo registro de metadado de campo (Seção 6) serve para ambos os formatos: apenas o atributo `origem` muda de sintaxe (referência de coluna XLSX versus XPath), enquanto tipo, obrigatoriedade, regra de conversão/validação e destino permanecem idênticos — este é o ponto central que torna o motor agnóstico de formato de entrada.

# Anexo G — Pseudocódigo do motor de validação

```
função validarRegistro(registro, template, contextoMigracao):
    resultados = []

    // 1. Validação de tipo/obrigatoriedade por campo
    para cada campoMeta em template.campos:
        valor = registro[campoMeta.origem]
        valorTransformado = aplicarConversao(valor, campoMeta.regra_conversao)

        se campoMeta.obrigatorio e valorTransformado é vazio:
            resultados.adicionar(ERRO_IMPEDITIVO, campoMeta, valor, "obrigatoriedade")
            continuar

        se não validarTipo(valorTransformado, campoMeta.tipo, campoMeta.tamanho_maximo):
            resultados.adicionar(ERRO_IMPEDITIVO, campoMeta, valor, "tipo_invalido")
            continuar

        se campoMeta.regra_validacao existe:
            para cada regra em campoMeta.regra_validacao:
                resultado = aplicarRegraValidacao(regra, valorTransformado, contextoMigracao)
                resultados.adicionar(resultado.classificacao, campoMeta, valor, regra, resultado.mensagem)

    // 2. Validação relacional / dependências
    para cada fk em template.chaves_estrangeiras:
        existeNoStagingDestaMigracao = buscarNoStaging(contextoMigracao, fk.template_referenciado, fk.valor)
        existeNoDestino = buscarNoDestino(fk.template_referenciado, fk.valor, contextoMigracao.nrOrg)
        se não existeNoStagingDestaMigracao e não existeNoDestino:
            resultados.adicionar(ERRO_IMPEDITIVO, fk, fk.valor, "existencia_referencia")

    // 3. Validação de duplicidade (equivalente ao COUNTIF contra aba Base)
    se existeDuplicidadeNoArquivo(registro, template) ou existeDuplicidadeNoDestino(registro, template, contextoMigracao):
        resultados.adicionar(ERRO_IMPEDITIVO, template.pk, registro[template.pk], "duplicidade")

    // 4. Validações temporais e de negócio (regras específicas do template)
    resultados.adicionarTodos( aplicarRegrasDeNegocio(registro, template, contextoMigracao) )

    retornar resultados


função processarLote(arquivoLido, template, contextoMigracao):
    validarEstruturaArquivo(arquivoLido, template)   // cabeçalhos, aba, encoding, schema

    para cada linha em arquivoLido.linhas:
        persistirStagingBruto(linha, contextoMigracao)
        registroNormalizado = normalizar(linha, template)
        persistirStagingNormalizado(registroNormalizado, contextoMigracao)
        resultados = validarRegistro(registroNormalizado, template, contextoMigracao)
        persistirResultadosValidacao(resultados)

    atualizarContadores(contextoMigracao)
    se não existeErroImpeditivoPendente(contextoMigracao):
        transicionarStatus(contextoMigracao, "aguardando aprovação")
    senão:
        transicionarStatus(contextoMigracao, "com inconsistências")
```

# Anexo H — Pseudocódigo do gerador de scripts

```
função gerarScripts(contextoMigracao):
    scripts = []
    templatesOrdenados = ordenarPorDependencia(contextoMigracao.tipoMigracao.templates)

    para cada template em templatesOrdenados:
        registrosAprovados = buscarStagingAprovado(contextoMigracao, template)

        para cada registro em registrosAprovados:
            para cada tabelaDestino em template.tabelasDestino:

                se tabelaDestino.gerador_pk:
                    chave = KeyResolutionService.reservarProximoCodigo(
                                contextoMigracao.nrOrg, tabelaDestino.contador)
                    registro[tabelaDestino.campoPk] = chave

                se ExisteNoDestino(tabelaDestino, registro, contextoMigracao.nrOrg):
                    continuar   // idempotência: não duplica

                comandoSql = montarComando(
                                template.scriptTemplate[tabelaDestino],
                                registro,
                                contextoMigracao)
                comandoRollback = montarComando(
                                template.scriptTemplateRollback[tabelaDestino],
                                registro,
                                contextoMigracao)

                scripts.adicionar({
                    tabela: tabelaDestino,
                    comando: comandoSql,
                    rollback: comandoRollback,
                    origem: registro.id
                })

    scriptsAgrupados = agruparEmLotes(scripts, tamanhoMaximoLote = 200)
    persistirScriptGerado(contextoMigracao, scriptsAgrupados)
    transicionarStatus(contextoMigracao, "scripts gerados")
    retornar scriptsAgrupados


função montarComando(templateTexto, registro, contextoMigracao):
    comando = templateTexto
    para cada campoMeta em registro.campos:
        marcador = "@" + campoMeta.nome + "@"
        valorFormatado = formatarPorDialeto(registro[campoMeta.nome], campoMeta.tipo, contextoMigracao.dialetoBanco)
        comando = substituir(comando, marcador, valorFormatado)
    comando = substituir(comando, "@NRORG@", contextoMigracao.nrOrg)
    comando = substituir(comando, "@USUARIO_TECNICO@", contextoMigracao.usuarioTecnico)
    retornar comando


função aplicarScripts(contextoMigracao, scriptsAgrupados):
    para cada lote em scriptsAgrupados:
        iniciarTransacao()
        tentar:
            para cada comando em lote:
                resultado = executar(comando.comando)
                registrarExecucao(comando, resultado)
            commit()
        capturar erro:
            rollback()
            registrarErro(lote, erro)
            transicionarStatus(contextoMigracao, "com erro")
            interromper

    se todosLotesComSucesso:
        transicionarStatus(contextoMigracao, "concluída")
    senão se existemApenasAlertas:
        transicionarStatus(contextoMigracao, "concluída com alertas")
```

# Anexo I — Conjunto inicial de critérios de aceite

Ver Seção 18 para a lista completa e numerada (10 critérios), cobrindo sequenciamento de templates, validação estrutural, obrigatoriedade, idempotência, bloqueio de concorrência, segregação de aprovação, tratamento de falha de aplicação, relatório final, rastreabilidade de transformação e extensibilidade por metadados sem novo código.

# Anexo J — Estratégia de MVP e evolução do produto

**Escopo do MVP**: cobrir exatamente os seis contextos anexados (Agências Bancárias, Estrutura, Ocupação, Escala de Trabalho, Vínculo, Dependentes), para uma única organização por vez, com:

- importador XLSX orientado por metadados (sem XML/API ainda);
- motor de validação com as seis categorias de regra, mas com domínios de valores limitados aos que puderem ser confirmados com a equipe funcional antes do início do desenvolvimento (Seção 19, risco 1);
- staging com rastreabilidade de dado bruto/normalizado/aprovado;
- console de tratamento de erros com exportação/reimportação de planilha;
- máquina de estados completa e bloqueio de concorrência por organização;
- gerador de scripts Oracle (único dialeto necessário para os seis contextos anexados) com script de reversão;
- aplicação manual do `.sql` gerado fora da plataforma (sem execução automática ainda), reduzindo risco na primeira operação em produção;
- trilha de auditoria básica (quem fez o quê, quando).

**Critério de saída do MVP**: o motor genérico reproduz, para os seis contextos anexados, o mesmo resultado de script hoje gerado pelas planilhas (validado por comparação direta em ambiente de homologação), com o ganho adicional de validação estruturada, staging auditável e bloqueio de concorrência — sem que nenhuma lógica de contexto tenha sido escrita em código, apenas em metadados.

**Evolução pós-MVP**: aplicação direta no banco (Fase 6), suporte a XML e múltiplos dialetos (Fase 5), dashboard operacional, e finalmente a camada de despacho via API (Fase 7), iniciando pelos contextos mais simples (Agências, Ocupação) antes de estender a Vínculo e Dependentes, que são os mais complexos e mais dependentes de regras de negócio da camada de aplicação do HCM.
