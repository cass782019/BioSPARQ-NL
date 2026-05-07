# Máquinas de Estado — BioSPARQL-NL

> Gerado pelo Detetive em 2026-05-04 | doc_level: detalhado

---

## SM-01 — Loop de Geração SPARQL (`BioSPARQLPipeline.run()`)

**Localização:** `src/pipeline/nl_to_sparql.py:run()` (linhas 385–483)
**Confiança:** 🟢 CONFIRMADO — extraído diretamente do código

Esta é a máquina de estado central do sistema. Governa o ciclo de tentativas de geração, validação, execução e correção de queries SPARQL.

### Estados

| Estado | Descrição |
|---|---|
| `IDLE` | Pipeline aguardando pergunta (antes de `run()` ser chamado) |
| `GENERATING` | Chamada ao backend LLM em andamento |
| `VALIDATING` | Query submetida ao `SchemaValidator` |
| `INVALID_FEEDBACK` | Query inválida; feedback formatado para re-prompt |
| `EXECUTING` | Query válida enviada ao Fuseki |
| `SEMANTIC_RETRY` | Query válida mas 0 resultados; re-prompt com feedback semântico |
| `DONE_SUCCESS` | Resultado com ≥1 binding retornado |
| `DONE_EMPTY` | Todas as tentativas esgotadas; 0 resultados |
| `DONE_ERROR` | LLMConnectionError ou FusekiConnectionError irrecuperável |
| `DONE_INVALID_FORCED` | Última tentativa inválida — query executada mesmo assim |

### Diagrama de Estados (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> GENERATING : run(question) chamado

    GENERATING --> VALIDATING : SPARQL gerado + pós-processado
    GENERATING --> DONE_ERROR : LLMConnectionError

    VALIDATING --> EXECUTING : valid=True
    VALIDATING --> INVALID_FEEDBACK : valid=False AND attempts < max_attempts
    VALIDATING --> DONE_INVALID_FORCED : valid=False AND attempts == max_attempts

    INVALID_FEEDBACK --> GENERATING : re-prompt com erros de validação

    EXECUTING --> DONE_SUCCESS : count > 0
    EXECUTING --> SEMANTIC_RETRY : count == 0 AND NOT semantic_retry_used AND attempts < max_attempts
    EXECUTING --> DONE_EMPTY : count == 0 AND (semantic_retry_used OR attempts == max_attempts)

    SEMANTIC_RETRY --> GENERATING : re-prompt com SEMANTIC_RETRY_FEEDBACK
    SEMANTIC_RETRY : (flag semantic_retry_used = True)

    DONE_SUCCESS --> [*]
    DONE_EMPTY --> [*]
    DONE_ERROR --> [*]
    DONE_INVALID_FORCED --> [*]
```

### Tabela de Transições

| Estado atual | Condição | Próximo estado |
|---|---|---|
| `IDLE` | `run(question)` chamado | `GENERATING` |
| `GENERATING` | SPARQL gerado com sucesso | `VALIDATING` |
| `GENERATING` | `LLMConnectionError` | `DONE_ERROR` |
| `VALIDATING` | `valid=True` | `EXECUTING` |
| `VALIDATING` | `valid=False` AND `attempt < max_attempts` | `INVALID_FEEDBACK` |
| `VALIDATING` | `valid=False` AND `attempt == max_attempts` | `DONE_INVALID_FORCED` |
| `INVALID_FEEDBACK` | feedback formatado | `GENERATING` |
| `EXECUTING` | `count > 0` | `DONE_SUCCESS` |
| `EXECUTING` | `count == 0` AND `not semantic_retry_used` AND `attempt < max_attempts` | `SEMANTIC_RETRY` |
| `EXECUTING` | `count == 0` AND (`semantic_retry_used` OR `attempt == max_attempts`) | `DONE_EMPTY` |
| `SEMANTIC_RETRY` | feedback semântico preparado, `semantic_retry_used = True` | `GENERATING` |

### Contadores e limites

```
max_attempts = max_retries + 2   # padrão: 2 + 2 = 4 tentativas totais
semantic_retry: apenas 1 vez por execução de run()
```

---

## SM-02 — Estado do Backend LLM (`LMStudioBackend.generate()`)

**Localização:** `src/pipeline/llm_backends.py:LMStudioBackend.generate()`
**Confiança:** 🟢 CONFIRMADO

Micro-máquina de retry para chamadas HTTP ao LM Studio.

```mermaid
stateDiagram-v2
    [*] --> CALLING_LLM
    CALLING_LLM --> SUCCESS : response recebido
    CALLING_LLM --> RETRY : APITimeoutError ou APIConnectionError (attempt < 3)
    CALLING_LLM --> RAISE_ERROR : APITimeoutError ou APIConnectionError (attempt == 3)
    RETRY --> CALLING_LLM : backoff exponencial (2^attempt segundos)
    SUCCESS --> [*]
    RAISE_ERROR --> [*]
```

**Nota:** `max_tokens` é controlável via env var `LLM_MAX_TOKENS` (padrão: 3000). Modelos de raciocínio (Nemotron) consomem tokens em `reasoning_content` antes do `content` visível.

---

## SM-03 — Estado do `SchemaValidator`

**Localização:** `src/pipeline/sparql_validator.py`
**Confiança:** 🟢 CONFIRMADO

O validator tem dois modos de operação determinados na inicialização:

```mermaid
stateDiagram-v2
    [*] --> LOADING_SCHEMA
    LOADING_SCHEMA --> STRICT_MODE : schemas.json válido
    LOADING_SCHEMA --> PERMISSIVE_MODE : FileNotFoundError ou JSONDecodeError

    STRICT_MODE --> VALIDATING : validate(query) chamado
    PERMISSIVE_MODE --> VALIDATING : validate(query) chamado

    state VALIDATING {
        [*] --> CHECK_SYNTAX
        CHECK_SYNTAX --> CHECK_UNSAFE : sem erro de sintaxe
        CHECK_SYNTAX --> [*] : SYNTAX_ERROR → errors[]
        CHECK_UNSAFE --> CHECK_GRAPHS : sem DELETE/INSERT
        CHECK_UNSAFE --> [*] : UNSAFE_OPERATION → errors[]
        CHECK_GRAPHS --> CHECK_PREFIXES
        CHECK_PREFIXES --> CHECK_TERMS
        CHECK_TERMS --> [*] : (só em STRICT_MODE)
    }

    VALIDATING --> RESULT_VALID : errors == []
    VALIDATING --> RESULT_INVALID : errors != []
    RESULT_VALID --> [*]
    RESULT_INVALID --> [*]
```

**Diferença STRICT vs PERMISSIVE:** Em modo permissivo, `CHECK_TERMS` (validação de classes/predicados contra schema) é pulado. As demais checagens (sintaxe, unsafe, grafos, prefixos) ocorrem em ambos os modos.

---

## SM-04 — Estado do `ClaudeCLIBackend` (src2)

**Localização:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend`
**Confiança:** 🟢 CONFIRMADO

Gerencia subprocesso `claude` CLI com timeout explícito.

```mermaid
stateDiagram-v2
    [*] --> SPAWN_SUBPROCESS
    SPAWN_SUBPROCESS --> STREAMING : processo iniciado (cwd = ~/.biosparql-bench-workdir)
    STREAMING --> DONE_OK : stdout capturado, returncode == 0
    STREAMING --> DONE_TIMEOUT : TimeoutExpired (padrão 180s)
    STREAMING --> DONE_ERROR : returncode != 0
    DONE_OK --> [*]
    DONE_TIMEOUT --> [*] : kill() + raise LLMConnectionError
    DONE_ERROR --> [*] : raise LLMConnectionError
```

**Isolamento:** roda em diretório temporário fora de `proj1/` para evitar auto-discovery do `CLAUDE.md` e contaminação do contexto.

---

## SM-05 — Estado do Playwright Runner (`playwright_runner.py`)

**Localização:** `src2/evaluation/playwright_runner.py`
**Confiança:** 🟢 CONFIRMADO

Automação E2E sobre o frontend React.

```mermaid
stateDiagram-v2
    [*] --> BROWSER_LAUNCH
    BROWSER_LAUNCH --> PAGE_OPEN : Chromium headless iniciado
    PAGE_OPEN --> QUESTION_LOOP : http://localhost:3000 carregado

    state QUESTION_LOOP {
        [*] --> TYPE_INPUT
        TYPE_INPUT --> WAIT_RESPONSE : texto digitado no InputBar
        WAIT_RESPONSE --> CAPTURE_JSON : interceptou POST /api/ask response
        CAPTURE_JSON --> APPEND_LOG : JSON gravado em output2/playwright_log.jsonl
        APPEND_LOG --> [*] : próxima questão
    }

    QUESTION_LOOP --> BROWSER_CLOSE : todas as questões processadas
    BROWSER_CLOSE --> WRITE_SUMMARY : playwright_summary.json salvo
    WRITE_SUMMARY --> [*]
```
