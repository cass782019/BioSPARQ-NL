# User Stories — Fluxo: Consulta via API REST

> Gerado pelo Redator (Writer) em 2026-05-04 | doc_level: detalhado
> Ator principal: Desenvolvedor ou sistema externo consumindo a API diretamente

---

## Contexto

O desenvolvedor ou um sistema automatizado (ex: script de avaliação, Playwright runner) chama os endpoints REST do backend FastAPI em `http://localhost:8000` sem passar pela interface web. Os dois endpoints disponíveis são `POST /api/ask` e `GET /health`.

---

## US-01 — Consulta via API com resposta bem-sucedida

**Como** desenvolvedor ou sistema automatizado,
**quero** chamar `POST /api/ask` com uma pergunta em linguagem natural,
**para** receber o SPARQL gerado, as entidades detectadas e os resultados de forma programática.

### Critérios de Aceitação

```gherkin
Dado que o servidor FastAPI está rodando em localhost:8000
E o Fuseki está rodando em localhost:3030 com os grafos carregados
E o LLM backend está disponível
Quando POST /api/ask é chamado com body {"question": "Quais fenótipos estão associados ao Parkinson?"}
Então o status HTTP retornado é 200
E o body contém o campo "answer" com texto descritivo dos resultados
E o body contém "success": true
E o body contém o campo "xai" com subcampos: entities, examples_used, sparql, validation, attempts, results_raw, results_count, timing
E results_count >= 1
```

**Rastreabilidade:** 🟢 `src/api/server.py:ask()`, `api/contracts.md`

---

## US-02 — Consulta com pipeline retornando 0 resultados

**Como** desenvolvedor ou sistema automatizado,
**quero** que o endpoint retorne HTTP 200 mesmo quando não há resultados,
**para** distinguir falha de consulta (success=false) de falha de servidor (5xx) sem lógica de exceção.

### Critérios de Aceitação

```gherkin
Dado que o pipeline processou a pergunta mas o Fuseki retornou 0 resultados
Quando a resposta de POST /api/ask chega
Então o status HTTP é 200
E o body contém "success": false
E o body contém "results_count": 0
E o body contém "results_raw": []
E o campo "xai" está presente com sparql, validation e timing preenchidos
E o campo "answer" contém mensagem explicativa (ex: "Nenhum resultado encontrado para esta consulta.")
```

**Rastreabilidade:** 🟢 `src/api/server.py:ask()` — decisão de design: erros de pipeline encapsulados em success=false, não em HTTP 4xx/5xx

---

## US-03 — Verificação de saúde do servidor antes de enviar consultas

**Como** desenvolvedor ou sistema de orquestração (ex: gate6, Playwright runner),
**quero** consultar `GET /health` antes de enviar perguntas,
**para** aguardar o servidor estar pronto sem gerar erros de conexão recusada.

### Critérios de Aceitação

```gherkin
Dado que o servidor FastAPI está rodando
Quando GET /health é chamado
Então o status HTTP é 200
E o body contém "status": "ok"
E o body contém "pipeline_loaded": false (antes da primeira chamada a /api/ask)
E o body contém "version" com a versão da API
```

```gherkin
Dado que o primeiro POST /api/ask já foi processado (pipeline inicializado)
Quando GET /health é chamado
Então "pipeline_loaded": true é retornado
```

**Rastreabilidade:** 🟢 `src/api/server.py:health()`, `src/api/server.py:get_pipeline()` — lazy init via global

---

## US-04 — Rejeição de pergunta vazia

**Como** desenvolvedor,
**quero** receber HTTP 400 quando enviar uma pergunta vazia,
**para** identificar rapidamente erros de integração no meu cliente.

### Critérios de Aceitação

```gherkin
Dado que POST /api/ask é chamado com body {"question": ""}
Quando o servidor valida o request
Então o status HTTP é 400
E o body contém {"detail": "Empty question"}
E o pipeline não é invocado
```

```gherkin
Dado que POST /api/ask é chamado com body {"question": "   "} (só espaços)
Quando o servidor valida o request
Então o status HTTP é 400
E o body contém {"detail": "Empty question"}
```

**Rastreabilidade:** 🟢 `src/api/server.py:ask()` — validação via Pydantic + guard explícito

---

## US-05 — Erro interno encapsulado (LLM ou Fuseki indisponível)

**Como** desenvolvedor,
**quero** receber um JSON estruturado mesmo quando o pipeline falha internamente,
**para** logar o erro sem tratar exceções HTTP 500.

### Critérios de Aceitação

```gherkin
Dado que o LLM backend está indisponível (LMStudio desligado ou API key inválida)
Quando POST /api/ask é chamado
Então o status HTTP é 200
E o body contém "success": false
E o body contém "answer" com mensagem de erro descritiva (ex: "Erro interno: LLMConnectionError: ...")
E o campo "xai" está presente com "errors" contendo a descrição do erro
E "results_count": 0 e "results_raw": []
```

```gherkin
Dado que o Fuseki está inacessível em localhost:3030
Quando POST /api/ask é chamado e o pipeline tenta executar a query
Então o status HTTP é 200
E o body contém "success": false com descrição do erro de conexão
```

**Rastreabilidade:** 🟢 `src/api/server.py:ask()` — tratamento de exceção com retorno de AskResponse com success=false; 🟢 `api/contracts.md` — invariante 1

---

## US-06 — Controle de CORS para origens locais

**Como** desenvolvedor de frontend rodando em localhost:5173,
**quero** que o servidor aceite minhas requisições cross-origin,
**para** que o browser não bloqueie as chamadas durante o desenvolvimento.

### Critérios de Aceitação

```gherkin
Dado uma requisição com header "Origin: http://localhost:5173"
Quando chega ao servidor FastAPI
Então a resposta inclui "Access-Control-Allow-Origin: http://localhost:5173"
E a requisição é processada normalmente
```

```gherkin
Dado uma requisição com header "Origin: http://localhost:3000" (Playwright)
Quando chega ao servidor FastAPI
Então a resposta inclui "Access-Control-Allow-Origin: http://localhost:3000"
```

```gherkin
Dado uma requisição com header "Origin: http://example.com" (origem não permitida)
Quando chega ao servidor FastAPI
Então a resposta não inclui "Access-Control-Allow-Origin" para essa origem
E o browser bloqueia a requisição (CORS rejeitado)
```

**Rastreabilidade:** 🟢 `src/api/server.py` — `CORSMiddleware` com `allow_origins=["http://localhost:5173", "http://localhost:3000"]`

---

## US-07 — Inicialização lazy do pipeline (primeira requisição mais lenta)

**Como** desenvolvedor,
**quero** entender que a primeira chamada ao endpoint demora mais por inicializar o pipeline,
**para** calibrar corretamente timeouts no meu cliente e não interpretar a demora como falha.

### Critérios de Aceitação

```gherkin
Dado que o servidor acabou de iniciar (nenhuma requisição processada)
E GET /health retorna "pipeline_loaded": false
Quando o primeiro POST /api/ask é enviado
Então o servidor carrega o BioSPARQLPipeline (modelos NLP ~30-60s)
E durante esse tempo, /health retorna "pipeline_loaded": false
E após a inicialização, a resposta ao /api/ask é retornada normalmente
E requisições subsequentes reutilizam a instância (sem recarregamento)
```

**Rastreabilidade:** 🟢 `src/api/server.py:get_pipeline()` — padrão singleton com `_pipeline = None`; 🟢 `api/requirements.md` RF-03

---

## US-08 — Uso pelo Playwright runner (avaliação automatizada)

**Como** script de avaliação automatizada (Playwright runner),
**quero** interceptar as respostas de `/api/ask` via frontend,
**para** coletar métricas das 30 questões do gold standard de forma realista (passando pelo browser).

### Critérios de Aceitação

```gherkin
Dado que o Playwright runner está executando com frontend em localhost:3000
E o backend FastAPI está em localhost:8000 (proxiado pelo Vite)
Quando playwright_runner.py submete cada questão via interface web e intercepta a resposta de /api/ask
Então o JSON interceptado contém exatamente o schema definido em api/contracts.md
E os campos xai.entities, xai.sparql, xai.validation, xai.timing, xai.results_count estão presentes
E o resultado é salvo em output2/playwright_log.jsonl
```

**Rastreabilidade:** 🟢 `src2/evaluation/playwright_runner.py:handle_response()` — intercepta /api/ask via `page.on("response", ...)`

---

## Estrutura da resposta `AskResponse` (referência rápida)

```
AskResponse
├── answer          string    Texto legível para humanos com resumo dos resultados
├── success         boolean   true = resultados encontrados; false = falha ou 0 resultados
└── xai
    ├── entities        list[str]    CURIEs detectados pelo NER (ex: ["DOID:14330", "HP:0001945"])
    ├── examples_used   list[dict]   Exemplos few-shot recuperados pelo FAISS
    ├── sparql          string       Query SPARQL final enviada ao Fuseki
    ├── validation
    │   ├── valid       boolean
    │   ├── errors      list[str]
    │   └── warnings    list[str]
    ├── attempts        int          Número de tentativas do loop de autocorreção (1–4)
    ├── results_raw     list[dict]   Bindings SPARQL JSON do Fuseki
    ├── results_count   int          len(results_raw)
    └── timing
        ├── ner_ms          float
        ├── faiss_ms        float
        ├── llm_ms          float
        ├── validation_ms   float
        ├── fuseki_ms       float
        └── total_ms        float
```

---

## Invariantes do Contrato

| Invariante | Confiança |
|---|---|
| `POST /api/ask` sempre retorna HTTP 200 (erros encapsulados em success=false) | 🟢 CONFIRMADO |
| `GET /health` sempre retorna HTTP 200 enquanto o servidor responde | 🟢 CONFIRMADO |
| Campo `xai` sempre presente na resposta de `/api/ask` | 🟢 CONFIRMADO |
| `timing` sempre presente com todos os campos (0.0 para etapas não executadas) | 🟢 CONFIRMADO |
| Mudanças neste contrato quebram o Playwright runner sem aviso visual | 🟢 CONFIRMADO |
