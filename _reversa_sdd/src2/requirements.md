# Requisitos — src2

> Unit: `src2/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `src2` |
| Caminho legado | `src2/pipeline/`, `src2/evaluation/` |
| Responsabilidade | Revisão 2 do pipeline — adiciona `ClaudeCLIBackend` (geração via `claude` CLI OAuth) e `PlaywrightRunner` (testes E2E via browser), além de análise comparativa de regressões |
| Complexidade | 🟢 Média |

---

## Contexto

`src2/` é uma extensão de `src/` que não substitui o pipeline principal. Acrescenta dois recursos ausentes na revisão 1:

1. **ClaudeCLIBackend** — permite usar Claude Sonnet via OAuth do Claude Code sem `ANTHROPIC_API_KEY`
2. **PlaywrightRunner** — teste E2E das 30+ questões diretamente pelo frontend, capturando o JSON completo da `AskResponse`

---

## Requisitos Funcionais

### RF-01 — ClaudeCLIBackend: geração de texto via `claude` CLI
🟢 **CONFIRMADO** — `src2/pipeline/llm_backends.py:ClaudeCLIBackend`

**Must**

O `ClaudeCLIBackend` deve invocar o `claude` CLI em modo `--print` via `subprocess.run`, passando o `user_msg` via stdin e o system prompt via `--system-prompt`. O backend deve reutilizar a sessão OAuth do Claude Code já autenticada — sem necessidade de `ANTHROPIC_API_KEY`.

**Critérios de Aceitação:**

```gherkin
Dado que o `claude` CLI está no PATH e autenticado via OAuth
Quando ClaudeCLIBackend.generate(system, user_msg) é chamado
Então subprocess.run executa com cwd=~/.biosparql-bench-workdir
E user_msg é passado via stdin (não como argumento)
E --disable-slash-commands está presente no comando
E o stdout do processo é retornado como string
```

```gherkin
Dado que o `claude` CLI não está no PATH
Quando ClaudeCLIBackend.__init__(config) é chamado
Então RuntimeError("claude CLI not found in PATH") é lançado imediatamente
```

```gherkin
Dado que o processo `claude` excede o timeout configurado
Quando subprocess.run lança TimeoutExpired
Então RuntimeError("claude CLI timeout after Ns") é lançado pelo backend
```

```gherkin
Dado que o processo `claude` retorna returncode != 0
Quando generate() processa o retorno
Então RuntimeError com stderr truncado (máx 500 chars) é lançado
```

---

### RF-02 — ClaudeCLIBackend: isolamento de workdir
🟢 **CONFIRMADO** — `src2/pipeline/llm_backends.py:ClaudeCLIBackend.__init__()`

**Must**

O backend deve executar o `claude` CLI em `~/.biosparql-bench-workdir` (fora de `proj1/`) para evitar que o Claude Code auto-descubra o `CLAUDE.md` do projeto e contamine o benchmark com instruções do projeto.

**Critérios de Aceitação:**

```gherkin
Dado que self.workdir = os.path.expanduser("~/.biosparql-bench-workdir")
Quando ClaudeCLIBackend.__init__() é chamado
Então os.makedirs(self.workdir, exist_ok=True) é executado
E subprocess.run usa cwd=self.workdir
```

---

### RF-03 — LMStudioBackend: retry com backoff exponencial
🟢 **CONFIRMADO** — `src2/pipeline/llm_backends.py:LMStudioBackend.generate()`

**Must**

O `LMStudioBackend` em `src2/` deve tentar a geração até 3 vezes em caso de `APIConnectionError` ou `APITimeoutError`, com backoff exponencial de 2s, 4s entre tentativas.

**Critérios de Aceitação:**

```gherkin
Dado que a API do LM Studio lança APIConnectionError na tentativa 1
Quando LMStudioBackend.generate() é chamado
Então aguarda 2s e retenta (tentativa 2)
Se falhar novamente, aguarda 4s e retenta (tentativa 3)
Se a terceira falhar, a exceção original é propagada
```

---

### RF-04 — PlaywrightRunner: execução E2E via browser
🟢 **CONFIRMADO** — `src2/evaluation/playwright_runner.py`

**Must**

O PlaywrightRunner deve abrir o frontend em `http://localhost:3000`, interceptar as respostas de `POST /api/ask`, e para cada questão do gold standard: preencher o campo, enviar, aguardar a resposta e logar o JSON completo em JSONL.

**Critérios de Aceitação:**

```gherkin
Dado que o frontend está rodando em localhost:3000
E as questões selecionadas foram carregadas de questions.json
Quando playwright_runner.run(questions, args) é executado
Então para cada questão:
  - page.fill preenche o campo de texto
  - page.keyboard.press("Enter") envia
  - a resposta de /api/ask é capturada via page.on("response")
  - o record completo é gravado em output2/playwright_log.jsonl (JSONL)
E ao final: output2/playwright_summary.json é gerado com métricas consolidadas
```

```gherkin
Dado --headed está ativo
Quando playwright_runner é executado
Então o browser Chromium abre em modo visível (não headless)
```

```gherkin
Dado --screenshots está ativo
Quando cada questão é processada
Então output2/playwright_screenshots/QXX.png é capturado após a resposta
```

---

### RF-05 — PlaywrightRunner: filtros de questões
🟢 **CONFIRMADO** — `src2/evaluation/playwright_runner.py:main()`

**Should**

O runner deve suportar seleção de subconjunto de questões via `--limit N` (primeiras N) e `--ids Q01 Q05` (IDs específicos).

**Critérios de Aceitação:**

```gherkin
Dado --limit 10
Quando main() seleciona questões
Então selected = all_questions[:10]
```

```gherkin
Dado --ids Q01 Q14
Quando main() filtra questões
Então selected = [q for q in all_questions if q["id"] in ["Q01", "Q14"]]
```

---

### RF-06 — PlaywrightRunner: modo regression-suite
🟢 **CONFIRMADO** — `src2/evaluation/playwright_runner.py:main()`

**Should**

Com `--regression-suite`, o runner lê `data/gold_standard/regression_suite.json` em vez de `questions.json`, e salva em `output2/regression_log.jsonl` e `output2/regression_summary.json`.

---

### RF-07 — corrections_report: análise comparativa baseline vs pós-correções
🟢 **CONFIRMADO** — `src2/evaluation/corrections_report.py`

**Must**

O script `corrections_report.py` deve comparar `output2/playwright_log_baseline.jsonl` (snapshot pré-correções) com `output2/playwright_log.jsonl` (pós-correções), classificar cada questão como: recuperada, regredida, ainda-ok ou ainda-falha, e gerar relatório em JSON e Markdown.

**Critérios de Aceitação:**

```gherkin
Dado os dois arquivos JSONL presentes
Quando corrections_report.main() é executado
Então output2/corrections_report.json contém:
  - baseline e corrected: métricas totais + por dificuldade
  - delta: absoluto (questões) e em pontos percentuais
  - recovered, regressed, still_failing: listas de IDs
  - failures_by_category: contagem por tipo de falha
E output2/corrections_report.md é gerado com tabelas Markdown
```

```gherkin
Dado que playwright_log_baseline.jsonl não existe
Quando corrections_report.main() é executado
Então load_jsonl retorna {} sem erro
E o relatório é gerado com baseline vazio (0/0)
```

---

### RF-08 — factory `create_backend`
🟢 **CONFIRMADO** — `src2/pipeline/llm_backends.py:create_backend()`

**Must**

A função `create_backend(config)` deve instanciar `ClaudeCLIBackend` se `config["backend"] == "claude_cli"`, ou `LMStudioBackend` para qualquer outro valor (default).

---

## Requisitos Não Funcionais

### RNF-01 — Encoding UTF-8 explícito
🟢 **CONFIRMADO** — `playwright_runner.py:sys.stdout.reconfigure(encoding="utf-8")` e `subprocess.run(encoding="utf-8", errors="replace")`

Todos os scripts `src2/` devem forçar UTF-8 na saída padrão e no processamento de stdout do subprocess (com `errors="replace"` para tolerar bytes inválidos).

### RNF-02 — Timeout por questão configurável
🟢 **CONFIRMADO** — `--question-timeout` default 300s

O timeout padrão por questão no Playwright é 300s (5 minutos), configurável via `--question-timeout`. O timeout do ClaudeCLI é 180s, configurável via `config["llm_timeout"]`.

### RNF-03 — Saída em `output2/` (separada de `output/`)
🟢 **CONFIRMADO** — `LOG_PATH = "output2/playwright_log.jsonl"`

Todos os artefatos de `src2/` vão para `output2/`, isolados dos resultados de `src/` em `output/`.

### RNF-04 — Sem dependência de `ANTHROPIC_API_KEY`
🟢 **CONFIRMADO** — ClaudeCLIBackend usa `--print` + OAuth

O `ClaudeCLIBackend` não usa a SDK Anthropic nem requer `ANTHROPIC_API_KEY` — depende apenas da sessão OAuth já ativa do `claude` CLI.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 ClaudeCLIBackend geração | **Must** | Permite avaliar Claude sem API key — viabiliza benchmarking |
| RF-02 Isolamento workdir | **Must** | Sem isso o CLAUDE.md do projeto contamina o benchmark |
| RF-03 LMStudioBackend retry | **Must** | LM Studio local pode ter falhas transitórias |
| RF-04 PlaywrightRunner E2E | **Must** | Único teste que valida o pipeline completo via UI real |
| RF-05 Filtros --limit/--ids | **Should** | Facilita debug e testes parciais |
| RF-06 Regression-suite | **Should** | Rastreia regressões em subconjunto estável |
| RF-07 corrections_report | **Must** | Mede impacto de cada iteração de correção |
| RF-08 create_backend factory | **Must** | Ponto de integração com o pipeline |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| `claude` CLI no PATH (OAuth ativo) | Ferramenta externa | Sim (para ClaudeCLIBackend) |
| LM Studio em localhost:1234 | Serviço externo local | Sim (para LMStudioBackend) |
| Frontend em localhost:3000 | Serviço externo local | Sim (para PlaywrightRunner) |
| `playwright` (Python) | Biblioteca Python | Sim (para PlaywrightRunner) |
| `openai` SDK | Biblioteca Python | Sim (para LMStudioBackend) |
| `data/gold_standard/questions.json` | Arquivo de dados | Sim |
