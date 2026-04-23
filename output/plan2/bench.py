"""Parallel comparison harness for all NER backends.

Usage:
    python -m biosparql_ner.bench --gold gold_standard.json --out results/

Gold standard format (JSON list):
[
  {
    "id": "Q01",
    "question": "Which phenotypes are associated with Parkinson disease?",
    "expected_entities": [
      {"text": "Parkinson disease", "type": "DISEASE", "ontology_id": "DOID:14330"}
    ]
  },
  ...
]
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean

from .base import Entity
from .config import get_all_backends


def _match(pred: Entity, gold: dict) -> bool:
    """An entity matches if its primary_id equals the gold ontology_id
    (exact string match, case-insensitive)."""
    if not pred.ontology_ids:
        return False
    gold_id = gold["ontology_id"].upper()
    return any(pid.upper() == gold_id for pid in pred.ontology_ids)


def _score_question(preds: list[Entity], gold_ents: list[dict]) -> dict:
    tp = 0
    matched_gold = set()
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


def _run_backend(backend, questions: list[dict]) -> dict:
    per_q = []
    for q in questions:
        t0 = time.perf_counter()
        try:
            preds = backend.extract(q["question"])
            err = None
        except Exception as exc:
            preds, err = [], repr(exc)
        dt = time.perf_counter() - t0

        metrics = _score_question(preds, q.get("expected_entities", []))
        per_q.append({
            "id": q["id"],
            "latency_s": dt,
            "error": err,
            "predictions": [vars(p) for p in preds],
            **metrics,
        })

    summary = {
        "backend": backend.name,
        "n": len(per_q),
        "errors": sum(1 for r in per_q if r["error"]),
        "precision": mean(r["precision"] for r in per_q),
        "recall":    mean(r["recall"]    for r in per_q),
        "f1":        mean(r["f1"]        for r in per_q),
        "latency_s": mean(r["latency_s"] for r in per_q),
        "coverage":  mean(
            1.0 if any(p["ontology_ids"] for p in r["predictions"]) else 0.0
            for r in per_q
        ),
    }
    return {"summary": summary, "per_question": per_q}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, help="Path to gold_standard.json")
    ap.add_argument("--out", default="bench_results", help="Output dir")
    ap.add_argument("--parallel", action="store_true",
                    help="Run backends in parallel threads (risky if they share GPU)")
    args = ap.parse_args()

    questions = json.loads(Path(args.gold).read_text())
    backends = get_all_backends()
    if not backends:
        raise SystemExit("No backends could be loaded.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    if args.parallel:
        with ThreadPoolExecutor(max_workers=len(backends)) as ex:
            futures = {ex.submit(_run_backend, b, questions): name
                       for name, b in backends.items()}
            for fut in as_completed(futures):
                name = futures[fut]
                results[name] = fut.result()
                print(f"[bench] {name} done")
    else:
        for name, b in backends.items():
            print(f"[bench] running {name} ...")
            results[name] = _run_backend(b, questions)

    (out_dir / "full.json").write_text(json.dumps(results, indent=2, default=str))

    print("\n=== Summary ===")
    header = f"{'backend':<14} {'P':>6} {'R':>6} {'F1':>6} {'cov':>6} {'lat(s)':>8} {'err':>4}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        s = r["summary"]
        print(f"{s['backend']:<14} "
              f"{s['precision']:>6.2f} {s['recall']:>6.2f} {s['f1']:>6.2f} "
              f"{s['coverage']:>6.2f} {s['latency_s']:>8.2f} {s['errors']:>4d}")


if __name__ == "__main__":
    main()
