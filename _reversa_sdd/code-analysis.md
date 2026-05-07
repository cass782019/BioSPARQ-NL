# Análise de Código — BioSPARQL-NL

> Gerado pelo Arqueólogo em 2026-05-04 | doc_level: detalhado

---

## Sumário Executivo

BioSPARQL-NL é um pipeline NL→SPARQL de pesquisa acadêmica (PPG Computação Aplicada — UNISINOS) que converte perguntas em linguagem natural para queries SPARQL executáveis sobre três ontologias biomédicas carregadas num triplestore Apache Jena Fuseki. A arquitetura é cliente-servidor: backend FastAPI em Python + frontend React. O núcleo é o `BioSPARQLPipeline`, que orquestra NER → recuperação few-shot → geração LLM → validação de schema → execução Fuseki → loop de autocorreção.

**Resultado chave da avaliação:** Nemotron 4B (80%) > Qwen 9B (50%) > Gemma 3 4B (46.7%) — arquitetura importa mais que tamanho de modelo.

---

## Módulo 1 — `pipeline` 🟢 CONFIRMADO

**Caminho:** `src/pipeline/`
**Propósito:** Orquestrador central do pipeline NL→SPARQL.

### Classe principal: `BioSPARQLPipeline`

**Arquivo:** `src/pipeline/nl_to_sparql.py`

#### Inicialização (`__init__`)

Configuração padrão via dict + env vars:
| Parâmetro | Padrão | Env override |
|---|---|---|
| `endpoint` | `http://localhost:3030/biomedical/sparql` | — |
| `lm_studio_url` | `http://localhost:1234/v1` | — |
| `llm_model` | `"auto"` | `LLM_MODEL` |
| `max_retries` | `2` | — |
| `top_k_examples` | `3` | — |
| `llm_timeout` | `300.0` | `LLM_TIMEOUT` |
| `fuseki_timeout` | `30` | — |

Componentes inicializados com graceful fallback:
- `backend` — LLM backend via `create_backend(config)` (LMStudio ou Anthropic)
- `entity_linker` — EntityLinker(endpoint), desabilitado silenciosamente se falhar
- `index` — FAISS index lido de `data/gold_standard/questions.index`, zero-shot se ausente
- `examples` — `data/gold_standard/questions.json` (30 questões)
- `schemas` — `data/schemas.json`, ignorado se ausente
- `validator` — `SchemaValidator()` (carrega schemas.json)
- `_embedder` — lazy-loaded `SentenceTransformer("all-MiniLM-L6-v2")`

#### Método `run(question)` — Loop principal

**Lógica complexa — ver flowchart `flowcharts/pipeline-run.md`**

```
max_attempts = max_retries + 2   # normalmente 4 tentativas
```

Loop while attempt < max_attempts:
1. `build_prompt` → system + user_msg
2. `generate_sparql` → SPARQL bruto do LLM
3. `validate` → SchemaValidator
4. Se válido → `execute_sparql` → Fuseki
   - Se 0 resultados + primeira vez → **semantic retry** com feedback específico
   - Senão → retorna resultado
5. Se inválido → formata feedback de validação e re-prompta
6. Última tentativa inválida → executa mesmo assim

**Semantic retry feedback:** orienta o LLM a usar labels em inglês, padrões DOID↔HPOA corretos.

#### Método `_fix_common_errors(query)` — Pós-processamento LLM

8 transformações aplicadas sequencialmente:
1. Remove blocos `DECLARE { ... }` (preserva PREFIX internos)
2. Remove pseudo-keywords soltas: `DECLARE`, `IMPORT`, `USE`, `NAMESPACE`
3. Canonicaliza URIs de prefixos conhecidos (9 prefixos)
4. Corrige `oboInOwl#localname` → `oboInOwl:localname`
5. Corrige `pred = ?var` → `pred ?var` (sintaxe SPARQL errada)
6. Remove declarações PREFIX usando URNs de grafo como namespace
7. Corrige URIs de grafo abreviadas: `<doid>` → `<urn:doid>`, etc.
8. Move FILTERs soltos após `}` para dentro do WHERE
9. Corrige BIND com auto-referência (variável fonte == destino)

#### Método `_inject_missing_prefixes(query)`

Detecta prefixos usados mas não declarados (regex sobre corpo da query) e injeta no início. Conhece 9 prefixos: `rdf`, `rdfs`, `xsd`, `owl`, `obo`, `oboInOwl`, `hpoa`, `skos`, `dc`.

#### Constante `KNOWN_PREFIXES`

```python
{
  "rdf":       "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  "rdfs":      "http://www.w3.org/2000/01/rdf-schema#",
  "xsd":       "http://www.w3.org/2001/XMLSchema#",
  "owl":       "http://www.w3.org/2002/07/owl#",
  "obo":       "http://purl.obolibrary.org/obo/",
  "oboInOwl":  "http://www.geneontology.org/formats/oboInOwl#",
  "hpoa":      "http://example.org/hpoa/",
  "skos":      "http://www.w3.org/2004/02/skos/core#",
  "dc":        "http://purl.org/dc/elements/1.1/",
}
```

### Classe: `SchemaValidator`

**Arquivo:** `src/pipeline/sparql_validator.py`

#### Validações executadas (em ordem)

| # | Checagem | Tipo de falha |
|---|---|---|
| 1 | Sintaxe via `rdflib.parseQuery` | error |
| 2 | Operações UNSAFE: DELETE/INSERT | error |
| 3 | GRAPH refs contra `valid_graphs` | error |
| 4 | Prefixos declarados vs. usados | warning |
| 5 | Classes/predicados contra schema | warning (permissive=False) |

**Modo permissivo:** ativado automaticamente se `schemas.json` ausente ou inválido.
**Grafos válidos por padrão:** `urn:doid`, `urn:hpo`, `urn:hpoa`

Retorna `{"valid": bool, "errors": list[str], "warnings": list[str]}`

**`format_feedback(validation_result, original_query)`:** formata erros+warnings em string para re-prompting LLM.

---

## Módulo 2 — `ner` 🟢 CONFIRMADO

**Caminho:** `src/pipeline/ner/`
**Propósito:** Backends NER plugáveis via variável de ambiente `NER_BACKEND`.

### Interface base (`base.py`)

```python
@dataclass
class Entity:
    text: str
    start: int        # char offset início
    end: int          # char offset fim
    type: str         # DISEASE | PHENOTYPE | GENE | CHEMICAL | OTHER
    ontology_ids: list[str]   # CURIEs: ["DOID:14330", "HP:0001250"]
    scores: list[float]        # confiança, decrescente
    backend: str

@runtime_checkable
class NERBackend(Protocol):
    name: str
    def extract(self, text: str) -> list[Entity]: ...
    def warm_up(self) -> None: ...
```

**`merge_overlaps(entities)`:** remove sobreposições de spans mantendo o de maior score.

### Factory (`factory.py`)

REGISTRY: `scispacy → ScispaCyBackend`, `gilda → GildaBackend`, `llm → LLMBackend`, `medcat → MedCATBackend`

`get_backend(name)` usa `@lru_cache` — instância singleton por backend. Selection order: arg explícito > env `NER_BACKEND` > `scispacy`.

### Backend: `ScispaCyBackend` (padrão)

1. `warm_up()`: carrega `en_core_sci_sm` via spaCy
2. `extract(text)`: `nlp(text)` → filtra ruídos via `_is_noise()` → resolve cada span via SPARQL Fuseki (`rdfs:label` exato, `LIMIT 1`)
3. Mapeia URIs OBO para CURIEs: `DOID_* → DOID:*`, `HP_* → HP:*`

**`_is_noise(text)`:** filtra spans com len < 4, stopwords PT+EN (lista de ~80 termos), ratio alfa < 50%.

**Resolução via Fuseki:** query SPARQL `FILTER(LCASE(STR(?label)) = LCASE('texto'))` — busca em todos os grafos.

### Backend: `LLMBackend` (`llm+gilda`)

1. LLM extrai spans como JSON estruturado (texto + tipo + offsets) via system prompt estrito
2. Gilda (`gilda.ground(span_text)`) resolve CURIEs deterministicamente (score mínimo: 0.5)
3. Mantém apenas namespaces: DOID, HP, OMIM, MESH
4. Sem alucinação de IDs: LLM só provê texto, Gilda provê IDs

### EntityLinker (`entity_linker.py`)

Adapter sobre NERBackend que preserva interface dict-based do pipeline (`extract_entities`, `format_for_prompt`).

CURIE→URI: `DOID:* → http://purl.obolibrary.org/obo/DOID_*` (urn:doid), `HP:* → http://purl.obolibrary.org/obo/HP_*` (urn:hpo).

---

## Módulo 3 — `api` 🟢 CONFIRMADO

**Caminho:** `src/api/server.py`
**Propósito:** Servidor FastAPI REST — interface entre frontend e pipeline.

### Endpoints

| Método | Path | Request | Response |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok"}` |
| POST | `/api/ask` | `{"question": str}` | `AskResponse` |

### CORS

Origens permitidas: `http://localhost:5173` (Vite dev) e `http://localhost:3000` (Playwright).

### Fluxo `POST /api/ask`

1. Valida question não vazia
2. `get_pipeline()` — singleton lazy-init
3. `_extract_entities(pipe, question)` — NER com timing
4. `_retrieve_examples(pipe, question)` — FAISS retrieval com timing
5. `pipe.run(question)` — pipeline completo com timing
6. `_format_answer(result)` — formata NL: 0 resultados / 1 resultado / N resultados com lista
7. Monta `AskResponse` com XAI completo

### Estrutura `AskResponse`

```
AskResponse:
  answer: str               # resposta NL formatada
  success: bool
  xai: ExplainabilityInfo:
    entities: list[str]     # labels das entidades NER
    examples_used: list[ExampleUsed]
    sparql: str             # query gerada
    validation: ValidationInfo (valid, errors, warnings)
    attempts: int
    results_raw: list[Any]
    results_count: int
    timing: TimingInfo (ner_s, retrieval_s, llm_s, total_s)
```

---

## Módulo 4 — `evaluation` 🟢 CONFIRMADO

**Caminho:** `src/evaluation/`
**Propósito:** Avaliação multi-modelo com 30 questões, ablação e geração de tabelas LaTeX.

### `run_evaluation.py`

Função `evaluate(pipeline, questions, use_validation)`:
- Cenário A (com validação): `max_retries=2`
- Cenário B (sem validação): `max_retries=0`
- Por questão: métricas — `valid`, `exec.success`, `exec.count`, `attempts`, `time_seconds`
- Spot-check semântico: verifica se `expected_contains` aparecem nos resultados

### Ablação (`ablation_configs.py` + `run_ablation.py`)

6 configurações de ablação:
| Config | NER | Few-shot | Schema | Validação |
|---|---|---|---|---|
| full | sim | sim | sim | sim |
| no_ner | não | sim | sim | sim |
| no_fewshot | sim | não | sim | sim |
| no_schema | sim | sim | não | sim |
| no_validation | sim | sim | sim | não |
| zero_shot | não | não | não | não |

### Saída

- `output/eval_{safe_model}.json` — resultados brutos por questão
- `output/evaluation_multi_model.json` — comparativo multi-modelo
- `output/ablation_{model}.json` — resultados ablação
- `output/tables/*.tex` — fragmentos LaTeX para o paper

### Métricas calculadas

- Correção geral (% questões com ≥1 resultado e meets_expected)
- Por dificuldade: easy / medium / hard
- Média de tentativas, tempo médio
- Taxa de validação bem-sucedida

---

## Módulo 5 — `utils` 🟢 CONFIRMADO

**Caminho:** `src/utils/`
**Propósito:** Utilitários de preparação de dados e infraestrutura.

### `hpoa_to_rdf.py` — `convert_hpoa_to_rdf(input_tsv, output_ttl)`

Converte `phenotype.hpoa` (TSV) → Turtle RDF:
- Pula linhas com `#`, cabeçalho, linhas com `qualifier=NOT`
- Cada linha gera 4 triplas: `rdf:type HPOA:Disease`, `rdfs:label`, `hpoa:has_phenotype`, `hpoa:source_id`
- `disease_uri`: `http://example.org/disease/OMIM_154700`
- `hpo_uri`: `http://purl.obolibrary.org/obo/HP_0001234`
- Chave de JOIN cross-graph: `hpoa:source_id` = valor textual `"OMIM:154700"`

**Suporta:** OMIM, ORPHA, DECIPHER como prefixos de doença.

### `schema_extractor.py` — Introspecção SPARQL

Extrai classes e predicados de cada grafo nomeado via queries `GROUP_CONCAT`. Retry exponencial (3 tentativas, backoff 2^n). Salva em `data/schemas.json`.

### `index_builder.py` — `build_index()`

1. Carrega `questions.json`
2. Gera embeddings com `SentenceTransformer("all-MiniLM-L6-v2")` (384 dim)
3. Cria `faiss.IndexFlatIP` (Inner Product = cosine com vetores normalizados)
4. Salva em `data/gold_standard/questions.index`

---

## Módulo 6 — `frontend` 🟢 CONFIRMADO

**Caminho:** `frontend/src/`
**Propósito:** Interface React SPA com painel XAI (explainabilidade).

### Arquitetura de componentes

```
App
├── ChatPanel       — histórico de mensagens (user + bot)
├── InputBar        — campo de entrada + envio
└── XaiPanel        — painel de explainabilidade
    ├── EntityBadges    — badges das entidades NER detectadas
    ├── SparqlBlock     — query SPARQL com syntax highlighting
    ├── ValidationStatus — status válido/inválido + erros
    ├── TimingBar       — barra de timing (NER / Retrieval / LLM)
    └── ResultsTable    — tabela de resultados brutos do Fuseki
```

### Estado global (App.jsx)

```javascript
const [messages, setMessages] = useState([])  // histórico chat
const [xai, setXai] = useState(null)          // dados XAI do último /api/ask
const [loading, setLoading] = useState(false)  // spinner
```

**Fluxo:** Input → `POST /api/ask` via axios → atualiza messages + xai.

**Proxy Vite:** `/api/*` → `http://localhost:8000` (configurado em `vite.config.js`).

---

## Módulo 7 — `src2` 🟢 CONFIRMADO

**Caminho:** `src2/`
**Propósito:** Revisão 2 do pipeline — adiciona ClaudeCLIBackend e testes E2E via Playwright.

### `ClaudeCLIBackend` (`src2/pipeline/llm_backends.py`)

Diferencial chave: usa `claude` CLI via subprocess com OAuth já autenticado no Claude Code — **não precisa de `ANTHROPIC_API_KEY`**.

Flags usados:
```
claude --print --model <model> --system-prompt <system> --output-format text
       --input-format text --disable-slash-commands [--max-budget-usd N]
```

Isolamento: `cwd = ~/.biosparql-bench-workdir` (fora de proj1, evita auto-discovery de CLAUDE.md).

Input via `stdin` (evita limites de arg no Windows). Timeout configurável (padrão 180s).

### `playwright_runner.py`

E2E browser-based sobre o frontend React (porta 3000):
1. Abre Chromium (headless por padrão)
2. Intercepta respostas `POST /api/ask` via `page.on("response")`
3. Para cada questão: digita no input, aguarda resposta, captura JSON
4. Loga em `output2/playwright_log.jsonl` (um JSON por linha)
5. Suporta `--limit N`, `--ids Q01 Q05`, `--headed`, `--screenshots`, `--regression-suite`

### `corrections_report.py`

Compara baseline (pré-correções) com pós-correções, gerando relatório de regressão/progresso.

---

## Módulo 8 — `gates` 🟢 CONFIRMADO

**Caminho:** `gates/`
**Propósito:** Validação por fase — verificam pré-condições antes de cada etapa do pipeline de pesquisa.

| Gate | Arquivo | Verifica |
|---|---|---|
| 0 | `gate0_check.py` | Python libs, scispaCy, Ollama, Java, Fuseki acessível |
| 1 | `gate1_check.py` | Dados: doid.owl, hp.owl, hpoa.ttl, schemas.json, FAISS index |
| 2 | `gate2_check.py` | Pipeline: FastAPI up, /api/health OK, pipeline instanciável |
| 3 | `gate3_check.py` | Avaliação: output/*.json existem, métricas dentro do esperado |
| 6 | `gate6_check.py` | Verificação final: todos os artefatos presentes |

---

## Hierarquia de Exceções 🟢 CONFIRMADO

**Arquivo:** `src/exceptions.py`

```
BioSPARQLError (base)
├── FusekiConnectionError      — Fuseki offline ou timeout
├── LLMConnectionError         — LLM offline ou timeout
├── ValidationError            — Query inválida após validação
├── SchemaLoadError            — schemas.json ausente ou corrompido
└── EntityLinkingError         — Falha no scispaCy/entity linking
```

---

## Algoritmos Não-Triviais

| Algoritmo | Localização | Confiança |
|---|---|---|
| Loop de autocorreção com semantic retry | `nl_to_sparql.py:run()` | 🟢 CONFIRMADO |
| Pós-processamento de SPARQL (8 regex transforms) | `nl_to_sparql.py:_fix_common_errors()` | 🟢 CONFIRMADO |
| Auto-declaração de prefixos faltantes | `nl_to_sparql.py:_inject_missing_prefixes()` | 🟢 CONFIRMADO |
| Deduplicação de spans NER por score | `ner/base.py:merge_overlaps()` | 🟢 CONFIRMADO |
| Filtragem de ruído NER (stopwords + ratio alfa) | `ner/scispacy_backend.py:_is_noise()` | 🟢 CONFIRMADO |
| Busca por similaridade FAISS (cosine via Inner Product) | `nl_to_sparql.py:retrieve_examples()` | 🟢 CONFIRMADO |
| Resolução NER via SPARQL Fuseki (rdfs:label exato) | `ner/scispacy_backend.py:_resolve()` | 🟢 CONFIRMADO |
| LLM-as-NER + Gilda grounding (sem alucinação de IDs) | `ner/llm_backend.py:extract()` | 🟢 CONFIRMADO |
| Conversão TSV→RDF com JOIN OMIM↔MIM | `utils/hpoa_to_rdf.py` | 🟢 CONFIRMADO |

---

## Regras de Negócio Implícitas (domínio)

| Regra | Localização | Confiança |
|---|---|---|
| DOID usa `MIM:` em `oboInOwl:hasDbXref`, HPOA usa `OMIM:` em `hpoa:source_id` | `nl_to_sparql.py:build_prompt()` | 🟢 CONFIRMADO |
| JOIN cross-graph requer `BIND(REPLACE(..., "^MIM:", "OMIM:") AS ?oid)` | `nl_to_sparql.py:SEMANTIC_RETRY_FEEDBACK` | 🟢 CONFIRMADO |
| Labels de fenótipos só em `urn:hpo`; anotações doença→fenótipo em `urn:hpoa` | `nl_to_sparql.py:build_prompt()` | 🟢 CONFIRMADO |
| `doid:` e `hpo:` NÃO são prefixos válidos no triplestore | `nl_to_sparql.py:_fix_common_errors()` | 🟢 CONFIRMADO |
| Labels devem ser em INGLÊS nos FILTER SPARQL | `nl_to_sparql.py:build_prompt()` | 🟢 CONFIRMADO |
| Qualificador "NOT" no HPOA é descartado na conversão | `utils/hpoa_to_rdf.py:convert_hpoa_to_rdf()` | 🟢 CONFIRMADO |
| Todos os modelos > 20B requerem verificação de memória prévia | `CLAUDE.md` | 🟡 INFERIDO |
