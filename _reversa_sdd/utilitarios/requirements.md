# Requisitos — utilitarios

> Unit: `src/utils/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `utilitarios` |
| Caminho legado | `src/utils/hpoa_to_rdf.py`, `schema_extractor.py`, `index_builder.py`, `gold_standard.py` |
| Responsabilidade | Scripts de preparação de dados executados em setup-time: conversão HPOA→RDF, extração de schema SPARQL, construção do índice FAISS |
| Complexidade | 🟡 Média |

---

## Requisitos Funcionais

### RF-01 — Conversão HPOA TSV → Turtle RDF
🟢 **CONFIRMADO** — `hpoa_to_rdf.py:convert_hpoa_to_rdf()`

**Must**

Converter o arquivo `data/annotations/phenotype.hpoa` (TSV) para `data/annotations/hpoa.ttl` (Turtle RDF) para carga no triplestore Fuseki como grafo `urn:hpoa`.

**Critérios de Aceitação:**

```gherkin
Dado o arquivo phenotype.hpoa com N linhas de anotação (sem qualifier=NOT)
Quando convert_hpoa_to_rdf("phenotype.hpoa", "hpoa.ttl") é chamado
Então hpoa.ttl é gerado com N × 4 triplas (rdf:type, rdfs:label, has_phenotype, source_id)
E linhas com qualifier=NOT são descartadas (não incluídas)
E linhas de comentário (#) e cabeçalho são ignoradas
E o arquivo .ttl é parseável por rdflib sem erro
```

---

### RF-02 — Descarte de anotações negativas (qualifier=NOT)
🟢 **CONFIRMADO** — `hpoa_to_rdf.py` — RN-05

**Must**

Linhas do TSV com `qualifier == "NOT"` representam ausência do fenótipo e devem ser descartadas. O triplestore deve conter apenas associações positivas doença→fenótipo.

**Critérios de Aceitação:**

```gherkin
Dado uma linha com qualifier="NOT" no phenotype.hpoa
Quando convert_hpoa_to_rdf() processa essa linha
Então nenhuma tripla é gerada para essa linha
```

---

### RF-03 — URIs corretas para JOIN com DOID (source_id como literal OMIM:*)
🟢 **CONFIRMADO** — `hpoa_to_rdf.py` — RN-01

**Must**

O campo `hpoa:source_id` deve ser um literal textual com prefixo `OMIM:` (ex: `"OMIM:154700"`) para compatibilidade com o JOIN DOID↔HPOA via `BIND(REPLACE(..., "^MIM:", "OMIM:"))`.

**Critérios de Aceitação:**

```gherkin
Dado uma linha HPOA com db_id="OMIM:154700"
Quando convert_hpoa_to_rdf() gera as triplas
Então hpoa:source_id é o literal "OMIM:154700" (não uma URI)
E a URI da doença é <http://example.org/disease/OMIM_154700>
```

---

### RF-04 — Extração de schema ontológico via introspecção SPARQL
🟢 **CONFIRMADO** — `schema_extractor.py:extract_class_schema()`

**Must**

Extrair classes OWL e predicados usados em cada grafo nomeado via queries SPARQL `GROUP_CONCAT` e persistir em `data/schemas.json`.

**Critérios de Aceitação:**

```gherkin
Dado Fuseki rodando com grafos urn:doid, urn:hpo, urn:hpoa carregados
Quando extract_class_schema() é executado para cada grafo
Então data/schemas.json é gerado com estrutura:
  {"urn:doid": {"classes": [...], "predicates": [...]}, ...}
E o arquivo é JSON válido
E contém ao menos 1 classe e 1 predicado por grafo
```

```gherkin
Dado que a query GROUP_CONCAT falha (timeout ou connection error)
Quando extract_class_schema() tenta
Então retry exponencial é executado: até 3 tentativas com sleep(2^n)
E após 3 falhas, exceção é lançada com mensagem descritiva
```

---

### RF-05 — Construção do índice FAISS para few-shot RAG
🟢 **CONFIRMADO** — `index_builder.py:build_index()`

**Must**

Gerar embeddings das 30 questões do gold standard e persistir índice FAISS em `data/gold_standard/questions.index`.

**Critérios de Aceitação:**

```gherkin
Dado data/gold_standard/questions.json com 30 questões
Quando build_index("questions.json", "questions.index", "all-MiniLM-L6-v2") é chamado
Então questions.index é gerado com 30 vetores de dimensão 384
E os vetores são normalizados (norma L2 = 1.0)
E faiss.read_index("questions.index").ntotal == 30
```

---

### RF-06 — Embeddings normalizados para similaridade cosine via Inner Product
🟢 **CONFIRMADO** — `index_builder.py` — ADR-P04

**Must**

O índice FAISS usa `IndexFlatIP` (Inner Product). Para que IP seja equivalente a cosine similarity, os vetores devem estar normalizados (norma L2 = 1.0) antes de ser adicionados ao índice.

---

## Requisitos Não Funcionais

### RNF-01 — Todos os utilitários são scripts de setup-time (não runtime)
🟢 **CONFIRMADO** — sem chamada desses módulos em `server.py` ou `run_evaluation.py` após setup

Estes utilitários são executados uma única vez antes do uso do sistema. Não fazem parte do caminho crítico de runtime.

### RNF-02 — Retry exponencial nas queries SPARQL de extração
🟢 **CONFIRMADO** — `schema_extractor.py`

Queries de introspecção em grafos grandes podem ser lentas. Retry: 3 tentativas, `sleep(2**attempt)`.

### RNF-03 — Saída ASCII nos prints (sem emojis)
🟢 **CONFIRMADO** — `CLAUDE.md` — encoding Windows

Todos os scripts de utils devem usar `[OK]` e `[FAIL]` em vez de emojis para compatibilidade com terminal Windows (cp1252).

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Conversão HPOA→RDF | **Must** | Sem hpoa.ttl, grafo urn:hpoa não existe no Fuseki |
| RF-02 Descarte qualifier=NOT | **Must** | Dados incorretos se anotações negativas forem incluídas |
| RF-03 source_id como literal OMIM:* | **Must** | JOIN DOID↔HPOA quebra sem o formato correto |
| RF-04 Schema SPARQL | **Must** | Sem schemas.json, SchemaValidator fica em modo permissivo |
| RF-05 Índice FAISS | **Must** | Sem index, pipeline zero-shot (sem few-shot) |
| RF-06 Vetores normalizados | **Must** | Sem normalização, IndexFlatIP não equivale a cosine |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| `data/annotations/phenotype.hpoa` | Arquivo fonte | Sim (RF-01) |
| Apache Jena Fuseki em `:3030` | Serviço externo | Sim (RF-04) |
| `data/gold_standard/questions.json` | Arquivo fonte | Sim (RF-05) |
| sentence-transformers `all-MiniLM-L6-v2` | Modelo Python | Sim (RF-05, download HuggingFace) |
| rdflib | Biblioteca Python | Sim (RF-01) |
| FAISS-CPU | Biblioteca Python | Sim (RF-05) |
