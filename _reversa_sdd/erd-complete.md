# ERD Completo — BioSPARQL-NL

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Nota sobre o modelo de dados

BioSPARQL-NL não usa banco de dados relacional. Seu "modelo de dados" é composto de:

1. **Entidades de runtime** — dataclasses Python em memória (sem persistência entre requests)
2. **Entidades RDF** — triplas no triplestore Fuseki (DOID, HPO, HPOA)
3. **Arquivos estáticos** — JSON/FAISS/binary (dados de configuração e golden standard)

Este ERD documenta as estruturas de dados do sistema, seus atributos e relacionamentos.

---

## ERD — Entidades de Runtime (Python)

```mermaid
erDiagram
    AskRequest {
        string question PK "Pergunta em linguagem natural (PT)"
    }

    AskResponse {
        string answer "Resposta textual formatada"
        bool success "True se query retornou resultados"
        ExplainabilityInfo xai "Dados de explicabilidade"
    }

    ExplainabilityInfo {
        list_string entities "CURIEs detectados (DOID:*, HP:*)"
        list_ExampleUsed examples_used "Exemplos few-shot recuperados"
        string sparql "Query SPARQL final gerada"
        ValidationInfo validation "Resultado da validação"
        int attempts "Número de tentativas (1-4)"
        list_dict results_raw "Bindings brutos do Fuseki"
        int results_count "Quantidade de resultados"
        TimingInfo timing "Breakdown de latências"
    }

    ExampleUsed {
        string question "Pergunta do gold standard"
        string sparql "Query SPARQL de referência"
        float similarity "Score cosine FAISS (0-1)"
    }

    ValidationInfo {
        bool valid "True se SPARQL passou na validação"
        list_string errors "Erros bloqueantes"
        list_string warnings "Avisos não-bloqueantes"
    }

    TimingInfo {
        float ner_ms "Latência NER em milissegundos"
        float faiss_ms "Latência recuperação FAISS"
        float llm_ms "Latência geração LLM"
        float validation_ms "Latência validação schema"
        float fuseki_ms "Latência execução Fuseki"
        float total_ms "Latência total end-to-end"
    }

    Entity {
        string text "Span de texto identificado"
        int start "Offset inicial (char)"
        int end "Offset final (char)"
        string type "DISEASE | PHENOTYPE | ..."
        list_string ontology_ids "CURIEs resolvidos [DOID:*, HP:*]"
        list_float scores "Scores de grounding"
        string backend "scispacy | llm | gilda"
    }

    PipelineConfig {
        string endpoint "URL SPARQL Fuseki"
        string lm_studio_url "URL LM Studio"
        string llm_model "Modelo ativo"
        int max_retries "Máx tentativas extras (padrão 2)"
        int top_k_examples "Exemplos few-shot (padrão 3)"
        float llm_timeout "Timeout LLM em segundos (300)"
        int fuseki_timeout "Timeout Fuseki em segundos (30)"
        bool disable_ner "Desativa NER (ablação)"
        bool disable_schema "Desativa validação (ablação)"
        bool semantic_retry "Habilita semantic retry"
    }

    AskRequest ||--|| AskResponse : "gera"
    AskResponse ||--|| ExplainabilityInfo : "contém"
    ExplainabilityInfo ||--|{ ExampleUsed : "usa"
    ExplainabilityInfo ||--|| ValidationInfo : "contém"
    ExplainabilityInfo ||--|| TimingInfo : "contém"
    ExplainabilityInfo }|--o{ Entity : "detectou"
    PipelineConfig ||--o{ AskRequest : "processa"
```

---

## ERD — Dados Estáticos (Arquivos)

```mermaid
erDiagram
    GoldStandardQuestion {
        string id PK "Q01–Q30"
        string question "Pergunta em PT"
        string sparql "Query SPARQL de referência"
        string difficulty "easy | medium | hard"
        string category "disease | phenotype | cross-graph"
    }

    FAISSIndex {
        string file "data/gold_standard/questions.index"
        int dimensions "384"
        string metric "Inner Product (= cosine com vetores normalizados)"
        int vectors "30 (um por questão)"
        string model "all-MiniLM-L6-v2"
    }

    OntologySchema {
        string graph PK "urn:doid | urn:hpo | urn:hpoa"
        list_string classes "Classes OWL detectadas"
        list_string predicates "Predicados usados"
        list_string prefixes "Prefixos válidos"
    }

    EvaluationResult {
        string id PK "Q01–Q30"
        string model "Modelo LLM avaliado"
        string scenario "A (com validação) | B (sem)"
        bool success "True se query retornou ≥1 resultado"
        int attempts "Tentativas usadas"
        float total_ms "Latência total"
        string sparql_generated "Query SPARQL gerada"
        string error "null ou mensagem de erro"
    }

    AblationConfig {
        string name PK "full | no_ner | no_fewshot | no_schema | no_validation | zero_shot"
        bool disable_ner "Flag"
        bool disable_fewshot "Flag"
        bool disable_schema "Flag"
        bool disable_validation "Flag"
        int max_retries "0 ou padrão"
    }

    PlaywrightLog {
        string id PK "Q01–Q30"
        string question "Texto da questão"
        bool success "Resultado do pipeline"
        string sparql "Query gerada"
        int attempts "Tentativas"
        float timing_total_ms "Latência medida pelo runner"
        string captured_at "ISO timestamp"
    }

    GoldStandardQuestion ||--|| FAISSIndex : "indexado em"
    GoldStandardQuestion ||--|{ EvaluationResult : "avaliado como"
    AblationConfig ||--|{ EvaluationResult : "configura"
    OntologySchema ||--o{ EvaluationResult : "usado por validador"
    GoldStandardQuestion ||--o{ PlaywrightLog : "testado via"
```

---

## ERD — Grafos RDF no Fuseki (Modelo Ontológico)

```mermaid
erDiagram
    DoidDisease {
        uri uri PK "http://purl.obolibrary.org/obo/DOID_*"
        string rdfs_label "Nome da doença (EN)"
        string obo_def "Definição OBO"
        uri rdf_type "obo:DOID_4 (Disease)"
        string hasDbXref "MIM:* | OMIM:* | ICD:* (literal)"
    }

    HpoTerm {
        uri uri PK "http://purl.obolibrary.org/obo/HP_*"
        string rdfs_label "Nome do fenótipo (EN)"
        uri rdf_type "obo:HP_0000118 (HumanPhenotype)"
        uri subClassOf "Hierarquia HPO"
    }

    HpoaAnnotation {
        uri disease_uri PK_FK "URI da doença (OMIM/ORPHA)"
        uri phenotype_uri PK_FK "URI do fenótipo HP_*"
        string source_id "OMIM:* (literal — incompatível com MIM: do DOID)"
        string aspect "P (phenotype) | I (inheritance)"
        string evidence "HP:0040279 (frequência)"
        string rdfs_label "Label da doença no contexto HPOA"
    }

    DoidDisease ||--o{ HpoaAnnotation : "referenciado via MIM:→OMIM: (BIND+REPLACE)"
    HpoTerm ||--o{ HpoaAnnotation : "hpoa:has_phenotype"
```

---

## Grafo de Namespaces Ativos

| Prefixo | Namespace | Grafo | Descrição |
|---|---|---|---|
| `obo:` | `http://purl.obolibrary.org/obo/` | `urn:doid`, `urn:hpo` | Classes OBO |
| `oboInOwl:` | `http://www.geneontology.org/formats/oboInOwl#` | `urn:doid` | Xrefs e sinonímia |
| `hpoa:` | `http://purl.obolibrary.org/obo/hp/` | `urn:hpoa` | Predicados de anotação |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | todos | label, subClassOf |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | todos | type |
| `owl:` | `http://www.w3.org/2002/07/owl#` | `urn:doid`, `urn:hpo` | Class, AnnotationProperty |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` | todos | tipos literais |

**Prefixos inválidos (alucinados por LLMs — removidos pelo pós-processamento):**
- `doid:` — não existe no triplestore
- `hpo:` — não existe no triplestore
