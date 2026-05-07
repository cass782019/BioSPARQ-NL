# Requisitos — api

> Unit: `src/api/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `api` |
| Caminho legado | `src/api/server.py` |
| Responsabilidade | Servidor FastAPI REST — interface entre frontend React e pipeline NL→SPARQL |
| Complexidade | 🟢 Baixa |

---

## Requisitos Funcionais

### RF-01 — Endpoint `POST /api/ask` para processar perguntas
🟢 **CONFIRMADO** — `server.py:ask()`

**Must**

Receber uma pergunta em linguagem natural via JSON, processar via `BioSPARQLPipeline.run()` e retornar resposta estruturada com dados de explicabilidade XAI.

**Critérios de Aceitação:**

```gherkin
Dado o servidor FastAPI rodando em localhost:8000
Quando POST /api/ask {"question": "Quais doenças causam febre?"} é enviado
Então status HTTP 200 é retornado
E o body contém campos: answer, success, xai
E xai contém: entities, examples_used, sparql, validation, attempts, results_raw, results_count, timing
```

```gherkin
Dado que o pipeline retorna success=False (query sem resultados)
Quando POST /api/ask é processado
Então status HTTP 200 é retornado (não 4xx/5xx)
E body contém success=False com detalhes de explicabilidade
```

---

### RF-02 — Endpoint `GET /api/health` para verificação de status
🟡 **INFERIDO** — corrigido pelo Reviewer em 2026-05-04 após inspeção de `server.py:health()`

**Must**

Retornar status de saúde do servidor.

**Caminho real:** `/api/health` (não `/health` como spec original indicava). 🟢 CONFIRMADO — `server.py:153`.

**Response model real:** apenas `{status: str}` — os campos `version` e `pipeline_loaded` não existem no `HealthResponse`. 🟢 CONFIRMADO — `server.py:HealthResponse` (linha 63).

**Critérios de Aceitação:**

```gherkin
Dado o servidor rodando
Quando GET /api/health é chamado
Então status HTTP 200 é retornado
E body contém campo: status="ok"
```

> ⚠️ Spec original dizia `/health` e campos `version`, `pipeline_loaded` — ambos incorretos.

---

### RF-03 — Singleton lazy-init do pipeline
🟢 **CONFIRMADO** — `server.py:get_pipeline()`

**Must**

O `BioSPARQLPipeline` deve ser instanciado apenas uma vez por processo (na primeira chamada a `/api/ask`) e reutilizado em todas as requisições subsequentes.

**Critérios de Aceitação:**

```gherkin
Dado que o servidor acabou de iniciar (pipeline não carregado)
Quando o primeiro POST /api/ask é enviado
Então o pipeline é inicializado (carregamento de modelos ~30-60s)
E requisições subsequentes reutilizam a mesma instância (sem recarregamento)
```

---

### RF-04 — CORS restrito a origens locais
🟢 **CONFIRMADO** — `server.py:app.add_middleware(CORSMiddleware, ...)`

**Must**

Requisições cross-origin devem ser aceitas apenas de `localhost:5173` (Vite dev) e `localhost:3000` (Playwright).

**Critérios de Aceitação:**

```gherkin
Dado uma requisição com Origin: http://localhost:5173
Quando chega ao servidor
Então Access-Control-Allow-Origin: http://localhost:5173 é retornado

Dado uma requisição com Origin: http://example.com
Quando chega ao servidor
Então a requisição é rejeitada pelo CORS (sem Access-Control-Allow-Origin)
```

---

### RF-05 — Resposta de erro estruturada em caso de falha interna
🟡 **INFERIDO** — padrão FastAPI com HTTPException

**Should**

Em caso de erro interno não tratado pelo pipeline (ex: exceção inesperada), o servidor deve retornar JSON com detalhes do erro em vez de stack trace bruto.

---

## Requisitos Não Funcionais

### RNF-01 — Processamento síncrono por requisição
🟢 **CONFIRMADO** — handler `async def ask()` com await implícito via uvicorn

O endpoint `/api/ask` é síncrono em relação ao pipeline (não há paralelismo interno). Múltiplas requisições simultâneas são serializadas pelo singleton do pipeline.

### RNF-02 — Porta padrão 8000
🟢 **CONFIRMADO** — comando de startup em `CLAUDE.md`

O servidor deve escutar na porta 8000 por padrão.

### RNF-03 — Hot-reload não requerido em produção
🟡 **INFERIDO** — uvicorn sem `--reload` no startup

Modo de recarga automática (`--reload`) não é usado — o carregamento de modelos NLP tornaria o reload proibitivamente lento.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 POST /api/ask | **Must** | Endpoint principal do sistema |
| RF-02 GET /health | **Must** | Usado por gates e Playwright para aguardar inicialização |
| RF-03 Singleton lazy-init | **Must** | Modelos NLP não podem ser carregados a cada requisição |
| RF-04 CORS restrito | **Must** | Segurança mínima — sistema local acadêmico |
| RF-05 Erro estruturado | **Should** | Melhora debugabilidade sem afetar funcionalidade |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| `BioSPARQLPipeline` (módulo pipeline) | Módulo interno | Sim |
| FastAPI 0.135.3 | Biblioteca Python | Sim |
| Uvicorn 0.44.0 | Servidor ASGI | Sim |
| Pydantic 2.12.5 | Validação de modelos | Sim |
