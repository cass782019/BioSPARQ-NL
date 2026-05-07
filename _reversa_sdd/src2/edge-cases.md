# Edge Cases — src2

> Unit: `src2/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## EC-01 — CLAUDE.md do projeto descoberto pelo `claude` CLI

**Origem:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend.__init__()` — `cwd=self.workdir`
**Confiança:** 🟢 CONFIRMADO

**Situação:** Se `ClaudeCLIBackend` for executado com `cwd` dentro de `proj1/` (ou de qualquer diretório ascendente que contenha `CLAUDE.md`), o `claude` CLI auto-descobre esse arquivo e injeta as instruções do projeto no contexto, contaminando o benchmark.

**Comportamento esperado:** O workdir isolado `~/.biosparql-bench-workdir` fica fora de qualquer repositório com `CLAUDE.md`, prevenindo a descoberta automática.

**Risco:** 🟡 Se o usuário mover o projeto para `~/.biosparql-bench-workdir/...` ou criar um `CLAUDE.md` em `~/`, a proteção falha. O mecanismo depende de convenção de localização, não de flag de opt-out explícita do `claude` CLI.

---

## EC-02 — `claude` CLI autenticado mas sem sessão OAuth válida

**Origem:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend.generate()`
**Confiança:** 🟡 INFERIDO

**Situação:** O `claude` CLI está no PATH (`shutil.which` não é None), mas a sessão OAuth expirou ou nunca foi estabelecida.

**Comportamento esperado:** O processo `claude` retorna `returncode != 0` com mensagem de erro de autenticação no stderr. O backend lança `RuntimeError` com os primeiros 500 caracteres do stderr.

**Risco:** 🔴 **LACUNA** — A mensagem de erro do `claude` CLI para sessão expirada não foi documentada. O usuário pode receber `RuntimeError: claude CLI failed (code 1): <mensagem de auth>` sem instrução clara de como reautenticar. Seria útil detectar esse padrão e sugerir `claude login`.

---

## EC-03 — Timeout do Playwright com frontend lento ao inicializar

**Origem:** `src2/evaluation/playwright_runner.py:run()` — `page.goto(..., timeout=30000)`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O frontend em `localhost:3000` demora mais de 30s para atingir `networkidle` (ex: Vite compilando arquivos grandes na primeira carga).

**Comportamento esperado:** `page.goto` lança `playwright.sync_api.TimeoutError`. Como está fora do try/except por questão, o erro propaga e aborta toda a execução do runner.

**Risco:** 🟡 Diferente do timeout por questão (que é capturado e logado como `exception`), o timeout do `page.goto` inicial aborta o runner completamente sem gerar nenhum JSONL. O usuário não tem indicação clara de que o problema foi o carregamento inicial, não uma questão específica.

---

## EC-04 — Questão com `captured["latest"]` nunca populado por rejeição de CORS ou erro de parse

**Origem:** `src2/evaluation/playwright_runner.py:handle_response()`
**Confiança:** 🟢 CONFIRMADO

**Situação A:** O proxy Vite está mal configurado e a chamada `/api/ask` retorna erro de rede (sem resposta HTTP). Nesse caso `handle_response` nunca é chamado e `captured["latest"]` permanece `None` até o timeout da questão.

**Situação B:** O backend retorna resposta com `Content-Type` incorreto (não JSON). `response.json()` lança exceção → `captured["error"]` é populado → record com `status="error"`.

**Comportamento esperado em A:** Timeout da questão → record com `status="exception"`, `exception="Timeout apos Ns"` — o loop continua para a próxima questão.

**Comportamento esperado em B:** Record com `status="error"`, `error=str(e)` — o loop continua.

---

## EC-05 — `--append` com log de sessão anterior incompleta

**Origem:** `src2/evaluation/playwright_runner.py:run()` — `fresh_run = not args.append`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O runner foi abortado no meio de uma execução anterior (ex: Ctrl+C na questão Q15). O JSONL contém Q01–Q14. O usuário roda novamente com `--append`.

**Comportamento esperado:** As questões Q15–Q30 são adicionadas ao JSONL. O summary final inclui apenas as questões desta execução (`summary_rows` acumulado apenas na sessão atual), não as 14 anteriores.

**Risco:** 🟡 O `playwright_summary.json` reflete apenas as questões da execução atual, não o total acumulado do JSONL. Para análise completa com `--append`, o usuário deve usar `corrections_report.py` ou processar o JSONL diretamente.

---

## EC-06 — `corrections_report` com questões presentes apenas no baseline ou apenas no current

**Origem:** `src2/evaluation/corrections_report.py:classify_changes()`
**Confiança:** 🟢 CONFIRMADO

**Situação:** Questões foram adicionadas ao gold standard entre o baseline e a execução atual (ex: baseline tem Q01–Q30, current tem Q01–Q35).

**Comportamento esperado:**

```python
for qid in sorted(set(base.keys()) | set(corr.keys())):
    b = base.get(qid, {}).get("success", False)  # False para qid ausente no baseline
    c = corr.get(qid, {}).get("success", False)
```

- Q31–Q35 presentes apenas no current: `b=False`, logo classificadas como `recovered` se `c=True`, ou `still_fail` se `c=False`.

**Risco:** 🟡 Questões novas (ausentes no baseline) que passam são contadas como "recuperadas" — tecnicamente incorreto, pois nunca falharam. O relatório pode inflar artificialmente a contagem de `recovered` quando o gold standard muda entre baseline e current.

---

## EC-07 — ClaudeCLIBackend com `--max-budget-usd` e resposta truncada

**Origem:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend.generate()` — `--max-budget-usd`
**Confiança:** 🟡 INFERIDO

**Situação:** `config["max_budget_usd"]` está definido (ex: `0.05`) e a geração de SPARQL atingiu o budget antes de completar a query.

**Comportamento esperado:** O `claude` CLI pode retornar resposta parcial com `returncode=0` (sem erro explícito) — o backend retorna o stdout parcial sem detectar o truncamento.

**Risco:** 🔴 **LACUNA** — Não há validação de que o output do ClaudeCLIBackend é uma query SPARQL completa antes de passá-la ao pipeline. O pós-processamento e validação do pipeline devem capturar o SPARQL malformado, mas a causa raiz (budget) não é rastreada no log.

---

## EC-08 — Polling do Playwright com `page.wait_for_timeout` bloqueando o event loop

**Origem:** `src2/evaluation/playwright_runner.py:run()` — polling loop
**Confiança:** 🟡 INFERIDO

**Situação:** O polling usa `page.wait_for_timeout(500)` dentro de um `while` que verifica `captured["latest"]`. Durante os 500ms de espera, o event loop do Playwright continua processando eventos — incluindo o `handle_response`. Porém, se o LLM demorar mais que `question_timeout` segundos, o loop encerra com `TimeoutError`.

**Comportamento esperado:** O `TimeoutError` é capturado pelo `except Exception as e` externo (linha ~195), gravado como record com `status="exception"` e o loop segue para a próxima questão.

**Risco:** 🟢 Comportamento correto e confirmado. Nenhuma questão com timeout aborta o runner completo. O risco residual é que questões com timeout consomem `question_timeout` segundos cada, podendo tornar a execução completa muito longa (ex: 30 questões × 300s = 2.5h no pior caso).

---

## EC-09 — run_all_models.py (src2): modelo com OOM silencioso

**Origem:** `src2/evaluation/run_all_models.py:check_lm_studio_responds()`
**Confiança:** 🟡 INFERIDO

**Situação:** O LM Studio carregou o modelo mas está em offload para CPU (memória insuficiente). A resposta a "Say OK" pode demorar mais de 60s (timeout do `check_lm_studio_responds`).

**Comportamento esperado:** `check_lm_studio_responds` retorna `False` → modelo classificado como `"oom"` → `[SKIP]`.

**Risco:** 🟡 O diagnóstico "OOM" é inferido pelo timeout de resposta, não por mensagem explícita do LM Studio. Um modelo lento (mas funcional) pode ser incorretamente classificado como OOM e pulado.

---

## EC-10 — Workdir `~/.biosparql-bench-workdir` não limpo entre execuções

**Origem:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend.__init__()` — `os.makedirs(exist_ok=True)`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O workdir é criado uma vez e reutilizado em todas as execuções. Arquivos temporários gerados pelo `claude` CLI (cache, logs internos) podem acumular ao longo do tempo.

**Comportamento esperado:** O diretório é apenas o CWD do processo — o `claude` CLI em modo `--print` não deve gerar arquivos persistentes nele. Porém, se o Claude Code escrever arquivos de configuração ou cache, eles permanecem entre execuções.

**Risco:** 🔴 **LACUNA** — Não há limpeza periódica do workdir documentada. Em execuções longas (centenas de benchmarks), o acúmulo de arquivos pode impactar o desempenho do sistema de arquivos ou causar comportamentos inesperados do `claude` CLI.
