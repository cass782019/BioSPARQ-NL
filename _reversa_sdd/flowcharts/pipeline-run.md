# Flowchart por Função — `BioSPARQLPipeline.run()`

> Gerado pelo Arqueólogo em 2026-05-04 | doc_level: detalhado
> Arquivo: `src/pipeline/nl_to_sparql.py`

## Loop principal de autocorreção

```mermaid
flowchart TD
    START([run: question: str]) --> INIT
    INIT[examples = retrieve_examples\nfeedback = None\nsemantic_retry_used = False\nmax_attempts = max_retries + 2\nattempt = 0] --> LOOP

    LOOP{attempt < max_attempts?} -- não --> FALLBACK
    LOOP -- sim --> INC[attempt += 1]

    INC --> PROMPT[build_prompt\nquestion + examples + feedback]
    PROMPT --> GEN[generate_sparql\nbackend.generate + post-proc]
    GEN -- LLMConnectionError --> ERR_LLM[return erro LLM\nsuccess=False]

    GEN --> VAL[validator.validate\nsparql_query]
    VAL --> VALID{valid?}

    VALID -- sim --> EXEC[execute_sparql\nFuseki]
    EXEC --> COUNT{count == 0 &&\nsemantic_retry &&\n!semantic_retry_used &&\nattempt < max_attempts?}

    COUNT -- sim --> SEMANTIC[semantic_retry_used = True\nfeedback = SEMANTIC_RETRY_FEEDBACK\nsalva last_result/query/validation]
    SEMANTIC --> LOOP

    COUNT -- não --> RETURN_OK[return\nquestion, sparql, validation\nexecution, attempts, success]

    VALID -- não --> MORE{attempt < max_attempts?}
    MORE -- sim --> FEEDBACK[feedback = validator.format_feedback\nerros + warnings + query]
    FEEDBACK --> LOOP

    MORE -- não --> LAST[execute_sparql\n última tentativa inválida]
    LAST --> RETURN_PARTIAL[return\nresultado parcial\nsuccess=False]

    FALLBACK[return last_result\nse semantic retry esgotou\nsuccess=False]

    style ERR_LLM fill:#f88,stroke:#c00
    style RETURN_OK fill:#8f8,stroke:#0a0
    style RETURN_PARTIAL fill:#fa8,stroke:#c60
    style FALLBACK fill:#fa8,stroke:#c60
```

## Semantic retry feedback (constante `SEMANTIC_RETRY_FEEDBACK`)

Quando query é válida sintática/semanticamente mas retorna 0 resultados, o pipeline envia ao LLM:
1. Instrução de usar labels em INGLÊS nos FILTER (febre→fever, etc.)
2. Padrão correto para consultar fenótipos em `urn:hpo` + `urn:hpoa`
3. Padrão correto de JOIN DOID↔HPOA com `BIND(REPLACE(..., "^MIM:", "OMIM:"))`
4. Proibição de usar `doid:`, `hpo:` como prefixos
