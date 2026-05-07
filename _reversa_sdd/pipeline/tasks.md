# Tasks — pipeline

> Unit: `src/pipeline/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Instruções de uso

Cada tarefa é autossuficiente: contém o comportamento esperado, o arquivo de origem e o critério de pronto. Um agente de IA sem acesso ao código original pode reimplementar cada tarefa a partir deste documento.

Execute as tarefas **na ordem listada** — há dependências entre elas (ex: T-03 depende de T-01 e T-02).

---

## T-01 — Implementar `BioSPARQLPipeline.__init__(config)`

**Origem:** `src/pipeline/nl_to_sparql.py:BioSPARQLPipeline.__init__()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

Inicializar o pipeline com os parâmetros de configuração e carregar todos os subcomponentes com graceful fallback.

1. Mesclar `config` (dict ou None) com defaults:
   - `endpoint`: `"http://localhost:3030/biomedical/sparql"`
   - `lm_studio_url`: `"http://localhost:1234/v1"`
   - `llm_model`: `os.environ.get("LLM_MODEL", "auto")`
   - `max_retries`: `2`
   - `top_k_examples`: `3`
   - `llm_timeout`: `float(os.environ.get("LLM_TIMEOUT", 300))`
   - `fuseki_timeout`: `30`
   - `disable_ner`: `False`
   - `disable_schema`: `False`
   - `semantic_retry`: `True`

2. Criar backend LLM via `create_backend(config)`:
   - Se `config['backend'] == 'anthropic'` → `AnthropicBackend`
   - Caso contrário → `LMStudioBackend`

3. Carregar NER (`EntityLinker`) com try/except → se falhar, `self.entity_linker = None`

4. Carregar FAISS index de `data/gold_standard/questions.index`:
   - Se ausente → `self.index = None`, `self.examples = []`

5. Carregar `data/gold_standard/questions.json` → `self.examples`

6. Carregar `data/schemas.json` → `self.schemas` (None se ausente)

7. Instanciar `SchemaValidator(schemas)`

8. `self._embedder = None` (lazy-load no primeiro uso de `retrieve_examples`)

**Critério de pronto:** Pipeline instancia sem exceção mesmo com Fuseki, LM Studio, NER e arquivos de dados ausentes.

---

## T-02 — Implementar `SchemaValidator`

**Origem:** `src/pipeline/sparql_validator.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

**Inicialização:**
- Tentar carregar `schemas` (dict). Se inválido ou ausente → `self.permissive_mode = True`
- `self.valid_graphs = {"urn:doid", "urn:hpo", "urn:hpoa"}` (hardcoded)

**`validate(sparql_query: str) → dict`:**

Executar checagens na ordem:
1. **CHECK_SYNTAX:** tentar parsear com `rdflib.plugins.sparql.prepareQuery()`. Falha → `errors.append("SYNTAX_ERROR: ...")`
2. **CHECK_UNSAFE:** regex para `\b(DELETE|INSERT|UPDATE)\b` → `errors.append("UNSAFE_OPERATION")`
3. **CHECK_GRAPHS:** extrair grafos da query (regex `FROM\s+<(.+?)>` e `GRAPH\s+<(.+?)>`). Se grafo não está em `valid_graphs` → `warnings.append(...)`
4. **CHECK_PREFIXES:** detectar prefixos declarados vs. conhecidos
5. **CHECK_TERMS** (só STRICT): verificar classes e predicados contra `schemas`

Retorno: `{"valid": bool, "errors": list, "warnings": list}`

**`format_feedback(validation_result, original_query) → str`:**

Formatar string de feedback para o LLM com os erros e warnings encontrados, incluindo trecho da query original para contexto.

**Critério de pronto:** `validate()` retorna `valid=False` com `"UNSAFE_OPERATION"` para qualquer query com DELETE ou INSERT; retorna `valid=True` para query SELECT válida contra grafos corretos.

---

## T-03 — Implementar `BioSPARQLPipeline._fix_common_errors(query)`

**Origem:** `src/pipeline/nl_to_sparql.py:_fix_common_errors()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

Aplicar 9 transformações regex sequenciais na ordem exata:

```python
# ① Remover blocos DECLARE { ... } preservando PREFIX internos
query = re.sub(r'DECLARE\s*[\{\(].*?[\}\)]', extract_prefixes_fn, query, flags=re.DOTALL)

# ② Remover pseudo-keywords soltas (linha inteira)
query = re.sub(r'^\s*(DECLARE|IMPORT|USE|NAMESPACE)\b.*$', '', query, flags=re.MULTILINE)

# ③ Canonicalizar URIs de prefixos (9 prefixos conhecidos)
for prefix, canonical_uri in KNOWN_PREFIXES.items():
    query = re.sub(rf'PREFIX\s+{prefix}:\s*<[^>]+>', f'PREFIX {prefix}: <{canonical_uri}>', query)

# ④a Corrigir oboInOwl#localname → oboInOwl:localname (fora de URIs <...>)
query = re.sub(r'(?<!<[^>]*)oboInOwl#(\w+)', r'oboInOwl:\1', query)

# ④b Corrigir pred = ?var → pred ?var
query = re.sub(r'(\S+)\s*=\s*(\?[\w]+)(?!\s*[,\)])', r'\1 \2', query)

# ④c Remover PREFIX usando URNs de grafo como namespace
query = re.sub(r'PREFIX\s+\w+:\s*<urn:(doid|hpo|hpoa)>\s*', '', query)

# ⑤ Corrigir URIs de grafo abreviadas
for g in ['doid', 'hpo', 'hpoa']:
    query = re.sub(rf'GRAPH\s+<{g}>', f'GRAPH <urn:{g}>', query)
    query = re.sub(rf'GRAPH\s+{g}:', f'GRAPH <urn:{g}>', query)

# ⑥ Remover asserções com prefixos inválidos
query = re.sub(r'\?\w+\s+a\s+(doid|hpo):\w+\s*\.', '', query)
query = query.replace('doid:Disease', 'obo:DOID_4')
query = query.replace('hpo:HumanPhenotype', 'obo:HP_0000118')

# ⑦ Mover FILTERs após o último } para dentro do WHERE
# Detectar FILTERs após último } e reinseri-los antes dele
...

# ⑧ Corrigir BIND com auto-referência (?x ... AS ?x)
# Renomear variável fonte para ?x_mim antes do BIND
...
```

**Critério de pronto:** Para cada uma das 9 transformações, existe ao menos um teste unitário que verifica a entrada problemática e a saída corrigida.

---

## T-04 — Implementar `BioSPARQLPipeline._inject_missing_prefixes(query)`

**Origem:** `src/pipeline/nl_to_sparql.py:_inject_missing_prefixes()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

1. Extrair prefixos já declarados na query (regex `PREFIX\s+(\w+):`)
2. Encontrar prefixos usados no corpo: regex `(\w+):[A-Z_]\w+` (CURIEs) e `(\w+):\w+` em predicados
3. Para cada prefixo usado não declarado que esteja em `KNOWN_PREFIXES`, prepend `PREFIX prefix: <uri>` ao início da query
4. Retornar query com prefixos injetados

**Critério de pronto:** Query que usa `obo:DOID_4` sem declarar `PREFIX obo:` recebe a declaração injetada automaticamente.

---

## T-05 — Implementar `BioSPARQLPipeline.retrieve_examples(question, top_k=3)`

**Origem:** `src/pipeline/nl_to_sparql.py:retrieve_examples()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

1. Se `self.index is None` → retornar `[]`
2. Lazy-load do embedder: `if self._embedder is None: self._embedder = SentenceTransformer("all-MiniLM-L6-v2")`
3. Embed a `question` com `_embedder.encode([question], normalize_embeddings=True)`
4. Pesquisar no FAISS com `self.index.search(embedding, top_k)` → índices `I` e distâncias `D`
5. Retornar `[self.examples[i] for i in I[0]]` como lista de dicts com campos `"question"` e `"sparql"`

**Critério de pronto:** Retorna 3 dicts quando index está carregado; retorna `[]` quando index é None, sem lançar exceção.

---

## T-06 — Implementar `BioSPARQLPipeline.execute_sparql(query)`

**Origem:** `src/pipeline/nl_to_sparql.py:execute_sparql()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

1. Enviar query ao Fuseki via `SPARQLWrapper` com `timeout=fuseki_timeout`
2. Definir `Accept: application/sparql-results+json`
3. Retornar `{"success": True, "results": bindings, "count": len(bindings)}` se sucesso
4. Em caso de timeout ou connection error → retornar `{"success": False, "results": [], "count": 0, "error": str(e)}`

**Critério de pronto:** Retorna dict com `success`, `results` e `count` em todos os casos (sucesso, timeout, erro de conexão).

---

## T-07 — Implementar backends LLM (`LMStudioBackend`, `AnthropicBackend`)

**Origem:** `src/pipeline/llm_backends.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### `LMStudioBackend.generate(system, user_msg) → str`

1. Instanciar `openai.OpenAI(base_url=lm_studio_url, api_key="lm-studio")`
2. Chamar `client.chat.completions.create(model=model, messages=[...], max_tokens=max_tokens, timeout=timeout)`
3. Em `APITimeoutError` ou `APIConnectionError`: retry até 3x com `time.sleep(2**attempt)`
4. Após 3 falhas → lançar `LLMConnectionError`
5. Extrair `response.choices[0].message.content` (ignorar `reasoning_content` se presente)

### `AnthropicBackend.generate(system, user_msg) → str`

1. Instanciar `anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)`
2. Chamar `client.messages.create(model=model, system=system, messages=[{"role":"user","content":user_msg}])`
3. Retornar `response.content[0].text`

**Critério de pronto:** `LMStudioBackend` retorna string e executa retry em timeout; `AnthropicBackend` retorna string dado API key válido.

---

## T-08 — Implementar `BioSPARQLPipeline.run(question)` — Loop principal

**Origem:** `src/pipeline/nl_to_sparql.py:run()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01, T-02, T-03, T-04, T-05, T-06, T-07

### Comportamento esperado

Implementar o loop de autocorreção conforme diagrama em `design.md`:

```
max_attempts = config['max_retries'] + 2   # padrão: 4
semantic_retry_used = False
feedback = None

for attempt in range(1, max_attempts + 1):
    system, user_msg = build_prompt(question, examples, feedback)
    try:
        sparql_raw = backend.generate(system, user_msg)
    except LLMConnectionError:
        return error_response(...)

    sparql = _fix_common_errors(sparql_raw)
    sparql = _inject_missing_prefixes(sparql)
    validation = validator.validate(sparql)

    if validation['valid']:
        result = execute_sparql(sparql)
        if result['count'] == 0 and config['semantic_retry'] and not semantic_retry_used and attempt < max_attempts:
            semantic_retry_used = True
            feedback = SEMANTIC_RETRY_FEEDBACK
            last_result = result
            continue
        return build_response(success=result['count'] > 0, ...)
    else:
        if attempt < max_attempts:
            feedback = validator.format_feedback(validation, sparql)
        else:
            # última tentativa: executa mesmo inválida
            result = execute_sparql(sparql)
            return build_response(success=False, ...)

# esgotou semantic retry
return build_response(success=False, last_result, ...)
```

**Critério de pronto:**
- Pergunta simples com Fuseki online → `success=True` em 1 tentativa
- LLM gera query inválida 3x consecutivas → `attempts=4`, `success=False`
- LLM offline → retorno imediato com `success=False` e mensagem de erro

---

## T-09 — Implementar `BioSPARQLPipeline.build_prompt(question, examples, feedback)`

**Origem:** `src/pipeline/nl_to_sparql.py:build_prompt()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

**System prompt** deve incluir (nesta ordem):
1. Papel: especialista em SPARQL sobre ontologias biomédicas
2. Grafos disponíveis com responsabilidades (RN-03)
3. Regra PT→EN para labels (RN-02)
4. Regra MIM→OMIM para JOIN cross-graph (RN-01)
5. Prefixos proibidos: `doid:`, `hpo:` (RN-04)
6. Schema das classes/predicados por grafo (de `self.schemas`, formatado)
7. Exemplos few-shot formatados como `# Pergunta:\n# SPARQL:\n`
8. Se `feedback` não None: seção "Feedback do validador" com os erros

**User message:** pergunta original em português

**Retorno:** `tuple[str, str]` — (system_prompt, user_message)

**Critério de pronto:** System prompt contém todos os 8 elementos; feedback de validação aparece no system quando fornecido.

---

## T-10 — Implementar `BioSPARQLPipeline._extract_sparql(raw)`

**Origem:** `src/pipeline/nl_to_sparql.py:_extract_sparql()` (linha 164) [identificado pelo Reviewer]
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** — (método estático, sem dependências)

### Comportamento esperado

Método estático que extrai a query SPARQL do texto bruto retornado pelo LLM, removendo delimitadores de blocos Markdown se presentes.

```python
@staticmethod
def _extract_sparql(raw: str) -> str:
    if "```sparql" in raw:
        return raw.split("```sparql")[1].split("```")[0].strip()
    elif "```" in raw:
        return raw.split("```")[1].split("```")[0].strip()
    return raw.strip()
```

É chamado por `generate_sparql()` como primeiro passo antes de `_fix_common_errors()`.

**Critério de pronto:** Para entrada com ` ```sparql\nSELECT ...\n``` `, retorna apenas `SELECT ...` sem delimitadores. Para entrada sem Markdown, retorna o texto original com strip.
