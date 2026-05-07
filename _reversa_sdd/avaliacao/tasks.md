# Tasks — avaliacao

> Unit: `src/evaluation/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Implementar `evaluate(pipeline, questions, use_validation)`

**Origem:** `src/evaluation/run_evaluation.py:evaluate()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
def evaluate(
    pipeline: BioSPARQLPipeline,
    questions: list[dict],
    use_validation: bool = True,
) -> list[dict]:
    """
    Avalia o pipeline nas questões fornecidas.
    Retorna lista de dicts com métricas por questão.
    """
    # Configurar cenário
    if use_validation:
        pipeline.config["max_retries"] = 2
        pipeline.config["disable_schema"] = False
    else:
        pipeline.config["max_retries"] = 0
        pipeline.config["disable_schema"] = True
        pipeline.validator = SchemaValidator(schemas=None)  # modo permissivo

    results = []
    for q in questions:
        t_start = time.perf_counter()
        try:
            result = pipeline.run(q["question"])
            error = None
        except Exception as e:
            result = {"sparql": "", "validation": {"valid": False, "errors": [str(e)]},
                      "execution": {"success": False, "count": 0, "results": []},
                      "attempts": 0, "success": False}
            error = str(e)

        elapsed = time.perf_counter() - t_start

        spot_check = _spot_check(result, q)
        meets_expected = result["execution"]["count"] >= q.get("min_expected", 1)

        results.append({
            "id": q["id"],
            "question": q["question"],
            "difficulty": q.get("difficulty", "unknown"),
            "sparql_generated": result.get("sparql", ""),
            "valid": result["validation"]["valid"],
            "exec_success": result["execution"]["success"],
            "results_count": result["execution"]["count"],
            "attempts": result.get("attempts", 0),
            "time_seconds": round(elapsed, 3),
            "meets_expected": meets_expected,
            "spot_check_pass": spot_check,
            "error": error,
        })

    return results
```

**Critério de pronto:**
- Retorna lista com exatamente `len(questions)` dicts
- `exec_success=True` somente quando `execution.count >= 1`
- Em caso de exceção do pipeline, `error` é preenchido e `exec_success=False`

---

## T-02 — Implementar `_spot_check(result, question)`

**Origem:** `src/evaluation/run_evaluation.py:_spot_check()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```python
def _spot_check(result: dict, question: dict) -> bool | None:
    """
    Verifica se os termos esperados aparecem nos bindings.
    Retorna None se expected_contains não estiver definido.
    """
    expected = question.get("expected_contains")
    if not expected:
        return None

    bindings = result.get("execution", {}).get("results", [])
    if not bindings:
        return False

    # Flatten todos os valores em string única lowercase
    flat = " ".join(
        str(v.get("value", "")).lower()
        for row in bindings
        for v in row.values()
    )

    return all(term.lower() in flat for term in expected)
```

**Critério de pronto:**
- `expected_contains=["parkinson"]`, bindings com "Parkinson disease" → `True`
- `expected_contains=["fever"]`, bindings vazios → `False`
- `expected_contains` ausente → `None`
- Todos os termos devem estar presentes (AND, não OR)

---

## T-03 — Implementar CLI de `run_evaluation.py`

**Origem:** `src/evaluation/run_evaluation.py` — bloco `if __name__ == "__main__"`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01, T-02

### Comportamento esperado

```python
if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend", default="lmstudio", choices=["lmstudio", "anthropic"])
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    # Carregar questões
    with open("data/gold_standard/questions.json") as f:
        questions = json.load(f)
    assert len(questions) == 30, "Gold standard deve ter exatamente 30 questões"

    # Instanciar pipeline
    config = {"llm_model": args.model, "backend": args.backend}
    pipeline = BioSPARQLPipeline(config)

    # Avaliar
    results_a = evaluate(pipeline, questions, use_validation=True)
    results_b = evaluate(pipeline, questions, use_validation=False)

    # Salvar
    safe_name = args.model.replace("/", "_")
    output = {
        "model": args.model,
        "backend": args.backend,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "scenarios": {
            "A": {"config": {"max_retries": 2}, "results": results_a,
                  "summary": _summarize(results_a)},
            "B": {"config": {"max_retries": 0}, "results": results_b,
                  "summary": _summarize(results_b)},
        }
    }
    out_path = f"{args.output_dir}/eval_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[OK] Salvo em {out_path}")
```

**Critério de pronto:**
- `python -m src.evaluation.run_evaluation --model "nvidia/nemotron-3-nano-4b"` gera `output/eval_nvidia_nemotron-3-nano-4b.json`
- Arquivo tem estrutura com `scenarios.A.results` (30 items) e `scenarios.B.results` (30 items)
- `assert len(questions) == 30` falha explicitamente se gold standard for reduzido

---

## T-04 — Implementar `_summarize(results)`

**Origem:** `src/evaluation/run_evaluation.py:_summarize()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
def _summarize(results: list[dict]) -> dict:
    total = len(results)
    successes = sum(1 for r in results if r["exec_success"])
    spot_checked = [r for r in results if r["spot_check_pass"] is not None]
    spot_pass = sum(1 for r in spot_checked if r["spot_check_pass"])

    return {
        "total": total,
        "exec_success": successes,
        "success_rate": round(successes / total, 4) if total else 0,
        "avg_attempts": round(
            sum(r["attempts"] for r in results) / total, 2
        ) if total else 0,
        "avg_time_s": round(
            sum(r["time_seconds"] for r in results) / total, 2
        ) if total else 0,
        "spot_check_total": len(spot_checked),
        "spot_check_pass": spot_pass,
        "spot_check_rate": round(spot_pass / len(spot_checked), 4) if spot_checked else None,
        "by_difficulty": _by_difficulty(results),
    }
```

**Critério de pronto:** `success_rate` é `exec_success / total` (não `meets_expected / total`).

---

## T-05 — Implementar `ablation_configs.py`

**Origem:** `src/evaluation/ablation_configs.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

Módulo que exporta a lista `ABLATION_CONFIGS` com as 6 configurações conforme `design.md`. Cada config é um dict com chaves: `name`, `disable_ner`, `disable_fewshot`, `disable_schema`, `disable_validation`, `max_retries`.

**Critério de pronto:** `len(ABLATION_CONFIGS) == 6` e todos os nomes são únicos.

---

## T-06 — Implementar `run_ablation.py`

**Origem:** `src/evaluation/run_ablation.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should
**Depende de:** T-01, T-05

### Comportamento esperado

```python
for cfg in ABLATION_CONFIGS:
    # Sobrescrever config do pipeline
    pipeline_cfg = base_config.copy()
    pipeline_cfg["disable_ner"] = cfg["disable_ner"]
    pipeline_cfg["top_k_examples"] = 0 if cfg["disable_fewshot"] else 3
    pipeline_cfg["disable_schema"] = cfg["disable_schema"]
    pipeline_cfg["max_retries"] = cfg["max_retries"]
    if cfg["disable_validation"]:
        pipeline_cfg["disable_schema"] = True

    pipeline = BioSPARQLPipeline(pipeline_cfg)
    results = evaluate(pipeline, questions, use_validation=not cfg["disable_validation"])
    ablation_results[cfg["name"]] = {
        "config": cfg,
        "results": results,
        "summary": _summarize(results),
    }

# Salvar
output_path = f"output/ablation_{safe_name}.json"
```

**Critério de pronto:** Arquivo de saída contém 6 chaves correspondendo aos nomes das configs.

---

## T-07 — Implementar `consolidate.py`

**Origem:** `src/evaluation/consolidate.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```python
import glob, json

eval_files = glob.glob("output/eval_*.json")
consolidated = {"models": [], "scenarios": {"A": {}, "B": {}}}

for path in eval_files:
    with open(path) as f:
        data = json.load(f)
    model = data["model"]
    consolidated["models"].append(model)
    for scenario in ["A", "B"]:
        consolidated["scenarios"][scenario][model] = data["scenarios"][scenario]["summary"]

with open("output/evaluation_multi_model.json", "w") as f:
    json.dump(consolidated, f, ensure_ascii=False, indent=2)
```

**Critério de pronto:** `evaluation_multi_model.json` contém todos os modelos presentes em `output/eval_*.json`.

---

## T-08 — Implementar `latex_tables.py`

**Origem:** `src/evaluation/latex_tables.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should
**Depende de:** T-07

### Comportamento esperado

Ler `output/evaluation_multi_model.json` e `output/ablation_*.json` e gerar:

1. `output/tables/table_main_results.tex` — tabela principal com colunas: Modelo | Params | Cenário A (%) | Cenário B (%) | Δ(pp)
2. `output/tables/table_ablation.tex` — tabela de ablação com linhas por config e colunas por modelo
3. `output/tables/table_per_difficulty.tex` — taxa por dificuldade (easy/medium/hard)

Formato: `\begin{tabular}{...} \hline ... \end{tabular}`, compatível com template SBC.

**Critério de pronto:**
- Arquivos `.tex` gerados sem erro de compilação LaTeX
- Números nas tabelas conferem com valores em `evaluation_multi_model.json`
- Não usar `\usepackage` — apenas fragmento `tabular` para importação via `\input{}`


## T-09 — `inter_annotator.py` — Concordância entre Anotadores

**Origem:** `src/evaluation/inter_annotator.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Could (utilitário ad-hoc — não integra o pipeline de avaliação automática)

### Comportamento esperado

Computa métricas de concordância entre dois conjuntos de resultados SPARQL (ex: dois modelos ou dois avaliadores humanos) sobre as 30 questões do gold standard.

**Métricas:**

| Métrica | Descrição | Interpretação |
|---|---|---|
| Jaccard similarity | `|A ∩ B| / |A ∪ B|` sobre conjuntos de resultados | 0 = sem sobreposição, 1 = idênticos |
| Cohen's kappa | Concordância corrigida por acaso | < 0.2: fraco, 0.6–0.8: bom, > 0.8: ótimo |

```python
def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)

def cohens_kappa(labels_a: list[bool], labels_b: list[bool]) -> float:
    """
    labels_a, labels_b: listas binárias de sucesso/falha por questão.
    """
    n = len(labels_a)
    po = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    pa = (sum(labels_a) / n) * (sum(labels_b) / n)
    pb = ((n - sum(labels_a)) / n) * ((n - sum(labels_b)) / n)
    pe = pa + pb
    return (po - pe) / (1 - pe) if pe < 1.0 else 1.0
```

**Entrada:** dois arquivos `eval_*.json` com o campo `scenarios.A.results`.

**Saída:** relatório em stdout com Jaccard médio e kappa global.

**Critério de pronto:**
- `jaccard({"a","b"}, {"b","c"})` → `0.333...`
- `cohens_kappa([True]*15 + [False]*15, [True]*15 + [False]*15)` → `1.0`
- Com dois arquivos de avaliação idênticos, kappa = 1.0

---

## T-10 — `bench_ner.py` — Benchmark de Backends NER

**Origem:** `src/evaluation/bench_ner.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Could (utilitário ad-hoc — execução manual para comparar backends)

### Comportamento esperado

Compara os backends NER disponíveis nas 30 questões do gold standard.

**Modo coverage (padrão):** para cada backend e questão, reporta quais entidades foram extraídas e quantas foram resolvidas (com CURIE).

**Modo scored (`--gold`):** se labels de entidade esperadas estiverem disponíveis no gold standard, computa P/R/F1 por backend.

```python
# CLI
parser.add_argument("--backend", nargs="+", default=["scispacy", "llm", "gilda"])
parser.add_argument("--gold", action="store_true", help="Modo scored: computa P/R/F1")
parser.add_argument("--limit", type=int, default=30)
```

**Saída modo coverage:**

```
Backend: scispacy
  Q01: ["Parkinson disease" → DOID:14330, "tremor" → HP:0001337]
  Q02: ["fever" → HP:0001945]
  ...
  Total: 28/30 questões com ≥1 entidade resolvida
```

**Saída modo scored:**

| Backend | Precision | Recall | F1 |
|---|---|---|---|
| scispacy | 0.82 | 0.74 | 0.78 |
| llm | 0.71 | 0.80 | 0.75 |
| gilda | 0.68 | 0.62 | 0.65 |

**Critério de pronto:**
- `--backend scispacy` executa sem Fuseki e reporta coverage (com Fuseki offline, CURIEs vazios)
- `--gold` só disponível se gold standard contiver campo `expected_entities`
- `--limit N` processa apenas as primeiras N questões
