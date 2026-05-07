# Flowchart — Módulo `ner`

> Gerado pelo Arqueólogo em 2026-05-04

## Seleção e uso do backend NER

```mermaid
flowchart TD
    ENV[NER_BACKEND env var\npadrão: scispacy] --> FACTORY[ner/factory.py\nget_backend]
    FACTORY --> CACHE{lru_cache\nhit?}
    CACHE -- sim --> INST[instância existente]
    CACHE -- não --> LOAD[importa classe\nvia REGISTRY]
    LOAD --> WARMUP[inst.warm_up\ncarrega modelos]
    WARMUP --> INST

    INST --> EXTRACT[backend.extract: text]
    EXTRACT --> OUT[list Entity]
    OUT --> MERGE[merge_overlaps\ndedup por score]
```

## Backend ScispaCy (padrão)

```mermaid
flowchart TD
    TEXT[texto da pergunta] --> NLP[spacy nlp text\nen_core_sci_sm]
    NLP --> ENTS[doc.ents]
    ENTS --> NOISE{_is_noise?\nlen<4, stopwords,\nratio alfa<0.5}
    NOISE -- sim --> SKIP[descarta span]
    NOISE -- não --> RESOLVE[_resolve via Fuseki\nrdfs:label LCASE match]
    RESOLVE --> FOUND{match?}
    FOUND -- sim --> CURIE[uri → CURIE\nDOID:*, HP:*]
    FOUND -- não --> EMPTY[ontology_ids=[]]
    CURIE & EMPTY --> ENTITY[Entity dataclass]
```

## Backend LLM+Gilda

```mermaid
flowchart TD
    TEXT[texto] --> LLM[POST LM Studio\nsystem: NER JSON schema\nresponse_format: json_object]
    LLM --> PARSE[JSON parse\nentities: text, type, start, end]
    PARSE --> GILDA[gilda.ground span_text\npor cada entidade]
    GILDA --> FILTER[filtra score >= 0.5\nnamespaces: DOID HP OMIM MESH]
    FILTER --> ENTITY[Entity dataclass\nsem alucinação de IDs]
    ENTITY --> MERGE[merge_overlaps]
```

## EntityLinker — Adapter

```mermaid
flowchart TD
    EL[EntityLinker.extract_entities text] --> BACKEND{_backend?}
    BACKEND -- None --> EMPTY[retorna []]
    BACKEND -- ok --> EXTRACT[backend.extract text]
    EXTRACT --> CONV[_entity_to_dict\nEntity → dict com uri+graph]
    CONV --> FORMAT[format_for_prompt\nlista formatada para LLM]
```
