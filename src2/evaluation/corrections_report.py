"""Gera relatorio comparativo baseline vs pos-correcoes.

Le:
- output2/playwright_log_baseline.jsonl (snapshot pre-correcoes)
- output2/playwright_log.jsonl (pos-correcoes, atualizado a cada rodada)

Gera:
- output2/corrections_report.json
- output2/corrections_report.md
"""
import json
import os
import sys
from collections import defaultdict

BASELINE_PATH = "output2/playwright_log_baseline.jsonl"
CORRECTED_PATH = "output2/playwright_log.jsonl"
OUT_JSON = "output2/corrections_report.json"
OUT_MD = "output2/corrections_report.md"


def load_jsonl(path):
    records = {}
    if not os.path.exists(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                records[r["id"]] = r
    return records


def compute(records):
    total = len(records)
    ok = sum(1 for r in records.values() if r.get("success"))
    by_diff = defaultdict(lambda: {"ok": 0, "total": 0})
    for r in records.values():
        d = r.get("difficulty", "?")
        by_diff[d]["total"] += 1
        if r.get("success"):
            by_diff[d]["ok"] += 1
    return {
        "total": total,
        "ok": ok,
        "fail": total - ok,
        "rate": ok / total if total else 0,
        "by_difficulty": dict(by_diff),
    }


def classify_changes(base, corr):
    recovered = []
    regressed = []
    still_ok = []
    still_fail = []
    for qid in sorted(set(base.keys()) | set(corr.keys())):
        b = base.get(qid, {}).get("success", False)
        c = corr.get(qid, {}).get("success", False)
        if not b and c:
            recovered.append(qid)
        elif b and not c:
            regressed.append(qid)
        elif b and c:
            still_ok.append(qid)
        else:
            still_fail.append(qid)
    return recovered, regressed, still_ok, still_fail


def classify_failure(record):
    if not record or record.get("success"):
        return None
    validation = record.get("validation", {}) or {}
    if not validation.get("valid", True):
        errs = validation.get("errors", [])
        err_str = str(errs[0]) if errs else "unknown"
        if "SYNTAX" in err_str.upper():
            return "syntax_error"
        return "validation_error"
    if record.get("status") == "exception":
        return "timeout_or_exception"
    return "zero_results"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    base = load_jsonl(BASELINE_PATH)
    corr = load_jsonl(CORRECTED_PATH)

    base_metrics = compute(base)
    corr_metrics = compute(corr)

    recovered, regressed, still_ok, still_fail = classify_changes(base, corr)

    # Failure category counts
    base_cats = defaultdict(int)
    corr_cats = defaultdict(int)
    for r in base.values():
        cat = classify_failure(r)
        if cat:
            base_cats[cat] += 1
    for r in corr.values():
        cat = classify_failure(r)
        if cat:
            corr_cats[cat] += 1

    report = {
        "baseline": base_metrics,
        "corrected": corr_metrics,
        "delta": {
            "absolute": corr_metrics["ok"] - base_metrics["ok"],
            "percentage_points": round(
                (corr_metrics["rate"] - base_metrics["rate"]) * 100, 1
            ),
        },
        "recovered": recovered,
        "regressed": regressed,
        "still_failing": still_fail,
        "still_ok_count": len(still_ok),
        "failures_by_category": {
            "baseline": dict(base_cats),
            "corrected": dict(corr_cats),
        },
    }

    os.makedirs("output2", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Markdown
    md = [
        "# BioSPARQL-NL: Relatorio de Correcoes",
        "",
        f"**Baseline:** {base_metrics['ok']}/{base_metrics['total']} ({base_metrics['rate']:.1%})",
        f"**Corrigido:** {corr_metrics['ok']}/{corr_metrics['total']} ({corr_metrics['rate']:.1%})",
        f"**Delta:** +{report['delta']['absolute']} questoes ({report['delta']['percentage_points']:+.1f} pp)",
        "",
        "## Por dificuldade",
        "",
        "| Dificuldade | Baseline | Corrigido | Delta |",
        "|-------------|----------|-----------|-------|",
    ]
    for d in ["easy", "medium", "hard"]:
        b = base_metrics["by_difficulty"].get(d, {"ok": 0, "total": 0})
        c = corr_metrics["by_difficulty"].get(d, {"ok": 0, "total": 0})
        delta = c["ok"] - b["ok"]
        md.append(
            f"| {d} | {b['ok']}/{b['total']} ({b['ok']/max(b['total'],1):.0%}) | "
            f"{c['ok']}/{c['total']} ({c['ok']/max(c['total'],1):.0%}) | "
            f"{delta:+d} |"
        )

    md += [
        "",
        "## Categorias de falha",
        "",
        "| Categoria | Baseline | Corrigido |",
        "|-----------|----------|-----------|",
    ]
    all_cats = set(base_cats.keys()) | set(corr_cats.keys())
    for cat in sorted(all_cats):
        md.append(f"| {cat} | {base_cats.get(cat, 0)} | {corr_cats.get(cat, 0)} |")

    md += [
        "",
        f"## Questoes recuperadas ({len(recovered)})",
        "",
    ]
    for qid in recovered:
        q_pt = corr.get(qid, {}).get("question", "")[:70]
        md.append(f"- **{qid}**: {q_pt}")

    md += [
        "",
        f"## Questoes que regrediram ({len(regressed)})",
        "",
    ]
    for qid in regressed:
        q_pt = corr.get(qid, {}).get("question", "")[:70]
        errs = corr.get(qid, {}).get("validation", {}).get("errors", [])
        err_short = str(errs[0])[:100] if errs else "zero_results"
        md.append(f"- **{qid}**: {q_pt}")
        md.append(f"  - erro: `{err_short}`")

    md += [
        "",
        f"## Ainda falhando ({len(still_fail)})",
        "",
        f"`{', '.join(still_fail)}`",
        "",
    ]

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Baseline:  {base_metrics['ok']}/{base_metrics['total']} ({base_metrics['rate']:.1%})")
    print(f"Corrigido: {corr_metrics['ok']}/{corr_metrics['total']} ({corr_metrics['rate']:.1%})")
    print(f"Delta: {report['delta']['absolute']:+d} questoes ({report['delta']['percentage_points']:+.1f} pp)")
    print()
    print(f"Recuperadas ({len(recovered)}): {', '.join(recovered)}")
    print(f"Regressoes  ({len(regressed)}): {', '.join(regressed)}")
    print(f"Ainda falhando ({len(still_fail)}): {', '.join(still_fail)}")
    print()
    print(f"[OK] {OUT_JSON}")
    print(f"[OK] {OUT_MD}")


if __name__ == "__main__":
    main()
