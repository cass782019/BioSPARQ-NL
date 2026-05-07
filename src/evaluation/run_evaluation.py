"""Avalia o pipeline em dois cenarios: COM e SEM validacao por schema."""
import json
import logging
import os
import sys
import time

os.environ["HF_HUB_DISABLE_XET"] = "1"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def evaluate(pipeline, questions, use_validation=True):
    """Executa todas as questoes."""
    if not use_validation:
        pipeline.config["max_retries"] = 0
    else:
        pipeline.config["max_retries"] = 2

    results = []
    for q in questions:
        start = time.time()
        try:
            r = pipeline.run(q["question_en"], question_id=q["id"])
        except Exception as e:
            logger.error(f"{q['id']} failed: {e}")
            r = {
                "question": q["question_en"],
                "sparql": "",
                "validation": {
                    "valid": False,
                    "errors": [str(e)],
                    "warnings": [],
                },
                "execution": {
                    "success": False,
                    "error": str(e),
                    "results": [],
                    "count": 0,
                },
                "attempts": 1,
                "success": False,
            }
        elapsed = time.time() - start

        r["question_id"] = q["id"]
        r["difficulty"] = q["difficulty"]
        r["type"] = q["type"]
        r["time_seconds"] = elapsed
        r["expected_min_results"] = q.get("expected_min_results", 1)
        r["meets_expected"] = r["execution"].get("count", 0) >= q.get(
            "expected_min_results", 1
        )

        # Spot-check semantico
        if "expected_contains" in q and r["execution"].get("results"):
            all_values = " ".join(
                str(v)
                for row in r["execution"]["results"]
                for v in row.values()
            ).lower()
            r["spot_check_pass"] = all(
                exp.lower() in all_values for exp in q["expected_contains"]
            )
        else:
            r["spot_check_pass"] = None

        results.append(r)
        print(
            f"  {q['id']} [{q['difficulty']}]: "
            f"valid={r['validation']['valid']}, "
            f"exec={r['execution'].get('success')}, "
            f"count={r['execution'].get('count', 0)}, "
            f"attempts={r['attempts']}, "
            f"time={elapsed:.1f}s"
        )

    return results


def compute_metrics(results):
    total = len(results)
    if total == 0:
        return {}

    syntactically_valid = sum(
        1 for r in results if r["validation"]["valid"]
    )
    executed_ok = sum(
        1 for r in results if r["execution"].get("success", False)
    )
    has_results = sum(
        1 for r in results if r["execution"].get("count", 0) > 0
    )
    meets_expected = sum(
        1 for r in results if r.get("meets_expected", False)
    )
    spot_checks = [r for r in results if r.get("spot_check_pass") is not None]
    spot_pass = sum(1 for r in spot_checks if r["spot_check_pass"])
    avg_attempts = sum(r["attempts"] for r in results) / total
    avg_time = sum(r["time_seconds"] for r in results) / total

    by_difficulty = {}
    for diff in ["easy", "medium", "hard"]:
        subset = [r for r in results if r["difficulty"] == diff]
        if subset:
            n = len(subset)
            by_difficulty[diff] = {
                "total": n,
                "valid": sum(
                    1 for r in subset if r["validation"]["valid"]
                ),
                "executed": sum(
                    1
                    for r in subset
                    if r["execution"].get("success", False)
                ),
                "correct": sum(
                    1 for r in subset if r.get("meets_expected", False)
                ),
                "valid_rate": sum(
                    1 for r in subset if r["validation"]["valid"]
                )
                / n,
                "exec_rate": sum(
                    1
                    for r in subset
                    if r["execution"].get("success", False)
                )
                / n,
                "correct_rate": sum(
                    1 for r in subset if r.get("meets_expected", False)
                )
                / n,
            }

    return {
        "total": total,
        "syntactically_valid": syntactically_valid,
        "syntactic_rate": syntactically_valid / total,
        "execution_success": executed_ok,
        "execution_rate": executed_ok / total,
        "has_results": has_results,
        "results_rate": has_results / total,
        "meets_expected": meets_expected,
        "correctness_rate": meets_expected / total,
        "spot_check_total": len(spot_checks),
        "spot_check_pass": spot_pass,
        "spot_check_rate": (spot_pass / len(spot_checks)) if spot_checks else None,
        "avg_attempts": avg_attempts,
        "avg_time_seconds": avg_time,
        "by_difficulty": by_difficulty,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Avaliacao BioSPARQL-NL")
    parser.add_argument(
        "--model",
        default="google/gemma-3-4b",
        help="Nome do modelo (ex: google/gemma-3-4b, claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--backend",
        default="lm_studio",
        choices=["lm_studio", "anthropic", "claude_cli", "huggingface"],
        help="Backend LLM: lm_studio (local), anthropic (Claude API), claude_cli (OAuth) ou huggingface (transformers)",
    )
    parser.add_argument(
        "--hf-instruct",
        action="store_true",
        default=False,
        help="HuggingFace: usar apply_chat_template (instruct). Padrao: text continuation.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Caminho de saida (padrao: output/eval_{safe_name}.json)",
    )
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    from src.pipeline.nl_to_sparql import BioSPARQLPipeline

    model_name = args.model
    safe_name = model_name.replace("/", "_")

    print(f"Modelo: {model_name} (backend: {args.backend})")
    print()

    config = {
        "endpoint": "http://localhost:3030/biomedical/sparql",
        "lm_studio_url": "http://localhost:1234/v1",
        "llm_model": model_name,
        "backend": args.backend,
        "hf_instruct": args.hf_instruct,
        "max_retries": 2,
        "top_k_examples": 3,
        "llm_timeout": 180.0,
        "fuseki_timeout": 30,
    }
    pipeline = BioSPARQLPipeline(config)

    with open("data/gold_standard/questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    # Cenario A: COM validacao
    print("=" * 60)
    print(f"CENARIO A: COM validacao ({len(questions)} questoes) [{model_name}]")
    print("=" * 60)
    results_a = evaluate(pipeline, questions, use_validation=True)
    metrics_a = compute_metrics(results_a)

    # Cenario B: SEM validacao
    print(f"\n{'=' * 60}")
    print(f"CENARIO B: SEM validacao [{model_name}]")
    print("=" * 60)
    results_b = evaluate(pipeline, questions, use_validation=False)
    metrics_b = compute_metrics(results_b)

    # Cenario C: ZERO-SHOT (sem NER, sem few-shot, sem schema, sem validacao)
    print(f"\n{'=' * 60}")
    print(f"CENARIO C: ZERO-SHOT [{model_name}]")
    print("=" * 60)
    config_c = {
        **config,
        "disable_ner": True,
        "top_k_examples": 0,
        "disable_schema": True,
        "max_retries": 0,
    }
    pipeline_c = BioSPARQLPipeline(config_c)
    results_c = evaluate(pipeline_c, questions, use_validation=False)
    metrics_c = compute_metrics(results_c)

    # Salvar por modelo
    output = {
        "model": model_name,
        "backend": args.backend,
        "scenario_a_with_validation": {
            "metrics": metrics_a,
            "results": results_a,
        },
        "scenario_b_without_validation": {
            "metrics": metrics_b,
            "results": results_b,
        },
        "scenario_c_zero_shot": {
            "metrics": metrics_c,
            "results": results_c,
        },
    }
    out_path = args.output or f"output/eval_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)

    # Tabela comparativa
    print(f"\n{'=' * 60}")
    print(f"COMPARACAO [{model_name}]")
    print(f"{'Metrica':<25} {'COM Valid.':<12} {'SEM Valid.':<12} {'Zero-shot':<12}")
    print("-" * 60)
    for label, key in [
        ("Validade Sintatica", "syntactic_rate"),
        ("Execucao com Sucesso", "execution_rate"),
        ("Correcao", "correctness_rate"),
        ("Media Tentativas", "avg_attempts"),
        ("Tempo Medio (s)", "avg_time_seconds"),
    ]:
        va = metrics_a.get(key, 0)
        vb = metrics_b.get(key, 0)
        vc = metrics_c.get(key, 0)
        if "rate" in key:
            print(f"{label:<25} {va:>10.1%} {vb:>10.1%} {vc:>10.1%}")
        else:
            print(f"{label:<25} {va:>10.2f} {vb:>10.2f} {vc:>10.2f}")

    print(f"\n[OK] Resultados salvos em {out_path}")


if __name__ == "__main__":
    main()
