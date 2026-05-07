# Code–Spec Matrix

> Gerado pelo Redator em 2026-05-04 | doc_level: detalhado
> Mapeia cada arquivo do legado à(s) unit(s) de spec que o cobre.

**Legenda de cobertura:**
- 🟢 Coberto — unit tem requirements + design + tasks derivados deste arquivo
- 🟡 Parcial — arquivo mencionado mas não analisado em profundidade
- `n/a` — sem unit correspondente (artefatos de dados, config, ou fora do escopo de specs)

---

## Módulo `pipeline`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/pipeline/nl_to_sparql.py` | `pipeline/` | 🟢 |
| `src/pipeline/sparql_validator.py` | `pipeline/` | 🟢 |
| `src/pipeline/llm_backends.py` | `pipeline/` | 🟢 |
| `src/pipeline/entity_linker.py` | `pipeline/` | 🟢 |
| `src/exceptions.py` | `pipeline/` | 🟡 |

---

## Módulo `ner`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/pipeline/ner/base.py` | `ner/` | 🟢 |
| `src/pipeline/ner/factory.py` | `ner/` | 🟢 |
| `src/pipeline/ner/scispacy_backend.py` | `ner/` | 🟢 |
| `src/pipeline/ner/llm_backend.py` | `ner/` | 🟢 |
| `src/pipeline/ner/gilda_backend.py` | `ner/` | 🟡 |
| `src/pipeline/ner/medcat_backend.py` | `ner/` | 🟡 |

---

## Módulo `api`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/api/server.py` | `api/` | 🟢 |
| `src/api/__init__.py` | `api/` | 🟡 |

---

## Módulo `evaluation`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/evaluation/run_evaluation.py` | `avaliacao/` | 🟢 |
| `src/evaluation/run_all_models.py` | `avaliacao/` | 🟢 |
| `src/evaluation/ablation_configs.py` | `avaliacao/` | 🟢 |
| `src/evaluation/run_ablation.py` | `avaliacao/` | 🟢 |
| `src/evaluation/consolidate.py` | `avaliacao/` | 🟢 |
| `src/evaluation/latex_tables.py` | `avaliacao/` | 🟢 |
| `src/evaluation/inter_annotator.py` | `avaliacao/` | 🟡 |
| `src/evaluation/bench_ner.py` | `avaliacao/` | 🟡 |
| `src/evaluation/run_evaluation_qald.py` | `avaliacao/` | 🟡 |

---

## Módulo `utils`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src/utils/hpoa_to_rdf.py` | `utilitarios/` | 🟢 |
| `src/utils/schema_extractor.py` | `utilitarios/` | 🟢 |
| `src/utils/index_builder.py` | `utilitarios/` | 🟢 |
| `src/utils/gold_standard.py` | `utilitarios/` | 🟢 |

---

## Módulo `frontend`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `frontend/src/App.jsx` | `frontend/` | 🟢 |
| `frontend/src/main.jsx` | `frontend/` | 🟢 |
| `frontend/src/components/ChatPanel.jsx` | `frontend/` | 🟢 |
| `frontend/src/components/XaiPanel.jsx` | `frontend/` | 🟢 |
| `frontend/src/components/SparqlBlock.jsx` | `frontend/` | 🟢 |
| `frontend/src/components/TimingBar.jsx` | `frontend/` | 🟢 |
| `frontend/vite.config.js` | `frontend/` | 🟢 |
| `frontend/package.json` | `frontend/` | 🟡 |
| `frontend/index.html` | `frontend/` | 🟡 |

---

## Módulo `src2`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `src2/pipeline/llm_backends.py` | `src2/` | 🟢 |
| `src2/pipeline/nl_to_sparql.py` | `src2/` | 🟢 |
| `src2/evaluation/playwright_runner.py` | `src2/` | 🟢 |
| `src2/evaluation/corrections_report.py` | `src2/` | 🟢 |
| `src2/evaluation/run_all_models.py` | `src2/` | 🟢 |
| `src2/evaluation/ablation_configs.py` | `src2/` | 🟡 |
| `src2/evaluation/run_ablation.py` | `src2/` | 🟡 |
| `src2/evaluation/latex_tables.py` | `src2/` | 🟡 |
| `src2/evaluation/inter_annotator.py` | `src2/` | 🟡 |

---

## Módulo `gates`

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `gates/gate0_check.py` | `gates/` | 🟢 |
| `gates/gate1_check.py` | `gates/` | 🟢 |
| `gates/gate2_check.py` | `gates/` | 🟢 |
| `gates/gate3_check.py` | `gates/` | 🟢 |
| `gates/gate6_check.py` | `gates/` | 🟢 |

---

## Testes

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `tests/unit/` | `pipeline/`, `ner/`, `api/` | 🟡 |
| `tests/integration/` | `pipeline/`, `api/` | 🟡 |
| `tests/regression/` | `pipeline/` | 🟡 |
| `pytest.ini` | n/a | n/a |
| `conftest.py` | n/a | n/a |

---

## Artefatos de Dados

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `data/ontologies/doid.owl` | n/a | n/a |
| `data/ontologies/hp.owl` | n/a | n/a |
| `data/annotations/phenotype.hpoa` | n/a | n/a |
| `data/annotations/hpoa.ttl` | n/a | n/a |
| `data/schemas.json` | `utilitarios/` | 🟡 |
| `data/gold_standard/questions.json` | `avaliacao/` | 🟡 |
| `data/gold_standard/questions.index` | `utilitarios/` | 🟡 |

---

## Configuração e Infraestrutura

| Arquivo do legado | Unit correspondente | Cobertura |
|---|---|---|
| `requirements.txt` | n/a | n/a |
| `CLAUDE.md` | n/a | n/a |
| `tools/apache-jena-fuseki-6.0.0/` | n/a | n/a |
| `fuseki-db/` | n/a | n/a |

---

## Resumo de Cobertura

| Módulo | Arquivos totais | 🟢 Cobertos | 🟡 Parciais | `n/a` |
|---|---|---|---|---|
| pipeline | 5 | 4 | 1 | 0 |
| ner | 6 | 4 | 2 | 0 |
| api | 2 | 1 | 1 | 0 |
| evaluation | 9 | 6 | 3 | 0 |
| utils | 4 | 4 | 0 | 0 |
| frontend | 9 | 7 | 2 | 0 |
| src2 | 9 | 4 | 5 | 0 |
| gates | 5 | 5 | 0 | 0 |
| tests | 4 | 0 | 3 | 1 |
| dados | 7 | 0 | 4 | 3 |
| config/infra | 4 | 0 | 0 | 4 |
| **TOTAL** | **64** | **35** | **21** | **8** |

**Cobertura estimada:** 35/56 arquivos de código com spec 🟢 = **62,5% cobertura plena**  
**Cobertura parcial incluída:** (35+21)/56 = **100% mencionados**

> Os arquivos 🟡 (parciais) são variantes de ablação, scripts auxiliares e backends alternativos.
> Candidatos para análise adicional em iteração futura do Archaeologist.
