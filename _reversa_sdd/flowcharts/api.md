# Flowchart — Módulo `api`

> Gerado pelo Arqueólogo em 2026-05-04

## Fluxo `POST /api/ask`

```mermaid
flowchart TD
    REQ[POST /api/ask\nAskRequest: question] --> EMPTY{question\nvazia?}
    EMPTY -- sim --> HTTP400[HTTP 400\nEmpty question]
    EMPTY -- não --> PIPE[get_pipeline\nsingleton lazy-init]

    PIPE --> NER[_extract_entities\npipe, question\n→ entities, ner_s]
    NER --> RETRIEVAL[_retrieve_examples\npipe, question\n→ examples, retrieval_s]
    RETRIEVAL --> RUN[pipe.run question\nt_llm_start = perf_counter]

    RUN -- Exception --> ERR[AskResponse\nsuccess=False\nxai com timing parcial]

    RUN --> FORMAT[_format_answer result\n0 resultados / 1 / N com lista]
    FORMAT --> TIMING[llm_s = perf_counter - t_llm_start\ntotal_s = ner_s + retrieval_s + llm_s]
    TIMING --> RESP[AskResponse\nanswer, success\nxai: ExplainabilityInfo completo]

    style HTTP400 fill:#f88
    style ERR fill:#fa8
    style RESP fill:#8f8
```

## Inicialização do Pipeline (singleton)

```mermaid
flowchart TD
    CALL[get_pipeline] --> CHECK{pipeline\nis None?}
    CHECK -- não --> RET[retorna instância existente]
    CHECK -- sim --> INIT[BioSPARQLPipeline\nconstrutor]
    INIT --> BACKENDS[inicializa:\nLLM backend\nEntityLinker\nFAISS index\nschemas\nSchemaValidator]
    BACKENDS --> RET
```

## Formatação da resposta NL (`_format_answer`)

```
count == 0  → "Nenhum resultado encontrado."
count == 1  → "Resultado: val1 | val2 | ..."
count > 1   → "Encontrados N resultados:\n- val1 | val2\n- ..."
```
