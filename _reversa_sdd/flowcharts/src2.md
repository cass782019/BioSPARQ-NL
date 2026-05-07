# Flowchart — Módulo `src2`

> Gerado pelo Arqueólogo em 2026-05-04

## ClaudeCLIBackend — geração via subprocess

```mermaid
flowchart TD
    INIT[ClaudeCLIBackend.__init__\nverifica claude no PATH\ncria workdir isolado] --> GEN

    GEN[generate system, user_msg] --> CMD["cmd = ['claude', '--print',\n'--model', model,\n'--system-prompt', system,\n'--output-format', 'text',\n'--disable-slash-commands']"]

    CMD --> RUN[subprocess.run\ncwd=~/.biosparql-bench-workdir\ninput=user_msg via stdin\ntimeout=180s]

    RUN -- TimeoutExpired --> TIMEOUT[raise RuntimeError\ntimeout]
    RUN -- returncode != 0 --> FAIL[raise RuntimeError\nclaude CLI failed]
    RUN -- ok --> RETURN[return result.stdout]

    style TIMEOUT fill:#f88
    style FAIL fill:#f88
    style RETURN fill:#8f8
```

**Por que workdir isolado?** Claude Code auto-descobre `CLAUDE.md` no diretório de trabalho. Rodar fora de `proj1/` evita que o benchmark seja contaminado pelas instruções do projeto.

## playwright_runner — E2E via browser

```mermaid
flowchart TD
    START[playwright_runner.py\n--limit --ids --headed --screenshots] --> LOAD_Q[carrega questions.json\nfiltra por --limit/--ids]
    LOAD_Q --> BROWSER[chromium.launch\nheadless=not headed]
    BROWSER --> GOTO[page.goto localhost:3000\nwait_until=networkidle]
    GOTO --> INTERCEPT[page.on response\ncaptura /api/ask POSTs]

    INTERCEPT --> LOOP[para cada questão]
    LOOP --> TYPE[page.fill input\ndigita pergunta]
    TYPE --> CLICK[page.press Enter]
    CLICK --> WAIT[page.wait_for_function\nresponse capturada]
    WAIT --> LOG[log_event JSONL\nquestion + xai completo]
    LOG --> SCREENSHOT{--screenshots?}
    SCREENSHOT -- sim --> PNG[page.screenshot PNG]
    SCREENSHOT --> LOOP

    LOOP --> DONE[playwright_summary.json\nconsolidado]
```

## corrections_report — Análise de regressão/progresso

```mermaid
flowchart TD
    BASELINE[playwright_log_baseline.jsonl\npré-correções] --> COMPARE[corrections_report.py]
    CURRENT[playwright_log.jsonl\npós-correções] --> COMPARE
    COMPARE --> DELTA[por questão:\nmelhorou / piorou / igual]
    DELTA --> REPORT[corrections_report.json\ncorrections_report.md]
```
