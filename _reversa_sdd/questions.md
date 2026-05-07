# Perguntas para Validação — BioSPARQL-NL

> Gerado pelo Revisor em 2026-05-04
> Responda cada pergunta no chat e me avise quando terminar.

---

## Pergunta 1

**Contexto:** `src/pipeline/nl_to_sparql.py:_fix_common_errors()` — transform ⑦ e interact com transforms anteriores
**Spec afetada:** [`_reversa_sdd/pipeline/questions.md#q-01`]
**Pergunta:** Existe algum caso conhecido em que as 9 transformações de pós-processamento interagem de forma problemática? Em particular: se o LLM gerar uma query com FILTER solto **e** BIND com auto-referência ao mesmo tempo, as transforms ⑦ e ⑧ são seguras de aplicar em sequência sobre a mesma query?
**Impacto:** Se a interação causar queries inválidas após correção, pode ser necessário adicionar testes de integração específicos para combinações de erros ou refatorar `_fix_common_errors()` para ser idempotente.

**Resposta:** <!-- preencha aqui -->

---

## Pergunta 2 ✅ Respondida

**Contexto:** `src/pipeline/sparql_validator.py:SchemaValidator` — modo permissivo quando `schemas.json` ausente
**Spec afetada:** [`_reversa_sdd/pipeline/questions.md#q-02`], [`_reversa_sdd/pipeline/requirements.md#rf-09`], [`_reversa_sdd/pipeline/edge-cases.md#ec-04`]

**Resposta (dados de ablação Gemma 3 4B):**
- `full_pipeline`: 50.0% correctness, 76.7% execution rate
- `no_schema`: 46.7% correctness, 60.0% execution rate
- Delta: −3.3pp correctness, **−16.7pp execution rate**

**Decisão:** Manter como warning (não erro fatal). Schema descarta queries semanticamente erradas que consumiriam o Fuseki desnecessariamente. Specs atualizadas: RF-09 e EC-04.

---

## Pergunta 3 ✅ Implementado

**Contexto:** `src/pipeline/nl_to_sparql.py:__init__()` — leitura de variáveis de ambiente
**Spec afetada:** [`_reversa_sdd/pipeline/questions.md#q-03`]

**Resposta:** `try/except ValueError` adicionado em 2026-05-05. Fallback: 300s com `logger.warning("LLM_TIMEOUT invalido, usando 300s")`. `LLM_MODEL` inválido resulta em erro na primeira chamada ao backend — comportamento aceitável.

---

## Pergunta 4 ✅ Respondida

**Contexto:** `gates/gate2_check.py` — thresholds de validação
**Spec afetada:** [`_reversa_sdd/gates/requirements.md#rf-03`]

**Resposta:** Bugs confirmados, corrigidos em 2026-05-05.
- `len(qs) >= 50` → `len(qs) >= 30` (`gate2_check.py:31`)
- `index.ntotal >= 50` → `index.ntotal >= 30` (`gate2_check.py:85`)
- Spec `gates/requirements.md` atualizada.

---

## Pergunta 5 ⏭️ Aceito como risco

**Contexto:** `gates/gate0_check.py` — verificação de Ollama
**Spec afetada:** [`_reversa_sdd/gates/requirements.md#rf-01`]

**Decisão (2026-05-05):** Manter o check Ollama legado. A falha neste check não bloqueia o gate (outros checks passam). Documentado como 🟡 INFERIDO (legado — sistema migrou para LM Studio).

---

## Resumo

| ID | Pergunta | Risco | Status |
|---|---|---|---|
| P-1 | Interações entre transforms ⑦ e ⑧ combinadas | 🔴 Alto | ⏭️ Aceito como risco — testes de combinação a escrever antes de reimplementar |
| P-2 | Falsos positivos em modo permissivo (schemas.json ausente) | 🟡 Médio | ✅ Respondido — warning, não fatal |
| P-3 | Validação de LLM_TIMEOUT não-numérico | 🟢 Baixo | ✅ Implementado — try/except ValueError em nl_to_sparql.py:__init__() |
| P-4 | Bug gate2: thresholds 50 vs 30 | 🔴 Alto (gate sempre falha) | ✅ Corrigido em 2026-05-05 |
| P-5 | Gate0: Ollama check legado | 🟡 Médio | ⏭️ Manter — check opcional, falha não bloqueia gate |
