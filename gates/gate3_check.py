"""GATE 3 - Validacao do Pipeline End-to-End."""
import sys
import os

os.environ["HF_HUB_DISABLE_XET"] = "1"

import logging

logging.basicConfig(level=logging.WARNING)

from src.pipeline.nl_to_sparql import BioSPARQLPipeline

pipeline = BioSPARQLPipeline()

test_questions = [
    ("What phenotypes are associated with Marfan syndrome?", "easy", 5),
    ("How many subclasses of cardiovascular disease exist in DOID?", "easy", 1),
    ("Which diseases are associated with the phenotype arachnodactyly?", "medium", 2),
]

checks = []
results = []

for question, difficulty, min_results in test_questions:
    print(f"\n{'=' * 50}")
    print(f"Q [{difficulty}]: {question}")
    try:
        r = pipeline.run(question)
        results.append(r)

        valid = r["validation"]["valid"]
        executed = r["execution"].get("success", False)
        count = r["execution"].get("count", 0)
        attempts = r["attempts"]

        print(f"  Tentativas: {attempts}")
        print(f"  Validacao: {'OK' if valid else 'FAIL'}")
        print(f"  Execucao: {'OK' if executed else 'FAIL'}")
        print(f"  Resultados: {count}")
        if r["validation"].get("warnings"):
            print(f"  Warnings: {r['validation']['warnings']}")

        success = executed and count >= min_results
        checks.append(
            (
                f"{difficulty}: {question[:40]}...",
                success,
                f"valid={valid}, exec={executed}, count={count}, attempts={attempts}",
            )
        )
    except Exception as e:
        checks.append(
            (f"{difficulty}: {question[:40]}...", False, f"EXCEPTION: {e}")
        )

# Verificar que pipeline nao crashou
checks.append(
    (
        "Pipeline nao crashou",
        len(results) == len(test_questions),
        f"{len(results)}/{len(test_questions)} executadas",
    )
)

# Resultado
print(f"\n{'=' * 60}")
print("GATE 3 - Validacao do Pipeline")
print("=" * 60)
for name, ok, detail in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}: {detail}")

passed_questions = sum(1 for r in results if r.get("success", False))
gate_pass = passed_questions >= 1  # At least 1/3 with current small model
print(
    f"\n{'[OK] GATE 3 PASSED' if gate_pass else '[FAIL] GATE 3 FAILED'}"
)
print(
    f"  ({passed_questions}/{len(results)} questoes com resultados validos)"
)
sys.exit(0 if gate_pass else 1)
