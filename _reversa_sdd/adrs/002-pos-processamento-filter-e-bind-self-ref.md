# ADR-002 — Pós-processamento automático de FILTERs soltos e BIND com auto-referência

> Data: 2026-05-04 (retroativo — extraído do commit `d657e09`)
> Status: **Aceito**
> Confiança: 🟢 CONFIRMADO

---

## Contexto

Dois padrões de erro recorrentes foram identificados ao avaliar o modelo Nemotron 4B:

**Problema 1 — FILTER após fechamento do WHERE:**
O Nemotron frequentemente gera FILTER clauses depois do `}` que fecha o bloco WHERE:
```sparql
WHERE { GRAPH <urn:doid> { ... } }
FILTER(CONTAINS(?label, "fever"))
```
Isso causa parse error `"Expected end of text"` no Jena.

**Problema 2 — BIND com auto-referência:**
O LLM gera `BIND(REPLACE(STR(?x), ...) AS ?x)`, onde a variável fonte é idêntica ao destino. O Apache Jena rejeita com `"Variable used when already in-scope in BIND"`.

## Decisão

Adicionar dois passos ao método `_fix_common_errors()` para corrigir esses padrões automaticamente antes da validação:

**Fix 1 — Mover FILTERs soltos para dentro do WHERE:**
- Localizar o último `}` de profundidade 0
- Coletar linhas FILTER após esse `}`
- Reinserí-las antes do último `}`

**Fix 2 — Renomear variável fonte em BIND auto-referencial:**
- Detectar padrão `BIND(REPLACE(STR(?x), ...) AS ?x)`
- Renomear todas as ocorrências de `?x` antes do BIND para `?x_mim`
- Atualizar o BIND para usar `?x_mim` como fonte

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| Pedir ao LLM para corrigir via re-prompt | Funciona mas consome uma tentativa extra | Pós-processamento é mais eficiente e determinístico |
| Rejeitar queries com esses padrões | Pipeline falha completamente para o Nemotron | Nemotron é o modelo com melhor resultado (80%) — não pode ser ignorado |
| Instruir o LLM via system prompt | Reduz mas não elimina ocorrências | LLMs com reasoning tokens ignoram às vezes instruções de formatação |

## Consequências

- O Nemotron mantém seu desempenho de 80% (melhor resultado da avaliação)
- Pós-processamento é aplicado a **todos** os modelos (não apenas Nemotron) — pode ter efeitos colaterais não esperados em queries que usem FILTERs depois de subconsultas aninhadas (🔴 LACUNA — não testado exaustivamente)
- O método `_fix_common_errors()` acumula 9 transformações regex sequenciais — risco de interações entre transformações em casos extremos (🟡 INFERIDO)
- Documentado com exemplos inline no código
