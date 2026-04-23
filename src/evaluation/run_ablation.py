"""Estudo de ablacao formal: roda cada configuracao e compara resultados."""
import json
import logging
import os
import sys

os.environ["HF_HUB_DISABLE_XET"] = "1"
logging.basicConfig(level=logging.WARNING)

from src.evaluation.ablation_configs import ABLATION_CONFIGS, ABLATION_LABELS
from src.evaluation.run_evaluation import evaluate, compute_metrics


def run_ablation(model_name, base_config, questions):
    """Executa todas as configs de ablacao e retorna resultados consolidados."""
    all_results = {}

    for config_name, overrides in ABLATION_CONFIGS.items():
        label = ABLATION_LABELS.get(config_name, config_name)
        print(f"\n{'=' * 60}")
        print(f"ABLACAO: {label} ({config_name})")
        print(f"  Overrides: {overrides}")
        print("=" * 60)

        config = {**base_config, **overrides}

        from src.pipeline.nl_to_sparql import BioSPARQLPipeline

        pipeline = BioSPARQLPipeline(config)
        results = evaluate(pipeline, questions, use_validation=(config.get("max_retries", 2) > 0))
        metrics = compute_metrics(results)

        all_results[config_name] = {
            "label": label,
            "overrides": overrides,
            "metrics": metrics,
            "results": results,
        }

    return all_results


def print_ablation_table(all_results):
    """Imprime tabela comparativa de ablacao."""
    print(f"\n{'=' * 80}")
    print("TABELA DE ABLACAO")
    print(f"{'=' * 80}")
    header = f"{'Config':<20} {'Sintatica':>10} {'Execucao':>10} {'Correcao':>10} {'Tempo':>8} {'Tent.':>6}"
    print(header)
    print("-" * 80)

    for config_name in ABLATION_CONFIGS:
        if config_name not in all_results:
            continue
        m = all_results[config_name]["metrics"]
        label = all_results[config_name]["label"]
        print(
            f"{label:<20} "
            f"{m.get('syntactic_rate', 0):>9.1%} "
            f"{m.get('execution_rate', 0):>9.1%} "
            f"{m.get('correctness_rate', 0):>9.1%} "
            f"{m.get('avg_time_seconds', 0):>7.1f}s "
            f"{m.get('avg_attempts', 0):>5.2f}"
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Estudo de ablacao BioSPARQL-NL")
    parser.add_argument("--model", default="google/gemma-3-4b")
    parser.add_argument("--backend", default="lm_studio", choices=["lm_studio", "anthropic"])
    parser.add_argument("--max-questions", type=int, default=None, help="Limit number of questions (default: all)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    base_config = {
        "endpoint": "http://localhost:3030/biomedical/sparql",
        "lm_studio_url": "http://localhost:1234/v1",
        "llm_model": args.model,
        "backend": args.backend,
        "max_retries": 2,
        "top_k_examples": 3,
        "llm_timeout": 180.0,
        "fuseki_timeout": 30,
    }

    with open("data/gold_standard/questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    if args.max_questions:
        questions = questions[:args.max_questions]

    print(f"Modelo: {args.model} (backend: {args.backend})")
    print(f"Questoes: {len(questions)}")

    all_results = run_ablation(args.model, base_config, questions)
    print_ablation_table(all_results)

    safe_name = args.model.replace("/", "_")
    out_path = f"output/ablation_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"model": args.model, "ablations": {
                k: {"label": v["label"], "overrides": v["overrides"], "metrics": v["metrics"]}
                for k, v in all_results.items()
            }},
            f, indent=2, default=str, ensure_ascii=False,
        )
    print(f"\n[OK] Resultados salvos em {out_path}")


if __name__ == "__main__":
    main()
