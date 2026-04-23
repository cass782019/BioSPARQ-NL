"""Roda avaliacao para todos os modelos (revisao 2): locais + Claude via CLI."""
import json
import os
import shutil
import subprocess
import sys
import time

import requests

os.environ["HF_HUB_DISABLE_XET"] = "1"

LOCAL_MODELS = [
    "google/gemma-3-4b",
    "nvidia/nemotron-3-nano-4b",
    "qwen/qwen3.5-9b",
    # Opcionais (lentos por offload CPU):
    # "google/gemma-4-26b-a4b",
    # "openai/gpt-oss-20b",
]

CLAUDE_CLI_MODELS = ["sonnet"]

LM_STUDIO_URL = "http://localhost:1234/v1"
OUTPUT_DIR = "output2"


def check_lm_studio_model(model_name):
    try:
        r = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        models = [m["id"] for m in r.json().get("data", [])]
        return model_name in models
    except Exception:
        return False


def check_lm_studio_responds(model_name):
    try:
        r = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 10,
            },
            timeout=60,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"    Modelo nao respondeu: {e}")
        return False


def check_claude_cli():
    if shutil.which("claude") is None:
        return False
    try:
        r = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def run_evaluation(model_name, backend="lm_studio"):
    safe_name = model_name.replace("/", "_")
    out_path = f"{OUTPUT_DIR}/eval_{safe_name}.json"

    if os.path.exists(out_path):
        with open(out_path) as f:
            d = json.load(f)
        n = d.get("scenario_a_with_validation", {}).get("metrics", {}).get("total", 0)
        if n >= 50:
            print(f"  [SKIP] {model_name}: ja avaliado ({n} questoes)")
            return True

    print(f"  [RUN] {model_name} (backend: {backend})...")
    start = time.time()
    result = subprocess.run(
        [
            sys.executable, "-u", "-m", "src2.evaluation.run_evaluation",
            "--model", model_name,
            "--backend", backend,
        ],
        env={**os.environ, "PYTHONPATH": ".", "HF_HUB_DISABLE_XET": "1"},
        capture_output=False,
        timeout=3600,
    )
    elapsed = time.time() - start
    print(f"  [{'OK' if result.returncode == 0 else 'FAIL'}] {model_name} ({elapsed:.0f}s)")
    return result.returncode == 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("AVALIACAO MULTI-MODELO (revisao 2)")
    print("=" * 60)

    # Verificar LM Studio
    try:
        r = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        available = [
            m["id"]
            for m in r.json().get("data", [])
            if not m["id"].startswith("text-embedding")
        ]
        print(f"LM Studio: {len(available)} modelos disponiveis")
        for m in available:
            print(f"  - {m}")
    except Exception:
        print("AVISO: LM Studio nao acessivel em localhost:1234")
        available = []

    print()
    results = {}

    # Modelos locais
    for model in LOCAL_MODELS:
        print(f"\n--- {model} ---")
        if not check_lm_studio_model(model):
            print(f"  [SKIP] Nao disponivel no LM Studio")
            results[model] = "unavailable"
            continue
        if not check_lm_studio_responds(model):
            print(f"  [SKIP] Modelo nao respondeu (OOM?)")
            results[model] = "oom"
            continue
        ok = run_evaluation(model, backend="lm_studio")
        results[model] = "ok" if ok else "failed"

    # Claude via CLI (upper bound comercial)
    if check_claude_cli():
        for model in CLAUDE_CLI_MODELS:
            print(f"\n--- {model} (Claude CLI) ---")
            ok = run_evaluation(model, backend="claude_cli")
            results[model] = "ok" if ok else "failed"
    else:
        print("\n[INFO] Claude CLI nao encontrado; pulando upper bound comercial")

    # Resumo
    print(f"\n{'=' * 60}")
    print("RESUMO")
    print("=" * 60)
    for model, status in results.items():
        print(f"  {model:40s} {status}")


if __name__ == "__main__":
    main()
