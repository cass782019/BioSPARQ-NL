# Requisitos — gates

> Unit: `gates/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `gates` |
| Caminho legado | `gates/gate0_check.py`, `gates/gate1_check.py`, `gates/gate2_check.py`, `gates/gate3_check.py`, `gates/gate6_check.py` |
| Responsabilidade | Validação sequencial por fase — verifica pré-condições do ambiente, integridade dos dados no Fuseki, coerência do gold standard e FAISS, execução end-to-end do pipeline, e integridade da interface FastAPI/React |
| Complexidade | 🟢 Baixa (scripts independentes sem estado compartilhado) |

---

## Requisitos Funcionais

### RF-01 — Gate 0: Validação do ambiente de desenvolvimento
🟢 **CONFIRMADO** — `gates/gate0_check.py`

**Must**

O gate 0 deve verificar que todas as dependências do ambiente estão instaladas e acessíveis antes de qualquer operação do pipeline.

**Verificações cobertas:**

| Check | Detalhe | Confiança |
|---|---|---|
| Python libs (9 pacotes) | owlready2, rdflib, SPARQLWrapper, sentence-transformers, faiss, fastapi, uvicorn, pytest, openai | 🟢 |
| Modelo scispaCy | `en_core_sci_sm` carregável via `spacy.load()` | 🟢 |
| Ollama acessível | `GET http://localhost:11434/api/tags` com timeout 5s | 🟢 |
| Modelo LLM (Ollama) | Qualquer modelo com "qwen" ou "llama" no nome | 🟡 (legado — sistema migrou para LM Studio) |
| Java runtime | `java -version` com exit code 0 | 🟢 |
| Node.js | `node --version` | 🟢 |
| npm | `npm.cmd --version` | 🟢 |
| pdflatex | `pdflatex --version` | 🟢 |
| Fuseki binary | Glob em `tools/apache-jena-fuseki-*/fuseki-server.bat` | 🟢 |

**Critérios de Aceitação:**

```gherkin
Dado que todas as dependências Python estão instaladas no venv ativo
E scispaCy en_core_sci_sm está instalado
E Ollama está rodando com modelo qwen ou llama carregado
E Java 21+, Node.js e npm estão no PATH
E pdflatex está disponível (MiKTeX)
E tools/apache-jena-fuseki-6.0.0/fuseki-server.bat existe
Quando python gates/gate0_check.py é executado
Então exit code = 0 e "[OK] GATE 0 PASSED" é impresso
```

```gherkin
Dado que qualquer dependência está ausente ou inacessível
Quando python gates/gate0_check.py é executado
Então exit code = 1 e "[FAIL] GATE 0 FAILED" é impresso
E cada check falho é listado com "[FAIL]"
```

---

### RF-02 — Gate 1: Validação dos dados no Fuseki
🟢 **CONFIRMADO** — `gates/gate1_check.py`

**Must**

O gate 1 deve verificar que os três grafos do triplestore estão carregados com volume de triplas acima dos mínimos esperados, e que consultas cross-graph funcionam corretamente.

**Verificações cobertas:**

| Check | Mínimo exigido | Grafo | Confiança |
|---|---|---|---|
| urn:doid triplas | 150.000 | Disease Ontology | 🟢 |
| urn:hpo triplas | 400.000 | Human Phenotype Ontology | 🟢 |
| urn:hpoa triplas | 50.000 | Anotações HPOA | 🟢 |
| Marfan phenotypes | ≥ 5 resultados | HPOA × HPO (OMIM:154700) | 🟢 |
| DOID diseases | ≥ 8.000 subclasses de DOID_4 | DOID | 🟢 |
| DOID hasDbXref MIM/OMIM | ≥ 100 xrefs | DOID | 🟢 |
| Cross-graph DOID ↔ HPOA | ≥ 1 resultado para OMIM:154700 | DOID + HPOA | 🟢 |

**Critérios de Aceitação:**

```gherkin
Dado que Fuseki está acessível em http://localhost:3030/biomedical/sparql
E os três grafos foram carregados via hpoa_to_rdf.py e upload de OWL
Quando python gates/gate1_check.py é executado
Então urn:doid tem >= 150.000 triplas
E urn:hpo tem >= 400.000 triplas
E urn:hpoa tem >= 50.000 triplas
E a query Marfan retorna >= 5 fenótipos
E exit code = 0
```

```gherkin
Dado que Fuseki está offline ou inacessível
Quando python gates/gate1_check.py é executado
Então um erro de conexão é capturado e reportado com "[FAIL]"
E exit code = 1
```

---

### RF-03 — Gate 2: Validação de schemas, gold standard e índice FAISS
🟢 **CONFIRMADO** — `gates/gate2_check.py`

**Must**

O gate 2 deve verificar que os artefatos estáticos do pipeline (schemas, gold standard, índice vetorial) estão presentes, íntegros e funcionais.

**Verificações cobertas:**

| Check | Critério | Confiança |
|---|---|---|
| schemas.json | Cada grafo tem > 0 classes e > 0 predicados | 🟢 |
| Gold standard total | `len(qs) >= 30` ✅ corrigido de 50 para 30 em 2026-05-05 | 🟢 |
| Distribuição de dificuldade | easy >= 10, medium >= 10, hard >= 10 | 🟢 |
| Campos obrigatórios | id, question_pt, question_en, sparql, type, difficulty, expected_min_results | 🟢 |
| IDs únicos | sem duplicatas | 🟢 |
| Sintaxe SPARQL | parseQuery(rdflib) sem exceção para todos os exemplos | 🟢 |
| FAISS index | `index.ntotal >= 30` ✅ corrigido de 50 para 30 em 2026-05-05 | 🟢 |
| Retrieval top-1 | "What symptoms does Marfan syndrome have?" → top-1 deve ser Q01 | 🟡 |

**Critérios de Aceitação:**

```gherkin
Dado que data/schemas.json, data/gold_standard/questions.json e questions.index existem
E o gold standard contém questões com campos obrigatórios e SPARQL válido
Quando python gates/gate2_check.py é executado
Então schemas.json tem classes e predicados para cada grafo
E a retrieval de "Marfan symptoms" retorna Q01 como top-1
E exit code = 0
```

---

### RF-04 — Gate 3: Validação end-to-end do pipeline
🟢 **CONFIRMADO** — `gates/gate3_check.py`

**Must**

O gate 3 deve verificar que o `BioSPARQLPipeline` consegue responder a pelo menos 1 de 3 perguntas de teste contra o Fuseki real (sem mock).

**Perguntas de teste usadas:**

| Pergunta | Dificuldade | Min. resultados exigidos |
|---|---|---|
| "What phenotypes are associated with Marfan syndrome?" | easy | 5 |
| "How many subclasses of cardiovascular disease exist in DOID?" | easy | 1 |
| "Which diseases are associated with the phenotype arachnodactyly?" | medium | 2 |

**Threshold de passagem:** `passed_questions >= 1` (≥ 1/3 com resultados válidos).

**Critérios de Aceitação:**

```gherkin
Dado que Fuseki está rodando com dados carregados (gate1 passou)
E LM Studio está rodando com modelo disponível
E o pipeline instancia sem exceção
Quando python gates/gate3_check.py é executado
Então ao menos 1 das 3 perguntas retorna count >= min_results
E exit code = 0
```

```gherkin
Dado que o pipeline lança uma exceção não tratada em qualquer pergunta
Quando gates/gate3_check.py é executado
Então a exceção é capturada e reportada como "[FAIL]"
E as outras perguntas continuam sendo testadas
E exit code depende do total de passagens
```

---

### RF-05 — Gate 6: Validação da interface API + frontend
🟢 **CONFIRMADO** — `gates/gate6_check.py`

**Must**

O gate 6 deve verificar que o servidor FastAPI importa sem erros, que os endpoints `/api/health` e `/api/ask` respondem corretamente via `TestClient`, e que o frontend React faz build com sucesso.

**Verificações cobertas:**

| Check | Critério | Confiança |
|---|---|---|
| FastAPI importa | `import fastapi` sem ImportError | 🟢 |
| Uvicorn importa | `import uvicorn` sem ImportError | 🟢 |
| API importa | `from src.api.server import app` sem exceção | 🟢 |
| Health endpoint | `GET /api/health` → 200 OK | 🟢 |
| Ask endpoint | `POST /api/ask {"question":"..."}` → 200 OK | 🟢 |
| XAI sparql | `xai.sparql` não-vazio | 🟢 |
| XAI timing | `xai.timing.total_s` presente | 🟢 |
| XAI entities | `xai.entities` é lista | 🟢 |
| XAI validation | `xai.validation.valid` presente | 🟢 |
| Empty question → 400 | `POST /api/ask {"question":""}` → HTTP 400 | 🟢 |
| Frontend build | `npx vite build` com exit code 0 | 🟢 |

**Critérios de Aceitação:**

```gherkin
Dado que FastAPI, Uvicorn e dependências estão instalados
E src/api/server.py importa sem erro
Quando python gates/gate6_check.py é executado via TestClient (sem servidor real)
Então /api/health retorna 200 com {"status": "ok"}
E /api/ask retorna 200 com campos XAI completos
E /api/ask com question vazia retorna 400
E frontend React faz build sem erros
E exit code = 0
```

---

### RF-06 — Execução sequencial independente
🟢 **CONFIRMADO** — design dos scripts (sem dependência de estado compartilhado)

**Should**

Cada gate deve poder ser executado individualmente sem depender de artefatos gerados por outros gates. A sequência recomendada (0→1→2→3→6) é convenção, não obrigação técnica.

**Critérios de Aceitação:**

```gherkin
Dado que o ambiente está configurado para gate1
Quando python gates/gate1_check.py é executado isoladamente (sem ter rodado gate0)
Então gate1 executa e reporta resultado independentemente
```

---

### RF-07 — Saída padronizada para automação
🟢 **CONFIRMADO** — todos os gates usam `sys.exit(0)` / `sys.exit(1)` e "[OK]"/"[FAIL]"

**Must**

Todos os gates devem terminar com `sys.exit(0)` em caso de sucesso e `sys.exit(1)` em caso de falha, e usar apenas ASCII no output (`[OK]`, `[FAIL]`) para compatibilidade com terminais Windows cp1252.

---

## Requisitos Não Funcionais

### RNF-01 — Timeout de verificações externas
🟢 **CONFIRMADO** — `gate0_check.py` usa `timeout=5` para Ollama e `timeout=10` para subprocess

Verificações de serviços externos devem ter timeout para não bloquear a execução.

### RNF-02 — Compatibilidade de output com Windows cp1252
🟢 **CONFIRMADO** — todos os prints usam apenas ASCII `[OK]` / `[FAIL]`

Nenhum gate deve imprimir caracteres UTF-8 fora do plano ASCII (sem emojis, sem acentos em saídas de status).

### RNF-03 — Sem efeitos colaterais
🟡 **INFERIDO** — gates apenas leem estado, não modificam dados

Os scripts de gate não devem modificar dados, apagar arquivos, ou alterar estado do Fuseki. São somente de leitura/verificação.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Gate 0 — ambiente | **Must** | Pré-condição para tudo; falha aqui bloqueia todo desenvolvimento |
| RF-02 Gate 1 — dados Fuseki | **Must** | Sem dados, pipeline e avaliação falham silenciosamente |
| RF-03 Gate 2 — schemas/gold/FAISS | **Must** | Artefatos estáticos críticos para few-shot e avaliação |
| RF-04 Gate 3 — pipeline E2E | **Must** | Única verificação de integração real (LLM + Fuseki) |
| RF-05 Gate 6 — API/frontend | **Must** | Valida entregável final do sistema |
| RF-06 Execução independente | **Should** | Facilita debugging mas não é bloqueante |
| RF-07 Saída padronizada ASCII | **Must** | Compatibilidade Windows + automação CI |

---

## Dependências

| Dependência | Gate | Obrigatória |
|---|---|---|
| Apache Jena Fuseki em `:3030` | Gate 1, Gate 3 | Sim |
| LM Studio ou backend LLM | Gate 3 | Sim |
| `data/schemas.json` | Gate 2 | Sim |
| `data/gold_standard/questions.json` | Gate 2, Gate 3 | Sim |
| `data/gold_standard/questions.index` | Gate 2 | Sim |
| `src/pipeline/nl_to_sparql.py` | Gate 3 | Sim |
| `src/api/server.py` | Gate 6 | Sim |
| `frontend/package.json` | Gate 6 | Sim |
| Java 21+ | Gate 0 | Sim |
| Node.js + npm | Gate 0, Gate 6 | Sim |
| pdflatex (MiKTeX) | Gate 0 | Sim |

---

## Rastreabilidade de Código

| Arquivo | Responsabilidade | Cobertura |
|---|---|---|
| `gates/gate0_check.py` | Validação de ambiente (libs, Java, Node, Fuseki binary) | 🟢 |
| `gates/gate1_check.py` | Validação de dados no Fuseki (triplas, queries cross-graph) | 🟢 |
| `gates/gate2_check.py` | Validação de schemas, gold standard e índice FAISS | 🟢 |
| `gates/gate3_check.py` | Validação end-to-end do pipeline (3 perguntas de teste) | 🟢 |
| `gates/gate6_check.py` | Validação da interface API + frontend (TestClient + vite build) | 🟢 |
