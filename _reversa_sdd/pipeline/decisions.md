# Decisions — pipeline

> Unit: `src/pipeline/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado
> ADRs de escopo do módulo pipeline: ADR-001, ADR-002, ADR-004, ADR-006

---

## ADR-P01 — BIND+REPLACE para JOIN DOID↔HPOA (não STRAFTER)

**Status:** ✅ Aceito
**Data:** 2026-05-04 (retroativo — commit `d657e09`)
**Confiança:** 🟢 CONFIRMADO

### Contexto

DOID armazena referências OMIM com prefixo `MIM:` em `oboInOwl:hasDbXref`. HPOA armazena o mesmo ID com prefixo `OMIM:` em `hpoa:source_id`. Para unir os dois grafos numa query SPARQL é necessário converter o prefixo. Dois padrões foram testados em produção:

```sparql
-- Opção A (descartada): STRAFTER
BIND(STRAFTER(STR(?mim), "MIM:") AS ?id)
-- Resultado: retorna "154700" — sem prefixo OMIM:, 0 correspondências

-- Opção B (adotada): REPLACE
BIND(REPLACE(STR(?mim), "^MIM:", "OMIM:") AS ?oid)
-- Resultado: retorna "OMIM:154700" — corresponde a hpoa:source_id
```

### Decisão

Usar `BIND+REPLACE` como padrão canônico em todo o sistema. Instruir o LLM explicitamente no system prompt e no `SEMANTIC_RETRY_FEEDBACK` a usar este padrão.

### Consequências

- O LLM pode ainda gerar `STRAFTER` (passa na validação, mas retorna 0 resultados) → detectado pelo semantic retry
- Documentado em `CLAUDE.md` como "Convenção Crítica do Domínio"
- Queries cross-graph sem o REPLACE sempre falharão silenciosamente

### Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| `STRAFTER` | Retorna apenas o número, sem prefixo `OMIM:` → 0 resultados |
| Unificar prefixo na ingestão (triplestore) | Modificaria dados originais das ontologias |

---

## ADR-P02 — Pós-processamento determinístico de erros LLM (9 transforms regex)

**Status:** ✅ Aceito
**Data:** 2026-05-04 (retroativo — commit `d657e09`)
**Confiança:** 🟢 CONFIRMADO

### Contexto

Dois padrões de erro recorrentes do modelo Nemotron 4B tornavam impossível execução direta das queries geradas:

1. **FILTER após `}`:** `FILTER` colocado fora do bloco WHERE → parse error no Jena
2. **BIND auto-referência:** `BIND(REPLACE(STR(?x),...) AS ?x)` → Jena rejeita com "Variable already in-scope"

Além disso, outros modelos geravam: pseudo-keywords (`DECLARE`, `IMPORT`), URIs de prefixo incorretas, `oboInOwl#` em vez de `oboInOwl:`, sintaxe SQL (`pred = ?var`) e URNs de grafo como namespaces de prefixo.

### Decisão

Implementar `_fix_common_errors()` com 9 transformações regex sequenciais aplicadas **antes da validação**, tornando o pré-processamento determinístico e reutilizável por todos os modelos.

### Consequências

- Nemotron mantém 80% de acurácia (seria ~50% sem as correções ⑦ e ⑧)
- Pós-processamento é aplicado a **todos** os modelos — pode ter efeitos colaterais em queries complexas com subconsultas aninhadas (🔴 LACUNA — não testado exaustivamente)
- Acumulação de 9 transforms gera risco de interações em edge cases
- Re-prompt seria alternativa mais limpa, mas consumiria uma tentativa extra por erro → latência maior

### Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Re-prompt para correção | Consome tentativa, latência maior |
| Rejeitar queries Nemotron | Melhor modelo (80%) — não pode ser descartado |
| Parser SPARQL completo | Rejeita queries inválidas antes da correção regex |

---

## ADR-P03 — Introspecção SPARQL para schema em vez de ShEx/SHACL

**Status:** ✅ Aceito
**Data:** 2026-05-04 (retroativo — mencionado em `CLAUDE.md`)
**Confiança:** 🟡 INFERIDO

### Contexto

Para validar classes e predicados nas queries geradas, o `SchemaValidator` precisa de um schema das ontologias. Alternativas formais (ShEx, SHACL) e dinâmicas (introspecção via SPARQL) foram consideradas.

### Decisão

Usar **introspecção SPARQL** via `src/utils/schema_extractor.py`: queries `GROUP_CONCAT` sobre cada grafo nomeado extraem classes e predicados e persistem em `data/schemas.json`.

### Consequências

- `schemas.json` gerado uma vez; pode ficar desatualizado com atualizações das ontologias
- Schema ausente → `SchemaValidator` modo permissivo silencioso (RN-06)
- Introspecção lenta em grafos grandes → retry exponencial implementado
- Schema contém apenas classes/predicados com instâncias — false negatives possíveis (🟡 INFERIDO)

### Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| ShEx shapes | Ontologias não distribuem shapes; criação manual é frágil |
| SHACL | Mesmo problema que ShEx |
| Schema hardcoded | Desatualiza a cada versão das ontologias |

---

## ADR-P04 — FAISS local para recuperação few-shot (não serviço externo)

**Status:** ✅ Aceito
**Data:** 2026-05-04 (retroativo — evidenciado pela estrutura do projeto)
**Confiança:** 🟡 INFERIDO

### Contexto

O pipeline usa few-shot RAG: recupera exemplos de queries similares do gold standard para incluir no prompt. A camada de recuperação precisava ser eficiente, offline e com graceful fallback.

### Decisão

Usar **FAISS-CPU com IndexFlatIP** (busca exata por Inner Product = cosine com vetores normalizados) e embeddings `all-MiniLM-L6-v2` (384 dimensões, sentence-transformers). Índice persistido em `data/gold_standard/questions.index`.

### Consequências

- Zero dependência de rede — funciona offline
- Embedder lazy-loaded: primeiro acesso tem latência de ~2-5s
- Índice ausente → fallback zero-shot automático (sem exceção)
- Corpus fixo de 30 exemplos — não cresce dinamicamente
- `IndexFlatIP` é busca exata — adequado para 30 exemplos; para >100K usaria `IndexIVFFlat`
- Modelo `all-MiniLM-L6-v2` genérico — não especializado em biomédico (possível melhoria futura)

### Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| ChromaDB | Overhead de servidor desnecessário para 30 exemplos |
| Pinecone / Weaviate | Dependência cloud, custo, incompatível com avaliação offline |
| BM25 lexical | Pior para similaridade semântica entre perguntas biomédicas |

---

## Resumo de Decisões

| ADR | Decisão | Status | Confiança |
|---|---|---|---|
| ADR-P01 | `BIND+REPLACE` para JOIN DOID↔HPOA | ✅ Aceito | 🟢 CONFIRMADO |
| ADR-P02 | 9 transforms regex em `_fix_common_errors()` | ✅ Aceito | 🟢 CONFIRMADO |
| ADR-P03 | Introspecção SPARQL para schema (não ShEx) | ✅ Aceito | 🟡 INFERIDO |
| ADR-P04 | FAISS local para few-shot RAG | ✅ Aceito | 🟡 INFERIDO |
