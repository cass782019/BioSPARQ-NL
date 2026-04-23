"""GATE 6 - Validacao da Interface (Backend FastAPI + Frontend React)."""
import sys
import os
import subprocess

os.environ["HF_HUB_DISABLE_XET"] = "1"

checks = []

# 6a. FastAPI + Uvicorn instalados
try:
    import fastapi
    checks.append(("FastAPI", True, fastapi.__version__))
except ImportError:
    checks.append(("FastAPI", False, "not installed"))

try:
    import uvicorn
    checks.append(("Uvicorn", True, "OK"))
except ImportError:
    checks.append(("Uvicorn", False, "not installed"))

# 6b. API importa sem erro
try:
    from src.api.server import app
    checks.append(("API importa", True, "OK"))
except Exception as e:
    checks.append(("API importa", False, str(e)[:80]))

# 6c. TestClient funciona
try:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.get("/api/health")
    checks.append(("Health endpoint", r.status_code == 200, str(r.json())))

    r = client.post("/api/ask", json={"question": "What is disease DOID_4?"})
    checks.append(("Ask endpoint", r.status_code == 200, f"status={r.status_code}"))

    xai = r.json().get("xai", {})
    checks.append(("XAI sparql", len(xai.get("sparql", "")) > 0, "present"))
    checks.append(
        ("XAI timing", "total_s" in xai.get("timing", {}), "present")
    )
    checks.append(
        ("XAI entities", isinstance(xai.get("entities"), list), "present")
    )
    checks.append(
        (
            "XAI validation",
            "valid" in xai.get("validation", {}),
            "present",
        )
    )

    r = client.post("/api/ask", json={"question": ""})
    checks.append(
        ("Empty question -> 400", r.status_code == 400, f"status={r.status_code}")
    )

except Exception as e:
    checks.append(("TestClient", False, str(e)[:80]))

# 6d. Frontend build
if os.path.exists("frontend/package.json"):
    try:
        r = subprocess.run(
            ["npx.cmd", "vite", "build"],
            cwd="frontend",
            capture_output=True,
            text=True,
            timeout=60,
        )
        checks.append(
            (
                "Frontend build",
                r.returncode == 0,
                "OK" if r.returncode == 0 else r.stderr[:80],
            )
        )
    except Exception as e:
        checks.append(("Frontend build", False, str(e)[:80]))
else:
    checks.append(("Frontend exists", False, "frontend/package.json not found"))

# Resultado
print("\n" + "=" * 60)
print("GATE 6 - Validacao da Interface")
print("=" * 60)
all_pass = True
for name, ok, detail in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}: {detail}")
    if not ok:
        all_pass = False

print(f"\n{'[OK] GATE 6 PASSED' if all_pass else '[FAIL] GATE 6 FAILED'}")
sys.exit(0 if all_pass else 1)
