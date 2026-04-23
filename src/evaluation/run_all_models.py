"""Roda avaliacao para todos os modelos disponiveis no LM Studio."""
import json
import os
import subprocess
import sys
import time

import requests

os.environ["HF_HUB_DISABLE_XET"] = "1"

LOCAL_MODELS = [
    "google/gemma-3-4b",
    "nvidia/nemotron-3-nano-4b",
    "google/gemma-4-26b-a4b",
    "qwen/qwen3.5-9b",
    "openai/gpt-oss-20b",
]

ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514",
]

LM_STUDIO_URL = "http://localhost:1234/v1"


def check_model_available(model_name):
    """Verifica se o modelo esta disponivel no LM Studio."""
    try:
        r = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        models = [m["id"] for m in r.json().get("data", [])]
        return model_name in models
    except Exception:
        return False


def check_model_responds(model_name):
    """Testa se o modelo responde a uma query simples."""
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


def run_evaluation(model_name, backend="lm_studio"):
    """Roda avaliacao para um modelo."""
    safe_name = model_name.replace("/", "_")
    out_path = f"output/eval_{safe_name}.json"

    # Pular se ja existe
    if os.path.exists(out_path):
        with open(out_path) as f:
            d = json.load(f)
        n = d.get("scenario_a_with_validation", {}).get("metrics", {}).get("total", 0)
        if n >= 30:
            print(f"  [SKIP] {model_name}: ja avaliado ({n} questoes)")
            return True

    print(f"  [RUN] {model_name} (backend: {backend})...")
    start = time.time()
    result = subprocess.run(
        [
            sys.executable, "-u", "-m", "src.evaluation.run_evaluation",
            "--model", model_name,
            "--backend", backend,
        ],
        env={**os.environ, "PYTHONPATH": ".", "HF_HUB_DISABLE_XET": "1"},
        capture_output=False,
        timeout=1800,  # 30min max per model
    )
    elapsed = time.time() - start
    print(f"  [{'OK' if result.returncode == 0 else 'FAIL'}] {model_name} ({elapsed:.0f}s)")
    return result.returncode == 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("AVALIACAO MULTI-MODELO")
    print("=" * 60)

    # Verificar LM Studio
    try:
        r = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        available = [m["id"] for m in r.json().get("data", []) if m["id"] != "text-embedding-nomic-embed-text-v1.5"]
        print(f"LM Studio: {len(available)} modelos disponiveis")
        for m in available:
            print(f"  - {m}")
    except Exception:
        print("ERRO: LM Studio nao acessivel em localhost:1234")
        sys.exit(1)

    print()
    results = {}

    # Modelos locais via LM Studio
    for model in LOCAL_MODELS:
        print(f"\n--- {model} ---")
        if not check_model_available(model):
            print(f"  [SKIP] Nao disponivel no LM Studio")
            results[model] = "unavailable"
            continue

        # Health check
        if not check_model_responds(model):
            print(f"  [SKIP] Modelo nao respondeu (OOM?)")
            results[model] = "oom"
            continue

        ok = run_evaluation(model, backend="lm_studio")
        results[model] = "ok" if ok else "failed"

    # Modelos Anthropic (upper bound comercial)
    if os.getenv("ANTHROPIC_API_KEY"):
        for model in ANTHROPIC_MODELS:
            print(f"\n--- {model} (Anthropic) ---")
            ok = run_evaluation(model, backend="anthropic")
            results[model] = "ok" if ok else "failed"
    else:
        print("\n[INFO] ANTHROPIC_API_KEY nao definida, pulando modelos Anthropic")

    # Resumo
    print(f"\n{'=' * 60}")
    print("RESUMO")
    print("=" * 60)
    for model, status in results.items():
        print(f"  {model:40s} {status}")

    # Consolidar
    print(f"\nConsolidando resultados...")
    subprocess.run(
        [sys.executable, "-m", "src.evaluation.consolidate"],
        env={**os.environ, "PYTHONPATH": ".", "HF_HUB_DISABLE_XET": "1"},
    )


if __name__ == "__main__":
    main()
