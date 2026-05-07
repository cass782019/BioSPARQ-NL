# C4 — Nível 3: Componentes

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Container: BioSPARQLPipeline (src/pipeline)

O container mais complexo do sistema. Decomposto abaixo em seus componentes internos.

```mermaid
C4Component
    title BioSPARQLPipeline — Componentes Internos (C4 Nível 3)

    Container_Boundary(pipeline_boundary, "BioSPARQLPipeline Container") {

        Component(nl_sparql, "nl_to_sparql.py", "Python class BioSPARQLPipeline", "Orquestrador principal. Implementa run(), build_prompt(), generate_sparql(), execute_sparql(), _fix_common_errors(), retrieve_examples(). Contém o loop de autocorreção com até 4 tentativas.")

        Component(llm_backends, "llm_backends.py", "Python classes LLMBackend", "Abstração plugável para geração LLM. Implementações: LMStudioBackend (OpenAI-compat :1234) e AnthropicBackend (ANTHROPIC_API_KEY). Seleção via config['backend'].")

        Component(sparql_validator, "sparql_validator.py", "Python class SchemaValidator", "Valida SPARQL contra schema.json (STRICT) ou apenas sintaxe+unsafe (PERMISSIVE). Bloqueia DELETE/INSERT. Valida grafos nomeados, prefixos e termos ontológicos.")

        Component(entity_linker, "entity_linker.py", "Python — wrapper NER", "Ponte entre pipeline e NER engine. Chama get_backend() da factory, executa extração e formata entidades para inclusão no prompt.")

        Component(ner_factory, "ner/factory.py", "Python — lru_cache singleton", "Instancia e cacheia o backend NER. Suporta: 'scispacy', 'llm', 'gilda'. Padrão: 'scispacy'.")

        Component(scispacy_backend, "ner/scispacy_backend.py", "Python class ScispaCyBackend", "Backend NER principal. Usa modelo en_ner_bc5cdr_md. Filtra ruídos (_is_noise). Resolve entidades via SPARQL Fuseki (rdfs:label LCASE). Fallback para Gilda grounding.")

        Component(llm_ner_backend, "ner/llm_backend.py", "Python class LLMBackend", "NER via LLM prompt. Extrai apenas texto (spans+tipo). Não alucina IDs — resolução delegada ao Gilda deterministicamente.")

        Component(base_ner, "ner/base.py", "Python dataclass Entity + merge_overlaps()", "Define dataclass Entity (text, start, end, type, ontology_ids, scores, backend). Implementa deduplicação de spans sobrepostos por score.")
    }

    Container_Ext(faiss_idx, "FAISS Index", "questions.index + questions.json")
    Container_Ext(gold_schema, "schemas.json", "Schema ontológico")
    Container_Ext(lmstudio_ext, "LM Studio :1234", "LLM local")
    Container_Ext(anthropic_ext, "Anthropic API", "LLM cloud")
    Container_Ext(fuseki_ext, "Fuseki :3030", "Triplestore")

    Rel(nl_sparql, llm_backends, "Delega geração de SPARQL", "Python call")
    Rel(nl_sparql, sparql_validator, "Valida query gerada", "Python call")
    Rel(nl_sparql, entity_linker, "Extrai entidades da pergunta", "Python call")
    Rel(nl_sparql, faiss_idx, "retrieve_examples() — top-3", "File I/O + FAISS search")
    Rel(nl_sparql, gold_schema, "Carrega schema no __init__", "File I/O")
    Rel(nl_sparql, fuseki_ext, "execute_sparql() SELECT", "HTTP SPARQL")
    Rel(llm_backends, lmstudio_ext, "LMStudioBackend.generate()", "HTTP POST /v1/chat/completions")
    Rel(llm_backends, anthropic_ext, "AnthropicBackend.generate()", "HTTPS Anthropic SDK")
    Rel(entity_linker, ner_factory, "get_backend(name)", "Python call")
    Rel(ner_factory, scispacy_backend, "Instancia ScispaCyBackend", "Python")
    Rel(ner_factory, llm_ner_backend, "Instancia LLMBackend", "Python")
    Rel(scispacy_backend, fuseki_ext, "_resolve() — label lookup SPARQL", "HTTP SPARQL :3030")
    Rel(scispacy_backend, base_ner, "Usa Entity + merge_overlaps()", "Python")
    Rel(llm_ner_backend, base_ner, "Usa Entity + merge_overlaps()", "Python")
```

---

## Container: FastAPI Backend (src/api)

```mermaid
C4Component
    title FastAPI Backend — Componentes Internos (C4 Nível 3)

    Container_Boundary(api_boundary, "FastAPI Backend") {

        Component(server, "server.py", "Python FastAPI app", "Define app FastAPI, registra CORS middleware, expõe endpoints. Mantém global pipeline_instance para singleton lazy-init.")

        Component(get_pipeline_fn, "get_pipeline()", "Python function (lazy-init)", "Inicializa BioSPARQLPipeline na primeira chamada e cacheia em global. Evita overhead de carregamento de modelos a cada request.")

        Component(ask_endpoint, "POST /api/ask", "FastAPI endpoint", "Recebe AskRequest(question). Chama pipeline.run(). Formata AskResponse com xai (entidades, SPARQL, validação, timing, exemplos usados).")

        Component(health_endpoint, "GET /health", "FastAPI endpoint", "Retorna status, versão e informações de configuração do pipeline. Usado por gates e Playwright para aguardar inicialização.")

        Component(models, "Pydantic models", "Python Pydantic v2", "AskRequest, AskResponse, ExplainabilityInfo, ExampleUsed, ValidationInfo, TimingInfo, HealthResponse. Validação e serialização JSON.")
    }

    Container_Ext(pipeline_ext, "BioSPARQLPipeline", "Core pipeline")
    Container_Ext(frontend_ext, "Frontend React", ":5173")
    Container_Ext(playwright_ext, "Playwright Runner", ":3000")

    Rel(frontend_ext, ask_endpoint, "POST /api/ask (via Vite proxy)", "HTTP")
    Rel(playwright_ext, ask_endpoint, "POST /api/ask (intercept)", "HTTP")
    Rel(ask_endpoint, get_pipeline_fn, "pipeline = get_pipeline()", "Python")
    Rel(get_pipeline_fn, pipeline_ext, "BioSPARQLPipeline(config)", "Python")
    Rel(ask_endpoint, models, "AskResponse serializada", "Pydantic v2")
    Rel(health_endpoint, get_pipeline_fn, "Verifica se pipeline está carregado", "Python")
```

---

## Container: NER Engine — Backends Disponíveis

| Backend | Classe | Extração | Grounding | Uso Típico |
|---|---|---|---|---|
| `scispacy` | `ScispaCyBackend` | spaCy NER model `en_ner_bc5cdr_md` | SPARQL Fuseki (rdfs:label) + Gilda fallback | Padrão — melhor F1 |
| `llm` | `LLMBackend` | LLM prompt extrai spans | Gilda (score ≥ 0.5) | Alternativo sem spaCy |
| `gilda` | Integrado no ScispaCy | — | `gilda.ground()` whitelist namespaces | Só resolução |

### Seleção de Backend
```
BIOSPARQL_NER_BACKEND=scispacy  # env var (padrão se ausente)
→ factory.get_backend("scispacy") → lru_cache singleton → ScispaCyBackend
```

---

## Container: src2 Extensions — Componentes

```mermaid
C4Component
    title src2 Extensions — Componentes Internos (C4 Nível 3)

    Container_Boundary(src2_boundary, "src2 Extensions") {

        Component(claude_cli, "ClaudeCLIBackend", "Python class (src2/pipeline/llm_backends.py)", "Executa 'claude --print --disable-slash-commands' como subprocess. Workdir isolado em ~/.biosparql-bench-workdir/. Timeout 180s. Usa OAuth já autenticado no Claude Code.")

        Component(playwright_runner, "playwright_runner.py", "Python + Playwright async", "Abre Chromium headless em localhost:3000. Para cada questão: digita texto, intercepta POST /api/ask response, extrai JSON, grava JSONL em output2/.")

        Component(corrections_report, "corrections_report.py", "Python CLI", "Compara playwright_log_baseline.jsonl (pré-correções) com playwright_log.jsonl (pós). Gera corrections_report.json e .md com delta de sucessos.")

        Component(run_all_src2, "run_all_models.py (src2)", "Python CLI", "Orquestra avaliação com LMStudioBackend e ClaudeCLIBackend. Salva em output2/ (não output/).")

        Component(src2_pipeline, "nl_to_sparql.py (src2)", "Python class BioSPARQLPipeline", "Fork do pipeline src/ com suporte a ClaudeCLIBackend. Mantém mesma interface run().")
    }

    Container_Ext(claude_cli_ext, "claude CLI", "Autenticado via OAuth Claude Code")
    Container_Ext(browser_ext, "Chromium (Playwright)", "Headless")
    Container_Ext(frontend_real, "Frontend React :3000", "Vite preview ou serve")

    Rel(claude_cli, claude_cli_ext, "subprocess(['claude', '--print', ...])", "stdin/stdout")
    Rel(playwright_runner, browser_ext, "async with async_playwright()", "Browser API")
    Rel(playwright_runner, frontend_real, "page.goto('http://localhost:3000')", "HTTP")
    Rel(playwright_runner, frontend_real, "page.on('response', intercept /api/ask)", "HTTP intercept")
    Rel(corrections_report, playwright_runner, "Lê output2/playwright_log*.jsonl", "File I/O")
```
