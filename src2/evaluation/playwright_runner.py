"""Playwright runner: testa perguntas do gold standard via frontend (porta 3000).

Uma a uma, espera a resposta chegar, intercepta a chamada /api/ask e loga
o JSON completo (entidades, SPARQL, validacao, execucao, timing) em JSONL
para analise posterior.

Uso:
    python -m src2.evaluation.playwright_runner                    # todas as 52
    python -m src2.evaluation.playwright_runner --limit 10         # so 10
    python -m src2.evaluation.playwright_runner --ids Q01 Q05 Q14  # questoes especificas
    python -m src2.evaluation.playwright_runner --headed           # mostra o browser

Saida:
    output2/playwright_log.jsonl  - um JSON por linha com tudo
    output2/playwright_summary.json - tabela consolidada
    output2/playwright_screenshots/QXX.png - opcional com --screenshots
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

LOG_PATH = "output2/playwright_log.jsonl"
SUMMARY_PATH = "output2/playwright_summary.json"
REGRESSION_LOG_PATH = "output2/regression_log.jsonl"
REGRESSION_SUMMARY_PATH = "output2/regression_summary.json"
SCREENSHOTS_DIR = "output2/playwright_screenshots"
FRONTEND_URL = "http://localhost:3000"
INPUT_PLACEHOLDER = "Faca uma pergunta em linguagem natural..."


def log_event(path, record):
    """Append a JSON line to the verbose log."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def run(questions, args):
    from playwright.sync_api import sync_playwright

    os.makedirs("output2", exist_ok=True)
    if args.screenshots:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # Selecionar paths conforme modo
    log_path = REGRESSION_LOG_PATH if args.regression_suite else LOG_PATH
    summary_path = REGRESSION_SUMMARY_PATH if args.regression_suite else SUMMARY_PATH

    summary_rows = []
    fresh_run = not args.append

    if fresh_run and os.path.exists(log_path):
        os.remove(log_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # Captura a resposta de /api/ask para cada requisicao
        captured = {"latest": None, "error": None}

        def handle_response(response):
            if "/api/ask" in response.url and response.request.method == "POST":
                try:
                    captured["latest"] = response.json()
                except Exception as e:
                    captured["error"] = str(e)

        page.on("response", handle_response)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Abrindo {FRONTEND_URL} ...")
        page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_selector(f'input[placeholder="{INPUT_PLACEHOLDER}"]', timeout=10000)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Frontend carregado.")

        for i, q in enumerate(questions, 1):
            qid = q["id"]
            question = q["question_pt"]
            start = time.time()

            print(f"\n[{i}/{len(questions)}] {qid} [{q['difficulty']}] {question[:70]}")

            # Reset captured data
            captured["latest"] = None
            captured["error"] = None

            try:
                # Preenche input e envia
                input_sel = f'input[placeholder="{INPUT_PLACEHOLDER}"]'
                page.wait_for_selector(input_sel, state="visible", timeout=5000)
                # Aguarda nao estar desabilitado (loading do anterior)
                page.wait_for_function(
                    f"() => !document.querySelector('{input_sel}').disabled",
                    timeout=args.question_timeout * 1000,
                )
                page.fill(input_sel, question)
                page.keyboard.press("Enter")

                # Espera a resposta chegar
                deadline = time.time() + args.question_timeout
                while captured["latest"] is None and captured["error"] is None:
                    if time.time() > deadline:
                        raise TimeoutError(f"Timeout apos {args.question_timeout}s")
                    page.wait_for_timeout(500)

                elapsed = time.time() - start

                if captured["error"]:
                    record = {
                        "id": qid,
                        "question": question,
                        "difficulty": q["difficulty"],
                        "type": q["type"],
                        "status": "error",
                        "error": captured["error"],
                        "elapsed_s": round(elapsed, 2),
                        "timestamp": datetime.now().isoformat(),
                    }
                    print(f"    [ERR] {captured['error']}")
                else:
                    data = captured["latest"]
                    xai = data.get("xai", {}) or {}
                    validation = xai.get("validation", {}) or {}
                    execution_results = xai.get("results_raw", []) or []
                    results_count = xai.get("results_count", len(execution_results))
                    timing = xai.get("timing", {}) or {}

                    record = {
                        "id": qid,
                        "question": question,
                        "question_en": q.get("question_en"),
                        "difficulty": q["difficulty"],
                        "type": q["type"],
                        "expected_min_results": q.get("expected_min_results", 1),
                        "sparql_patterns": q.get("sparql_patterns", []),
                        "status": "ok" if data.get("success") else "failed",
                        "success": data.get("success", False),
                        "answer": data.get("answer", "")[:500],
                        "sparql_generated": xai.get("sparql", ""),
                        "sparql_reference": q.get("sparql", ""),
                        "entities": xai.get("entities", []),
                        "examples_used": xai.get("examples_used", []),
                        "validation": {
                            "valid": validation.get("valid"),
                            "errors": validation.get("errors", []),
                            "warnings": validation.get("warnings", []),
                        },
                        "attempts": xai.get("attempts", 1),
                        "results_count": results_count,
                        "results_sample": execution_results[:5],
                        "meets_expected": results_count >= q.get("expected_min_results", 1),
                        "timing": {
                            "ner_s": timing.get("ner_s"),
                            "retrieval_s": timing.get("retrieval_s"),
                            "llm_s": timing.get("llm_s"),
                            "total_s": timing.get("total_s"),
                        },
                        "elapsed_s": round(elapsed, 2),
                        "timestamp": datetime.now().isoformat(),
                    }

                    flag = "OK " if record["success"] else "FAIL"
                    print(
                        f"    [{flag}] results={results_count} "
                        f"valid={validation.get('valid')} "
                        f"attempts={record['attempts']} "
                        f"time={elapsed:.1f}s"
                    )
                    if validation.get("errors"):
                        for e in validation["errors"][:2]:
                            print(f"      err: {str(e)[:120]}")

                log_event(log_path, record)
                summary_rows.append({
                    "id": qid,
                    "difficulty": q["difficulty"],
                    "status": record["status"],
                    "success": record.get("success", False),
                    "results_count": record.get("results_count", 0),
                    "expected_min": q.get("expected_min_results", 1),
                    "attempts": record.get("attempts", 1),
                    "elapsed_s": record["elapsed_s"],
                    "valid": record.get("validation", {}).get("valid"),
                    "error_short": (record.get("validation", {}).get("errors", [None]) or [None])[0],
                })

                if args.screenshots:
                    shot_path = os.path.join(SCREENSHOTS_DIR, f"{qid}.png")
                    page.screenshot(path=shot_path, full_page=True)

            except Exception as e:
                elapsed = time.time() - start
                record = {
                    "id": qid,
                    "question": question,
                    "difficulty": q["difficulty"],
                    "status": "exception",
                    "exception": str(e),
                    "elapsed_s": round(elapsed, 2),
                    "timestamp": datetime.now().isoformat(),
                }
                log_event(log_path, record)
                summary_rows.append({
                    "id": qid,
                    "difficulty": q["difficulty"],
                    "status": "exception",
                    "success": False,
                    "results_count": 0,
                    "attempts": 0,
                    "elapsed_s": record["elapsed_s"],
                    "error_short": str(e)[:100],
                })
                print(f"    [EXC] {e}")

            if args.delay_s > 0 and i < len(questions):
                time.sleep(args.delay_s)

        browser.close()

    # Sumario
    total = len(summary_rows)
    ok = sum(1 for r in summary_rows if r["success"])
    failed = sum(1 for r in summary_rows if not r["success"] and r["status"] == "ok")
    errored = sum(1 for r in summary_rows if r["status"] != "ok")

    summary = {
        "total_questions": total,
        "success": ok,
        "failed_no_results": failed,
        "errored": errored,
        "success_rate": (ok / total) if total else 0,
        "rows": summary_rows,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"RESUMO: {ok}/{total} sucesso ({summary['success_rate']:.1%})")
    print(f"  - Falharam (query OK, 0 resultados): {failed}")
    print(f"  - Erros (excecao ou validacao): {errored}")
    print(f"\nLog verbose: {log_path}")
    print(f"Sumario: {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Playwright runner for BioSPARQL-NL frontend")
    parser.add_argument("--limit", type=int, default=None, help="Limita numero de questoes")
    parser.add_argument("--ids", nargs="+", default=None, help="IDs especificos (ex: Q01 Q14)")
    parser.add_argument("--regression-suite", action="store_true",
                        help="Usa regression_suite.json (12 Q) em vez de questions.json (52 Q)")
    parser.add_argument("--headed", action="store_true", help="Mostra o browser (nao-headless)")
    parser.add_argument("--screenshots", action="store_true", help="Captura screenshots por questao")
    parser.add_argument("--delay-s", type=float, default=0.5, help="Delay entre questoes")
    parser.add_argument("--question-timeout", type=int, default=300, help="Timeout por questao em s")
    parser.add_argument("--append", action="store_true", help="Nao apaga log anterior")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    source_path = (
        "data/gold_standard/regression_suite.json"
        if args.regression_suite
        else "data/gold_standard/questions.json"
    )
    with open(source_path, encoding="utf-8") as f:
        all_questions = json.load(f)

    if args.ids:
        selected = [q for q in all_questions if q["id"] in args.ids]
    else:
        selected = all_questions
    if args.limit:
        selected = selected[: args.limit]

    print(f"Total de questoes selecionadas: {len(selected)}")
    run(selected, args)


if __name__ == "__main__":
    main()
