"""Calcula concordancia inter-anotador sobre o gold standard."""
import json
import logging
import sys

from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)

ENDPOINT = "http://localhost:3030/biomedical/sparql"
TIMEOUT = 30


def execute_query(query: str) -> set:
    """Executa SPARQL e retorna conjunto de resultados como strings."""
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(TIMEOUT)
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        result_set = set()
        for row in bindings:
            vals = tuple(sorted((k, v.get("value", "")) for k, v in row.items()))
            result_set.add(vals)
        return result_set
    except Exception as e:
        logger.warning(f"Query failed: {e}")
        return set()


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity entre dois conjuntos."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def cohens_kappa(agreements: list) -> float:
    """Cohen's kappa para lista de (binary_a, binary_b) tuples."""
    n = len(agreements)
    if n == 0:
        return 0.0

    # Contingency table
    both_yes = sum(1 for a, b in agreements if a and b)
    both_no = sum(1 for a, b in agreements if not a and not b)
    a_yes_b_no = sum(1 for a, b in agreements if a and not b)
    a_no_b_yes = sum(1 for a, b in agreements if not a and b)

    po = (both_yes + both_no) / n  # observed agreement
    p_a_yes = (both_yes + a_yes_b_no) / n
    p_b_yes = (both_yes + a_no_b_yes) / n
    pe = p_a_yes * p_b_yes + (1 - p_a_yes) * (1 - p_b_yes)  # expected agreement

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def compute_agreement(questions_a_path: str, annotations_b_path: str):
    """Compara anotadores A e B executando ambos os SPARQL no Fuseki."""
    with open(questions_a_path, encoding="utf-8") as f:
        questions_a = {q["id"]: q for q in json.load(f)}
    with open(annotations_b_path, encoding="utf-8") as f:
        annotations_b = {a["id"]: a for a in json.load(f)}

    results = []
    binary_pairs = []

    common_ids = sorted(set(questions_a.keys()) & set(annotations_b.keys()))
    print(f"Comparando {len(common_ids)} questoes...")

    for qid in common_ids:
        qa = questions_a[qid]
        qb = annotations_b[qid]

        results_a = execute_query(qa["sparql"])
        results_b = execute_query(qb["sparql"])

        jaccard = jaccard_similarity(results_a, results_b)
        has_results_a = len(results_a) > 0
        has_results_b = len(results_b) > 0
        binary_pairs.append((has_results_a, has_results_b))

        results.append({
            "id": qid,
            "results_a_count": len(results_a),
            "results_b_count": len(results_b),
            "jaccard": round(jaccard, 4),
            "both_produce_results": has_results_a and has_results_b,
        })

        status = "OK" if jaccard > 0.8 else "DIVERGE"
        print(f"  {qid}: A={len(results_a)}, B={len(results_b)}, Jaccard={jaccard:.3f} [{status}]")

    kappa = cohens_kappa(binary_pairs)
    avg_jaccard = sum(r["jaccard"] for r in results) / len(results) if results else 0

    summary = {
        "total_questions": len(common_ids),
        "cohens_kappa": round(kappa, 4),
        "avg_jaccard": round(avg_jaccard, 4),
        "perfect_agreement": sum(1 for r in results if r["jaccard"] == 1.0),
        "high_agreement": sum(1 for r in results if r["jaccard"] >= 0.8),
        "details": results,
    }

    print(f"\nCohen's Kappa: {kappa:.4f}")
    print(f"Jaccard medio: {avg_jaccard:.4f}")
    print(f"Concordancia perfeita: {summary['perfect_agreement']}/{len(common_ids)}")
    print(f"Concordancia alta (>=0.8): {summary['high_agreement']}/{len(common_ids)}")

    return summary


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    summary = compute_agreement(
        "data/gold_standard/questions.json",
        "data/gold_standard/annotations_b.json",
    )

    out_path = "output/inter_annotator_agreement.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Resultados salvos em {out_path}")


if __name__ == "__main__":
    main()
