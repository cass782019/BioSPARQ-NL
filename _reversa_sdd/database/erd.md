# ERD — BioSPARQL-NL

> Camada de dados é **RDF triple store** (Apache Jena Fuseki 6.0.0 / TDB2), não relacional.
> ERD adaptado: classes OWL → entidades; predicados → relacionamentos; named graphs → contextos isolados.
> Endpoint: `http://localhost:3030/biomedical/sparql` (read-only via SPARQL 1.1).

🟢 CONFIRMADO — extraído de `data/schemas.json` (introspecção SPARQL via `src/utils/schema_extractor.py`).

---

## 1. Topologia geral (named graphs + datasets auxiliares)

```mermaid
flowchart LR
    subgraph FUSEKI["Apache Jena Fuseki — Dataset /biomedical (TDB2)"]
        DOID[("urn:doid<br/>Disease Ontology<br/>~302K triplas<br/>15.732 owl:Class")]
        HPO[("urn:hpo<br/>Human Phenotype Ontology<br/>~908K triplas<br/>47.014 owl:Class")]
        HPOA[("urn:hpoa<br/>HPO Annotations<br/>~320K triplas<br/>12.996 hpoa:Disease")]
    end

    subgraph FILES["Datasets em arquivo (read-only)"]
        OWL_D["data/ontologies/doid.owl<br/>27 MB OWL/XML"]
        OWL_H["data/ontologies/hp.owl<br/>73 MB OWL/XML"]
        TSV["data/annotations/phenotype.hpoa<br/>34 MB TSV"]
        TTL["data/annotations/hpoa.ttl<br/>16 MB Turtle (derivado)"]
        QJSON["data/gold_standard/questions.json<br/>30 pares NL/SPARQL"]
        FAISS["data/gold_standard/questions.index<br/>FAISS IndexFlatIP (384d)"]
        SCH["data/schemas.json<br/>cache da introspecção"]
    end

    OWL_D -- load OWL --> DOID
    OWL_H -- load OWL --> HPO
    TSV -- "hpoa_to_rdf.py<br/>(TSV→Turtle)" --> TTL
    TTL -- load Turtle --> HPOA

    DOID -. "MIM:xxxxxx ↔ OMIM:xxxxxx<br/>(REPLACE/BIND)" .-> HPOA
    HPOA -- "has_phenotype<br/>OBO URI HP_xxxxxxx" --> HPO

    QJSON -- "encode all-MiniLM-L6-v2<br/>(index_builder.py)" --> FAISS

    DOID -- "introspecção GROUP_CONCAT<br/>(schema_extractor.py)" --> SCH
    HPO -- introspecção --> SCH
    HPOA -- introspecção --> SCH
```

---

## 2. ERD — entidades centrais (vista relacional simplificada)

```mermaid
erDiagram
    DOID_CLASS ||--o{ DOID_AXIOM : "annotated by"
    DOID_CLASS ||--o{ DOID_RESTRICTION : "subClassOf"
    DOID_CLASS ||--o{ DOID_XREF : "hasDbXref"
    DOID_CLASS }o--|| DOID_CLASS : "subClassOf+"

    HPO_CLASS ||--o{ HPO_AXIOM : "annotated by"
    HPO_CLASS ||--o{ HPO_RESTRICTION : "subClassOf"
    HPO_CLASS ||--o{ HPO_XREF : "hasDbXref"
    HPO_CLASS }o--|| HPO_CLASS : "subClassOf+"

    HPOA_DISEASE ||--o{ HPOA_HAS_PHENOTYPE : "has_phenotype"
    HPOA_DISEASE ||--|| HPOA_SOURCE_ID : "source_id"
    HPOA_DISEASE ||--o| HPOA_LABEL : "rdfs:label"

    HPOA_HAS_PHENOTYPE }o--|| HPO_CLASS : "→ HP_xxxxxxx"

    DOID_XREF }o..o| HPOA_SOURCE_ID : "MIM↔OMIM (BIND REPLACE)"

    DOID_CLASS {
        IRI uri PK "obo:DOID_xxxxxxx"
        string label
        string definition "obo:IAO_0000115"
        string oboId "obo:id"
    }
    DOID_XREF {
        string value "ex.: MIM:154700, orpha.net/..., NCI:..."
        IRI subject FK
    }
    HPO_CLASS {
        IRI uri PK "obo:HP_xxxxxxx"
        string label
        string definition
    }
    HPOA_DISEASE {
        IRI uri PK "ex.org/disease/{db}_{id}"
        string label "rdfs:label"
        string source_id "ex.: OMIM:154700, ORPHA:558, DECIPHER:1"
    }
    HPOA_HAS_PHENOTYPE {
        IRI subject FK
        IRI object FK "→ HPO_CLASS.uri"
    }
```

---

## 3. ERD — `urn:doid` (detalhe interno)

```mermaid
erDiagram
    OWL_CLASS ||--o{ OWL_AXIOM : "annotatedSource"
    OWL_AXIOM ||--|| OWL_ANNOTATION_PROPERTY : "annotatedProperty"
    OWL_CLASS ||--o{ OWL_RESTRICTION : "subClassOf"
    OWL_RESTRICTION ||--|| OWL_OBJECT_PROPERTY : "onProperty"
    OWL_RESTRICTION ||--|| OWL_CLASS : "someValuesFrom"
    OWL_CLASS }o--o{ OWL_CLASS : "equivalentClass"
    OWL_CLASS ||--o{ OWL_CLASS : "disjointWith"
    OWL_ALLDISJOINT ||--o{ OWL_CLASS : "members"

    OWL_CLASS {
        IRI uri PK
        int count "15.732"
        string label "rdfs:label"
        string definition "obo:IAO_0000115"
        string namespace "oboInOwl:hasOBONamespace"
        string oboId
        bool deprecated "owl:deprecated"
    }
    OWL_AXIOM {
        int count "14.507"
        IRI annotatedSource FK
        IRI annotatedProperty FK
        any annotatedTarget
    }
    OWL_RESTRICTION {
        int count "10.462"
        IRI onProperty FK
        IRI someValuesFrom FK
    }
```

---

## 4. ERD — `urn:hpo` (detalhe interno)

```mermaid
erDiagram
    OWL_CLASS_H ||--o{ OWL_AXIOM_H : "annotatedSource"
    OWL_CLASS_H ||--o{ OWL_RESTRICTION_H : "subClassOf"
    OWL_RESTRICTION_H ||--|| OWL_OBJECT_PROPERTY_H : "onProperty"
    OWL_RESTRICTION_H ||--|| OWL_CLASS_H : "someValuesFrom"
    OWL_CLASS_H }o--|| OWL_CLASS_H : "subClassOf+ (hierarquia fenotípica)"
    OWL_CLASS_H ||--o{ HPO_XREF : "hasDbXref"

    OWL_CLASS_H {
        IRI uri PK "obo:HP_xxxxxxx"
        int count "47.014"
        string label
        string definition
    }
    OWL_OBJECT_PROPERTY_H {
        int count "235"
        bool transitive
        bool symmetric
        bool functional
    }
    OWL_RESTRICTION_H {
        int count "43.479"
    }
    HPO_XREF {
        string value "ex.: UMLS:C0001925, MSH:D008594"
        int count "111.204"
    }
```

---

## 5. ERD — `urn:hpoa` (detalhe interno, schema mínimo)

```mermaid
erDiagram
    DISEASE ||--o{ HAS_PHENOTYPE : "has_phenotype"
    DISEASE ||--|| SOURCE_ID : "source_id"
    DISEASE ||--o| LABEL : "rdfs:label"

    DISEASE {
        IRI uri PK "ex.org/disease/{db}_{id}"
        int count "12.996"
    }
    HAS_PHENOTYPE {
        int count "281.399"
        IRI object "→ obo:HP_xxxxxxx"
    }
    SOURCE_ID {
        string value "OMIM:|ORPHA:|DECIPHER:"
        int count "12.996"
    }
    LABEL {
        string value
        int count "13.050"
    }
```

---

## 6. Cross-graph join — DOID ↔ HPOA ↔ HPO

```mermaid
sequenceDiagram
    participant Q as Query SPARQL
    participant D as urn:doid
    participant A as urn:hpoa
    participant P as urn:hpo

    Q->>D: SELECT ?xref WHERE { ?d oboInOwl:hasDbXref ?xref<br/>FILTER STRSTARTS(?xref,"MIM:") }
    D-->>Q: "MIM:154700"
    Q->>Q: BIND(REPLACE(?xref,"^MIM:","OMIM:") AS ?omim)
    Q->>A: ?disease hpoa:source_id ?omim ;<br/>hpoa:has_phenotype ?pheno
    A-->>Q: ?pheno = obo:HP_0001166
    Q->>P: ?pheno rdfs:label ?phenotype_label
    P-->>Q: "Arachnodactyly"
```

🟡 INFERIDO — apenas `BIND(REPLACE(...))` foi confirmado em queries do gold standard (Q21). Direção inversa (`OMIM→MIM`) também é válida via `CONCAT`.
