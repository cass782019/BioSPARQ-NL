# Tasks — api

> Unit: `src/api/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Definir modelos Pydantic

**Origem:** `src/api/server.py` — classes Pydantic
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

Implementar todos os modelos de request/response conforme `design.md`:

```python
from pydantic import BaseModel
from typing import Any

class AskRequest(BaseModel):
    question: str

class TimingInfo(BaseModel):
    ner_ms: float = 0.0
    faiss_ms: float = 0.0
    llm_ms: float = 0.0
    validation_ms: float = 0.0
    fuseki_ms: float = 0.0
    total_ms: float = 0.0

class ValidationInfo(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []

class ExampleUsed(BaseModel):
    question: str
    sparql: str
    similarity: float = 0.0

class ExplainabilityInfo(BaseModel):
    entities: list[str] = []
    examples_used: list[ExampleUsed] = []
    sparql: str = ""
    validation: ValidationInfo
    attempts: int = 1
    results_raw: list[Any] = []
    results_count: int = 0
    timing: TimingInfo

class AskResponse(BaseModel):
    answer: str
    success: bool
    xai: ExplainabilityInfo

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    pipeline_loaded: bool
```

**Critério de pronto:** Todos os modelos são instanciáveis. `AskResponse` serializa corretamente para JSON com `model.model_dump()`.

---

## T-02 — Implementar singleton `get_pipeline()`

**Origem:** `src/api/server.py:get_pipeline()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from src.pipeline.nl_to_sparql import BioSPARQLPipeline

_pipeline_instance: BioSPARQLPipeline | None = None

def get_pipeline() -> BioSPARQLPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = BioSPARQLPipeline()
    return _pipeline_instance
```

**Critério de pronto:**
- Duas chamadas consecutivas retornam o mesmo objeto (`is`)
- Não lança exceção se Fuseki ou LM Studio estiverem offline (pipeline usa graceful fallback)

---

## T-03 — Implementar `_format_answer(result)`

**Origem:** `src/api/server.py:_format_answer()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
def _format_answer(result: dict) -> str:
    execution = result.get("execution", {})
    count = execution.get("count", 0)
    bindings = execution.get("results", [])

    if count == 0:
        return "Nenhum resultado encontrado para esta consulta."

    def row_to_str(row: dict) -> str:
        return " | ".join(str(v.get("value", "")) for v in row.values())

    if count == 1:
        return f"Resultado: {row_to_str(bindings[0])}"

    lines = [f"- {row_to_str(row)}" for row in bindings[:10]]
    suffix = f"\n(exibindo 10 de {count})" if count > 10 else ""
    return f"Encontrados {count} resultado(s):\n" + "\n".join(lines) + suffix
```

**Critério de pronto:**
- `count=0` → string com "Nenhum resultado"
- `count=1` → string com "Resultado: ..."
- `count=5` → string com "Encontrados 5 resultado(s):" + 5 linhas
- `count=15` → exibe apenas 10 primeiros + nota de truncamento

---

## T-04 — Implementar endpoint `POST /api/ask`

**Origem:** `src/api/server.py:ask()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01, T-02, T-03

### Comportamento esperado

```python
from fastapi import FastAPI, HTTPException
from time import perf_counter

app = FastAPI()

@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    pipeline = get_pipeline()
    t_start = perf_counter()

    try:
        result = pipeline.run(request.question)
    except Exception as e:
        total_ms = (perf_counter() - t_start) * 1000
        return AskResponse(
            answer=f"Erro interno: {str(e)}",
            success=False,
            xai=ExplainabilityInfo(
                validation=ValidationInfo(valid=False, errors=[str(e)]),
                timing=TimingInfo(total_ms=total_ms)
            )
        )

    answer = _format_answer(result)
    total_ms = (perf_counter() - t_start) * 1000

    # Mapear resultado do pipeline para AskResponse
    timing = TimingInfo(
        ner_ms=result.get("timing", {}).get("ner_ms", 0),
        faiss_ms=result.get("timing", {}).get("faiss_ms", 0),
        llm_ms=result.get("timing", {}).get("llm_ms", 0),
        validation_ms=result.get("timing", {}).get("validation_ms", 0),
        fuseki_ms=result.get("timing", {}).get("fuseki_ms", 0),
        total_ms=total_ms,
    )
    validation = ValidationInfo(**result.get("validation", {"valid": True, "errors": [], "warnings": []}))
    examples = [ExampleUsed(**e) for e in result.get("examples_used", [])]

    xai = ExplainabilityInfo(
        entities=result.get("entities", []),
        examples_used=examples,
        sparql=result.get("sparql", ""),
        validation=validation,
        attempts=result.get("attempts", 1),
        results_raw=result.get("execution", {}).get("results", []),
        results_count=result.get("execution", {}).get("count", 0),
        timing=timing,
    )

    return AskResponse(answer=answer, success=result.get("success", False), xai=xai)
```

**Critério de pronto:**
- Pergunta válida com pipeline online → HTTP 200 com `AskResponse` completo
- Pergunta vazia → HTTP 400
- Exceção no pipeline → HTTP 200 com `success=False` e mensagem de erro (não HTTP 500)

---

## T-05 — Implementar endpoint `GET /health`

**Origem:** `src/api/server.py:health()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        pipeline_loaded=_pipeline_instance is not None,
    )
```

**Critério de pronto:**
- Antes do primeiro `/api/ask`: `pipeline_loaded=false`
- Após primeiro `/api/ask`: `pipeline_loaded=true`
- Sempre retorna HTTP 200

---

## T-06 — Configurar CORS e inicialização do app

**Origem:** `src/api/server.py` — bloco de configuração
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BioSPARQL-NL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Critério de pronto:** Requisição com `Origin: http://localhost:5173` recebe header `Access-Control-Allow-Origin` na resposta. Requisição de outra origem não recebe o header.
