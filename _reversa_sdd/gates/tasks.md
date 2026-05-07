# Tarefas — gates

> Unit: `gates/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Contexto

Este arquivo descreve as tarefas de implementação derivadas dos requisitos e design da unidade `gates`. Cada tarefa cita o arquivo legado de referência, inclui critério de pronto (DoD) e confiança baseada na extração do código atual.

---

## TASK-GATES-01 — Reimplementar Gate 0 com suporte a LM Studio

**Prioridade:** Must  
**Origem:** `gates/gate0_check.py` + decisão de design DD-03  
**Confiança:** 🟡 INFERIDO (migração Ollama → LM Studio não foi concluída no gate)

**Descrição:**  
O gate0 atual verifica Ollama em `localhost:11434`. O sistema migrou para LM Studio em `localhost:1234` com API OpenAI-compatible. O check de "LLM model" deve ser atualizado para verificar `GET http://localhost:1234/v1/models` e confirmar que pelo menos um modelo está carregado.

**Comportamento esperado (novo):**

```python
# Substituir checks de Ollama por:
try:
    import requests
    r = requests.get("http://localhost:1234/v1/models", timeout=5)
    models = [m["id"] for m in r.json().get("data", [])]
    checks.append(("LM Studio", True, f"models: {models}"))
    has_model = len(models) > 0
    checks.append(("LLM model", has_model, "loaded" if has_model else "NO MODEL LOADED"))
except Exception:
    checks.append(("LM Studio", False, "offline"))
    checks.append(("LLM model", False, "LM Studio offline"))
```

**Critério de pronto:**  
- `[OK] LM Studio` aparece quando LM Studio está rodando com modelo carregado  
- `[FAIL] LM Studio` aparece quando LM Studio está offline  
- Check de Ollama removido ou mantido como check secundário opcional  
- Todos os outros checks do gate0 preservados sem alteração  

---

## TASK-GATES-02 — Corrigir thresholds no Gate 2

**Prioridade:** Must  
**Origem:** `gates/gate2_check.py` — checks de gold standard e FAISS  
**Confiança:** 🔴 LACUNA (bug confirmado — thresholds maiores que o tamanho real)

**Descrição:**  
O gate2 tem dois checks com thresholds incorretos que sempre falham:
1. `len(qs) >= 50` — o gold standard tem **30 questões**
2. `index.ntotal >= 50` — o índice FAISS tem **30 vetores**

Os thresholds devem ser corrigidos para `>= 30`.

**Correção esperada:**

```python
# Em gate2_check.py:
# Linha de gold standard total:
checks.append(("Gold standard total", len(qs) >= 30, f"{len(qs)} questoes"))

# Linha de FAISS index:
checks.append(("FAISS index", index.ntotal >= 30, f"{index.ntotal} vetores"))
```

**Critério de pronto:**  
- `[OK] Gold standard total: 30 questoes` quando questions.json tem 30 questões  
- `[OK] FAISS index: 30 vetores` quando index tem 30 vetores  
- gate2 passa com exit code 0 em ambiente configurado corretamente  

---

## TASK-GATES-03 — Adicionar gate4 e gate5 ou documentar ausência

**Prioridade:** Could  
**Origem:** `gates/` — numeração não-contígua (0,1,2,3,6)  
**Confiança:** 🔴 LACUNA (propósito de gate4/gate5 desconhecido)

**Descrição:**  
A numeração dos gates é não-contígua. Não está claro se gate4 e gate5 foram planejados e não implementados, ou se os números foram reservados para fases futuras. Deve ser documentado explicitamente.

**Opção A:** Adicionar `README.md` em `gates/` explicando a numeração:
```
Gate 0 — Ambiente
Gate 1 — Dados (Fuseki)
Gate 2 — Gold Standard e FAISS
Gate 3 — Pipeline E2E
Gate 4 — (reservado: avaliação formal, src/evaluation)
Gate 5 — (reservado: ablação)
Gate 6 — Interface (API + Frontend)
```

**Opção B:** Implementar gate4 (avaliação) e gate5 (ablação) como wrappers dos scripts de avaliação.

**Critério de pronto:**  
- Numeração documentada e justificada  
- Ou gates 4 e 5 implementados  

---

## TASK-GATES-04 — Adicionar gate para verificação do paper LaTeX

**Prioridade:** Could  
**Origem:** `gates/gate6_check.py` — gate6 não verifica LaTeX; gate0 só verifica binário pdflatex  
**Confiança:** 🟡 INFERIDO (gate6 original do flowchart incluía LaTeX, mas o código atual não tem)

**Descrição:**  
Conforme o flowchart do Arqueólogo, o gate6 deveria verificar que o paper LaTeX compila. O código atual de gate6 não inclui essa verificação — apenas gate0 verifica se o binário `pdflatex` existe. Um gate dedicado ou adição ao gate6 para verificar `pdflatex biosparql-nl` em `output/relatorio/` seria útil.

**Comportamento esperado:**

```python
# Em gate6_check.py (novo check):
if os.path.exists("output/relatorio/biosparql-nl.tex"):
    try:
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "biosparql-nl.tex"],
            cwd="output/relatorio",
            capture_output=True, text=True, timeout=60
        )
        checks.append(("LaTeX compila", r.returncode == 0, "OK" if r.returncode == 0 else r.stdout[-200:]))
    except Exception as e:
        checks.append(("LaTeX compila", False, str(e)[:80]))
```

**Critério de pronto:**  
- `[OK] LaTeX compila` quando biosparql-nl.tex compila sem erros fatais  
- `[FAIL] LaTeX compila` com output parcial do erro quando falha  

---

## TASK-GATES-05 — Criar script orquestrador `run_all_gates.py`

**Prioridade:** Should  
**Origem:** ausência de orquestrador — gates são executados manualmente um a um  
**Confiança:** 🔴 LACUNA (não existe no código atual)

**Descrição:**  
Não existe um script que execute todos os gates em sequência e produza um relatório consolidado. Um `gates/run_all_gates.py` deveria:

1. Executar gate0 → gate1 → gate2 → gate3 → gate6 via `subprocess.run`
2. Parar na primeira falha (fail-fast) ou continuar e reportar todos os resultados
3. Imprimir sumário final com status de cada gate
4. Retornar exit code 0 apenas se todos passaram

**Interface esperada:**

```bash
python gates/run_all_gates.py
# Saída:
# GATE 0: [OK]
# GATE 1: [OK]
# GATE 2: [FAIL]   ← para aqui com --fail-fast (padrão)
# [FAIL] 1 gate(s) falharam
# exit code 1
```

**Critério de pronto:**  
- Executa os 5 gates em sequência  
- Modo `--fail-fast` (padrão) e `--continue-on-fail`  
- Sumário com status por gate e exit code correto  

---

## TASK-GATES-06 — Adicionar verificação de Fuseki online no Gate 0

**Prioridade:** Should  
**Origem:** `gates/gate0_check.py` — verifica binário mas não verifica serviço rodando  
**Confiança:** 🟡 INFERIDO — gate0 verifica Fuseki binary mas gate1 é quem requer Fuseki online

**Descrição:**  
O gate0 verifica que o **binário** `fuseki-server.bat` existe em `tools/`, mas não verifica se o **servidor Fuseki** está respondendo em `:3030`. Gate1 é o primeiro a verificar conectividade com Fuseki. Seria útil adicionar em gate0 um check de `GET http://localhost:3030/$/ping` para detectar a falha mais cedo.

**Comportamento esperado:**

```python
# Adicionar em gate0_check.py após o check do binário:
try:
    r = requests.get("http://localhost:3030/$/ping", timeout=5)
    checks.append(("Fuseki online", r.status_code == 200, "OK"))
except Exception:
    checks.append(("Fuseki online", False, "offline (start with gate startup script)"))
```

**Critério de pronto:**  
- `[OK] Fuseki online` quando Fuseki responde em `:3030`  
- `[FAIL] Fuseki online` com mensagem útil quando offline  

---

## TASK-GATES-07 — Padronizar saída de erros de exceção

**Prioridade:** Could  
**Origem:** todos os gates — `str(e)[:80]` pode truncar mensagens úteis  
**Confiança:** 🟡 INFERIDO — limite de 80 chars pode ocultar causa raiz

**Descrição:**  
Quando uma exceção é capturada, todos os gates truncam a mensagem em 80 caracteres: `str(e)[:80]`. Para exceções de rede (ConnectionRefused, Timeout), o início da mensagem já é informativo. Para erros de importação, pode truncar o nome do módulo faltante. Avaliar se `[:200]` ou incluir o tipo da exceção (`type(e).__name__`) seria mais útil.

**Critério de pronto:**  
- Mensagens de erro incluem tipo da exceção e são legíveis sem truncar informação crítica  

---

## Resumo

| Task | Prioridade | Confiança | Arquivo(s) afetados |
|---|---|---|---|
| TASK-GATES-01 — LM Studio no gate0 | Must | 🟡 | `gates/gate0_check.py` |
| TASK-GATES-02 — Corrigir thresholds gate2 | Must | 🔴 | `gates/gate2_check.py` |
| TASK-GATES-03 — Documentar gate4/gate5 | Could | 🔴 | `gates/README.md` |
| TASK-GATES-04 — LaTeX em gate6 | Could | 🟡 | `gates/gate6_check.py` |
| TASK-GATES-05 — Orquestrador all gates | Should | 🔴 | `gates/run_all_gates.py` (novo) |
| TASK-GATES-06 — Fuseki online em gate0 | Should | 🟡 | `gates/gate0_check.py` |
| TASK-GATES-07 — Mensagens de exceção | Could | 🟡 | todos os gates |
