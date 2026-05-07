# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

Pipeline NL→SPARQL sobre ontologias biomédicas (DOID + HPO) com validação por esquema ontológico, loop de autocorreção, avaliação multi-modelo e interface XAI (React + FastAPI).

**Autor**: Cassiano Ricardo Neubauer Moralles
**Orientador**: Sandro J. Rigo
**Programa**: PPG Computação Aplicada — UNISINOS

---

## Stack Real do Projeto

### Infraestrutura (dependências externas)

- **Apache Jena Fuseki 6.0.0** rodando em `http://localhost:3030/biomedical` (TDB2 persistente em `fuseki-db/`)
- **LM Studio** rodando em `http://localhost:1234/v1` (OpenAI-compatible API)
- **Anthropic API** via `ANTHROPIC_API_KEY` (upper bound comercial, opcional)
- **MiKTeX** para compilar o relatório LaTeX
- **Node.js 24+** para frontend React (Vite)
- **Java 21+** para Fuseki

### Modelos LLM disponíveis

| Modelo | Params | Status avaliação |
| --- | --- | --- |
| `google/gemma-3-4b` | 4B | Completo (30 questões) |
| `nvidia/nemotron-3-nano-4b` | 4B | Completo (30 questões) |
| `qwen/qwen3.5-9b` | 9B | Completo (30 questões) |
| `google/gemma-4-26b-a4b` | 26B (4B active) | Timeout 30min |
| `openai/gpt-oss-20b` | 20B | Não avaliado (memória) |
| `claude-sonnet-4-20250514` | - | Via Anthropic API ou CLI OAuth (src2) |

**Resultado chave**: Nemotron 4B (80% correção) > Qwen 9B (50%) > Gemma 3 4B (46.7%) — arquitetura importa mais que tamanho.

---

## Convenções Críticas do Domínio

### MIM vs OMIM (incompatibilidade conhecida)

- **DOID** usa prefixo `MIM:` em `oboInOwl:hasDbXref` (ex: `"MIM:154700"`)
- **HPOA** usa prefixo `OMIM:` em `hpoa:source_id` (ex: `"OMIM:154700"`)
- Queries cross-graph DOID↔HPOA devem usar `BIND(REPLACE(?xref, "^MIM:", "OMIM:") AS ?omim_id)` ou filtro alternativo.

### Grafos no Fuseki

- `urn:doid` — Disease Ontology (302K triplas)
- `urn:hpo` — Human Phenotype Ontology (908K triplas)
- `urn:hpoa` — Anotações doença→fenótipo convertidas de TSV (320K triplas)

### Encoding Windows

Todos os prints de scripts Python devem usar ASCII (`[OK]`, `[FAIL]`) e nunca emojis, pois o terminal Windows (cp1252) falha com UTF-8. Para forçar UTF-8: `sys.stdout.reconfigure(encoding='utf-8')`.

---

## Estrutura do Projeto (real)

```text
c:\Users\cass7\proj1\
├── CLAUDE.md
├── requirements.txt
├── pytest.ini
├── SBC/                             # Template LaTeX SBC (read-only)
├── data/
│   ├── ontologies/ (doid.owl, hp.owl)
│   ├── annotations/ (phenotype.hpoa, hpoa.ttl)
│   ├── schemas.json                 # Extraído via introspecção SPARQL
│   └── gold_standard/
│       ├── questions.json           # 30 questões (10/10/10)
│       └── questions.index          # FAISS index (384d)
├── src/                             # Revisão 1 — LM Studio + Anthropic API
│   ├── exceptions.py
│   ├── api/server.py                # FastAPI backend
│   ├── pipeline/
│   │   ├── nl_to_sparql.py          # BioSPARQLPipeline
│   │   ├── llm_backends.py          # LM Studio + Anthropic API
│   │   ├── entity_linker.py         # scispaCy NER
│   │   └── sparql_validator.py
│   ├── utils/
│   │   ├── hpoa_to_rdf.py
│   │   ├── schema_extractor.py
│   │   ├── index_builder.py
│   │   └── gold_standard.py
│   └── evaluation/
│       ├── run_evaluation.py        # 1 modelo (--model --backend)
│       ├── run_all_models.py        # Multi-modelo orquestrador
│       ├── consolidate.py           # Gera tabelas comparativas
│       ├── ablation_configs.py      # Configs ablação
│       ├── run_ablation.py          # Estudo de ablação
│       ├── latex_tables.py          # Gera .tex para paper
│       ├── inter_annotator.py
│       ├── bench_ner.py             # Benchmark de backends NER (P/R/F1)
│       └── run_evaluation_qald.py   # Avaliação de generalização QALD-9+/DBpedia
├── src2/                            # Revisão 2 — adiciona ClaudeCLIBackend + Playwright
│   ├── pipeline/
│   │   ├── nl_to_sparql.py          # BioSPARQLPipeline (usa src2 backends)
│   │   └── llm_backends.py          # LMStudioBackend + ClaudeCLIBackend
│   └── evaluation/
│       ├── run_evaluation.py
│       ├── run_all_models.py        # Orquestra LM Studio + Claude CLI; saída em output2/
│       ├── playwright_runner.py     # Testa frontend via Playwright (intercepta /api/ask)
│       ├── corrections_report.py    # Compara baseline vs pós-correções
│       ├── ablation_configs.py
│       ├── run_ablation.py
│       ├── latex_tables.py
│       └── inter_annotator.py
├── frontend/                        # React + Vite + axios
├── tests/                           # unit + integration + regression
├── gates/                           # Scripts gate0-gate6
├── tools/apache-jena-fuseki-6.0.0/
├── fuseki-db/                       # TDB2 (gitignored)
├── output/                          # Resultados src (revisão 1)
│   ├── eval_<safe_model>.json
│   ├── evaluation_multi_model.json
│   ├── ablation_<model>.json
│   ├── tables/                      # Fragmentos .tex
│   └── relatorio/                   # LaTeX SBC + PDF final
│       ├── biosparql-nl.tex
│       ├── biosparql-nl.bib         # 22 refs verificadas
│       └── biosparql-nl.pdf
└── output2/                         # Resultados src2 (revisão 2)
    ├── playwright_log.jsonl         # Log Playwright por questão
    ├── playwright_summary.json
    ├── playwright_log_baseline.jsonl # Snapshot pré-correções
    ├── corrections_report.json/.md
    ├── four_way_comparison.json/.md
    └── regression_log.jsonl
```

---

## src2: Revisão 2 do Pipeline

`src2/` é uma revisão do pipeline que adiciona dois recursos não presentes em `src/`:

**ClaudeCLIBackend** (`src2/pipeline/llm_backends.py`): usa o `claude` CLI em modo subprocesso (`--print`) com a sessão OAuth já autenticada no Claude Code — não precisa de `ANTHROPIC_API_KEY`. Para isolar o benchmark, roda em diretório temporário fora de `proj1/` (evita descoberta automática deste CLAUDE.md) e passa `--disable-slash-commands`.

**Playwright runner** (`src2/evaluation/playwright_runner.py`): testa as 30 questões diretamente via frontend na porta 3000, intercepta chamadas `/api/ask` e salva o JSON completo (entidades, SPARQL, validação, timing) em `output2/playwright_log.jsonl`. Suporta `--limit N`, `--ids Q01 Q05`, `--headed` e `--screenshots`.

`src2/evaluation/run_all_models.py` salva em `output2/` (não em `output/`).

---

## Regras de Trabalho

### Paper LaTeX

- **Máximo 10 páginas** (template SBC)
- **Todas as referências verificadas** via CrossRef/Semantic Scholar API (não inventar autores/DOIs)
- **Todos os números conferem** com dados reais em `output/eval_*.json`
- **Autor**: Cassiano Ricardo Neubauer Moralles (nunca `[Seu Nome]`)
- Compilar com: `pdflatex → bibtex → pdflatex → pdflatex` (3 passes)

### Avaliação

- **30 questões** no gold standard (10 easy/10 medium/10 hard) — não reduzir
- **2 cenários padrão**: com validação (A) e sem validação (B)
- **Cenário zero-shot (C)** para ablação
- Resultados em `output/eval_{safe_name}.json` onde `safe_name = model.replace("/", "_")`
- **Não rodar modelos >20B** sem verificar memória disponível (8GB VRAM + 16GB RAM)

### Bibliografia

- Verificar cada DOI via `https://api.crossref.org/works/<DOI>` antes de aceitar
- Para papers sem DOI (arXiv, conferências), usar Semantic Scholar API (`ARXIV:<id>` ou `ACL:<id>`)
- **Nunca usar `and others`** — listar pelo menos 3 autores reais ou usar `et al.` em runtime
- Rodar verificação completa via skill `verify-bib`

### Testes

- Unit tests em `tests/unit/` devem passar sem Fuseki/LM Studio (usar fixtures)
- Integration/regression tests usam markers pytest: `fuseki`, `ollama`, `integration`, `regression`
- Skip automático se serviços offline (via `conftest.py`)

---

## Serviços Necessários (startup)

Para desenvolvimento completo, estes 4 serviços precisam estar rodando:

```bash
# 1. Fuseki (terminal 1)
cd c:/Users/cass7/proj1
PATH="/c/Program Files/Eclipse Adoptium/jdk-21.0.10.7-hotspot/bin:$PATH" \
  MSYS_NO_PATHCONV=1 \
  java -Xmx2G -jar tools/apache-jena-fuseki-6.0.0/fuseki-server.jar \
  --tdb2 --loc=fuseki-db --update /biomedical

# 2. LM Studio (GUI app, não CLI)
# Abrir LM Studio, carregar um modelo, iniciar servidor em localhost:1234

# 3. Backend FastAPI (terminal 2)
cd c:/Users/cass7/proj1
HF_HUB_DISABLE_XET=1 PYTHONPATH=. \
  .venv/Scripts/python.exe -m uvicorn src.api.server:app --port 8000

# 4. Frontend React (terminal 3)
cd c:/Users/cass7/proj1/frontend
npx vite dev
# Abrir http://localhost:5173
```

---

## Comandos Rápidos

| Tarefa | Comando |
| --- | --- |
| Rodar 1 modelo (src) | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.run_evaluation --model "<nome>"` |
| Rodar todos os modelos (src) | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.run_all_models` |
| Rodar todos os modelos (src2) | `PYTHONPATH=. .venv/Scripts/python.exe -m src2.evaluation.run_all_models` |
| Playwright (frontend, 30 questões) | `PYTHONPATH=. .venv/Scripts/python.exe -m src2.evaluation.playwright_runner` |
| Playwright (questões específicas) | `PYTHONPATH=. .venv/Scripts/python.exe -m src2.evaluation.playwright_runner --ids Q01 Q05 --headed` |
| Relatório pós-correções | `PYTHONPATH=. .venv/Scripts/python.exe -m src2.evaluation.corrections_report` |
| Consolidar resultados | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.consolidate` |
| Gerar tabelas LaTeX | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.latex_tables` |
| Benchmark NER | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.bench_ner` |
| Avaliação QALD-9+ (generalização) | `PYTHONPATH=. .venv/Scripts/python.exe -m src.evaluation.run_evaluation_qald` |
| Compilar paper | `cd output/relatorio && pdflatex biosparql-nl && bibtex biosparql-nl && pdflatex biosparql-nl && pdflatex biosparql-nl` |
| Testes unitários | `pytest tests/unit/ -v` |
| Gate 1 (dados) | `PYTHONPATH=. .venv/Scripts/python.exe gates/gate1_check.py` |
| Query direta no Fuseki | `curl "http://localhost:3030/biomedical/sparql" --data-urlencode "query=<SPARQL>" -H "Accept: application/sparql-results+json"` |

---

## Histórico de Correções (auditoria de alucinações)

- ShEx shapes → Introspecção SPARQL com `GROUP_CONCAT`
- HPO annotations em RDF nativo → `hpoa_to_rdf.py` TSV→Turtle
- BioPortal SPARQL endpoint → Fuseki local
- `auer2007dbpedia` para SPARQL → `harris2013sparql` (W3C Recommendation)
- `dejean2024sparqlllm` → `emonet2024sparqlllm` (autoria corrigida via Semantic Scholar)
- Autores inventados em `prenosil2025neurosymbolic` → 9 autores reais + DOI correto
- `xu2025survey` → `lu2025survey` (DOI apontava para paper diferente)
- `manda2025llms` vol 12(1) → vol 12(11) p1260 (DOI correto)
- `toro2024dragonai` pages=11 → pages=19 + DOI correto
- DOID usa `MIM:` e HPOA usa `OMIM:` — documentado em consultas cross-graph


---

# Reversa

> Framework de Engenharia Reversa instalado neste projeto.

## Como usar

Digite `/reversa` para ativar o Reversa e iniciar ou retomar a análise do projeto.

## Comportamento ao ativar

Quando o usuário digitar `/reversa` ou a palavra `reversa` sozinha em uma mensagem:

1. Ative o skill `reversa` disponível em `.claude/skills/reversa/SKILL.md`
2. Se não encontrar em `.claude/skills/`, tente `.agents/skills/reversa/SKILL.md`
3. Leia o SKILL.md na íntegra e siga exatamente as instruções do Reversa

## Regra não-negociável

Nunca apague, modifique ou sobrescreva arquivos pré-existentes do projeto legado.
O Reversa escreve **apenas** em `.reversa/` e `_reversa_sdd/`.
