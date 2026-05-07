# Design — utilitarios

> Unit: `src/utils/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Visão Geral

O módulo `utilitarios` contém scripts de preparação de dados executados uma única vez em setup-time. Cada script é independente, sem dependências entre si, e produz um artefato persistido usado pelo pipeline em runtime. O design é simples e linear — sem classes abstratas ou padrões complexos.

---

## Estrutura de Arquivos

| Arquivo | Artefato gerado | Usado por |
|---|---|---|
| `src/utils/hpoa_to_rdf.py` | `data/annotations/hpoa.ttl` | Fuseki (carga manual) |
| `src/utils/schema_extractor.py` | `data/schemas.json` | `SchemaValidator` |
| `src/utils/index_builder.py` | `data/gold_standard/questions.index` | `BioSPARQLPipeline.retrieve_examples()` |
| `src/utils/gold_standard.py` | `data/gold_standard/questions.json` | `run_evaluation.py`, `index_builder.py` |

---

## `hpoa_to_rdf.py` — Conversão TSV → Turtle

### Fluxo

```mermaid
flowchart TD
    TSV["data/annotations/phenotype.hpoa\n(TSV, UTF-8)"] --> OPEN[abrir arquivo]
    OPEN --> LINE[para cada linha]
    LINE --> SKIP{comentário # \nou cabeçalho?}
    SKIP -- sim --> LINE
    SKIP -- não --> PARSE["parse colunas:\n[0] db_id (OMIM:154700)\n[1] disease_name\n[3] qualifier\n[4] hpo_id (HP:0001945)"]
    PARSE --> NOT{qualifier == 'NOT'?}
    NOT -- sim --> LINE
    NOT -- não --> URIS["gerar URIs:\nhpo_uri = obo:HP_{hpo_id sem HP:}\ndisease_uri = <http://example.org/disease/OMIM_{id}>"]
    URIS --> TRIPLES["4 triplas por anotação:\n1. disease_uri rdf:type hpoa:Disease\n2. disease_uri rdfs:label disease_name\n3. disease_uri hpoa:has_phenotype hpo_uri\n4. disease_uri hpoa:source_id 'db_id' (literal)"]
    TRIPLES --> LINE
    LINE --> DONE{fim do arquivo?}
    DONE --> SERIALIZE["graph.serialize('hpoa.ttl', format='turtle')"]
    SERIALIZE --> OUT["hpoa.ttl (~320K triplas)"]
```

### Namespace e URIs

```python
HPOA = Namespace("http://purl.obolibrary.org/obo/hp/")
OBO  = Namespace("http://purl.obolibrary.org/obo/")
DIS  = Namespace("http://example.org/disease/")

# HP:0001945 → obo:HP_0001945
hpo_uri = OBO[f"HP_{hpo_id.replace('HP:', '')}"]

# OMIM:154700 → <http://example.org/disease/OMIM_154700>
disease_uri = DIS[f"OMIM_{db_id.replace('OMIM:', '')}"]

# source_id é literal (não URI) — crucial para JOIN com DOID via REPLACE
graph.add((disease_uri, HPOA.source_id, Literal(db_id)))  # "OMIM:154700"
```

🟢 **CONFIRMADO** — RN-01, RN-05

---

## `schema_extractor.py` — Introspecção SPARQL

### Fluxo

```mermaid
flowchart TD
    GRAPHS["grafos: urn:doid, urn:hpo, urn:hpoa"] --> LOOP[para cada grafo]
    LOOP --> QCLASS["query GROUP_CONCAT classes:\nSELECT (GROUP_CONCAT(DISTINCT ?cls) AS ?classes)\nWHERE { GRAPH <grafo> { ?s rdf:type ?cls } }"]
    QCLASS --> RETRY1{timeout?}
    RETRY1 -- sim, attempt<3 --> SLEEP1["sleep(2**attempt)"]
    SLEEP1 --> QCLASS
    RETRY1 -- não --> QPRED["query GROUP_CONCAT predicados:\nSELECT (GROUP_CONCAT(DISTINCT ?p) AS ?preds)\nWHERE { GRAPH <grafo> { ?s ?p ?o } }"]
    QPRED --> RETRY2{timeout?}
    RETRY2 -- sim --> SLEEP2["sleep(2**attempt)"]
    SLEEP2 --> QPRED
    RETRY2 -- não --> STORE["schemas[grafo] = {classes: [...], predicates: [...]}"]
    STORE --> LOOP
    LOOP --> SAVE["json.dump → data/schemas.json"]
```

### Estrutura de `schemas.json`

```json
{
  "urn:doid": {
    "classes": [
      "http://www.w3.org/2002/07/owl#Class",
      "http://purl.obolibrary.org/obo/DOID_4"
    ],
    "predicates": [
      "http://www.w3.org/2000/01/rdf-schema#label",
      "http://www.geneontology.org/formats/oboInOwl#hasDbXref",
      "http://www.w3.org/2002/07/owl#subClassOf"
    ]
  },
  "urn:hpo": { "classes": [...], "predicates": [...] },
  "urn:hpoa": { "classes": [...], "predicates": [...] }
}
```

🟢 **CONFIRMADO** — ADR-P03

---

## `index_builder.py` — Índice FAISS

### Fluxo

```mermaid
flowchart TD
    QS["data/gold_standard/questions.json\n30 questões"] --> TEXTS["texts = [q['question'] for q in questions]"]
    TEXTS --> EMB["SentenceTransformer('all-MiniLM-L6-v2')\n.encode(texts, normalize_embeddings=True)\n→ float32 array [30, 384]"]
    EMB --> IDX["faiss.IndexFlatIP(384)\n(Inner Product = cosine com vetores normalizados)"]
    IDX --> ADD["index.add(embeddings)"]
    ADD --> WRITE["faiss.write_index(index, 'questions.index')"]
    WRITE --> OUT["data/gold_standard/questions.index\n(binário FAISS, ~50KB)"]
```

### Por que IndexFlatIP + normalização = cosine

```
cosine(a, b) = (a · b) / (|a| × |b|)

Se |a| = |b| = 1.0 (vetores normalizados):
  cosine(a, b) = a · b = IndexFlatIP(a, b)

Portanto: IndexFlatIP com vetores normalizados ≡ busca por similaridade cosine exata.
```

🟢 **CONFIRMADO** — `index_builder.py:build_index()` + ADR-P04

### Uso em runtime (`retrieve_examples`)

```python
# Em BioSPARQLPipeline.retrieve_examples():
embedding = self._embedder.encode([question], normalize_embeddings=True)
distances, indices = self.index.search(embedding, top_k)
examples = [self.examples[i] for i in indices[0]]
```

---

## `gold_standard.py` — Gestão do Gold Standard

Script auxiliar para criar/validar `data/gold_standard/questions.json`. Estrutura de cada questão:

```json
{
  "id": "Q01",
  "question": "Quais fenótipos estão associados ao Parkinson?",
  "difficulty": "easy",
  "category": "phenotype",
  "sparql_reference": "SELECT ?phenotype WHERE { ... }",
  "expected_contains": ["tremor", "rigidity"],
  "min_expected": 1
}
```

| Campo | Obrigatório | Descrição |
|---|---|---|
| `id` | Sim | Q01–Q30 |
| `question` | Sim | Pergunta em português |
| `difficulty` | Sim | `easy` \| `medium` \| `hard` |
| `sparql_reference` | Não | Query de referência (não usada no pipeline) |
| `expected_contains` | Não | Termos para spot-check semântico |
| `min_expected` | Não | Mínimo de resultados esperados (padrão: 1) |

---

## Dependências entre Utilitários (ordem de execução)

```
1. hpoa_to_rdf.py          → gera hpoa.ttl
2. [carga manual no Fuseki] → carrega doid.owl, hp.owl, hpoa.ttl
3. schema_extractor.py      → gera schemas.json   (requer Fuseki online)
4. index_builder.py         → gera questions.index (requer questions.json)
```

Os passos 3 e 4 são independentes entre si, mas ambos dependem dos anteriores.

---

## Encoding e Compatibilidade Windows

Todos os `print()` devem usar ASCII puro (`[OK]`, `[FAIL]`, `[INFO]`). Nunca usar emojis ou caracteres UTF-8 acima de U+007F sem `sys.stdout.reconfigure(encoding='utf-8')`.

🟢 **CONFIRMADO** — `CLAUDE.md` — "Encoding Windows"
