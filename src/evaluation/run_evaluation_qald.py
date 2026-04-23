"""Adaptador QALD-9+ (DBpedia): avalia generalizacao do pipeline NL->SPARQL."""
import argparse
import json
import logging
import os
import sys
import time

os.environ["HF_HUB_DISABLE_XET"] = "1"
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DBPEDIA_ENDPOINT = "https://dbpedia.org/sparql"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

DBPEDIA_SCHEMA = """Prefixos DBpedia disponiveis:
  dbo:  <http://dbpedia.org/ontology/>      -- classes e propriedades ontologicas
  dbp:  <http://dbpedia.org/property/>      -- propriedades de infoboxes
  res:  <http://dbpedia.org/resource/>      -- entidades (ex: res:Germany)
  rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  xsd:  <http://www.w3.org/2001/XMLSchema#>

Padroes comuns:
  ?x a dbo:Person ; dbo:birthPlace res:City .
  res:Entity dbo:property ?val .
  FILTER(?val > 1000)"""


def load_fewshot(path="data/gold_standard/qald_fewshot.json"):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(fewshot_examples):
    examples_text = "\n\n".join(
        f"Pergunta: {ex['question']}\nSPARQL:\n{ex['sparql']}"
        for ex in fewshot_examples
    )
    return f"""Voce converte perguntas em linguagem natural para queries SPARQL sobre o grafo DBpedia.

{DBPEDIA_SCHEMA}

Exemplos:
{examples_text}

Responda SOMENTE com a query SPARQL, sem explicacoes. Comece com PREFIX ou SELECT."""


DBPEDIA_PREFIXES = """\
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX res: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
"""


def inject_prefixes(sparql: str) -> str:
    """Injeta prefixos DBpedia se ausentes na query."""
    if not sparql.strip():
        return sparql
    # Check which prefixes are used but not declared
    lines = sparql.strip()
    needed = []
    for prefix_line in DBPEDIA_PREFIXES.strip().splitlines():
        prefix_name = prefix_line.split(":")[0].replace("PREFIX ", "") + ":"
        if prefix_name in sparql and f"PREFIX {prefix_name}" not in sparql:
            needed.append(prefix_line)
    if needed:
        return "\n".join(needed) + "\n" + sparql
    return sparql


def extract_sparql(text: str) -> str:
    """Extrai o bloco SPARQL da resposta do LLM."""
    text = text.strip()
    # Remove markdown code fences
    for fence in ["```sparql", "```SPARQL", "```"]:
        if fence in text:
            parts = text.split(fence)
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    text = part.strip()
                    break
    # Trim trailing fence
    if "```" in text:
        text = text.split("```")[0].strip()
    # If there's still preamble before PREFIX/SELECT, strip it
    for kw in ["PREFIX ", "SELECT ", "ASK ", "CONSTRUCT "]:
        idx = text.find(kw)
        if idx > 0:
            text = text[idx:]
            break
    return text


def execute_sparql(sparql: str, endpoint: str, timeout: int = 30) -> dict:
    """Executa SPARQL contra endpoint e retorna resultados ou erro."""
    import urllib.request
    import urllib.parse

    # Virtuoso (DBpedia) needs format param + Content-Type header
    params = {"query": sparql, "format": "application/sparql-results+json"}
    data = urllib.parse.urlencode(params).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
        "User-Agent": "BioSPARQL-NL/1.0 (academic research)",
    }
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            bindings = result.get("results", {}).get("bindings", [])
            values = set()
            for row in bindings:
                for v in row.values():
                    values.add(v.get("value", ""))
            return {"success": True, "values": values, "count": len(values)}
    except Exception as e:
        return {"success": False, "error": str(e), "values": set(), "count": 0}


def compute_f1(predicted: set, expected: set) -> float:
    """F1 sobre conjuntos de URIs/valores."""
    if not expected:
        return 1.0 if not predicted else 0.0
    if not predicted:
        return 0.0
    tp = len(predicted & expected)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(expected)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def parse_expected(result_query_str: str) -> set:
    """Extrai URIs do campo result.query (string de lista Python)."""
    if not result_query_str or result_query_str in ("[nan]", "[]", "nan"):
        return set()
    try:
        import ast
        items = ast.literal_eval(result_query_str)
        return {str(x) for x in items if x and str(x) != "nan"}
    except Exception:
        return set()


def main():
    parser = argparse.ArgumentParser(description="Avaliacao QALD-9+ (DBpedia)")
    parser.add_argument("--model", default="google/gemma-3-4b")
    parser.add_argument(
        "--backend",
        default="lm_studio",
        choices=["lm_studio", "anthropic", "claude_cli", "huggingface"],
    )
    parser.add_argument("--max-questions", type=int, default=30)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--endpoint",
        default=DBPEDIA_ENDPOINT,
        help="SPARQL endpoint (padrao: DBpedia)",
    )
    parser.add_argument("--delay", type=float, default=1.5, help="Delay entre queries (s)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    from src.pipeline.llm_backends import create_backend

    model_name = args.model
    safe_name = model_name.replace("/", "_")

    print(f"Modelo: {model_name} (backend: {args.backend})")
    print(f"Endpoint: {args.endpoint}")
    print()

    config = {
        "lm_studio_url": "http://localhost:1234/v1",
        "llm_model": model_name,
        "backend": args.backend,
        "llm_timeout": 120.0,
    }
    backend = create_backend(config)

    # Carregar dataset QALD-9+
    print("Carregando QALD-9+...")
    import datasets as hf_datasets

    ds = hf_datasets.load_dataset("casey-martin/qald_9_plus")
    en_questions = [
        x
        for x in ds["train"]
        if x["language"] == "en"
        and x["query.sparql"]
        and "SELECT" in (x["query.sparql"] or "")
        and parse_expected(x.get("result.query", ""))  # apenas com respostas conhecidas
    ]

    # Deduplicar por ID, pegar primeiras N
    seen_ids = set()
    questions = []
    for q in en_questions:
        if q["id"] not in seen_ids:
            seen_ids.add(q["id"])
            questions.append(q)
        if len(questions) >= args.max_questions:
            break

    print(f"Questoes selecionadas: {len(questions)}")
    print()

    fewshot = load_fewshot()
    system_prompt = build_system_prompt(fewshot)

    results = []
    f1_scores = []

    print(f"{'ID':<6} {'F1':>6} {'Exec':>6} {'Count':>6}  Question[:50]")
    print("-" * 80)

    for q in questions:
        q_id = q["id"]
        question_text = q["question"]
        gold_sparql = q["query.sparql"]
        expected_vals = parse_expected(q.get("result.query", ""))

        start = time.time()
        try:
            raw = backend.generate(system_prompt, question_text)
            predicted_sparql = inject_prefixes(extract_sparql(raw))
            exec_result = execute_sparql(predicted_sparql, args.endpoint)
        except Exception as e:
            predicted_sparql = ""
            exec_result = {"success": False, "error": str(e), "values": set(), "count": 0}
        elapsed = time.time() - start

        predicted_vals = exec_result["values"]
        f1 = compute_f1(predicted_vals, expected_vals)
        f1_scores.append(f1)

        row = {
            "id": q_id,
            "question": question_text,
            "gold_sparql": gold_sparql,
            "predicted_sparql": predicted_sparql,
            "expected_values": list(expected_vals),
            "predicted_values": list(predicted_vals),
            "execution_success": exec_result["success"],
            "execution_error": exec_result.get("error"),
            "predicted_count": exec_result["count"],
            "expected_count": len(expected_vals),
            "f1": f1,
            "time_seconds": elapsed,
        }
        results.append(row)

        print(
            f"{q_id:<6} {f1:>6.3f} {str(exec_result['success']):>6} {exec_result['count']:>6}"
            f"  {question_text[:50]}"
        )

        time.sleep(args.delay)

    # Metricas
    n = len(results)
    exec_ok = sum(1 for r in results if r["execution_success"])
    avg_f1 = sum(f1_scores) / n if n else 0.0
    exact_match = sum(1 for f in f1_scores if f >= 1.0)
    partial_match = sum(1 for f in f1_scores if 0 < f < 1.0)

    metrics = {
        "total": n,
        "execution_success": exec_ok,
        "execution_rate": exec_ok / n if n else 0,
        "avg_f1": avg_f1,
        "exact_match": exact_match,
        "exact_match_rate": exact_match / n if n else 0,
        "partial_match": partial_match,
    }

    print()
    print("=" * 60)
    print(f"Total questoes:      {n}")
    print(f"Exec com sucesso:    {exec_ok} ({metrics['execution_rate']:.1%})")
    print(f"F1 medio:            {avg_f1:.3f}")
    print(f"Exact match (F1=1):  {exact_match} ({metrics['exact_match_rate']:.1%})")
    print("=" * 60)

    output_data = {
        "model": model_name,
        "backend": args.backend,
        "endpoint": args.endpoint,
        "dataset": "casey-martin/qald_9_plus",
        "metrics": metrics,
        "results": results,
    }

    out_path = args.output or f"output/eval_qald9plus_{safe_name}.json"
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)

    print(f"[OK] Resultados salvos em {out_path}")


if __name__ == "__main__":
    main()
