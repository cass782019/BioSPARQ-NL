# ADR-001 — BIND+REPLACE para JOIN DOID↔HPOA em vez de STRAFTER

> Data: 2026-05-04 (retroativo — extraído do commit `d657e09`)
> Status: **Aceito**
> Confiança: 🟢 CONFIRMADO

---

## Contexto

DOID armazena referências OMIM com prefixo `MIM:` (ex: `"MIM:154700"`) no predicado `oboInOwl:hasDbXref`. HPOA armazena o mesmo ID com prefixo `OMIM:` (ex: `"OMIM:154700"`) no predicado `hpoa:source_id`. Para unir os dois grafos numa query SPARQL, é necessário converter o prefixo.

Dois padrões foram testados:

**Opção A — STRAFTER:**
```sparql
BIND(STRAFTER(STR(?mim), "MIM:") AS ?id)
```

**Opção B — REPLACE:**
```sparql
BIND(REPLACE(STR(?mim), "^MIM:", "OMIM:") AS ?oid)
```

## Decisão

Adotar **Opção B — BIND+REPLACE** como padrão canônico no sistema prompt e no `SEMANTIC_RETRY_FEEDBACK`.

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| `STRAFTER(STR(?mim), "MIM:")` | **0 resultados em todos os testes** | Retorna apenas a parte numérica (`154700`), sem prefixo `OMIM:`, que não coincide com `hpoa:source_id` = `"OMIM:154700"` |
| `REPLACE(STR(?mim), "^MIM:", "OMIM:")` | ✅ Resultados corretos | Produz `"OMIM:154700"` que coincide exatamente |
| Pre-processamento na ingestão (unificar prefixo no triplestore) | Não tentado | Modificaria os dados originais das ontologias |

## Consequências

- O system prompt do pipeline instrui explicitamente o LLM a usar `REPLACE` para joins DOID↔HPOA
- O `SEMANTIC_RETRY_FEEDBACK` (disparado quando query retorna 0 resultados) inclui o padrão correto
- Queries que usem `STRAFTER` podem ser geradas pelo LLM e passam na validação, mas retornarão 0 resultados — detectado pelo semantic retry
- Documentado em `CLAUDE.md` como "Convenção Crítica do Domínio"
