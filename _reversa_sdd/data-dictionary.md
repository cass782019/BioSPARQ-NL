# Dicionário de Dados — BioSPARQL-NL

> Gerado pelo Arqueólogo em 2026-05-04

---

## Entidades Python (dataclasses / Pydantic)

### `Entity` — `src/pipeline/ner/base.py`

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---|---|
| `text` | `str` | sim | — | Substring exata do texto original |
| `start` | `int` | sim | — | Offset de início (0-indexed, chars) |
| `end` | `int` | sim | — | Offset de fim (chars) |
| `type` | `str` | sim | — | Um de: `DISEASE`, `PHENOTYPE`, `GENE`, `CHEMICAL`, `OTHER` |
| `ontology_ids` | `list[str]` | não | `[]` | CURIEs ordenados por confiança: `["DOID:14330"]` |
| `scores` | `list[float]` | não | `[]` | Scores de confiança correspondentes a `ontology_ids` |
| `backend` | `str` | não | `""` | Nome do backend que extraiu: `"scispacy"`, `"llm+gilda"` |

Propriedade: `primary_id → str | None` — primeiro CURIE ou None.

---

### `AskRequest` — `src/api/server.py`

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `question` | `str` | sim | Não vazia (HTTP 400 se vazia) |

---

### `AskResponse` — `src/api/server.py`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `answer` | `str` | sim | Resposta NL formatada |
| `success` | `bool` | sim | True se execução retornou ≥1 resultado |
| `xai` | `ExplainabilityInfo` | sim | Dados de explainabilidade completos |

---

### `ExplainabilityInfo` — `src/api/server.py`

| Campo | Tipo | Descrição |
|---|---|---|
| `entities` | `list[str]` | Labels das entidades NER detectadas |
| `examples_used` | `list[ExampleUsed]` | Exemplos few-shot recuperados via FAISS |
| `sparql` | `str` | Query SPARQL gerada |
| `validation` | `ValidationInfo` | Resultado da validação de schema |
| `attempts` | `int` | Número de tentativas no loop de autocorreção |
| `results_raw` | `list[Any]` | Bindings brutos do Fuseki |
| `results_count` | `int` | Contagem de resultados |
| `timing` | `TimingInfo` | Timing por estágio |

---

### `ValidationInfo` — `src/api/server.py`

| Campo | Tipo | Descrição |
|---|---|---|
| `valid` | `bool` | True = sem erros hard |
| `errors` | `list[str]` | Erros que impedem execução |
| `warnings` | `list[str]` | Alertas (prefixos, classes não encontradas) |

**Códigos de erro conhecidos:** `SYNTAX_ERROR`, `UNSAFE_OPERATION`, `INVALID_GRAPH`, `UNDEFINED_PREFIX`, `UNKNOWN_TERM`
**Código de warning:** `NO_GRAPH`, `UNDEFINED_PREFIX`, `UNKNOWN_TERM`

---

### `TimingInfo` — `src/api/server.py`

| Campo | Tipo | Unidade |
|---|---|---|
| `ner_s` | `float` | segundos |
| `retrieval_s` | `float` | segundos |
| `llm_s` | `float` | segundos |
| `total_s` | `float` | segundos |

---

### `ExampleUsed` — `src/api/server.py`

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `str` | ID da questão: `"Q01"` .. `"Q30"` |
| `difficulty` | `str` | `"easy"`, `"medium"`, `"hard"` |
| `question_en` | `str` | Texto da pergunta em inglês |

---

### `HealthResponse` — `src/api/server.py`

| Campo | Tipo | Valor |
|---|---|---|
| `status` | `str` | `"ok"` |

---

## Estrutura do Gold Standard

### `data/gold_standard/questions.json`

Array de 30 objetos:

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | `str` | sim | `"Q01"` .. `"Q30"` |
| `difficulty` | `str` | sim | `"easy"`, `"medium"`, `"hard"` (10 cada) |
| `type` | `str` | sim | Tipo de questão (exploração, comparação, etc.) |
| `question_en` | `str` | sim | Pergunta em inglês (usada pelo pipeline) |
| `sparql` | `str` | sim | Query SPARQL de referência |
| `expected_min_results` | `int` | não | Mínimo de resultados esperados (padrão: 1) |
| `expected_contains` | `list[str]` | não | Termos que devem aparecer nos resultados (spot-check) |

---

## Estrutura de Resultado de Avaliação

### `output/eval_{safe_model}.json`

| Campo | Tipo | Descrição |
|---|---|---|
| `question_id` | `str` | ID da questão |
| `difficulty` | `str` | Dificuldade |
| `type` | `str` | Tipo de questão |
| `question` | `str` | Texto da pergunta |
| `sparql` | `str` | SPARQL gerado |
| `validation.valid` | `bool` | Validação passou |
| `validation.errors` | `list[str]` | Erros de validação |
| `execution.success` | `bool` | Execução no Fuseki OK |
| `execution.count` | `int` | Número de resultados |
| `attempts` | `int` | Tentativas no loop |
| `time_seconds` | `float` | Tempo total da questão |
| `meets_expected` | `bool` | count >= expected_min_results |
| `spot_check_pass` | `bool | None` | Spot-check semântico (None se sem expected_contains) |

---

## Entidades RDF no Triplestore

### Grafo `urn:doid` — Disease Ontology

| Predicado | Tipo | Descrição |
|---|---|---|
| `rdf:type` | URI | Classe OBO (ex: `obo:DOID_4` = Disease) |
| `rdfs:label` | Literal (EN) | Nome da doença em inglês |
| `oboInOwl:hasDbXref` | Literal | Cross-reference: `"MIM:154700"`, `"ORPHA:558"` |
| `obo:IAO_0000115` | Literal | Definição da doença |

### Grafo `urn:hpo` — Human Phenotype Ontology

| Predicado | Tipo | Descrição |
|---|---|---|
| `rdf:type` | URI | Classe HPO |
| `rdfs:label` | Literal (EN) | Nome do fenótipo em inglês |
| `oboInOwl:hasDbXref` | Literal | Cross-reference |

### Grafo `urn:hpoa` — Anotações Doença→Fenótipo

| Predicado | Tipo | Descrição |
|---|---|---|
| `rdf:type` | URI | `hpoa:Disease` |
| `rdfs:label` | Literal | Nome da doença (fonte: HPOA TSV col 2) |
| `hpoa:has_phenotype` | URI | URI HPO do fenótipo |
| `hpoa:source_id` | Literal | `"OMIM:154700"`, `"ORPHA:558"` — chave JOIN cross-graph |

**Namespace HPOA:** `http://example.org/hpoa/`
**Namespace doença:** `http://example.org/disease/`

---

## Configuração de Pipeline (`BioSPARQLPipeline.config`)

| Chave | Tipo | Padrão | Override env |
|---|---|---|---|
| `endpoint` | `str` | `http://localhost:3030/biomedical/sparql` | — |
| `lm_studio_url` | `str` | `http://localhost:1234/v1` | — |
| `llm_model` | `str` | `"auto"` | `LLM_MODEL` |
| `max_retries` | `int` | `2` | — |
| `top_k_examples` | `int` | `3` | — |
| `llm_timeout` | `float` | `300.0` | `LLM_TIMEOUT` |
| `fuseki_timeout` | `int` | `30` | — |
| `disable_ner` | `bool` | `False` | — (ablação) |
| `disable_schema` | `bool` | `False` | — (ablação) |
| `semantic_retry` | `bool` | `True` | — (ablação) |
| `backend` | `str` | `"lm_studio"` | — |
| `max_budget_usd` | `float|None` | `None` | — (ClaudeCLI) |

---

## Hierarquia de Exceções

| Classe | Pai | Quando |
|---|---|---|
| `BioSPARQLError` | `Exception` | Base |
| `FusekiConnectionError` | `BioSPARQLError` | Fuseki offline/timeout |
| `LLMConnectionError` | `BioSPARQLError` | LLM offline/timeout |
| `ValidationError` | `BioSPARQLError` | Query inválida |
| `SchemaLoadError` | `BioSPARQLError` | schemas.json ausente/corrompido |
| `EntityLinkingError` | `BioSPARQLError` | Falha NER/scispaCy |

---

## Variáveis de Ambiente

| Variável | Tipo | Padrão | Usado em |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `str` | — | src/pipeline/llm_backends.py |
| `NER_BACKEND` | `str` | `"scispacy"` | src/pipeline/ner/factory.py |
| `FUSEKI_ENDPOINT` | `str` | `http://localhost:3030/biomedical/sparql` | ner/scispacy_backend.py |
| `LLM_BASE_URL` | `str` | `http://localhost:1234/v1` | ner/llm_backend.py |
| `LLM_MODEL` | `str` | `"auto"` | pipeline/nl_to_sparql.py |
| `LLM_TIMEOUT` | `float` | `300` | pipeline/nl_to_sparql.py |
| `LLM_MAX_TOKENS` | `int` | `3000` | pipeline/llm_backends.py |
| `HF_HUB_DISABLE_XET` | `str` | — | server.py (desabilita HF XET) |
