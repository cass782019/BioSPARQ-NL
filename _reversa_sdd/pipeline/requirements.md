# Requisitos — pipeline

> Unit: `src/pipeline/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `pipeline` |
| Caminho legado | `src/pipeline/nl_to_sparql.py`, `src/pipeline/sparql_validator.py`, `src/pipeline/llm_backends.py`, `src/pipeline/entity_linker.py` |
| Responsabilidade | Orquestração completa do fluxo NL→SPARQL: NER, few-shot RAG, geração LLM, pós-processamento, validação de schema e loop de autocorreção |
| Complexidade | 🔴 Alta |

---

## Requisitos Funcionais

### RF-01 — Tradução de pergunta NL para SPARQL executável
🟢 **CONFIRMADO** — `nl_to_sparql.py:run()`

**Must**

Dado uma pergunta em linguagem natural (português), o pipeline deve produzir uma query SPARQL válida e executável contra o triplestore Fuseki.

**Critérios de Aceitação:**

```gherkin
Dado que o pipeline está inicializado com Fuseki e LLM backend disponíveis
Quando run("Quais doenças estão associadas ao fenótipo febre?") é chamado
Então o resultado contém campo "sparql" não-vazio
E o resultado contém campo "success" = True
E o resultado contém "results_count" >= 1
```

```gherkin
Dado que o LLM gera uma query com erro de sintaxe na primeira tentativa
Quando run() executa o loop de autocorreção
Então o pipeline re-prompta o LLM com feedback de validação
E tenta novamente até max_retries + 2 vezes no total
```

---

### RF-02 — Loop de autocorreção com até 4 tentativas
🟢 **CONFIRMADO** — `nl_to_sparql.py:run()` — `max_attempts = max_retries + 2`

**Must**

O pipeline deve tentar corrigir automaticamente queries inválidas re-promtando o LLM com feedback estruturado dos erros de validação.

**Critérios de Aceitação:**

```gherkin
Dado que max_retries = 2 (padrão)
Então max_attempts = 4 tentativas totais
E cada tentativa fracassada inclui o feedback de validação no próximo prompt
E na última tentativa, query inválida é executada mesmo assim (DONE_INVALID_FORCED)
```

---

### RF-03 — Pós-processamento SPARQL (9 transformações regex)
🟢 **CONFIRMADO** — `nl_to_sparql.py:_fix_common_errors()`

**Must**

Antes de validar, o SPARQL gerado pelo LLM deve ser corrigido automaticamente por 9 transformações sequenciais para erros comuns de alucinação.

**Critérios de Aceitação:**

```gherkin
Dado que o LLM gerou "PREFIX doid: <urn:doid>" (prefixo inválido)
Quando _fix_common_errors() é chamado
Então a declaração PREFIX inválida é removida
E a query resultante não contém "PREFIX doid:"

Dado que o LLM gerou "FILTER (?label = 'fever')" após o "}"
Quando _fix_common_errors() é chamado
Então o FILTER é movido para dentro do bloco WHERE
```

---

### RF-04 — Injeção automática de prefixos faltantes
🟢 **CONFIRMADO** — `nl_to_sparql.py:_inject_missing_prefixes()`

**Should**

Se a query usa um prefixo conhecido (rdf, rdfs, obo, oboInOwl, hpoa, etc.) sem declará-lo, o pipeline deve injetá-lo automaticamente no início da query.

---

### RF-05 — Recuperação de exemplos few-shot via FAISS
🟢 **CONFIRMADO** — `nl_to_sparql.py:retrieve_examples()`

**Must**

O pipeline deve recuperar os `top_k` exemplos mais similares do gold standard (FAISS cosine similarity) e incluí-los no prompt para guiar o LLM.

**Critérios de Aceitação:**

```gherkin
Dado que o FAISS index está carregado com 30 questões
Quando retrieve_examples("febre") é chamado com top_k=3
Então retorna uma lista de 3 dicts com campos "question" e "sparql"
E os exemplos são ordenados por similaridade decrescente
```

```gherkin
Dado que data/gold_standard/questions.index está ausente
Quando o pipeline é inicializado
Então retrieve_examples() retorna [] sem lançar exceção
E o pipeline funciona em modo zero-shot
```

---

### RF-06 — Semantic retry para query válida com 0 resultados
🟢 **CONFIRMADO** — `nl_to_sparql.py:run()` — flag `semantic_retry_used`

**Should**

Quando uma query é sintaticamente válida mas retorna 0 resultados, o pipeline deve re-promptar o LLM uma única vez com orientações semânticas (labels em inglês, conversão MIM→OMIM).

**Critérios de Aceitação:**

```gherkin
Dado que a query é válida e Fuseki retorna 0 resultados
E semantic_retry_used = False
Quando execute_sparql() detecta count == 0
Então pipeline re-prompta com SEMANTIC_RETRY_FEEDBACK
E semantic_retry_used = True (não repete)
```

---

### RF-07 — Validação de schema SPARQL antes da execução
🟢 **CONFIRMADO** — `sparql_validator.py:SchemaValidator.validate()`

**Must**

Toda query gerada deve ser validada antes de ser enviada ao Fuseki. A validação verifica: sintaxe, operações unsafe (DELETE/INSERT), grafos nomeados válidos, prefixos e termos ontológicos.

---

### RF-08 — Bloqueio de operações de escrita (DELETE/INSERT)
🟢 **CONFIRMADO** — `sparql_validator.py` — `UNSAFE_OPERATION` check

**Must**

O pipeline nunca deve permitir que queries contendo DELETE, INSERT ou UPDATE cheguem ao Fuseki.

**Critérios de Aceitação:**

```gherkin
Dado qualquer query contendo "DELETE" ou "INSERT"
Quando SchemaValidator.validate() é chamado
Então valid=False e errors contém "UNSAFE_OPERATION"
E a query não é enviada ao Fuseki
```

---

### RF-09 — Graceful degradation quando componentes estão ausentes
🟢 **CONFIRMADO** — `nl_to_sparql.py:__init__()` — fallbacks

**Must**

O pipeline deve inicializar e funcionar mesmo que componentes opcionais estejam indisponíveis:
- FAISS index ausente → zero-shot (sem exemplos)
- NER falha → continua sem entidades
- schemas.json ausente → modo permissivo (só sintaxe) + **log.warning obrigatório**

**Nota (validada por ablação 2026-05-05):** a ausência de `schemas.json` reduz a taxa de execução no Fuseki em ~16.7pp (queries sintaticamente válidas mas semanticamente erradas chegam ao endpoint). Manter como warning, não erro fatal — correctness cai apenas 3.3pp.

---

### RF-10 — Backend LLM plugável
🟢 **CONFIRMADO** — `llm_backends.py` — `LMStudioBackend`, `AnthropicBackend`

**Must**

O pipeline deve suportar backends LLM intercambiáveis sem alterar a lógica de orquestração. Interface: `generate(system: str, user_msg: str) → str`.

---

## Requisitos Não Funcionais

### RNF-01 — Latência de geração
🟡 **INFERIDO** — timeout de 300s configurado para LLM

O timeout padrão de 300s para o LLM implica que latências acima desse valor são consideradas falha. Para uso interativo via frontend, latências > 60s degradam a experiência.

### RNF-02 — Timeout do Fuseki
🟢 **CONFIRMADO** — `config['fuseki_timeout'] = 30`

Queries SPARQL que não respondem em 30s são consideradas timeout e resultam em falha.

### RNF-03 — Retry do backend LLM
🟢 **CONFIRMADO** — `llm_backends.py:LMStudioBackend.generate()` — 3 tentativas com backoff exponencial

O backend LLM tenta até 3 vezes com backoff exponencial (2^n segundos) antes de lançar `LLMConnectionError`.

### RNF-04 — Sem estado entre requisições
🟢 **CONFIRMADO** — `run()` não mantém estado entre chamadas

Cada chamada a `run()` é stateless: o único estado compartilhado é o pipeline singleton (configuração + modelos carregados).

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Tradução NL→SPARQL | **Must** | Funcionalidade central do sistema |
| RF-02 Loop de autocorreção | **Must** | Sem isso, taxa de sucesso cai ~30pp |
| RF-03 Pós-processamento SPARQL | **Must** | LLMs alucinam prefixos constantemente |
| RF-04 Injeção de prefixos | **Should** | Complementar ao RF-03, já incluso |
| RF-05 Few-shot FAISS | **Must** | Impacto medido no estudo de ablação |
| RF-06 Semantic retry | **Should** | Melhora recall mas adiciona latência |
| RF-07 Validação de schema | **Must** | Evita erros silenciosos no Fuseki |
| RF-08 Bloqueio DELETE/INSERT | **Must** | Invariante de segurança do sistema |
| RF-09 Graceful degradation | **Must** | Sistema não deve quebrar em setup parcial |
| RF-10 Backend plugável | **Should** | Permite experimentos com múltiplos LLMs |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| Apache Jena Fuseki em `:3030` | Serviço externo | Sim |
| LM Studio em `:1234` OU Anthropic API | Serviço externo | Sim (um dos dois) |
| `data/gold_standard/questions.index` | Arquivo | Não (zero-shot se ausente) |
| `data/gold_standard/questions.json` | Arquivo | Não (zero-shot se ausente) |
| `data/schemas.json` | Arquivo | Não (modo permissivo se ausente) |
| NER engine (scispaCy) | Módulo interno | Não (continua sem entidades) |
