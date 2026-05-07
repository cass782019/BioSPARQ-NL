# Regras de Negócio na Camada de Dados — BioSPARQL-NL

> Triple stores não suportam triggers/check constraints/stored procedures nativamente. Regras estão **na aplicação** (Python) e **embutidas no formato dos dados** (convenções de namespace, prefixos). Documentadas aqui para preservar conhecimento.

🟢 CONFIRMADO via leitura de código (`src/utils/hpoa_to_rdf.py`, `src/pipeline/sparql_validator.py`, `src/pipeline/nl_to_sparql.py`).

---

## 1. Reescrita MIM ↔ OMIM (cross-graph join)

**Regra:** ao juntar `urn:doid` com `urn:hpoa` via xref de doença, normalizar o prefixo.

**Onde está:** queries SPARQL do gold standard (Q21) e queries geradas pelo LLM. O ADR `001-bind-replace-para-join-doid-hpoa.md` documenta a decisão. O validador permissivo aceita queries que omitam essa transformação mas elas falharão em runtime (zero bindings).

```sparql
GRAPH <urn:doid> { ?d oboInOwl:hasDbXref ?xref . FILTER(STRSTARTS(STR(?xref),"MIM:")) }
BIND(REPLACE(STR(?xref), "^MIM:", "OMIM:") AS ?omim_id)
GRAPH <urn:hpoa> { ?disease hpoa:source_id ?omim_id . }
```

**Direção inversa** (HPOA → DOID) usa `BIND(CONCAT("MIM:", STRAFTER(?source_id, "OMIM:")) AS ?mim_xref)` ou `REPLACE(?source_id, "^OMIM:", "MIM:")`.

**Razão histórica:** DOID importa OMIM com prefixo legado `MIM:`; HPOA segue convenção HPO/Monarch (`OMIM:`). Sem normalização, joins retornam zero.

---

## 2. Filtragem de qualifier `NOT` na ingest TSV → Turtle

**Onde:** `src/utils/hpoa_to_rdf.py` linhas 42-44.

```python
qualifier = parts[2]
if qualifier == "NOT":
    skipped += 1
    continue
```

**Regra:** anotações com qualifier `NOT` (negação explícita do fenótipo na doença) são descartadas no pipeline atual. Não são representadas via `owl:NegativePropertyAssertion`.

**Implicação:** queries que perguntem "quais fenótipos *não* ocorrem em X" não têm dados.

🟡 INFERIDO — manter triplas negativas exigiria predicado custom `hpoa:has_not_phenotype` ou reificação OWL.

---

## 3. Threshold de skip ratio na ingest

**Onde:** `src/utils/hpoa_to_rdf.py` linhas 66-69.

```python
if total > 0 and skipped / total > 0.10:
    logger.warning(f"⚠️ {skipped}/{total} linhas ignoradas ({skipped / total:.1%})")
```

**Regra:** se >10% das linhas TSV foram skipped (header inválido, colunas faltando ou qualifier=NOT), emitir warning. Não bloqueia ingest — apenas alerta.

**Lacuna:** sem unit test verificando que skip ratio < 10% para snapshots conhecidos do HPOA.

---

## 4. URI templating das instâncias HPOA

**Onde:** `src/utils/hpoa_to_rdf.py` linhas 46-53.

```python
hpo_uri = URIRef(f"http://purl.obolibrary.org/obo/{hpo_id.replace(':', '_')}")
disease_uri = URIRef(f"http://example.org/disease/{db_id.replace(':', '_')}")
```

**Regra:** transforma `HP:0001166` → `obo:HP_0001166` (alinhado com URIs de `urn:hpo`) e `OMIM:154700` → `ex.org/disease/OMIM_154700` (namespace local).

**Implicação:** o sujeito IRI da doença HPOA é determinístico — mesmo `db_id` sempre gera mesma IRI. Re-ingests substituem cleanly se o triple store for limpo antes do load.

---

## 5. Manutenção de `source_id` como literal textual

**Onde:** `src/utils/hpoa_to_rdf.py` linha 59 — `g.add((disease_uri, HPOA["source_id"], Literal(db_id)))`.

**Regra:** apesar de `disease_uri` codificar o ID no path, o predicado `hpoa:source_id` é mantido como literal duplicado (`"OMIM:154700"`). Razão: queries do gold standard fazem match textual via `source_id` (Q01, Q12, Q14, Q17), não via comparação de IRI.

**Implicação:** **redundância intencional**. Não eliminar mesmo que pareça desnormalização.

---

## 6. Validador SPARQL permissivo

**Onde:** `src/pipeline/sparql_validator.py`.

**Regra:** o `SchemaValidator` checa se predicados/classes referenciados existem em `data/schemas.json`, mas em **modo permissivo** (`strict=False`): termos desconhecidos geram aviso, não erro.

**Razão:** alguns termos válidos (URIs blank-node, propriedades raras com count baixo no GROUP_CONCAT da introspecção) podem não estar no cache.

🟡 LACUNA — comportamento do modo permissivo com termos inventados pelo LLM ainda não foi medido em ablação. Está em `_reversa_sdd/state.json:checkpoints.detective.lacunas`.

---

## 7. Pós-processamento SPARQL (8 transformações regex)

**Onde:** `src/pipeline/nl_to_sparql.py` (ver `_reversa_sdd/flowcharts/pipeline-fix_common_errors.md`).

**Regras aplicadas em sequência** (impactam queries antes de submissão ao Fuseki):

1. Remover `\boundary` e markers de markdown
2. Inserir prefixos faltantes (PREFIX rdfs:, obo:, hpoa:, oboInOwl:)
3. Mover `FILTER` para dentro do `GRAPH { }` correto
4. Resolver `BIND` que se auto-referencia
5. Adicionar `LIMIT` default se ausente em queries do tipo `list`
6. Normalizar literais string com aspas duplas
7. Trimar whitespace excessivo
8. Validar parênteses balanceados antes de submeter

**Razão:** LLMs (especialmente <10B params) emitem queries quase corretas; pequenos fixes determinísticos elevam taxa de sucesso de ~50% para ~80% (caso Nemotron 4B).

---

## 8. Cache de schema com fallback offline

**Onde:** `src/utils/schema_extractor.py` linhas 161-167.

**Regra:** se introspecção SPARQL falhar (Fuseki down), `extract_all_schemas` carrega `data/schemas.json` do disco em vez de propagar exceção.

**Implicação:** pipeline degrada graciosamente — testes unitários e geração offline funcionam sem Fuseki ativo.

---

## 9. Convenção de URI para classes OBO

**Regra implícita** em todas as queries: classes seguem padrão `http://purl.obolibrary.org/obo/{ONTO}_{numeric_id}` onde `{ONTO}` ∈ `{DOID, HP, ...}`. Sem essa convenção, joins via OBO URI quebrariam.

**Garantia:** `doid.owl` e `hp.owl` (release oficial) já seguem o padrão; `hpoa_to_rdf.py` constrói URIs HPO no mesmo formato.

---

## 10. Read-only do pipeline

**Regra de segurança:** o pipeline NL→SPARQL **nunca emite SPARQL Update** (`INSERT`, `DELETE`, `DROP`). Verificado via grep em `src/`: nenhum `setQuery` com Update; apenas SELECT/ASK/CONSTRUCT.

**Endpoint Fuseki é configurado com `--update`** (admin) mas o app não usa esse path.

🟢 CONFIRMADO via grep `INSERT|UPDATE|DELETE|DROP` em `src/` (sem matches no caminho de runtime).

---

## 11. Triggers / Stored Procedures / Functions

**Não aplicável.** Apache Jena Fuseki / TDB2 não suporta triggers nem stored procedures. Toda lógica reside na aplicação Python ou nos predicados RDF.

---

## 12. Views / Materialized Views

**Não aplicável** no Fuseki nativo. Equivalente conceitual:

- `data/schemas.json` é uma "view materializada" da estrutura via introspecção.
- FAISS index é uma "view materializada" das embeddings das perguntas.
- `data/annotations/hpoa.ttl` é uma materialização (TSV → Turtle) do `phenotype.hpoa`.

Re-materialização: rodar `schema_extractor.py`, `index_builder.py`, `hpoa_to_rdf.py` respectivamente.
