# Lacunas da Documentação — BioSPARQL-NL

> Gerado pelo Revisor em 2026-05-04
> Categorizado por severidade: crítico / moderado / cosmético

---

## Crítico — bloqueiam reimplementação segura

### GAP-01 — Transforms ⑦ e ⑧ em queries combinadas não testadas
**Unit:** `pipeline`
**Arquivo afetado:** `_reversa_sdd/pipeline/questions.md#q-01`
**Descrição:** Não há testes que verifiquem o comportamento quando FILTER solto + BIND auto-referência coexistem na mesma query. Ordem de aplicação (⑦ antes de ⑧) pode produzir resultado diferente de ⑧ antes de ⑦.
**Evidência:** Ambos os padrões foram observados em produção (EC-01 e EC-02). Nenhum teste de combinação existe em `tests/unit/`.
**Ação recomendada:** Escrever ao menos 2 testes unitários com queries combinadas antes de reimplementar.

---

### ~~GAP-02~~ — ✅ RESOLVIDO em 2026-05-05
**Unit:** `gates`
**Resolução:** Thresholds corrigidos de `>= 50` para `>= 30` em `gate2_check.py:31` e `gate2_check.py:85`. Spec `gates/requirements.md` atualizada.

---

## Moderado — impactam qualidade mas não bloqueiam

### ~~GAP-03~~ — ✅ RESOLVIDO em 2026-05-05
**Unit:** `pipeline`
**Resolução:** Ablação Gemma 3 4B confirmou −16.7pp execution rate sem schema. Decisão: manter warning, não erro fatal. RF-09 e EC-04 atualizados.

### GAP-04 — Gate 0 verifica Ollama (migrado para LM Studio)
**Unit:** `gates`
**Arquivo afetado:** `gates/gate0_check.py` — verificação Ollama
**Descrição:** O check de Ollama em `localhost:11434` nunca passará em ambiente com LM Studio em `:1234`. Não está claro se deve ser substituído ou removido.
**Ação recomendada:** Atualizar conforme decisão do usuário (P-5).

### ~~GAP-05~~ — ✅ RESOLVIDO em 2026-05-04
**Unit:** `utilitarios`
**Resolução:** T-07 em `utilitarios/tasks.md` expandido com spec completa de `GOLD_STANDARD` (30 dicts, invariante 10/10/10) e `save_gold_standard(output_path)` (serialização JSON + print de distribuição).

### ~~GAP-06~~ — ✅ RESOLVIDO em 2026-05-04
**Unit:** `ner`
**Resolução:** T-10 (`GildaBackend`) e T-11 (`MedCATBackend`) adicionados a `ner/tasks.md` com spec de implementação, critérios de pronto e documentação de dependências. Ambos marcados `Could` (backends experimentais, fora do pipeline de produção).

---

## Cosmético — inconsistências menores

### GAP-07 — Timing fields em segundos (`_s`), não milissegundos (`_ms`)
**Unit:** `pipeline`
**Arquivo afetado:** `_reversa_sdd/pipeline/design.md` (já corrigido pelo Reviewer)
**Descrição:** Spec original dizia `ner_ms`, `faiss_ms` etc. mas o código usa `ner_s`, `retrieval_s`, `llm_s`, `total_s` (segundos). **Já corrigido no design.md.**

### ~~GAP-08~~ — ✅ RESOLVIDO em 2026-05-04
**Unit:** `ner`
**Resolução:** `ner/design.md` expandido com seção "Backends Experimentais" contendo fluxograma do `GildaBackend` (spaCy → gilda.ground → filtro score+namespace → merge_overlaps) e dependências do `MedCATBackend` (variáveis de ambiente + build step).

### ~~GAP-09~~ — ✅ RESOLVIDO em 2026-05-04
**Unit:** `avaliacao`
**Resolução:** T-09 (`inter_annotator.py`) e T-10 (`bench_ner.py`) expandidos em `avaliacao/tasks.md` com spec completa: métricas (Jaccard + Cohen's kappa), modos de operação (coverage e scored), CLI, critérios de pronto.

---

## Resumo por severidade

| Severidade | Quantidade | GAPs |
|---|---|---|
| Crítico | 2 | GAP-01 (aberto), GAP-02 (✅) |
| Moderado | 4 | GAP-03 (✅), GAP-04 (aceito), GAP-05 (✅), GAP-06 (✅) |
| Cosmético | 3 | GAP-07 (✅), GAP-08 (✅), GAP-09 (✅) |
| **Abertos** | **2** | GAP-01 (testes combinados), GAP-04 (Ollama check aceito como risco) |
