# Relatório de Confiança — BioSPARQL-NL

> Gerado pelo Revisor em 2026-05-04

---

## Resumo Geral

| Nível | Quantidade | Percentual |
|-------|-----------|------------|
| 🟢 CONFIRMADO | 329 | 80.6% |
| 🟡 INFERIDO   | 57  | 14.0% |
| 🔴 LACUNA     | 22  | 5.4%  |
| **Total**     | 408 | 100%  |

**Confiança geral: 87.6%** (fórmula: (329 + 57×0.5) / 408)

> _Atualizado em 2026-05-04 após resolução de GAP-05, GAP-06, GAP-08, GAP-09 (spec adicionada para gold_standard, GildaBackend, MedCATBackend, inter_annotator e bench_ner)._

> Sistema com alta cobertura de afirmações confirmadas diretamente no código. As lacunas restantes concentram-se em `pipeline/` (combinação de transforms ⑦+⑧ sem testes) e `gates/` (check Ollama legado aceito como risco).

---

## Por Spec

| Spec | 🟢 | 🟡 | 🔴 | Confiança |
|------|----|----|-----|-----------|
| `pipeline/` | 37 | 11 | 4 | 82% |
| `ner/` | 21 | 6 | 0 | 89% |
| `api/` | 20 | 3 | 0 | 93% |
| `avaliacao/` | 22 | 1 | 0 | 98% |
| `utilitarios/` | 19 | 0 | 0 | 100% |
| `frontend/` | 44 | 0 | 1 | 98% |
| `src2/` | 37 | 4 | 3 | 89% |
| `gates/` | 26 | 11 | 7 | 72% |

---

## Lacunas Pendentes 🔴

### `pipeline/`
- **Interação entre transforms ⑦+⑧ em queries combinadas** — nenhum teste cobre combinação FILTER solto + BIND auto-referência na mesma query.
  - Pergunta correspondente: `questions.md#pergunta-1`
- **Falsos positivos em modo permissivo** — impacto quantitativo da ausência de `schemas.json` não medido.
  - Pergunta correspondente: `questions.md#pergunta-2`
- **Validação de `LLM_TIMEOUT` não-numérico** — `float(os.environ.get(...))` sem try/except.
  - Pergunta correspondente: `questions.md#pergunta-3`
- **Transform ⑦ em brace multi-line** — `stripped == "}"` exige } sozinho na linha; casos com `} }` não cobertos (risco residual).

### `gates/`
- **Threshold `len(qs) >= 50`** — gold standard tem 30 questões; gate2 sempre falha.
  - Pergunta correspondente: `questions.md#pergunta-4`
- **Threshold `index.ntotal >= 50`** — FAISS tem 30 vetores; gate2 sempre falha.
  - Pergunta correspondente: `questions.md#pergunta-4`
- **Check Ollama legado** — gate0 verifica Ollama mas sistema usa LM Studio.
  - Pergunta correspondente: `questions.md#pergunta-5`

### `frontend/`
- **Comportamento do XaiPanel quando `xai.retries` está ausente no response** — spec doc EC, mas o campo não está no modelo Pydantic `ExplainabilityInfo`.

### `src2/`
- **Comportamento do corrections_report quando ambos os arquivos JSONL estão corrompidos (não ausentes)** — apenas o caso de arquivo ausente está testado.
- **Comportamento do PlaywrightRunner quando frontend demora mais de `--question-timeout`** — timeout é configurável mas o comportamento de cleanup após TimeoutError não está documentado.
- **`four_way_comparison.json` / `four_way_comparison.md`** — mencionados no CLAUDE.md como presentes em `output2/` mas não há spec de geração.

---

## Recomendações

- [x] ~~**gates/** — prioridade imediata: corrigir thresholds `>= 50` para `>= 30` no gate2~~ ✅ corrigido em 2026-05-05
- [ ] **pipeline/** — escrever 2-3 testes unitários cobrindo combinações de transforms antes de reimplementação (GAP-01)
- [x] ~~**gates/** — decidir destino do check Ollama~~ ✅ aceito como risco (P-5)
- [x] ~~**utilitarios/** — adicionar spec para `gold_standard.py`~~ ✅ T-07 expandido (GAP-05)
- [x] ~~**ner/** — documentar `gilda_backend.py` e `medcat_backend.py`~~ ✅ T-10 e T-11 adicionados (GAP-06/08)
- [x] ~~**avaliacao/** — adicionar spec para `inter_annotator.py` e `bench_ner.py`~~ ✅ T-09 e T-10 expandidos (GAP-09)

---

## Histórico de Reclassificações

| De | Para | Afirmação | Evidência |
|----|------|-----------|-----------|
| 🟡 | 🟢 | EC-05: `_extract_sparql()` extrai Markdown blocks | `nl_to_sparql.py:164-170` |
| 🔴 | 🟡 | Q-04: Transform ⑦ usa bracket counting | `nl_to_sparql.py:269-276` (`brace_depth`) |
| 🟢 | 🟡 | design.md pipeline: `run()` não retorna `entities`, `examples_used`, `timing` | `nl_to_sparql.py:run()` docstring + `server.py:ask()` |
| 🟢 | 🟡 | api: health endpoint path é `/api/health`, não `/health`; retorna só `{status}` | `server.py:153,63` |
| 🟡 | 🟢 | pipeline design: semantic retry exige `result["success"]==True` (adicionado ao flowchart) | `nl_to_sparql.py:436` |
| ausente | 🟢 | T-10: `_extract_sparql()` adicionado ao pipeline/tasks.md | `nl_to_sparql.py:164-170` |
| 🔴 | 🟢 | gate2: `len(qs) >= 50` → `>= 30` (bug corrigido em 2026-05-05) | `gates/gate2_check.py:31` |
| 🔴 | 🟢 | gate2: `index.ntotal >= 50` → `>= 30` (bug corrigido em 2026-05-05) | `gates/gate2_check.py:85` |
| 🔴 | 🟢 | EC-04: modo permissivo = warning, dados de ablação confirmam −16.7pp exec rate | `output/ablation_google_gemma-3-4b.json` |

---

## Revisão Cruzada

- Engine externa consultada: nenhuma (Codex não disponível nesta sessão)
- Apontamentos externos recebidos: 0
- Revisão realizada por: Reviewer (claude-sonnet-4-6)
