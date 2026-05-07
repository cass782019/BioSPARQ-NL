# C4 — Nível 2: Containers

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Diagrama

```mermaid
C4Container
    title BioSPARQL-NL — Diagrama de Containers (C4 Nível 2)

    Person(pesquisador, "Pesquisador Biomédico", "Formula perguntas em português")

    System_Boundary(biosparql, "BioSPARQL-NL") {
        Container(frontend, "Frontend React", "React 18 + Vite 5", "SPA com interface de chat e painel XAI. Mostra entidades detectadas, SPARQL gerado, validação e timing.")
        Container(backend, "FastAPI Backend", "Python + FastAPI 0.135 + Uvicorn", "REST API. Expõe /api/ask e /health. Mantém singleton do pipeline. Proxy-alvo do Vite em dev.")
        Container(pipeline, "BioSPARQLPipeline", "Python — módulo src/pipeline", "Orquestrador NL→SPARQL. Executa NER, few-shot RAG, geração LLM, pós-processamento, validação e loop de autocorreção.")
        Container(ner_engine, "NER Engine", "Python — scispaCy 0.6 + Gilda + LLM fallback", "Extração plugável de entidades biomédicas. Backends: scispaCy (padrão), LLM-as-NER, Gilda. Singleton com lru_cache.")
        Container(faiss_index, "FAISS Index", "FAISS-CPU 1.13 + sentence-transformers 5.4", "Índice de similaridade cosine sobre 30 questões do gold standard. Recupera top-3 exemplos por query.")
        Container(validator, "SchemaValidator", "Python — módulo src/pipeline", "Valida SPARQL gerado contra schema extraído por introspecção. Modos: STRICT (com schemas.json) e PERMISSIVE (sem).")
        Container(gold_data, "Gold Standard + Schemas", "JSON + FAISS binary", "30 questões anotadas (questions.json), índice FAISS (questions.index), schema ontológico (schemas.json). Dados estáticos em data/.")
        Container(evaluation, "Evaluation Framework", "Python — módulo src/evaluation", "Avaliação multi-modelo (30 questões, 2 cenários), ablação (6 configs), consolidação e geração de tabelas LaTeX. CLI-only.")
        Container(src2_ext, "src2 Extensions", "Python — módulo src2", "ClaudeCLIBackend (OAuth subprocess) e Playwright E2E runner. Revisão 2 do pipeline para experimentos com Claude CLI e testes via browser.")
        Container(gates, "Gates", "Python scripts", "Validação de pré-condições por fase (gate0–gate6). Verifica deps, dados, pipeline e avaliação.")
    }

    System_Ext(fuseki, "Apache Jena Fuseki", "Triplestore local :3030")
    System_Ext(lmstudio, "LM Studio", "LLM local :1234")
    System_Ext(anthropic, "Anthropic API", "Cloud LLM")

    Rel(pesquisador, frontend, "Digita pergunta em PT", "HTTPS/HTTP :5173")
    Rel(frontend, backend, "POST /api/ask", "HTTP REST :8000 (proxy Vite)")
    Rel(backend, pipeline, "Invoca run(question)", "Python call (in-process)")
    Rel(pipeline, ner_engine, "Extrai entidades da pergunta", "Python call")
    Rel(pipeline, faiss_index, "Recupera top-3 exemplos similares", "Python call")
    Rel(pipeline, validator, "Valida SPARQL gerado", "Python call")
    Rel(pipeline, fuseki, "Executa query SPARQL SELECT", "HTTP SPARQL :3030")
    Rel(pipeline, lmstudio, "Gera SPARQL (LMStudioBackend)", "HTTP OpenAI-compat :1234")
    Rel(pipeline, anthropic, "Gera SPARQL (AnthropicBackend, opcional)", "HTTPS")
    Rel(pipeline, gold_data, "Lê exemplos e schema em runtime", "File I/O")
    Rel(backend, frontend, "AskResponse (answer + xai JSON)", "HTTP REST")
    Rel(src2_ext, pipeline, "Herda lógica base, estende backends", "Python import")
    Rel(src2_ext, frontend, "Testa via browser (Playwright)", "HTTP :3000")
    Rel(evaluation, pipeline, "Instancia e avalia pipeline", "Python call")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

---

## Descrição dos Containers

### Frontend React
- **Tech:** React 18.3.1 + Vite 5.4.0 + axios
- **Porta:** 5173 (dev), 3000 (Playwright)
- **Responsabilidade:** Interface de chat single-page com painel XAI colapsável. Exibe entidades detectadas (highlights), query SPARQL gerada, status de validação, número de tentativas e breakdown de timing.
- **Comunicação:** Proxy Vite em `/api/*` → `localhost:8000`.

### FastAPI Backend
- **Tech:** FastAPI 0.135.3 + Uvicorn 0.44.0 + Pydantic 2.12.5
- **Porta:** 8000
- **Endpoints:** `GET /health`, `POST /api/ask`
- **Responsabilidade:** Interface REST, gerenciamento de singleton do pipeline (lazy-init no primeiro request).
- **CORS:** `localhost:5173` e `localhost:3000` apenas.

### BioSPARQLPipeline
- **Tech:** Python puro + integrações com NER, FAISS, LLM backends
- **Responsabilidade:** Orquestração completa do fluxo NL→SPARQL. Inclui construção de prompt, pós-processamento (8 regex), loop de autocorreção com até 4 tentativas e semantic retry.

### NER Engine
- **Tech:** scispaCy 0.6.2 + spaCy 3.7.5 + Gilda + OpenAI SDK
- **Padrão:** `scispacy` (com fallback para zero-shot se falhar)
- **Responsabilidade:** Extração de spans biomédicos e resolução para CURIEs ontológicos (DOID/HP).

### FAISS Index
- **Tech:** FAISS-CPU 1.13.2 + sentence-transformers 5.4.0 (all-MiniLM-L6-v2, 384d)
- **Responsabilidade:** Recuperação por similaridade cosine das 30 questões do gold standard para few-shot prompting.

### SchemaValidator
- **Tech:** Python + rdflib/SPARQLWrapper (para extração) + regex (para validação)
- **Responsabilidade:** Valida grafos, prefixos, classes e predicados de queries SPARQL geradas. Bloqueia operações de escrita (DELETE/INSERT).

### Evaluation Framework
- **Tech:** Python CLI scripts
- **Responsabilidade:** Avaliação reprodutível de múltiplos modelos. Gera `output/eval_*.json`, tabelas comparativas e fragmentos LaTeX para o paper.

### src2 Extensions
- **Tech:** Python + Playwright (via playwright CLI)
- **Responsabilidade:** Revisão 2 do pipeline que adiciona `ClaudeCLIBackend` (autenticação OAuth via `claude` CLI subprocess) e `PlaywrightRunner` para testes E2E sobre o frontend real.

### Gates
- **Tech:** Python scripts CLI
- **Responsabilidade:** Validação sequencial de pré-condições antes de avançar de fase. `gate0` (deps), `gate1` (dados), `gate2` (pipeline), `gate3` (avaliação), `gate6` (final).
