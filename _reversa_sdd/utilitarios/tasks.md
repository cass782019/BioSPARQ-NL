# Tasks — utilitarios

> Unit: `src/utils/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Implementar `convert_hpoa_to_rdf(input_tsv, output_ttl)`

**Origem:** `src/utils/hpoa_to_rdf.py:convert_hpoa_to_rdf()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS

HPOA = Namespace("http://purl.obolibrary.org/obo/hp/")
OBO  = Namespace("http://purl.obolibrary.org/obo/")
DIS  = Namespace("http://example.org/disease/")

def convert_hpoa_to_rdf(input_tsv: str, output_ttl: str) -> int:
    """
    Converte phenotype.hpoa (TSV) para Turtle RDF.
    Retorna o número de triplas geradas.
    Descarta linhas com qualifier=NOT.
    """
    graph = Graph()
    graph.bind("hpoa", HPOA)
    graph.bind("obo", OBO)
    graph.bind("disease", DIS)

    triple_count = 0

    with open(input_tsv, encoding="utf-8") as f:
        for line in f:
            # Ignorar comentários e cabeçalho
            if line.startswith("#") or line.startswith("database_id"):
                continue

            cols = line.strip().split("\t")
            if len(cols) < 5:
                continue

            db_id = cols[0].strip()        # "OMIM:154700"
            disease_name = cols[1].strip()
            qualifier = cols[3].strip()    # "" ou "NOT"
            hpo_id = cols[4].strip()       # "HP:0001945"

            # Descartar anotações negativas (RN-05)
            if qualifier == "NOT":
                continue

            # Gerar URIs
            hpo_local = hpo_id.replace("HP:", "HP_")
            hpo_uri = OBO[hpo_local]

            db_local = db_id.replace(":", "_")
            disease_uri = DIS[db_local]

            # 4 triplas por anotação
            graph.add((disease_uri, RDF.type, HPOA.Disease))
            graph.add((disease_uri, RDFS.label, Literal(disease_name)))
            graph.add((disease_uri, HPOA.has_phenotype, hpo_uri))
            graph.add((disease_uri, HPOA.source_id, Literal(db_id)))  # literal "OMIM:154700"
            triple_count += 4

    graph.serialize(output_ttl, format="turtle")
    print(f"[OK] {triple_count} triplas geradas em {output_ttl}")
    return triple_count
```

**Critério de pronto:**
- `convert_hpoa_to_rdf("phenotype.hpoa", "hpoa.ttl")` gera arquivo `.ttl` parseável por rdflib
- Linhas com `qualifier=NOT` não geram triplas
- `hpoa:source_id` é literal `"OMIM:154700"` (não URI)
- Retorna contagem de triplas (divisível por 4)

---

## T-02 — Implementar `extract_class_schema(endpoint_url, graph_uri)`

**Origem:** `src/utils/schema_extractor.py:extract_class_schema()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
import time
from SPARQLWrapper import SPARQLWrapper, JSON

def extract_class_schema(endpoint_url: str, graph_uri: str, max_retries: int = 3) -> dict:
    """
    Extrai classes e predicados de um grafo nomeado via introspecção SPARQL.
    Usa retry exponencial em caso de falha.
    """
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setReturnFormat(JSON)

    def run_query(query: str, attempt: int = 0) -> list:
        try:
            sparql.setQuery(query)
            results = sparql.query().convert()
            bindings = results["results"]["bindings"]
            return bindings
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                print(f"[INFO] retry {attempt+1}/{max_retries} em {sleep_time}s: {e}")
                time.sleep(sleep_time)
                return run_query(query, attempt + 1)
            raise

    # Query classes
    class_query = f"""
    SELECT (GROUP_CONCAT(DISTINCT STR(?cls); separator="|") AS ?classes)
    WHERE {{ GRAPH <{graph_uri}> {{ ?s a ?cls }} }}
    """
    class_results = run_query(class_query)
    classes_raw = class_results[0]["classes"]["value"] if class_results else ""
    classes = [c for c in classes_raw.split("|") if c.strip()]

    # Query predicados
    pred_query = f"""
    SELECT (GROUP_CONCAT(DISTINCT STR(?p); separator="|") AS ?preds)
    WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}
    """
    pred_results = run_query(pred_query)
    preds_raw = pred_results[0]["preds"]["value"] if pred_results else ""
    predicates = [p for p in preds_raw.split("|") if p.strip()]

    return {"classes": classes, "predicates": predicates}
```

**Critério de pronto:**
- Com Fuseki online, retorna dict com pelo menos 1 classe e 1 predicado para `urn:doid`
- Em timeout, faz retry até 3 vezes com backoff 1s, 2s, 4s
- Após 3 falhas, lança exceção (não silencia o erro)

---

## T-03 — Implementar script principal `schema_extractor.py`

**Origem:** `src/utils/schema_extractor.py` — bloco `__main__`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-02

### Comportamento esperado

```python
if __name__ == "__main__":
    import json
    ENDPOINT = "http://localhost:3030/biomedical/sparql"
    GRAPHS = ["urn:doid", "urn:hpo", "urn:hpoa"]

    schemas = {}
    for graph in GRAPHS:
        print(f"[INFO] Extraindo schema de {graph}...")
        try:
            schemas[graph] = extract_class_schema(ENDPOINT, graph)
            print(f"[OK] {graph}: {len(schemas[graph]['classes'])} classes, "
                  f"{len(schemas[graph]['predicates'])} predicados")
        except Exception as e:
            print(f"[FAIL] {graph}: {e}")
            schemas[graph] = {"classes": [], "predicates": []}

    with open("data/schemas.json", "w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2, ensure_ascii=False)
    print("[OK] data/schemas.json gerado")
```

**Critério de pronto:** Gera `data/schemas.json` válido mesmo se um grafo falhar (preenche com listas vazias e continua).

---

## T-04 — Implementar `build_index(questions_path, index_path, model_name)`

**Origem:** `src/utils/index_builder.py:build_index()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def build_index(
    questions_path: str,
    index_path: str,
    model_name: str = "all-MiniLM-L6-v2"
) -> faiss.Index:
    """
    Gera embeddings das questões e constrói índice FAISS IndexFlatIP.
    Vetores normalizados → IP equivale a cosine similarity.
    """
    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)

    texts = [q["question"] for q in questions]

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]  # 384 para all-MiniLM-L6-v2
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, index_path)
    print(f"[OK] {index.ntotal} vetores indexados em {index_path} (dim={dim})")
    return index
```

**Critério de pronto:**
- `build_index("questions.json", "questions.index")` gera arquivo binário
- `faiss.read_index("questions.index").ntotal == len(questions)`
- Vetores têm norma L2 ≈ 1.0 (verificável com `np.linalg.norm(embeddings, axis=1)`)

---

## T-05 — Script CLI para `index_builder.py`

**Origem:** `src/utils/index_builder.py` — bloco `__main__`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-04

### Comportamento esperado

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="data/gold_standard/questions.json")
    parser.add_argument("--index", default="data/gold_standard/questions.index")
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()

    idx = build_index(args.questions, args.index, args.model)
    print(f"[OK] Index com {idx.ntotal} vetores salvo em {args.index}")
```

**Critério de pronto:** `python -m src.utils.index_builder` gera `data/gold_standard/questions.index` com 30 vetores.

---

## T-06 — Script CLI para `hpoa_to_rdf.py`

**Origem:** `src/utils/hpoa_to_rdf.py` — bloco `__main__`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01

### Comportamento esperado

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/annotations/phenotype.hpoa")
    parser.add_argument("--output", default="data/annotations/hpoa.ttl")
    args = parser.parse_args()

    n = convert_hpoa_to_rdf(args.input, args.output)
    print(f"[OK] {n} triplas geradas")
```

**Critério de pronto:** `python -m src.utils.hpoa_to_rdf` gera `data/annotations/hpoa.ttl` sem erro. Arquivo resultante tem tamanho > 0 e é parseável com `rdflib.Graph().parse("hpoa.ttl")`.


## T-07 — `GOLD_STANDARD` e `save_gold_standard(output_path)`

**Origem:** `src/utils/gold_standard.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

`gold_standard.py` contém dois artefatos:

**1. `GOLD_STANDARD`** — lista hardcoded de 30 dicts com estrutura:

```python
{
    "id": "Q01",
    "question_pt": "...",               # pergunta em português
    "question_en": "...",               # tradução em inglês (opcional)
    "sparql": "SELECT ...",             # query de referência
    "difficulty": "easy"|"medium"|"hard",
    "expected_min_results": 1,
}
```

Invariante: exatamente 10 easy / 10 medium / 10 hard.

**2. `save_gold_standard(output_path)`** — serializa `GOLD_STANDARD` para JSON e imprime distribuição:

```python
def save_gold_standard(output_path: str = "data/gold_standard/questions.json") -> None:
    import json, os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(GOLD_STANDARD, f, ensure_ascii=False, indent=2)

    by_diff = {}
    for q in GOLD_STANDARD:
        by_diff[q["difficulty"]] = by_diff.get(q["difficulty"], 0) + 1

    print(f"[OK] {len(GOLD_STANDARD)} questoes salvas em {output_path}")
    for diff, count in sorted(by_diff.items()):
        print(f"  {diff}: {count}")
```

**Critério de pronto:**
- `len(GOLD_STANDARD) == 30` com distribuição 10/10/10
- `save_gold_standard()` gera JSON parseável com os 30 registros
- Distribuição impressa soma 30 com 3 categorias (easy/medium/hard)
- Os dados devem ser preservados integralmente — não há lógica a reimplementar além de `save_gold_standard()`
