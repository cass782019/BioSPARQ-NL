# Casos de Borda — gates

> Unit: `gates/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## EC-01 — Check de LLM model sempre falha em ambiente com apenas LM Studio

**Confiança:** 🟢 CONFIRMADO — `gates/gate0_check.py:linha 39-46`

**Cenário:** Ambiente de desenvolvimento atual usa LM Studio (porta 1234), não Ollama (porta 11434).

**Comportamento atual:**
```
[FAIL] Ollama: offline
[FAIL] LLM model: Ollama offline
```

**Impacto:** Gate 0 retorna exit code 1 e "[FAIL] GATE 0 FAILED" em qualquer máquina sem Ollama, mesmo com LM Studio rodando e modelo disponível.

**Workaround documentado:** Executar gate0 com consciência de que os checks de Ollama sempre falharão. Os outros checks ainda são válidos.

**Correção:** Ver `tasks.md:TASK-GATES-01`.

---

## EC-02 — Gold standard total e FAISS index sempre falham no gate2

**Confiança:** 🔴 LACUNA — `gates/gate2_check.py:linhas 31, 84` — bug no código

**Cenário:** Gold standard tem 30 questões, FAISS index tem 30 vetores. Os checks exigem >= 50.

**Comportamento atual:**
```
[FAIL] Gold standard total: 30 questoes (min: 50)
[FAIL] FAISS index: 30 vetores (min: 50)
```

**Impacto:** Gate 2 retorna exit code 1 mesmo quando todos os dados estão corretos e completos. Todo o pipeline pode funcionar perfeitamente com gate2 relatando falha.

**Risco de confusão:** Um desenvolvedor novo pode interpretar essas falhas como dados corrompidos e tentar recarregar os dados (operação demorada), quando a causa é apenas o threshold incorreto no script.

**Correção:** Ver `tasks.md:TASK-GATES-02`.

---

## EC-03 — Gate 3 falha se LM Studio offline (mesmo com Fuseki funcionando)

**Confiança:** 🟢 CONFIRMADO — `gates/gate3_check.py` — `BioSPARQLPipeline()` falha se backend LLM inacessível

**Cenário:** Fuseki está rodando e dados carregados, mas LM Studio não está no ar.

**Comportamento atual:**
```
EXCEPTION: LLMConnectionError: Failed to connect to LM Studio after 3 attempts
[FAIL] easy: What phenotypes are associated with ...
[FAIL] easy: How many subclasses of...
[FAIL] medium: Which diseases are...
[FAIL] Pipeline nao crashou: 0/3 executadas   ← NÃO, pipeline crashou na instância
```

**Observação:** Se `BioSPARQLPipeline()` lança exceção na instanciação (antes do loop), `results` fica vazio e o gate reporta `0/3 executadas` mas a mensagem pode ser confusa — o script tenta capturar por exceção individualmente no loop, mas a instância falhou antes.

**Recomendação:** Envolver `BioSPARQLPipeline()` em try/except separado com mensagem explícita: `"[FAIL] Instância do pipeline: LM Studio offline"`.

---

## EC-04 — Gate 1 falha silenciosamente se grafo não existe (retorna 0, não erro)

**Confiança:** 🟢 CONFIRMADO — `gates/gate1_check.py:linhas 19-22`

**Cenário:** Um dos grafos (ex.: `urn:hpoa`) não foi carregado no Fuseki — grafo simplesmente não existe.

**Comportamento atual:**
```python
actual = counts.get(graph, 0)   # retorna 0 se grafo ausente
ok = actual >= min_count         # False, reportado como [FAIL]
```

**Comportamento:** Gate 1 reporta `[FAIL] urn:hpoa triplas: 0 (min: 50,000)` — correto e informativo. Mas pode confundir com "grafo existe com 0 triplas" vs "grafo nunca foi carregado". A distinção não está no output.

**Impacto:** Menor — o check falha corretamente, mas a mensagem de diagnóstico poderia ser mais específica ("grafo não encontrado" vs "grafo vazio").

---

## EC-05 — Gate 6 passa mesmo se pipeline retorna SPARQL vazio

**Confiança:** 🟡 INFERIDO — `gates/gate6_check.py:linha 43` — check de presença, não de qualidade

**Cenário:** O pipeline instancia mas falha na geração de SPARQL, retornando uma string vazia em `xai.sparql`.

**Comportamento atual:**
```python
checks.append(("XAI sparql", len(xai.get("sparql", "")) > 0, "present"))
```

**Risco:** Se `pipeline.run()` captura internamente uma falha e retorna `{"sparql": "SELECT WHERE {}", ...}` (query mínima/inválida), o check de `len > 0` passaria. O gate6 verifica presença do campo, não corretude da query.

**Contexto:** Gate6 usa `TestClient` (in-process), então depende do comportamento real do pipeline naquele momento.

---

## EC-06 — Timeout de subprocess no gate0 pode bloquear se Java lento

**Confiança:** 🟡 INFERIDO** — `gates/gate0_check.py:linha 51` — `timeout=10` para subprocess

**Cenário:** Em máquinas com JVM fria (primeiro boot, antivírus escaneando), `java -version` pode levar > 10 segundos.

**Comportamento atual:** `subprocess.run(..., timeout=10)` lança `subprocess.TimeoutExpired`, capturado pelo `except Exception`, reportado como `[FAIL] Java: not found` (mensagem imprecisa — Java existe mas demorou).

**Impacto:** Raro, mas pode confundir — a mensagem sugere que Java não está instalado quando na verdade só demorou para iniciar.

---

## EC-07 — Gate 2 downloada modelo de embedding na primeira execução

**Confiança:** 🟢 CONFIRMADO — `gates/gate2_check.py:linha 91` — `SentenceTransformer("all-MiniLM-L6-v2")`

**Cenário:** Primeira execução em máquina sem cache HuggingFace.

**Comportamento atual:** `SentenceTransformer("all-MiniLM-L6-v2")` faz download automático do modelo (~22MB) do HuggingFace Hub. A variável `HF_HUB_DISABLE_XET=1` está configurada no gate2 para desativar XET transport, mas o download HTTP ainda ocorre.

**Impacto:** Primeira execução do gate2 pode levar 30-60 segundos a mais sem aviso ao usuário. Em ambientes sem internet, o gate2 falhará com `ConnectionError`.

**Mitigação atual:** O modelo fica em cache após primeira execução. Execuções subsequentes são rápidas.

---

## EC-08 — Execução dos gates requer cwd = raiz do projeto

**Confiança:** 🟢 CONFIRMADO — caminhos relativos usados em todos os gates

**Cenário:** Executar `python gates/gate0_check.py` de dentro da pasta `gates/`.

**Comportamento atual:**
- `gate0`: `glob.glob("tools/apache-jena-fuseki-*/fuseki-server.bat")` → retorna `[]` (caminho relativo quebrado)
- `gate2`: `open("data/schemas.json")` → `FileNotFoundError`
- `gate3`: `BioSPARQLPipeline()` usa caminhos relativos internamente → falha

**Impacto:** Gates falham com erros confusos se executados de diretório incorreto.

**Workaround:** Sempre executar de `c:/Users/cass7/proj1/`:
```bash
cd c:/Users/cass7/proj1
python gates/gate0_check.py
```

---

## EC-09 — npm.cmd vs npm no Gate 0 (Windows específico)

**Confiança:** 🟢 CONFIRMADO — `gates/gate0_check.py:linha 60` — `"npm.cmd"` hardcoded

**Cenário:** Execução em Linux/macOS (ex.: CI container, WSL).

**Comportamento atual:** `subprocess.run(["npm.cmd", "--version"], ...)` falha com `FileNotFoundError` em sistemas não-Windows porque o executável se chama `npm`, não `npm.cmd`.

**Impacto:** Gate0 falhará no check npm em qualquer sistema não-Windows, mesmo com npm instalado.

**Recomendação:** Detectar plataforma e usar `"npm"` em não-Windows:
```python
npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
```
