# User Stories — Fluxo: Configuração e Carga de Ontologias (Setup)

> Gerado pelo Redator (Writer) em 2026-05-04 | doc_level: detalhado
> Ator principal: Pesquisador/administrador configurando o ambiente pela primeira vez (ou após reset)

---

## Contexto

Antes de qualquer consulta ou avaliação, o ambiente BioSPARQL-NL precisa ser preparado: ontologias carregadas no Fuseki, anotações HPOA convertidas para RDF, schema ontológico extraído, índice FAISS construído e gates de validação executados em sequência. Este fluxo é executado uma única vez no setup inicial e repetido apenas após reset de dados ou atualização de ontologias.

**Ordem recomendada:** Gate 0 → utilitários (HPOA, schema, FAISS) → Gate 1 → Gate 2 → Gate 3 → Gate 6

---

## US-01 — Validar o ambiente de desenvolvimento antes de começar (Gate 0)

**Como** pesquisador,
**quero** verificar que todas as dependências do ambiente estão instaladas antes de qualquer outra operação,
**para** detectar problemas de configuração cedo e receber uma lista clara do que está faltando.

### Critérios de Aceitação

```gherkin
Dado que o venv do projeto está ativo com todas as libs instaladas
E scispaCy en_core_sci_sm está instalado
E Java 21+, Node.js, npm e pdflatex (MiKTeX) estão no PATH
E tools/apache-jena-fuseki-6.0.0/fuseki-server.bat existe
Quando python gates/gate0_check.py é executado
Então cada check imprime "[OK] <nome do check>"
E a saída final é "[OK] GATE 0 PASSED"
E exit code = 0
```

```gherkin
Dado que pdflatex não está no PATH
Quando python gates/gate0_check.py é executado
Então a linha do pdflatex imprime "[FAIL] pdflatex not found"
E a saída final é "[FAIL] GATE 0 FAILED"
E exit code = 1
E todos os outros checks ainda são executados e reportados
```

**Nota:** O check de Ollama no gate0 está desatualizado (sistema migrou para LM Studio), mas ainda executa sem bloquear o gate.

**Rastreabilidade:** 🟢 `gates/gate0_check.py`; 🟡 check Ollama — legado, LM Studio não é verificado no gate0

---

## US-02 — Converter anotações HPOA para RDF antes de carregar no Fuseki

**Como** pesquisador,
**quero** converter o arquivo `phenotype.hpoa` (TSV) para formato Turtle (RDF),
**para** que as anotações doença→fenótipo possam ser carregadas como grafo `urn:hpoa` no Fuseki.

### Critérios de Aceitação

```gherkin
Dado que data/annotations/phenotype.hpoa existe com anotações válidas
Quando hpoa_to_rdf.py é executado
Então data/annotations/hpoa.ttl é gerado
E cada anotação positiva gera 4 triplas: rdf:type, rdfs:label, hpoa:has_phenotype, hpoa:source_id
E linhas com qualifier="NOT" são descartadas (associações negativas ignoradas)
E linhas de comentário (#) e o cabeçalho são ignorados
E hpoa.ttl é parseável por rdflib sem erro
```

```gherkin
Dado uma linha com db_id="OMIM:154700" no phenotype.hpoa
Quando hpoa_to_rdf.py processa essa linha
Então a tripla hpoa:source_id tem o literal "OMIM:154700" (não URI)
E a URI da doença é <http://example.org/disease/OMIM_154700>
E esse formato é compatível com JOIN DOID↔HPOA via BIND(REPLACE(?xref, "^MIM:", "OMIM:"))
```

**Rastreabilidade:** 🟢 `src/utils/hpoa_to_rdf.py`; 🟢 RN-01 (incompatibilidade MIM/OMIM); 🟢 RN-05 (qualifier=NOT descartado)

---

## US-03 — Carregar os três grafos ontológicos no Fuseki

**Como** pesquisador,
**quero** carregar doid.owl, hp.owl e hpoa.ttl no triplestore Fuseki como grafos nomeados,
**para** que o pipeline possa executar queries SPARQL contra os três grafos.

### Critérios de Aceitação

```gherkin
Dado que Fuseki está rodando em localhost:3030 com dataset /biomedical (TDB2)
E data/ontologies/doid.owl, hp.owl e data/annotations/hpoa.ttl existem
Quando os três arquivos são carregados via HTTP PUT/POST no Fuseki
  (ex: curl -X PUT --data-binary @doid.owl -H "Content-Type: text/turtle" http://localhost:3030/biomedical/data?graph=urn:doid)
Então o grafo urn:doid contém >= 150.000 triplas
E o grafo urn:hpo contém >= 400.000 triplas
E o grafo urn:hpoa contém >= 50.000 triplas
```

**Rastreabilidade:** 🟢 `CLAUDE.md` — comando de startup Fuseki; 🟢 `gates/gate1_check.py` — mínimos validados

---

## US-04 — Validar a integridade dos dados no Fuseki (Gate 1)

**Como** pesquisador,
**quero** verificar que os grafos foram carregados corretamente e que queries cross-graph funcionam,
**para** garantir que o pipeline terá dados corretos antes de rodar qualquer avaliação.

### Critérios de Aceitação

```gherkin
Dado que Fuseki está rodando com os três grafos carregados
Quando python gates/gate1_check.py é executado
Então urn:doid tem >= 150.000 triplas    → "[OK] DOID graph: 302XXX triples"
E urn:hpo tem >= 400.000 triplas         → "[OK] HPO graph: 908XXX triples"
E urn:hpoa tem >= 50.000 triplas         → "[OK] HPOA graph: 320XXX triples"
E a query de fenótipos da Síndrome de Marfan (OMIM:154700) retorna >= 5 resultados
E a query cross-graph DOID↔HPOA retorna >= 1 resultado
E exit code = 0
```

```gherkin
Dado que o grafo urn:hpoa tem < 50.000 triplas (carga incompleta)
Quando gate1_check.py é executado
Então "[FAIL] HPOA graph: only XXXXX triples (expected >= 50000)" é impresso
E exit code = 1
```

**Rastreabilidade:** 🟢 `gates/gate1_check.py` — thresholds: doid≥150k, hpo≥400k, hpoa≥50k, Marfan≥5, cross-graph≥1

---

## US-05 — Extrair schema ontológico dos grafos via introspecção SPARQL

**Como** pesquisador,
**quero** gerar o arquivo `data/schemas.json` com as classes e predicados de cada grafo,
**para** que o SchemaValidator do pipeline possa validar queries antes de enviá-las ao Fuseki.

### Critérios de Aceitação

```gherkin
Dado que Fuseki está rodando com os grafos carregados
Quando schema_extractor.py é executado
Então data/schemas.json é gerado com estrutura:
  {"urn:doid": {"classes": [...], "predicates": [...]},
   "urn:hpo":  {"classes": [...], "predicates": [...]},
   "urn:hpoa": {"classes": [...], "predicates": [...]}}
E cada grafo tem >= 1 classe e >= 1 predicado
E o JSON é válido e parseável
```

```gherkin
Dado que uma query GROUP_CONCAT falha por timeout no Fuseki
Quando schema_extractor.py tenta
Então retry exponencial é executado (até 3 tentativas com sleep(2^n segundos))
E após 3 falhas consecutivas, uma exceção descritiva é lançada
```

**Rastreabilidade:** 🟢 `src/utils/schema_extractor.py`; 🟢 ADR-004 (introspecção SPARQL em vez de ShEx)

---

## US-06 — Construir o índice FAISS para recuperação few-shot

**Como** pesquisador,
**quero** gerar o índice vetorial das 30 questões do gold standard,
**para** que o pipeline possa recuperar exemplos similares e melhorar a geração SPARQL.

### Critérios de Aceitação

```gherkin
Dado que data/gold_standard/questions.json contém 30 questões
E sentence-transformers all-MiniLM-L6-v2 está disponível (HuggingFace cache ou offline)
Quando index_builder.py é executado
Então data/gold_standard/questions.index é gerado
E faiss.read_index("questions.index").ntotal == 30
E os vetores têm dimensão 384 e norma L2 = 1.0 (normalizados)
E uma busca de teste retorna os k vizinhos mais próximos corretamente
```

```gherkin
Dado que questions.index está ausente no momento de inicialização do pipeline
Quando BioSPARQLPipeline.__init__() é chamado
Então o pipeline inicializa em modo zero-shot (sem few-shot)
E retrieve_examples() retorna [] sem lançar exceção
```

**Rastreabilidade:** 🟢 `src/utils/index_builder.py`; 🟢 `src/pipeline/nl_to_sparql.py` — graceful fallback sem FAISS index (RF-09)

---

## US-07 — Validar schemas, gold standard e índice FAISS (Gate 2)

**Como** pesquisador,
**quero** verificar a integridade dos artefatos estáticos do pipeline,
**para** garantir que schemas.json, questions.json e questions.index estão corretos antes de rodar avaliações.

### Critérios de Aceitação

```gherkin
Dado que data/schemas.json, data/gold_standard/questions.json e questions.index existem
Quando python gates/gate2_check.py é executado
Então schemas.json tem classes e predicados para cada um dos três grafos
E questions.json tem questões com todos os campos obrigatórios (id, question_pt, question_en, sparql, difficulty, expected_min_results)
E IDs das questões são únicos
E todas as queries SPARQL do gold standard são sintáticamente válidas (parseQuery sem exceção)
E a retrieval FAISS de "What symptoms does Marfan syndrome have?" retorna Q01 como top-1
E exit code = 0
```

**Nota:** O gate2 tem dois checks com limiares errados (`len(qs) >= 50` e `index.ntotal >= 50`) que sempre falham — o gold standard tem 30, não 50. Isso é um bug conhecido documentado nas specs.

**Rastreabilidade:** 🟢 `gates/gate2_check.py`; 🔴 bug: thresholds `>= 50` incorretos (gold standard tem 30)

---

## US-08 — Validar o pipeline end-to-end com perguntas reais (Gate 3)

**Como** pesquisador,
**quero** verificar que o BioSPARQLPipeline consegue responder ao menos 1 de 3 perguntas de teste,
**para** confirmar que LLM + Fuseki + pipeline estão integrados corretamente antes de rodar a avaliação completa.

### Critérios de Aceitação

```gherkin
Dado que Fuseki está rodando com dados carregados (gate1 passou)
E LM Studio está rodando com modelo disponível em localhost:1234
E o pipeline instancia sem exceção
Quando python gates/gate3_check.py é executado
Então as três perguntas são testadas:
  1. "What phenotypes are associated with Marfan syndrome?" → min 5 resultados
  2. "How many subclasses of cardiovascular disease exist in DOID?" → min 1 resultado
  3. "Which diseases are associated with the phenotype arachnodactyly?" → min 2 resultados
E ao menos 1 das 3 retorna count >= min_results
E exit code = 0
```

```gherkin
Dado que o pipeline lança exceção em uma pergunta (ex: LLMConnectionError)
Quando gate3_check.py trata a exceção
Então a exceção é capturada e reportada como "[FAIL] Q<n>: <mensagem>"
E as demais perguntas continuam sendo testadas (sem abort)
E o threshold de passagem (>= 1/3) ainda determina o exit code
```

**Rastreabilidade:** 🟢 `gates/gate3_check.py`; 🟢 threshold: `passed_questions >= 1`

---

## US-09 — Validar a interface API e o build do frontend (Gate 6)

**Como** pesquisador,
**quero** verificar que a API FastAPI e o frontend React estão funcionais,
**para** confirmar que o entregável final do sistema está pronto para uso e demonstração.

### Critérios de Aceitação

```gherkin
Dado que FastAPI, Uvicorn e React/Vite estão instalados
E src/api/server.py importa sem erro
Quando python gates/gate6_check.py é executado
Então GET /health retorna 200 com {"status": "ok"}
E POST /api/ask retorna 200 com xai.sparql não-vazio, xai.timing presente, xai.entities como lista
E POST /api/ask com question="" retorna HTTP 400
E npx vite build (em frontend/) termina com exit code 0
E "[OK] GATE 6 PASSED" é impresso
E exit code = 0
```

**Nota:** Gate 6 usa `TestClient` do FastAPI (sem servidor real) — não requer Fuseki nem LM Studio rodando.

**Rastreabilidade:** 🟢 `gates/gate6_check.py`; 🟢 `src/api/server.py`

---

## Sequência completa de setup (ordem recomendada)

```
Passo 1 — Verificar ambiente
  python gates/gate0_check.py
  → exit 0 antes de continuar

Passo 2 — Iniciar o Fuseki
  java -Xmx2G -jar tools/apache-jena-fuseki-6.0.0/fuseki-server.jar \
    --tdb2 --loc=fuseki-db --update /biomedical

Passo 3 — Preparar dados
  3a. Converter HPOA:
      PYTHONPATH=. .venv/Scripts/python.exe -m src.utils.hpoa_to_rdf
  3b. Carregar ontologias no Fuseki (doid.owl, hp.owl, hpoa.ttl via HTTP PUT)
  3c. Extrair schema:
      PYTHONPATH=. .venv/Scripts/python.exe -m src.utils.schema_extractor
  3d. Construir índice FAISS:
      PYTHONPATH=. .venv/Scripts/python.exe -m src.utils.index_builder

Passo 4 — Validar dados
  python gates/gate1_check.py   → verifica triplas e cross-graph
  python gates/gate2_check.py   → verifica schemas, gold standard, FAISS
  [nota: gate2 tem bug nos thresholds >= 50 — gold standard tem 30]

Passo 5 — Validar pipeline E2E
  python gates/gate3_check.py   → requer LM Studio rodando com modelo

Passo 6 — Validar API + frontend
  python gates/gate6_check.py   → usa TestClient (sem serviços externos)

Passo 7 — Iniciar serviços de desenvolvimento
  FastAPI:   PYTHONPATH=. .venv/Scripts/python.exe -m uvicorn src.api.server:app --port 8000
  Frontend:  cd frontend && npx vite dev   → http://localhost:5173
```

---

## Bugs conhecidos no fluxo de setup

| Local | Problema | Confiança |
|---|---|---|
| `gate0_check.py` — check Ollama | Verifica Ollama em vez de LM Studio (sistema migrou) | 🟢 CONFIRMADO — legado documentado |
| `gate2_check.py` — `len(qs) >= 50` | Gold standard tem 30 questões, não 50 — sempre falha | 🔴 LACUNA — bug confirmado nas specs |
| `gate2_check.py` — `index.ntotal >= 50` | FAISS tem 30 vetores, não 50 — sempre falha | 🔴 LACUNA — bug confirmado nas specs |
