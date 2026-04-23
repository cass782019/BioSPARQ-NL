# BioSPARQL-NL: Comparativo 4-way (baseline, locais corrigidos, Claude upper bound)

| Modelo | Overall | Easy | Medium | Hard | Sint. | Tempo |
|--------|---------|------|--------|------|-------|-------|
| baseline (gemma-3-4b sem correcoes) | **24/52 (46.2%)** | 9/13 (69%) | 9/18 (50%) | 6/21 (29%) | 92% | 18.9s |
| gemma-3-4b (corrigido) | **30/52 (57.7%)** | 10/13 (77%) | 13/18 (72%) | 7/21 (33%) | 90% | 12.4s |
| nvidia/nemotron-3-nano-4b (corrigido) | **19/52 (36.5%)** | 7/13 (54%) | 7/18 (39%) | 5/21 (24%) | 54% | 37.4s |
| claude-sonnet (via CLI, upper bound) | **45/52 (86.5%)** | 12/13 (92%) | 16/18 (89%) | 17/21 (81%) | 100% | 11.5s |

## Principais achados

- **Baseline (gemma sem correcoes): 46%**
- **gemma-3-4b corrigido: +11pp** via prompt engineering + NER filter + post-proc
- **Nemotron (corrigido): 36%** — reasoning content consome budget e thermal throttling degradou o resultado
- **Claude Sonnet (upper bound): 86%** — diferenca de 28pp vs melhor modelo local

## Claude Sonnet vs gemma-3-4b corrigido

- Claude ganha em 15 questoes: Q05, Q06, Q15, Q20, Q23, Q25, Q27, Q28, Q29, Q38, Q39, Q40, Q45, Q46, Q49
- Claude perde em 0 questoes: nenhuma
- Ainda falha no Claude: Q09, Q16, Q30, Q32, Q41, Q51, Q52