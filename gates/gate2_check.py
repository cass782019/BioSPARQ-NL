"""GATE 2 - Validacao de Schemas, Gold Standard e Indice FAISS."""
import json
import sys
import os

os.environ["HF_HUB_DISABLE_XET"] = "1"

import faiss
from sentence_transformers import SentenceTransformer

checks = []

# 2a. Schemas extraidos
try:
    with open("data/schemas.json", encoding="utf-8") as f:
        schemas = json.load(f)
    for name in list(schemas.keys()):
        s = schemas.get(name, {})
        nc = len(s.get("classes", []))
        np = len(s.get("predicates", []))
        checks.append(
            (f"Schema {name}", nc > 0 and np > 0, f"{nc} classes, {np} predicados")
        )
except Exception as e:
    checks.append(("schemas.json", False, str(e)))

# 2b. Gold standard tem 30 questoes
try:
    with open("data/gold_standard/questions.json", encoding="utf-8") as f:
        qs = json.load(f)
    checks.append(("Gold standard total", len(qs) >= 50, f"{len(qs)} questoes"))

    # Distribuicao
    easy = sum(1 for q in qs if q["difficulty"] == "easy")
    medium = sum(1 for q in qs if q["difficulty"] == "medium")
    hard = sum(1 for q in qs if q["difficulty"] == "hard")
    checks.append(
        (
            "Distribuicao",
            easy >= 10 and medium >= 10 and hard >= 10,
            f"easy={easy}, medium={medium}, hard={hard}",
        )
    )

    # Campos obrigatorios
    required = {
        "id", "question_pt", "question_en", "sparql",
        "type", "difficulty", "expected_min_results",
    }
    all_fields = all(required.issubset(q.keys()) for q in qs)
    checks.append(
        ("Campos obrigatorios", all_fields,
         "todos presentes" if all_fields else "campos faltando")
    )

    # IDs unicos
    ids = [q["id"] for q in qs]
    checks.append(
        ("IDs unicos", len(ids) == len(set(ids)), f"{len(set(ids))}/{len(ids)} unicos")
    )

    # Sintaxe SPARQL valida
    from rdflib.plugins.sparql.parser import parseQuery
    syntax_ok = 0
    syntax_errors = []
    for q in qs:
        try:
            parseQuery(q["sparql"])
            syntax_ok += 1
        except Exception as e:
            syntax_errors.append(f"{q['id']}: {str(e)[:60]}")
    checks.append(
        ("Sintaxe SPARQL", syntax_ok == len(qs), f"{syntax_ok}/{len(qs)} validas")
    )
    if syntax_errors:
        for err in syntax_errors[:3]:
            checks.append(("  Erro sintaxe", False, err))

except Exception as e:
    checks.append(("Gold standard", False, str(e)))

# 2c. Indice FAISS
try:
    index = faiss.read_index("data/gold_standard/questions.index")
    checks.append(("FAISS index", index.ntotal >= 50, f"{index.ntotal} vetores"))
except Exception as e:
    checks.append(("FAISS index", False, str(e)))

# 2d. Teste de retrieval
try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query = model.encode(
        ["What symptoms does Marfan syndrome have?"], normalize_embeddings=True
    )
    D, I = index.search(query.astype("float32"), k=3)
    top1_id = qs[I[0][0]]["id"]
    checks.append(
        ("Retrieval top-1", top1_id == "Q01",
         f"top-1={top1_id}, score={D[0][0]:.3f}")
    )
except Exception as e:
    checks.append(("Retrieval", False, str(e)))

# Resultado
print("\n" + "=" * 60)
print("GATE 2 - Validacao de Schemas e Indice")
print("=" * 60)
all_pass = True
for name, ok, detail in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}: {detail}")
    if not ok:
        all_pass = False

print(f"\n{'[OK] GATE 2 PASSED' if all_pass else '[FAIL] GATE 2 FAILED'}")
sys.exit(0 if all_pass else 1)
