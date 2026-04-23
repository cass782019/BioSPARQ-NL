"""NER backend benchmark harness for BioSPARQL-NL.

Coverage mode (default): no gold labels needed, reports which entities
each backend extracted per question.

Scored mode (--gold with expected_entities field): computes P/R/F1.

Usage:
  # coverage mode (default gold path)
  PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.bench_ner

  # scored mode
  PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.bench_ner \\
    --gold data/gold_standard/questions.json --out output/bench_ner.json
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean

from src.pipeline.ner.base import Entity
from src.pipeline.ner.factory import get_all_backends

_DEFAULT_GOLD = "data/gold_standard/questions.json"
_DEFAULT_OUT = "output/bench_ner.json"


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _match(pred: Entity, gold: dict) -> bool:
    if not pred.ontology_ids:
        return False
    gold_id = gold.get("ontology_id", "").upper()
    return any(pid.upper() == gold_id for pid in pred.ontology_ids)


def _score_question(preds: list[Entity], gold_ents: list[dict]) -> dict:
    tp = 0
    matched_gold: set[int] = set()
    for p in preds:
        for i, g in enumerate(gold_ents):
            if i in matched_gold:
                continue
            if _match(p, g):
                tp += 1
                matched_gold.add(i)
                break
    fp = len(preds) - tp
    fn = len(gold_ents) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1}


# ---------------------------------------------------------------------------
# Per-backend runner
# ---------------------------------------------------------------------------

def _run_backend(backend, questions: list[dict]) -> dict:
    has_gold = any("expected_entities" in q for q in questions)
    per_q = []
    for q in questions:
        t0 = time.perf_counter()
        try:
            preds = backend.extract(q.get("question") or q.get("question_en", ""))
            err = None
        except Exception as exc:
            preds, err = [], repr(exc)
        dt = time.perf_counter() - t0

        gold_ents = q.get("expected_entities", [])
        metrics = _score_question(preds, gold_ents) if has_gold else {}
        per_q.append({
            "id": q.get("id", ""),
            "difficulty": q.get("difficulty", ""),
            "latency_s": round(dt, 4),
            "error": err,
            "predictions": [
                {"text": p.text, "type": p.type,
                 "ontology_ids": p.ontology_ids, "scores": p.scores}
                for p in preds
            ],
            **metrics,
        })

    summary: dict = {
        "backend": backend.name,
        "n": len(per_q),
        "errors": sum(1 for r in per_q if r["error"]),
        "latency_s_mean": round(mean(r["latency_s"] for r in per_q), 4) if per_q else 0,
        "coverage": round(mean(
            1.0 if r["predictions"] else 0.0 for r in per_q
        ), 4) if per_q else 0,
    }
    if has_gold:
        summary["precision"] = round(mean(r["precision"] for r in per_q), 4)
        summary["recall"]    = round(mean(r["recall"]    for r in per_q), 4)
        summary["f1"]        = round(mean(r["f1"]        for r in per_q), 4)

    return {"summary": summary, "per_question": per_q}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="NER backend benchmark")
    ap.add_argument("--gold", default=_DEFAULT_GOLD,
                    help="Path to questions.json")
    ap.add_argument("--out", default=_DEFAULT_OUT,
                    help="Output JSON path")
    ap.add_argument("--backend", default=None,
                    help="Run only this backend (default: all)")
    ap.add_argument("--parallel", action="store_true",
                    help="Run backends in parallel threads")
    args = ap.parse_args()

    questions = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    print(f"[bench_ner] {len(questions)} questions loaded from {args.gold}")

    all_backends = get_all_backends()
    if not all_backends:
        raise SystemExit("[bench_ner] No backends could be loaded.")

    if args.backend:
        name = args.backend.lower()
        if name not in all_backends:
            raise SystemExit(f"[bench_ner] Backend '{name}' not available. "
                             f"Available: {list(all_backends)}")
        backends = {name: all_backends[name]}
    else:
        backends = all_backends

    has_gold = any("expected_entities" in q for q in questions)
    mode = "scored" if has_gold else "coverage"
    print(f"[bench_ner] mode={mode}, backends={list(backends)}")

    results: dict[str, dict] = {}
    if args.parallel:
        with ThreadPoolExecutor(max_workers=len(backends)) as ex:
            futures = {ex.submit(_run_backend, b, questions): name
                       for name, b in backends.items()}
            for fut in as_completed(futures):
                name = futures[fut]
                results[name] = fut.result()
                print(f"[bench_ner] {name} done")
    else:
        for name, b in backends.items():
            print(f"[bench_ner] running {name} ...")
            results[name] = _run_backend(b, questions)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[bench_ner] results saved -> {args.out}")

    # Summary table (ASCII only)
    print()
    if has_gold:
        header = f"{'backend':<14} {'P':>6} {'R':>6} {'F1':>6} {'cov':>6} {'lat(s)':>8} {'err':>4}"
    else:
        header = f"{'backend':<14} {'cov':>6} {'lat(s)':>8} {'err':>4}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        s = r["summary"]
        if has_gold:
            print(f"{s['backend']:<14} "
                  f"{s['precision']:>6.3f} {s['recall']:>6.3f} {s['f1']:>6.3f} "
                  f"{s['coverage']:>6.3f} {s['latency_s_mean']:>8.3f} {s['errors']:>4d}")
        else:
            print(f"{s['backend']:<14} "
                  f"{s['coverage']:>6.3f} {s['latency_s_mean']:>8.3f} {s['errors']:>4d}")


if __name__ == "__main__":
    main()
