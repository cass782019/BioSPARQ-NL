# Contracts — api

> Unit: `src/api/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Contrato HTTP REST — BioSPARQL-NL API

Base URL: `http://localhost:8000`

---

## `POST /api/ask`

### Request

```
POST /api/ask HTTP/1.1
Content-Type: application/json
Origin: http://localhost:5173
```

**Body:**
```json
{
  "question": "Quais doenças estão associadas ao fenótipo febre?"
}
```

| Campo | Tipo | Obrigatório | Restrições |
|---|---|---|---|
| `question` | string | Sim | Não pode ser vazia ou somente espaços |

### Response — Sucesso (`200 OK`)

```json
{
  "answer": "Encontrados 12 resultado(s):\n- Familial Mediterranean Fever | DOID:2987\n- ...",
  "success": true,
  "xai": {
    "entities": ["DOID:14330", "HP:0001945"],
    "examples_used": [
      {
        "question": "Quais fenótipos estão associados ao Parkinson?",
        "sparql": "SELECT ?phenotype WHERE { ... }",
        "similarity": 0.87
      }
    ],
    "sparql": "SELECT DISTINCT ?disease ?label WHERE {\n  GRAPH <urn:hpoa> { ... }\n}",
    "validation": {
      "valid": true,
      "errors": [],
      "warnings": []
    },
    "attempts": 2,
    "results_raw": [
      {"disease": {"type": "uri", "value": "http://purl.obolibrary.org/obo/DOID_2987"},
       "label": {"type": "literal", "value": "Familial Mediterranean Fever"}}
    ],
    "results_count": 12,
    "timing": {
      "ner_ms": 45.2,
      "faiss_ms": 3.1,
      "llm_ms": 8420.5,
      "validation_ms": 12.0,
      "fuseki_ms": 280.3,
      "total_ms": 8761.1
    }
  }
}
```

### Response — Sem resultados (`200 OK`, `success=false`)

```json
{
  "answer": "Nenhum resultado encontrado para esta consulta.",
  "success": false,
  "xai": {
    "entities": [],
    "examples_used": [...],
    "sparql": "SELECT ?x WHERE { ... }",
    "validation": {"valid": true, "errors": [], "warnings": []},
    "attempts": 4,
    "results_raw": [],
    "results_count": 0,
    "timing": { ... }
  }
}
```

### Response — Pergunta vazia (`400 Bad Request`)

```json
{
  "detail": "Empty question"
}
```

### Response — Erro interno (`200 OK`, tratado pelo pipeline)

```json
{
  "answer": "Erro interno: LLMConnectionError: ...",
  "success": false,
  "xai": {
    "entities": [],
    "examples_used": [],
    "sparql": "",
    "validation": {"valid": false, "errors": ["LLMConnectionError: ..."], "warnings": []},
    "attempts": 0,
    "results_raw": [],
    "results_count": 0,
    "timing": {"total_ms": 30012.0, ...}
  }
}
```

> **Nota:** Erros internos do pipeline retornam HTTP 200 (não 500) com `success=false`. Isso é uma decisão de design — o frontend trata `success` como indicador de falha. 🟢 CONFIRMADO

---

## `GET /health`

### Request

```
GET /health HTTP/1.1
```

### Response — Sucesso (`200 OK`)

```json
{
  "status": "ok",
  "version": "1.0.0",
  "pipeline_loaded": true
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | string | Sempre `"ok"` se servidor está respondendo |
| `version` | string | Versão da API |
| `pipeline_loaded` | boolean | `false` antes do primeiro `/api/ask`, `true` após |

---

## Headers CORS

| Header | Valor | Condição |
|---|---|---|
| `Access-Control-Allow-Origin` | `http://localhost:5173` ou `http://localhost:3000` | Apenas para origens permitidas |
| `Access-Control-Allow-Credentials` | `true` | Sempre |
| `Access-Control-Allow-Methods` | `*` | Em preflight OPTIONS |
| `Access-Control-Allow-Headers` | `*` | Em preflight OPTIONS |

---

## Invariantes do Contrato

🟢 **CONFIRMADO**

1. `/api/ask` **sempre** retorna HTTP 200 — erros de pipeline são encapsulados em `success=false`
2. `/health` **sempre** retorna HTTP 200 enquanto o servidor estiver rodando
3. O campo `xai` **sempre** está presente na resposta de `/api/ask`, mesmo em caso de erro
4. `results_raw` contém bindings no formato SPARQL JSON (`{"type": "uri"|"literal", "value": "..."}`)
5. `timing` tem todos os campos presentes, com `0.0` para etapas não executadas

---

## Compatibilidade com Playwright Runner

O `playwright_runner.py` (src2) intercepta respostas de `POST /api/ask` via `page.on("response", ...)` e espera exatamente este schema JSON. Mudanças no contrato **quebram** o Playwright runner sem necessidade de alterar o frontend visualmente.

🟢 **CONFIRMADO** — `src2/evaluation/playwright_runner.py:handle_response()`
