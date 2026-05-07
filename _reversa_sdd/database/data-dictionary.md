# Data Dictionary — BioSPARQL-NL

> Triple store RDF (Apache Jena Fuseki / TDB2). Sem schema relacional; "tabelas" = classes OWL agregadas por named graph. Tipos = IRI / Literal (xsd:string, xsd:int, xsd:date implícitos).

🟢 CONFIRMADO via `data/schemas.json` (introspecção SPARQL `GROUP_CONCAT` em 2026-04-10).

---

## Inventário — Datasets

| Dataset | Tipo | Localização | Tamanho | Acesso | Persistente |
| --- | --- | --- | --- | --- | --- |
| Fuseki `/biomedical` | RDF triple store TDB2 | `localhost:3030/biomedical` | ~1,5M triplas total | SPARQL 1.1 (read-only no pipeline) | ✅ `fuseki-db/` |
| FAISS index | Vector index 384d | `data/gold_standard/questions.index` | 30 vetores | `faiss.read_index` | ✅ |
| Gold standard | JSON | `data/gold_standard/questions.json` | 30 entradas | `json.load` | ✅ |
| QALD-9+ few-shot | JSON | `data/gold_standard/qald_fewshot.json` | n entries | `json.load` | ✅ |
| Regression suite | JSON | `data/gold_standard/regression_suite.json` | n entries | `json.load` | ✅ |
| schemas.json | JSON cache | `data/schemas.json` | 1160 linhas | leitura no `nl_to_sparql.py` | ✅ |
| doid.owl | OWL/XML (input) | `data/ontologies/doid.owl` | 27 MB | carregamento Fuseki | ✅ read-only |
| hp.owl | OWL/XML (input) | `data/ontologies/hp.owl` | 73 MB | carregamento Fuseki | ✅ read-only |
| phenotype.hpoa | TSV (input) | `data/annotations/phenotype.hpoa` | 34 MB | `hpoa_to_rdf.py` | ✅ read-only |
| hpoa.ttl | Turtle (derivado) | `data/annotations/hpoa.ttl` | 16 MB | carregamento Fuseki | ✅ regerado por `hpoa_to_rdf.py` |

---

## Named Graph: `urn:doid` — Disease Ontology

**Origem:** `data/ontologies/doid.owl` (27 MB, OWL/XML)
**Volume:** ~302K triplas. **Top-level entity**: `obo:DOID_4` ("disease").

### Classes (entities)

| URI | Count | Significado |
| --- | --- | --- |
| `owl:Class` | 15.732 | Doenças e categorias (ex.: `obo:DOID_10652` = Alzheimer) |
| `owl:Axiom` | 14.507 | Reificação para anotar tripla com metadados (autor, fonte) |
| `owl:Restriction` | 10.462 | Restrições anônimas (ex.: `subClassOf` com `someValuesFrom`) |
| `owl:AnnotationProperty` | 57 | Propriedades de anotação (`hasDbXref`, `hasExactSynonym`, etc.) |
| `owl:AllDisjointClasses` | 18 | Conjuntos de classes mutuamente disjuntas |
| `owl:ObjectProperty` | 2 | Relações entre classes |
| `owl:Ontology` | 1 | Metadados da ontologia |

### Predicates principais (>500 ocorrências)

| Predicado | Count | Domínio | Range | Uso típico |
| --- | --- | --- | --- | --- |
| `oboInOwl:hasDbXref` | **53.773** | Class, Axiom | xsd:string | **CHAVE** para join com HPOA (`MIM:`, `orpha.net/...`, `NCI:...`) |
| `rdfs:subClassOf` | 26.409 | Class | Class, Restriction | Hierarquia (suporta `+` para fechamento transitivo) |
| `oboInOwl:hasExactSynonym` | 21.970 | Class | xsd:string | Sinônimos lexicais |
| `rdfs:label` | 14.655 | — | xsd:string | Nome humano-legível |
| `oboInOwl:hasOBONamespace` | 14.591 | Class, ObjectProperty | xsd:string | Namespace OBO (`disease_ontology`) |
| `oboInOwl:id` | 14.590 | Class | xsd:string | ID OBO curto (`DOID:10652`) |
| `owl:annotatedSource` | 14.507 | Axiom | ObjectProp/Class/SymProp | Reificação da tripla anotada |
| `owl:annotatedTarget` | 14.507 | Axiom | any | Reificação do objeto |
| `owl:annotatedProperty` | 14.507 | Axiom | AnnotationProperty | Reificação do predicado |
| `oboInOwl:inSubset` | 10.737 | Class | AnnotationProperty | Subconjunto OBO (slim) |
| `owl:onProperty` | 10.462 | Restriction | — | Propriedade da restrição |
| `owl:someValuesFrom` | 10.454 | Restriction | — | Existência (∃) |
| `obo:IAO_0000115` | 10.449 | — | xsd:string | **Definição textual** (chave para queries) |
| `dc:type` | 10.260 | Axiom | — | Tipo do axioma |
| `oboInOwl:hasSynonymType` | 4.056 | Axiom | AnnotationProperty | Categoria do sinônimo |

### Predicates secundários

`rdf:first/rest`, `owl:deprecated` (2.511), `oboInOwl:hasAlternativeId` (1.736), `skos:exactMatch` (1.289), `rdfs:comment` (1.288), `owl:intersectionOf` (1.006), `oboInOwl:creation_date` (766), `owl:equivalentClass` (725), `oboInOwl:hasRelatedSynonym` (499), `owl:unionOf` (136), `skos:broadMatch` (84), `oboInOwl:hasNarrowSynonym` (82), `skos:narrowMatch` (35), `oboInOwl:hasBroadSynonym` (32), `skos:closeMatch` (29), `skos:relatedMatch` (29), `obo:IAO_0100001` (28, "term replaced by"), `owl:disjointWith` (8), `owl:onClass` (8), `owl:qualifiedCardinality` (5), `owl:minQualifiedCardinality` (3), `oboInOwl:consider` (2).

### Padrões de xref encontrados (em `oboInOwl:hasDbXref`)

`MIM:xxxxxx`, `OMIM:xxxxxx` (raros), `ORDO:` / `Orphanet_` / `orpha.net/...`, `NCI:Cxxxxx`, `MESH:D...`, `UMLS_CUI:C...`, `ICD9CM:...`, `ICD10CM:...`, `SNOMEDCT_US:...`, `EFO:...`.

**⚠️ Convenção crítica:** DOID usa `MIM:` (sem `O`) — ver `business-rules.md` §1.

---

## Named Graph: `urn:hpo` — Human Phenotype Ontology

**Origem:** `data/ontologies/hp.owl` (73 MB).
**Volume:** ~908K triplas. **Top-level entity**: `obo:HP_0000118` ("Phenotypic abnormality").

### Classes

| URI | Count | Significado |
| --- | --- | --- |
| `owl:Axiom` | 61.410 | Reificação |
| `owl:Class` | 47.014 | Termos fenotípicos (`obo:HP_xxxxxxx`) |
| `owl:Restriction` | 43.479 | Restrições anônimas |
| `owl:ObjectProperty` | 235 | Relações lógicas entre fenótipos |
| `owl:AnnotationProperty` | 126 | Propriedades de anotação |
| `owl:TransitiveProperty` | 30 | ObjectProperties com fechamento transitivo |
| `owl:SymmetricProperty` | 7 | |
| `owl:AllDisjointClasses` | 2 | |
| `owl:IrreflexiveProperty` | 2 | |
| `owl:AsymmetricProperty` | 1 | |
| `owl:FunctionalProperty` | 1 | |
| `owl:InverseFunctionalProperty` | 1 | |
| `owl:Ontology` | 1 | |

### Predicates principais

| Predicado | Count | Uso |
| --- | --- | --- |
| `oboInOwl:hasDbXref` | 111.204 | Mapeamentos cruzados (UMLS, MeSH, SNOMED) |
| `owl:onProperty` | 69.182 | Restrições |
| `owl:annotatedSource` | 61.411 | Reificação |
| `owl:annotatedProperty` | 61.410 | |
| `owl:annotatedTarget` | 61.410 | |
| `rdfs:subClassOf` | 55.989 | Hierarquia fenotípica (suporta `+`) |
| `owl:someValuesFrom` | 43.432 | Existência |
| `oboInOwl:hasExactSynonym` | 43.287 | Sinônimos |
| `rdf:first/rest` | 38.093 / 38.027 | Listas RDF |
| `rdfs:label` | 32.795 | **Chave** para resolver `?pheno → label` em joins HPOA→HPO |
| `obo:IAO_0000115` | 28.300 | Definição textual |

### Hierarquia fenotípica

Raiz: `obo:HP_0000118` ("Phenotypic abnormality"). Subclasses imediatas formam categorias usadas em Q29 (distribuição por categoria raiz). Profundidade típica: 5–8 níveis.

---

## Named Graph: `urn:hpoa` — HPO Annotations

**Origem:** `data/annotations/phenotype.hpoa` (TSV, 34 MB) → `data/annotations/hpoa.ttl` (Turtle, 16 MB) via `src/utils/hpoa_to_rdf.py`.
**Volume:** ~320K triplas. **Schema mínimo, custom** (namespace `http://example.org/hpoa/`).

### Classes

| URI | Count | Significado |
| --- | --- | --- |
| `hpoa:Disease` | **12.996** | Doença anotada (uma instância por linha de fonte) |

### Predicates

| Predicado | Count | Domain | Range | Uso |
| --- | --- | --- | --- | --- |
| `hpoa:has_phenotype` | **281.399** | `hpoa:Disease` | IRI (`obo:HP_xxxxxxx`) | Liga doença a fenótipo HPO |
| `rdfs:label` | 13.050 | `hpoa:Disease` | xsd:string | Nome da doença |
| `hpoa:source_id` | 12.996 | `hpoa:Disease` | xsd:string | **CHAVE** para join: `OMIM:154700`, `ORPHA:558`, `DECIPHER:1` |

### Convenção URI das instâncias

`http://example.org/disease/{prefix}_{id}` onde `{prefix}` ∈ `{OMIM, ORPHA, DECIPHER}` e separador é `_` (ex.: `disease/OMIM_154700`). Total ~13K diseases × 281K phenotype links = média de 21,7 fenótipos/doença.

### Filtros aplicados na ingest (TSV → Turtle)

- Linhas iniciadas em `#` ou `database_id` → header, descartadas
- Linhas com < 5 colunas → skipped
- `qualifier == "NOT"` → skipped (negação não é triplada)
- Threshold: skip ratio > 10% → log warning

---

## FAISS Index — `data/gold_standard/questions.index`

**Tipo:** `IndexFlatIP` (Inner Product = cosine com vetores normalizados).
**Modelo:** `sentence-transformers/all-MiniLM-L6-v2`. **Dimensão:** 384.
**Conteúdo:** embeddings de `question_en` das 30 perguntas do gold standard.
**Builder:** `src/utils/index_builder.py`. **Consumer:** `nl_to_sparql.py` (few-shot retrieval — top-k similar questions).

| Campo | Tipo | Origem |
| --- | --- | --- |
| vector[i] | float32[384] | `model.encode(question_en, normalize_embeddings=True)` |
| metadata[i] | dict | `questions.json[i]` (id, question_pt, sparql, type, difficulty, expected_min_results, expected_contains) |

---

## Dataset JSON: `questions.json`

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `id` | string | ✅ | `Q01`–`Q30` |
| `question_pt` | string | ✅ | Pergunta em português |
| `question_en` | string | ✅ | Pergunta em inglês (input para FAISS) |
| `sparql` | string | ✅ | Query SPARQL gold |
| `type` | enum | ✅ | `factoid \| count \| list \| aggregation \| hierarchy \| set_operation \| complex_join` |
| `difficulty` | enum | ✅ | `easy \| medium \| hard` (10 cada) |
| `expected_min_results` | int | ✅ | Mínimo de bindings esperados |
| `expected_contains` | string[] | ❌ | Substrings que devem aparecer no resultado |
| `sparql_patterns` | string[] | ❌ | Tags (`GRAPH_JOIN`, `COUNT`, `PROPERTY_PATH`, ...) |
| `annotator` | string | ❌ | `A` / `B` (inter-annotator agreement) |

---

## Cache: `data/schemas.json`

Resultado da introspecção SPARQL `GROUP_CONCAT` por named graph. Estrutura:

```json
{
  "urn:doid": { "classes": [...], "predicates": [...] },
  "urn:hpo":  { "classes": [...], "predicates": [...] },
  "urn:hpoa": { "classes": [...], "predicates": [...] }
}
```

**Fallback:** se Fuseki offline, `schema_extractor.py` carrega cache do disco em vez de falhar.
