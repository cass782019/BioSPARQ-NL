"""GATE 0 — Validação do Ambiente BioSPARQL-NL."""
import sys
import os
import subprocess
import glob as glob_mod

checks = []

# 0a. Python libs
for lib_name, import_name in [
    ("owlready2", "owlready2"),
    ("rdflib", "rdflib"),
    ("SPARQLWrapper", "SPARQLWrapper"),
    ("sentence-transformers", "sentence_transformers"),
    ("FAISS", "faiss"),
    ("FastAPI", "fastapi"),
    ("Uvicorn", "uvicorn"),
    ("pytest", "pytest"),
    ("openai", "openai"),
]:
    try:
        mod = __import__(import_name)
        ver = getattr(mod, "__version__", "OK")
        checks.append((lib_name, True, str(ver)))
    except ImportError:
        checks.append((lib_name, False, "not installed"))

# 0b. scispaCy + modelo
try:
    import spacy
    nlp = spacy.load("en_core_sci_sm")
    checks.append(("scispaCy model", True, "en_core_sci_sm loaded"))
except Exception:
    checks.append(("scispaCy model", False, "model not found"))

# 0c. LM Studio acessivel + modelo carregado
try:
    import requests
    r = requests.get("http://localhost:1234/v1/models", timeout=5)
    models = [m["id"] for m in r.json().get("data", [])]
    checks.append(("LM Studio", True, f"models: {models}"))
    has_model = bool(models)
    checks.append(("LLM model", has_model, "loaded" if has_model else "no model loaded"))
except Exception:
    checks.append(("LM Studio", False, "offline (start LM Studio + load a model)"))
    checks.append(("LLM model", False, "LM Studio offline"))

# 0d. Java
try:
    r = subprocess.run(
        ["java", "-version"], capture_output=True, text=True, timeout=10
    )
    java_ver = r.stderr.split('"')[1] if '"' in r.stderr else r.stderr.strip()[:50]
    checks.append(("Java", True, java_ver))
except Exception:
    checks.append(("Java", False, "not found"))

# 0e. Node.js + npm
for cmd, name in [("node", "Node.js"), ("npm.cmd", "npm")]:
    try:
        r = subprocess.run(
            [cmd, "--version"], capture_output=True, text=True, timeout=10
        )
        checks.append((name, r.returncode == 0, r.stdout.strip()))
    except Exception:
        checks.append((name, False, "not found"))

# 0f. pdflatex
try:
    r = subprocess.run(
        ["pdflatex", "--version"], capture_output=True, text=True, timeout=10
    )
    checks.append(("pdflatex", r.returncode == 0, r.stdout.split("\n")[0][:50]))
except Exception:
    checks.append(("pdflatex", False, "not found (install MiKTeX)"))

# 0g. Fuseki binário existe
fuseki_found = glob_mod.glob("tools/apache-jena-fuseki-*/fuseki-server.bat")
if fuseki_found:
    checks.append(("Fuseki binary", True, fuseki_found[0]))
else:
    checks.append(("Fuseki binary", False, "NOT FOUND in tools/"))

# Resultado
print("\n" + "=" * 60)
print("GATE 0 — Validação do Ambiente")
print("=" * 60)
all_pass = True
for name, ok, detail in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}: {detail}")
    if not ok:
        all_pass = False

print(f"\n{'[OK] GATE 0 PASSED' if all_pass else '[FAIL] GATE 0 FAILED'}")
sys.exit(0 if all_pass else 1)
