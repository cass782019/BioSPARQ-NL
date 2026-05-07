# Edge Cases — pipeline

> Unit: `src/pipeline/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## EC-01 — LLM gera query com BIND auto-referência (`?x AS ?x`)

**Origem:** `_fix_common_errors()` — transform ⑧
**Confiança:** 🟢 CONFIRMADO — correção existente no código
**Frequência:** 🟡 Ocasional (observado em múltiplos modelos)

### Descrição

O Jena rejeita queries que referenciam a mesma variável como fonte e destino de BIND:

```sparql
# Alucinação comum
BIND(REPLACE(STR(?xref), "^MIM:", "OMIM:") AS ?xref)
# Erro Jena: "Variable ?xref is already in-scope"
```

### Tratamento atual

Transform ⑧ detecta o padrão via regex e renomeia a variável fonte:
```sparql
# Após correção
BIND(REPLACE(STR(?xref_mim), "^MIM:", "OMIM:") AS ?xref)
```

### Risco residual

Se a variável renomeada (`?xref_mim`) for referenciada em outros pontos da query (ex: em um SELECT), a renomeação parcial cria uma variável indefinida. 🔴 **Lacuna documentada pelo Detetive.**

---

## EC-02 — FILTER colocado após o último `}` do WHERE

**Origem:** `_fix_common_errors()` — transform ⑦
**Confiança:** 🟢 CONFIRMADO — correção existente no código
**Frequência:** 🟡 Frequente (Nemotron especificamente)

### Descrição

Modelos como Nemotron colocam FILTER fora do bloco WHERE:

```sparql
SELECT ?disease WHERE {
  ?disease rdfs:label ?label .
}
FILTER(CONTAINS(LCASE(?label), "parkinson"))  # inválido — fora do WHERE
```

### Tratamento atual

Transform ⑦ detecta FILTERs após o último `}` com regex e os move para dentro:

```sparql
SELECT ?disease WHERE {
  ?disease rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), "parkinson"))
}
```

### Risco residual

Queries com **subconsultas aninhadas** (`{ SELECT ... WHERE { ... } }`) podem ter múltiplos fechamentos `}`. A regex pode inserir o FILTER no bloco errado. 🔴 **Lacuna documentada pelo Detetive.**

---

## EC-03 — Query sintaticamente válida retorna 0 resultados (label em português)

**Origem:** `run()` — semantic retry trigger
**Confiança:** 🟢 CONFIRMADO — `SEMANTIC_RETRY_FEEDBACK` existe no código
**Frequência:** 🔴 Alta (causa mais comum de falha nas 30 questões)

### Descrição

O LLM usa o termo da pergunta diretamente no FILTER sem traduzir para inglês:

```sparql
# Gerado para "Quais doenças causam febre?"
FILTER(CONTAINS(LCASE(?label), "febre"))  # 0 resultados — labels são em inglês
```

### Tratamento atual

Semantic retry: pipeline detecta `count == 0` em query válida, seta `semantic_retry_used = True` e re-prompta com `SEMANTIC_RETRY_FEEDBACK` que instrui explicitamente a usar "fever" em vez de "febre".

### Risco residual

O semantic retry dispara apenas **uma vez** por execução. Se a segunda tentativa também usar português (LLM ignora o feedback), o resultado é `DONE_EMPTY`. Não há terceiro retry semântico.

---

## EC-04 — schemas.json ausente ou corrompido → modo permissivo silencioso

**Origem:** `SchemaValidator.__init__()`
**Confiança:** 🟢 CONFIRMADO — RN-06
**Frequência:** 🟡 Raro em produção, comum em setup inicial

### Descrição

Se `data/schemas.json` não existe ou tem JSON inválido, o `SchemaValidator` entra em modo `PERMISSIVE` sem log de erro visível ao usuário. Queries com predicados inválidos (ex: `hpoa:invented_predicate`) passam na validação e chegam ao Fuseki, onde retornam 0 resultados sem explicação clara.

### Tratamento atual

Modo permissivo faz apenas checagem de sintaxe, unsafe ops e grafos. Termos ontológicos não são verificados.

### Dados medidos (ablação Gemma 3 4B)

| Config | Correctness | Execution rate |
|--------|-------------|----------------|
| `full_pipeline` | 50.0% | 76.7% |
| `no_schema` | 46.7% | 60.0% |
| Delta | −3.3pp | **−16.7pp** |

🟢 **CONFIRMADO** (2026-05-05) — o schema descarta queries sintaticamente válidas mas semanticamente erradas antes de chegarem ao Fuseki. Penalidade em correctness é pequena, mas custo em execuções desperdiçadas é significativo.

### Decisão validada

Manter `schemas.json` ausente como **warning** (fallback silencioso), não como erro fatal. Adicionar `log.warning("SchemaValidator em modo PERMISSIVE — schemas.json ausente")` no `__init__`.

---

## EC-05 — LLM retorna SPARQL dentro de bloco Markdown (```sparql ... ```)

**Origem:** `nl_to_sparql.py:_extract_sparql()` — chamado em `generate_sparql()`
**Confiança:** 🟢 CONFIRMADO — `nl_to_sparql.py:164-170` [Revisão Reviewer]
**Frequência:** 🟡 Frequente com modelos instrução-seguidos

### Descrição

Modelos instruction-tuned frequentemente envolvem a query em blocos Markdown. Se não extraído corretamente, a query inclui os delimitadores e falha na validação de sintaxe.

### Tratamento real (CONFIRMADO)

`generate_sparql()` chama `_extract_sparql(raw)` (método estático) antes de aplicar `_fix_common_errors`:

```python
@staticmethod
def _extract_sparql(raw: str) -> str:
    if "```sparql" in raw:
        return raw.split("```sparql")[1].split("```")[0].strip()
    elif "```" in raw:
        return raw.split("```")[1].split("```")[0].strip()
    return raw.strip()
```

Extrai corretamente blocos ` ```sparql ``` ` e ` ``` ``` ` genéricos. Risco residual: se o LLM usar um bloco sem fechamento ` ``` `, o split pode capturar mais texto do que o esperado.

---

## EC-06 — Todas as tentativas esgotadas com query inválida (DONE_INVALID_FORCED)

**Origem:** `run()` — branch `attempt == max_attempts AND NOT valid`
**Confiança:** 🟢 CONFIRMADO — RN-07
**Frequência:** 🟢 Raro (ocorre com questões "hard" e LLMs 4B)

### Descrição

Após 4 tentativas, a última query ainda é inválida. O pipeline a executa mesmo assim (`DONE_INVALID_FORCED`).

**Comportamento:** O Fuseki pode retornar:
- Erro de parse → `execute_sparql()` retorna `success=False, count=0`
- Resultado parcial (se o erro não bloquear execução) → pode retornar dados úteis

**Retorno ao caller:** `success=False`, `attempts=4`, `execution.success` pode ser True ou False dependendo do Fuseki.

### Risco

O caller (FastAPI/frontend) recebe `success=False` mas `execution.results` pode ter dados. A lógica de apresentação no frontend deve tratar esse estado ambíguo.

---

## EC-07 — Semantic retry esgotado sem sucesso (FALLBACK)

**Origem:** `run()` — condição `semantic_retry_used AND count == 0 AND attempt == max_attempts`
**Confiança:** 🟢 CONFIRMADO — flowchart FALLBACK state
**Frequência:** 🟡 Ocasional (questões cross-graph com LLMs 4B)

### Descrição

O pipeline usou o semantic retry mas a segunda tentativa também retornou 0 resultados. Ao esgotar `max_attempts`, retorna o `last_result` (salvo antes do retry) com `success=False`.

**Impacto:** O usuário recebe uma query válida (sintaticamente) mas sem resultados, sem explicação clara de que o problema é semântico (labels em PT vs EN).

---

## EC-08 — LLM gera query com múltiplos blocos PREFIX duplicados

**Origem:** `_fix_common_errors()` — transform ③ + `_inject_missing_prefixes()`
**Confiança:** 🟡 INFERIDO — padrão observado em modelos de raciocínio
**Frequência:** 🟡 Ocasional (Nemotron com reasoning tokens)

### Descrição

Após canonicalização (transform ③) e injeção de prefixos (T-04), a query pode ter o mesmo `PREFIX` declarado duas vezes se o LLM já o declarou e o injetor o adiciona novamente.

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>  # duplicado
```

O Jena rejeita prefixos duplicados com erro de sintaxe.

### Mitigação recomendada

`_inject_missing_prefixes()` deve verificar se o prefixo já está declarado antes de injetar (comparar contra resultado de `re.findall(r'PREFIX\s+(\w+):', query)`).

---

## EC-09 — NER resolve entidade para CURIE de grafo errado

**Origem:** `entity_linker.py` + `scispacy_backend.py:_resolve()`
**Confiança:** 🟡 INFERIDO
**Frequência:** 🟡 Rara mas possível

### Descrição

O NER pode resolver "Parkinson disease" para `DOID:14330`, mas se a pergunta pergunta sobre fenótipos associados, a query precisa do CURIE em `urn:hpoa`, não em `urn:doid`. O LLM recebe o CURIE correto mas pode não saber em qual grafo usá-lo.

### Tratamento atual

O `build_prompt()` instrui o LLM sobre qual grafo usar para cada tipo de informação. O CURIE é fornecido como contexto, mas a query correta pode ou não usá-lo diretamente.

---

## EC-10 — Pergunta em inglês enviada ao pipeline

**Origem:** `build_prompt()` — sem detecção de idioma
**Confiança:** 🟡 INFERIDO
**Frequência:** 🟢 Raro (sistema voltado para PT)

### Descrição

O sistema não detecta o idioma da pergunta. Se o usuário digita em inglês ("What diseases are associated with fever?"), o system prompt instrui a traduzir PT→EN, mas a pergunta já está em inglês. O comportamento é geralmente correto (o LLM ignora a instrução de tradução), mas a instrução de PT→EN pode confundir modelos menores.

### Impacto

🟢 Baixo — em experimentos, perguntas em inglês funcionaram corretamente nos 3 modelos avaliados.
