# Tasks — src2

> Unit: `src2/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Implementar ClaudeCLIBackend

**Origem:** `src2/pipeline/llm_backends.py:ClaudeCLIBackend`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
import shutil, subprocess, os

class ClaudeCLIBackend:
    def __init__(self, config):
        if shutil.which("claude") is None:
            raise RuntimeError("claude CLI not found in PATH")
        self.model   = config.get("llm_model", "sonnet")
        self.timeout = int(config.get("llm_timeout", 180))
        self.max_budget = config.get("max_budget_usd")
        self.workdir = os.path.expanduser("~/.biosparql-bench-workdir")
        os.makedirs(self.workdir, exist_ok=True)

    def generate(self, system: str, user_msg: str) -> str:
        cmd = [
            "claude", "--print",
            "--model", self.model,
            "--system-prompt", system,
            "--output-format", "text",
            "--input-format", "text",
            "--disable-slash-commands",
        ]
        if self.max_budget is not None:
            cmd += ["--max-budget-usd", str(self.max_budget)]

        try:
            result = subprocess.run(
                cmd,
                input=user_msg,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
                cwd=self.workdir,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timeout after {self.timeout}s") from e

        if result.returncode != 0:
            err = (result.stderr or "").strip()[:500]
            raise RuntimeError(f"claude CLI failed (code {result.returncode}): {err}")
        return result.stdout
```

**Critério de pronto:**
- `shutil.which("claude") is None` → RuntimeError no `__init__`
- Processo com returncode != 0 → RuntimeError com stderr truncado
- Processo que excede timeout → RuntimeError com mensagem de timeout
- Chamada bem-sucedida → retorna `result.stdout` como string UTF-8

---

## T-02 — Implementar LMStudioBackend com retry exponencial

**Origem:** `src2/pipeline/llm_backends.py:LMStudioBackend`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
import time
from openai import OpenAI, APITimeoutError, APIConnectionError

class LMStudioBackend:
    def __init__(self, config):
        self.client = OpenAI(
            base_url=config["lm_studio_url"],
            api_key="lm-studio",
            timeout=config.get("llm_timeout", 120.0),
        )
        self.model = config["llm_model"]

    def generate(self, system: str, user_msg: str) -> str:
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                )
                return response.choices[0].message.content
            except (APIConnectionError, APITimeoutError):
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))   # 2s, 4s
                    continue
                raise
```

**Critério de pronto:**
- Falha na tentativa 1 → sleep 2s → retry
- Falha na tentativa 2 → sleep 4s → retry
- Falha na tentativa 3 → exceção propagada sem sleep
- Sucesso na tentativa 1 → sem sleep, retorno imediato

---

## T-03 — Implementar factory create_backend

**Origem:** `src2/pipeline/llm_backends.py:create_backend()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01, T-02

### Comportamento esperado

```python
def create_backend(config):
    backend_type = config.get("backend", "lm_studio")
    if backend_type == "claude_cli":
        return ClaudeCLIBackend(config)
    return LMStudioBackend(config)
```

**Critério de pronto:**
- `config={"backend": "claude_cli", ...}` → instancia `ClaudeCLIBackend`
- `config={"backend": "lm_studio", ...}` → instancia `LMStudioBackend`
- `config={}` (sem chave `backend`) → instancia `LMStudioBackend` (default)

---

## T-04 — Implementar PlaywrightRunner: loop de questões

**Origem:** `src2/evaluation/playwright_runner.py:run()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from playwright.sync_api import sync_playwright

def run(questions, args):
    captured = {"latest": None, "error": None}

    def handle_response(response):
        if "/api/ask" in response.url and response.request.method == "POST":
            try:
                captured["latest"] = response.json()
            except Exception as e:
                captured["error"] = str(e)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        page.on("response", handle_response)

        page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
        page.wait_for_selector('input[placeholder="Faca uma pergunta..."]', timeout=10000)

        for i, q in enumerate(questions, 1):
            captured["latest"] = None
            captured["error"] = None

            # aguarda input habilitado, preenche, envia
            input_sel = 'input[placeholder="Faca uma pergunta..."]'
            page.wait_for_function(
                f"() => !document.querySelector('{input_sel}').disabled",
                timeout=args.question_timeout * 1000,
            )
            page.fill(input_sel, q["question_pt"])
            page.keyboard.press("Enter")

            # polling até resposta ou timeout
            deadline = time.time() + args.question_timeout
            while captured["latest"] is None and captured["error"] is None:
                if time.time() > deadline:
                    raise TimeoutError(f"Timeout apos {args.question_timeout}s")
                page.wait_for_timeout(500)

            # monta record e loga em JSONL
            log_event(log_path, record)

        browser.close()
    # grava playwright_summary.json
```

**Critério de pronto:**
- Cada questão gera exatamente 1 linha no JSONL
- Timeout por questão → record com `status="exception"` (não aborta o loop)
- Erro na captura JSON → record com `status="error"`
- `--append` → log anterior não é apagado
- `--screenshots` → PNG gerado por questão em `output2/playwright_screenshots/`

---

## T-05 — Implementar log_event e escrita de summary

**Origem:** `src2/evaluation/playwright_runner.py:log_event()`, `run()` final
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-04

### Comportamento esperado

```python
def log_event(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
```

Summary ao final:

```python
summary = {
    "total_questions": total,
    "success": ok,
    "failed_no_results": failed,
    "errored": errored,
    "success_rate": ok / total if total else 0,
    "rows": summary_rows,
}
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
```

**Critério de pronto:**
- JSONL: cada linha é JSON válido com `\n` ao final
- `ensure_ascii=False` garante caracteres PT-BR preservados
- `default=str` serializa objetos não-serializáveis (ex: datetime) como string
- Summary tem chave `success_rate` como float [0, 1]

---

## T-06 — Implementar corrections_report

**Origem:** `src2/evaluation/corrections_report.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
def load_jsonl(path) -> dict:
    """Retorna dict {qid: record}. Retorna {} se arquivo não existe."""

def compute(records) -> dict:
    """Métricas: total, ok, fail, rate, by_difficulty."""

def classify_changes(base, corr) -> tuple:
    """Retorna (recovered, regressed, still_ok, still_fail)."""

def classify_failure(record) -> str | None:
    """Classifica falha: syntax_error | validation_error |
       timeout_or_exception | zero_results. None se success."""

def main():
    base = load_jsonl(BASELINE_PATH)   # ok se não existe
    corr = load_jsonl(CORRECTED_PATH)
    # calcula métricas, classifica mudanças, grava JSON + MD
```

**Critério de pronto:**
- Questão que falhou no baseline e passa agora → `recovered`
- Questão que passava e agora falha → `regressed`
- `BASELINE_PATH` ausente → `base = {}`, relatório gerado sem erro
- JSON de saída contém `delta.percentage_points` arredondado a 1 casa decimal
- MD contém seções "Recuperadas", "Regressões" e "Ainda falhando"

---

## T-07 — Implementar run_all_models.py (src2)

**Origem:** `src2/evaluation/run_all_models.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```python
# Verificações antes de rodar cada modelo local:
def check_lm_studio_model(model_name) -> bool:
    """GET /v1/models → model_name in ids"""

def check_lm_studio_responds(model_name) -> bool:
    """POST /v1/chat/completions com 'Say OK' em 60s → status 200"""

def check_claude_cli() -> bool:
    """shutil.which('claude') and claude --version returncode 0"""

def run_evaluation(model_name, backend) -> bool:
    """subprocess.run src2.evaluation.run_evaluation --model --backend
       skip se output2/eval_{safe}.json já tem >= 50 questões"""
```

**Critério de pronto:**
- Modelo não disponível no LM Studio → `[SKIP]` sem tentar rodar
- Modelo não responde (OOM) → `[SKIP]` sem tentar rodar
- `claude` CLI não encontrado → seção Claude CLI pulada com `[INFO]`
- Modelo já avaliado (>= 50 Q) → `[SKIP]` sem re-executar
- Resultados salvos em `output2/` (não em `output/`)
