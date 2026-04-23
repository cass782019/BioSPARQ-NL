# BioSPARQL-NL: Comparativo 3-way de modelos locais

| Modelo | Overall | Easy | Medium | Hard | Sintatica |
|--------|---------|------|--------|------|-----------|
| baseline (gemma-3-4b, sem correcoes) | 24/52 (46.2%) | 9/13 (69%) | 9/18 (50%) | 6/21 (29%) | 92.3% |
| gemma-3-4b (corrigido) | 30/52 (57.7%) | 10/13 (77%) | 13/18 (72%) | 7/21 (33%) | 90.4% |
| nvidia/nemotron-3-nano-4b (corrigido) | 19/52 (36.5%) | 7/13 (54%) | 7/18 (39%) | 5/21 (24%) | 53.8% |

## Conclusao

**Vencedor: gemma-3-4b corrigido** em todas as categorias de dificuldade.

Nemotron-3-nano-4b, apesar de ser um modelo de raciocinio (reasoning content),
teve desempenho inferior neste workload porque:
1. Budget de tokens consumido por reasoning antes do content final
2. Instabilidade com prompts longos (+3k tokens) - queries invalidas frequentes
3. Lentidao (~40-80s vs ~10s gemma) amplificando erros e causando timeouts
4. Arquitetura nao escala para padroes SPARQL complexos (subquery, UNION, triple joins)