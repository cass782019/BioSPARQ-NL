"""Consolida resultados de avaliacao multi-modelo e gera tabelas."""
import glob
import json
import os
import sys


def load_all_results():
    """Carrega todos os eval_*.json."""
    results = {}
    for path in sorted(glob.glob("output/eval_*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        model = d.get("model", os.path.basename(path).replace("eval_", "").replace(".json", ""))
        results[model] = d
    return results


def print_comparison_table(all_results):
    """Imprime tabela comparativa no terminal."""
    print(f"\n{'=' * 90}")
    print("COMPARACAO MULTI-MODELO (Cenario A: COM validacao)")
    print(f"{'=' * 90}")
    print(f"{'Modelo':<30} {'Params':>7} {'Sintat.':>8} {'Exec.':>7} {'Corr.':>7} {'Tempo':>7} {'Tent.':>6}")
    print("-" * 90)

    param_map = {
        "google/gemma-3-4b": "4B",
        "nvidia/nemotron-3-nano-4b": "4B",
        "qwen/qwen3.5-9b": "9B",
        "openai/gpt-oss-20b": "20B",
        "google/gemma-4-26b-a4b": "26B/4B",
    }

    for model, data in all_results.items():
        m = data.get("scenario_a_with_validation", {}).get("metrics", {})
        if not m:
            continue
        params = param_map.get(model, "?")
        print(
            f"{model:<30} {params:>7} "
            f"{m.get('syntactic_rate', 0):>7.1%} "
            f"{m.get('execution_rate', 0):>6.1%} "
            f"{m.get('correctness_rate', 0):>6.1%} "
            f"{m.get('avg_time_seconds', 0):>6.1f}s "
            f"{m.get('avg_attempts', 0):>5.2f}"
        )

    # Por dificuldade
    print(f"\n{'=' * 90}")
    print("CORRECAO POR DIFICULDADE (Cenario A)")
    print(f"{'=' * 90}")
    print(f"{'Modelo':<30} {'Easy':>8} {'Medium':>8} {'Hard':>8}")
    print("-" * 60)

    for model, data in all_results.items():
        m = data.get("scenario_a_with_validation", {}).get("metrics", {})
        bd = m.get("by_difficulty", {})
        if not bd:
            continue
        easy = bd.get("easy", {}).get("correct_rate", 0)
        med = bd.get("medium", {}).get("correct_rate", 0)
        hard = bd.get("hard", {}).get("correct_rate", 0)
        print(f"{model:<30} {easy:>7.0%} {med:>7.0%} {hard:>7.0%}")

    # Detalhamento Q01-Q30
    print(f"\n{'=' * 90}")
    print("RESULTADO POR QUESTAO (Cenario A: [+] = correto, [-] = falhou)")
    print(f"{'=' * 90}")

    models = list(all_results.keys())
    short_names = [m.split("/")[-1][:12] for m in models]
    header = f"{'ID':<5} {'Diff':<7} " + " ".join(f"{s:>12}" for s in short_names)
    print(header)
    print("-" * len(header))

    # Pegar questoes do primeiro modelo
    first_results = list(all_results.values())[0]
    questions_a = first_results.get("scenario_a_with_validation", {}).get("results", [])
    q_ids = [r.get("question_id", "?") for r in questions_a]
    q_diffs = [r.get("difficulty", "?") for r in questions_a]

    for i, (qid, diff) in enumerate(zip(q_ids, q_diffs)):
        row = f"{qid:<5} {diff:<7} "
        for model in models:
            results = all_results[model].get("scenario_a_with_validation", {}).get("results", [])
            if i < len(results):
                ok = results[i].get("success", False)
                count = results[i].get("execution", {}).get("count", 0)
                row += f"{'[+]' + str(count):>12}" if ok else f"{'[-]':>12}"
            else:
                row += f"{'N/A':>12}"
        print(row)


def save_consolidated(all_results):
    """Salva resultado consolidado."""
    out = {"models": {}}
    for model, data in all_results.items():
        out["models"][model] = {
            "metrics_with_validation": data.get("scenario_a_with_validation", {}).get("metrics", {}),
            "metrics_without_validation": data.get("scenario_b_without_validation", {}).get("metrics", {}),
        }

    with open("output/evaluation_multi_model.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Consolidado salvo em output/evaluation_multi_model.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    all_results = load_all_results()

    if not all_results:
        print("Nenhum resultado encontrado em output/eval_*.json")
        sys.exit(1)

    print(f"Encontrados {len(all_results)} modelos avaliados:")
    for m in all_results:
        print(f"  - {m}")

    print_comparison_table(all_results)
    save_consolidated(all_results)


if __name__ == "__main__":
    main()
