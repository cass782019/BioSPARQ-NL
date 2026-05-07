# Stored Procedures, Functions & Views — BioSPARQL-NL

> **Não aplicável no sentido tradicional.** Apache Jena Fuseki (TDB2) não suporta stored procedures, funções definidas pelo usuário em SQL/PSM, nem views materializadas nativas. Lógica equivalente reside em scripts Python ou em queries SPARQL salvas.

🟢 CONFIRMADO — verificado em `tools/apache-jena-fuseki-6.0.0/` e ausência de DDL/triggers em `src/`.

---

## 1. Equivalentes funcionais (lógica fora do banco)

| Conceito relacional | Equivalente neste projeto | Localização |
| --- | --- | --- |
| Stored procedure | Funções Python no pipeline | `src/pipeline/`, `src/utils/` |
| Trigger | Pós-processamento determinístico (regex) e validação | `src/pipeline/nl_to_sparql.py`, `src/pipeline/sparql_validator.py` |
| View | `data/schemas.json` (introspecção materializada) | `src/utils/schema_extractor.py` |
| Materialized view (FAISS) | `data/gold_standard/questions.index` | `src/utils/index_builder.py` |
| ETL TSV → Turtle | `convert_hpoa_to_rdf` | `src/utils/hpoa_to_rdf.py` |

---

## 2. Funções utilitárias críticas (Python — atuam sobre dados)

### 2.1 `convert_hpoa_to_rdf(input_tsv, output_ttl) -> int`

**Arquivo:** `src/utils/hpoa_to_rdf.py`.
**Propósito:** ETL de `phenotype.hpoa` (TSV oficial Monarch) para `hpoa.ttl` (Turtle carregado em `urn:hpoa`).
**Entrada:** path para TSV.
**Saída:** path para Turtle gerado; retorna count de triplas geradas.
**Regras embutidas:**
- skip header (`#`, `database_id`)
- skip qualifier `NOT`
- threshold 10% para warning
- URI templating determinístico

```python
convert_hpoa_to_rdf("data/annotations/phenotype.hpoa", "data/annotations/hpoa.ttl")
# → 281.399 ligações has_phenotype + 12.996 instâncias Disease
```

---

### 2.2 `extract_class_schema(endpoint_url, graph_uri) -> dict`

**Arquivo:** `src/utils/schema_extractor.py`.
**Propósito:** introspecção via SPARQL `GROUP_CONCAT` para mapear classes/predicados/domínios/ranges de um named graph.
**Entrada:** URL do endpoint Fuseki e URI do graph.
**Saída:** dict com `classes` e `predicates` (cada um com count, label, domains, ranges).

**Queries embutidas:**

```sparql
-- Classes
SELECT ?class (COUNT(?s) AS ?count) (SAMPLE(?label) AS ?classLabel)
WHERE {
  GRAPH <{graph_uri}> {
    ?s a ?class .
    OPTIONAL { ?class rdfs:label ?label }
  }
}
GROUP BY ?class
ORDER BY DESC(?count)
LIMIT 100

-- Predicados (com domains/ranges via GROUP_CONCAT)
SELECT ?predicate
       (COUNT(*) AS ?count)
       (GROUP_CONCAT(DISTINCT ?sType; separator=',') AS ?domains)
       (GROUP_CONCAT(DISTINCT ?oType; separator=',') AS ?ranges)
WHERE {
  GRAPH <{graph_uri}> {
    ?s ?predicate ?o .
    OPTIONAL { ?s a ?sType }
    OPTIONAL { ?o a ?oType }
    FILTER(?predicate != rdf:type)
  }
}
GROUP BY ?predicate
ORDER BY DESC(?count)
LIMIT 100
```

**Retry:** exponential backoff (`MAX_RETRIES=3`, `BACKOFF_BASE=2`).
**Fallback offline:** carrega `data/schemas.json` se Fuseki indisponível.

---

### 2.3 `extract_all_schemas(endpoint_url, graphs, output_path) -> dict`

**Arquivo:** `src/utils/schema_extractor.py`.
**Propósito:** orquestra `extract_class_schema` para os 3 graphs e persiste em `data/schemas.json`.
**Periodicidade:** executar manualmente após qualquer reload de ontologia (anual ou ad-hoc quando DOID/HPO publicam release).

---

### 2.4 `build_index(questions_path, index_path, model_name) -> faiss.Index`

**Arquivo:** `src/utils/index_builder.py`.
**Propósito:** materializa embeddings das 30 perguntas-gold em FAISS `IndexFlatIP` (cosine via vetores normalizados).
**Modelo:** `all-MiniLM-L6-v2` (384d).
**Saída:** `data/gold_standard/questions.index`.

---

### 2.5 `save_gold_standard(output_path)` + `GOLD_STANDARD` (lista)

**Arquivo:** `src/utils/gold_standard.py`.
**Propósito:** materializa as 30 perguntas em `questions.json`. Distribuição esperada: 10 easy + 10 medium + 10 hard.
**Verificação inline:** print da contagem por dificuldade.

---

## 3. Queries "salvas" (gold standard) — análogo a stored procedures

As 30 queries SPARQL em `data/gold_standard/questions.json` funcionam como uma biblioteca de procedures parametrizadas:

| ID | Tipo | Padrão SPARQL | Equivale a |
| --- | --- | --- | --- |
| Q01–Q10 | factoid / count / list | BGP simples por graph | SELECT direto |
| Q11–Q20 | join / list / aggregation | join cross-graph (HPOA↔HPO) | JOIN 2-table |
| Q21–Q30 | aggregation / hierarchy / set_op / complex_join | join 3-graph + GROUP BY / HAVING | CTE / window function |

**Não parametrizáveis** sem rewrite: cada query é literal. O LLM gera queries dinâmicas que conceitualmente "instanciam" esses padrões a partir da pergunta NL.

---

## 4. Endpoints Fuseki ativos

```
http://localhost:3030/biomedical/sparql       # SPARQL query (read)
http://localhost:3030/biomedical/update       # SPARQL update (admin only — não usado pelo app)
http://localhost:3030/biomedical/data         # Graph Store Protocol (load .owl/.ttl)
http://localhost:3030/biomedical/get          # Graph Store Protocol (download)
```

🟢 CONFIRMADO no comando de start em `CLAUDE.md` (`--update /biomedical`).

---

## 5. Operações de carga (não automatizadas em CI)

```bash
# 1. Limpar e recarregar urn:doid
curl -X DELETE "http://localhost:3030/biomedical/data?graph=urn:doid"
curl -X PUT "http://localhost:3030/biomedical/data?graph=urn:doid" \
     -H "Content-Type: application/rdf+xml" --data-binary @data/ontologies/doid.owl

# 2. Idem para urn:hpo
curl -X DELETE "http://localhost:3030/biomedical/data?graph=urn:hpo"
curl -X PUT "http://localhost:3030/biomedical/data?graph=urn:hpo" \
     -H "Content-Type: application/rdf+xml" --data-binary @data/ontologies/hp.owl

# 3. Regenerar e recarregar urn:hpoa
PYTHONPATH=. .venv/Scripts/python.exe -m src.utils.hpoa_to_rdf
curl -X DELETE "http://localhost:3030/biomedical/data?graph=urn:hpoa"
curl -X PUT "http://localhost:3030/biomedical/data?graph=urn:hpoa" \
     -H "Content-Type: text/turtle" --data-binary @data/annotations/hpoa.ttl
```

🔴 LACUNA — não há script `reload_ontologies.sh` consolidando esses passos. Recomendado para reprodutibilidade.

---

## 6. Reasoning / inferência

**Não habilitado.** TDB2 padrão não materializa inferências OWL DL. Queries que precisariam de:
- `subClassOf+` transitividade → resolvido via property path SPARQL (`+`)
- `equivalentClass` simetria → não materializado
- Inverse properties → não materializado

🟡 INFERIDO — habilitar reasoner exigiria configuração custom de Jena (`tdb2:assembler` com `ja:reasoner`). Custo: ~5–10x latência. Decisão atual: deixar inferência ao LLM via prompt + property paths SPARQL.
