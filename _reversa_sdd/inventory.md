# Inventário do Projeto — proj1 (BioSPARQL-NL)

> Gerado pelo Scout em 2026-05-04

---

## Visão Geral

| Campo | Valor |
|---|---|
| Nome | BioSPARQL-NL |
| Propósito | Pipeline NL→SPARQL sobre ontologias biomédicas (DOID + HPO) |
| Linguagem principal | Python |
| Framework backend | FastAPI 0.135.3 |
| Framework frontend | React 18.3.1 + Vite 5.4.0 |
| Gerenciador de pacotes | pip (Python) + npm (Node) |
| Total de arquivos (código) | ~120 arquivos (excl. venv, output, tools) |

---

## Estrutura de Diretórios

```
proj1/
├── src/                          # Revisão 1 do pipeline
│   ├── api/
│   │   └── server.py             # FastAPI app (entry point backend)
│   ├── pipeline/
│   │   ├── nl_to_sparql.py       # BioSPARQLPipeline (orquestrador principal)
│   │   ├── llm_backends.py       # LMStudioBackend, AnthropicBackend, ClaudeCLIBackend
│   │   ├── entity_linker.py      # EntityLinker (scispaCy)
│   │   ├── sparql_validator.py   # SchemaValidator
│   │   └── ner/                  # Backends NER plugáveis
│   │       ├── base.py
│   │       ├── factory.py
│   │       ├── scispacy_backend.py
│   │       ├── gilda_backend.py
│   │       ├── llm_backend.py
│   │       └── medcat_backend.py
│   ├── evaluation/
│   │   ├── run_evaluation.py     # Avaliação de 1 modelo
│   │   ├── run_all_models.py     # Multi-modelo
│   │   ├── run_ablation.py       # Estudo de ablação
│   │   ├── ablation_configs.py   # Configurações de ablação
│   │   ├── consolidate.py        # Tabelas comparativas
│   │   ├── latex_tables.py       # Geração de .tex
│   │   ├── inter_annotator.py    # Acordo inter-anotador
│   │   ├── bench_ner.py          # Benchmark P/R/F1 NER
│   │   └── run_evaluation_qald.py # Generalização QALD-9+
│   └── utils/
│       ├── hpoa_to_rdf.py        # Conversão TSV→Turtle HPOA
│       ├── schema_extractor.py   # Introspecção SPARQL → schemas.json
│       ├── index_builder.py      # Construção FAISS index
│       ├── gold_standard.py      # Utilitários gold standard
│       └── download_data.py      # Download de ontologias
│
├── src2/                         # Revisão 2 (ClaudeCLI + Playwright)
│   ├── pipeline/
│   │   ├── nl_to_sparql.py       # BioSPARQLPipeline (usa src2 backends)
│   │   └── llm_backends.py       # LMStudioBackend + ClaudeCLIBackend
│   └── evaluation/
│       ├── run_evaluation.py
│       ├── run_all_models.py     # Salva em output2/
│       ├── playwright_runner.py  # Testes E2E via browser
│       ├── corrections_report.py # Relatório baseline vs pós-correções
│       ├── ablation_configs.py
│       ├── run_ablation.py
│       ├── latex_tables.py
│       └── inter_annotator.py
│
├── frontend/                     # Interface React XAI
│   ├── src/
│   │   ├── App.jsx               # Componente raiz
│   │   ├── main.jsx              # Entry point React
│   │   └── components/
│   │       ├── ChatPanel.jsx
│   │       ├── EntityBadges.jsx
│   │       ├── InputBar.jsx
│   │       ├── ResultsTable.jsx
│   │       ├── SparqlBlock.jsx
│   │       ├── TimingBar.jsx
│   │       ├── ValidationStatus.jsx
│   │       └── XaiPanel.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── ontologies/
│   │   ├── doid.owl              # Disease Ontology
│   │   └── hp.owl                # Human Phenotype Ontology
│   ├── annotations/
│   │   ├── phenotype.hpoa        # Anotações doença→fenótipo (TSV original)
│   │   └── hpoa.ttl              # Convertido para Turtle
│   ├── gold_standard/
│   │   ├── questions.json        # 30 questões (10 fáceis / 10 médias / 10 difíceis)
│   │   ├── questions.index       # FAISS index (384d)
│   │   ├── qald_fewshot.json     # Questões QALD-9+ para generalização
│   │   └── regression_suite.json # Suite de regressão
│   └── schemas.json              # Schema extraído via introspecção SPARQL
│
├── gates/
│   ├── gate0_check.py            # Verificação de dependências
│   ├── gate1_check.py            # Verificação de dados
│   ├── gate2_check.py            # Verificação do pipeline
│   ├── gate3_check.py            # Verificação de avaliação
│   └── gate6_check.py            # Verificação final
│
├── tests/
│   ├── conftest.py               # Fixtures e markers pytest
│   └── unit/
│       ├── test_entity_linker.py
│       ├── test_gold_standard.py
│       ├── test_hpoa_to_rdf.py
│       ├── test_index_builder.py
│       └── test_sparql_validator.py
│
├── output/                       # Resultados avaliação (src)
│   ├── eval_*.json               # Resultados por modelo
│   ├── ablation_*.json           # Resultados ablação
│   ├── evaluation_multi_model.json
│   ├── relatorio/                # Paper LaTeX SBC
│   │   ├── biosparql-nl.tex
│   │   ├── biosparql-nl.bib
│   │   └── biosparql-nl.pdf
│   └── tables/                   # Fragmentos .tex
│
├── output2/                      # Resultados avaliação (src2)
│   ├── playwright_log*.jsonl     # Logs E2E por modelo
│   ├── playwright_summary*.json
│   ├── corrections_report.*
│   └── four_way_comparison.*
│
├── tools/
│   └── apache-jena-fuseki-6.0.0/ # SPARQL triplestore local
│
├── docsfhir/                     # Crawler FHIR (exploratório)
│   ├── crawler.py
│   └── pages/                    # HTML/JSON/TTL de recursos FHIR
│
├── references/                   # PDFs das referências bibliográficas
├── run/                          # Templates de configuração Fuseki
├── requirements.txt              # Dependências Python
├── pytest.ini                    # Configuração pytest
├── CLAUDE.md                     # Instruções para Claude Code
└── .env.example                  # Variáveis de ambiente
```

---

## Módulos Identificados

| Módulo | Caminho | Responsabilidade |
|---|---|---|
| `pipeline` | `src/pipeline/` | Orquestrador NL→SPARQL (NER, embeddings, LLM, validação, execução) |
| `api` | `src/api/` | Servidor FastAPI REST (endpoints `/api/ask`, `/api/health`) |
| `evaluation` | `src/evaluation/` | Avaliação multi-modelo, ablação, tabelas LaTeX |
| `utils` | `src/utils/` | Conversão HPOA, extração de schema, construção de índice FAISS |
| `ner` | `src/pipeline/ner/` | Backends NER plugáveis (scispaCy, Gilda, LLM, MedCAT) |
| `frontend` | `frontend/` | Interface React XAI (visualização de entidades, SPARQL, timing) |
| `src2` | `src2/` | Revisão 2: adiciona ClaudeCLIBackend e Playwright runner |
| `gates` | `gates/` | Scripts de validação por fase (gate0–gate6) |

---

## Pontos de Entrada

| Tipo | Arquivo | Descrição |
|---|---|---|
| Backend server | `src/api/server.py` | FastAPI app — `uvicorn src.api.server:app --port 8000` |
| Frontend | `frontend/src/main.jsx` | React entry point — `npx vite dev` (porta 5173) |
| Avaliação | `src/evaluation/run_evaluation.py` | 1 modelo: `--model <nome>` |
| Avaliação multi | `src/evaluation/run_all_models.py` | Todos os modelos |
| Avaliação src2 | `src2/evaluation/run_all_models.py` | Salva em `output2/` |
| Playwright E2E | `src2/evaluation/playwright_runner.py` | Testes via browser (porta 3000) |
| Gates | `gates/gate*.py` | Validação por fase |

---

## Configuração

| Arquivo | Propósito |
|---|---|
| `.env.example` | Template de variáveis de ambiente |
| `pytest.ini` | Configuração pytest com markers |
| `frontend/vite.config.js` | Configuração Vite (proxy para backend) |
| `data/schemas.json` | Schema SPARQL das ontologias (gerado por `schema_extractor.py`) |

---

## Contagem de Arquivos por Linguagem

| Linguagem | Extensão | Arquivos (código) |
|---|---|---|
| Python | `.py` | 57 |
| JSON | `.json` | 18 |
| JSX (React) | `.jsx` | 10 |
| Markdown | `.md` | 8 |
| JSONL | `.jsonl` | 6 |
| Turtle (RDF) | `.ttl` | 2 |
| OWL | `.owl` | 2 |
| JavaScript | `.js` | 1 |
| HTML | `.html` | 2 |

---

## Testes

| Tipo | Framework | Arquivos | Observação |
|---|---|---|---|
| Unit | pytest | 5 | `tests/unit/` — sem serviços externos |
| Integration | pytest | — | Markers `fuseki`, `ollama` — requer serviços |
| Regression | pytest | — | Marker `regression` — requer Fuseki |
| E2E | Playwright | `playwright_runner.py` | Via browser, porta 3000 |

**Markers pytest**: `unit`, `integration`, `regression`, `fuseki`, `ollama`

---

## Banco de Dados / RDF Store

| Componente | Tecnologia | Localização |
|---|---|---|
| SPARQL triplestore | Apache Jena Fuseki 6.0.0 | `tools/apache-jena-fuseki-6.0.0/` |
| TDB2 persistente | TDB2 | `fuseki-db/` (gitignored) |
| Grafo DOID | OWL → TDB2 | `urn:doid` (~302K triplas) |
| Grafo HPO | OWL → TDB2 | `urn:hpo` (~908K triplas) |
| Grafo HPOA | Turtle → TDB2 | `urn:hpoa` (~320K triplas) |
| FAISS Index | CPU | `data/gold_standard/questions.index` |

---

## Integrações Externas

| Serviço | URL | Propósito |
|---|---|---|
| LM Studio | `http://localhost:1234/v1` | LLM local (API OpenAI-compat) |
| Anthropic API | cloud | Claude Sonnet (upper bound) |
| Fuseki | `http://localhost:3030/biomedical` | SPARQL endpoint |

---

## Modelos LLM Avaliados

| Modelo | Parâmetros | Resultado |
|---|---|---|
| `nvidia/nemotron-3-nano-4b` | 4B | 80% correção (**melhor**) |
| `qwen/qwen3.5-9b` | 9B | 50% correção |
| `google/gemma-3-4b` | 4B | 46.7% correção |
| `claude-sonnet-4-20250514` | — | Via Anthropic API |
