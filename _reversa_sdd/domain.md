# Domínio — BioSPARQL-NL

> Gerado pelo Detetive em 2026-05-04 | doc_level: detalhado

---

## Glossário do Domínio

| Termo | Definição | Confiança |
|---|---|---|
| **NL→SPARQL** | Tradução de pergunta em linguagem natural para query SPARQL executável | 🟢 CONFIRMADO |
| **Ontologia** | Vocabulário formal de conceitos e relações num domínio (ex: doenças, fenótipos) | 🟢 CONFIRMADO |
| **DOID** | Disease Ontology — vocabulário de doenças humanas com ~302K triplas RDF | 🟢 CONFIRMADO |
| **HPO** | Human Phenotype Ontology — vocabulário de fenótipos humanos com ~908K triplas | 🟢 CONFIRMADO |
| **HPOA** | HP Ontology Annotations — anotações que ligam doenças a fenótipos (~320K triplas) | 🟢 CONFIRMADO |
| **Triplestore** | Banco de dados RDF (Apache Jena Fuseki TDB2) que armazena e responde queries SPARQL | 🟢 CONFIRMADO |
| **Grafo nomeado** | Subconjunto de triplas identificado por URI: `urn:doid`, `urn:hpo`, `urn:hpoa` | 🟢 CONFIRMADO |
| **SPARQL** | Linguagem de query para grafos RDF (W3C Recommendation) | 🟢 CONFIRMADO |
| **NER** | Named Entity Recognition — identificação automática de entidades em texto (doenças, fenótipos) | 🟢 CONFIRMADO |
| **Few-shot RAG** | Recuperação de exemplos similares (FAISS) para incluir no prompt do LLM | 🟢 CONFIRMADO |
| **Loop de autocorreção** | Re-prompt iterativo do LLM com feedback de erros de validação | 🟢 CONFIRMADO |
| **Semantic retry** | Re-prompt especial quando query é válida mas retorna 0 resultados | 🟢 CONFIRMADO |
| **Ablação** | Experimento que desativa componentes individuais do pipeline para medir contribuição | 🟢 CONFIRMADO |
| **Gold standard** | Conjunto de 30 questões anotadas manualmente (10 easy / 10 medium / 10 hard) | 🟢 CONFIRMADO |
| **XAI** | Explainable AI — painel que mostra entidades detectadas, SPARQL gerado, timing e validação | 🟢 CONFIRMADO |
| **CURIE** | Compact URI (ex: `DOID:14330`, `HP:0001250`) — forma abreviada de URIs OBO | 🟢 CONFIRMADO |
| **MIM** | Prefixo usado pelo DOID em `oboInOwl:hasDbXref` para referências OMIM (ex: `"MIM:154700"`) | 🟢 CONFIRMADO |
| **OMIM** | Prefixo usado pelo HPOA em `hpoa:source_id` (ex: `"OMIM:154700"`) — incompatível com MIM | 🟢 CONFIRMADO |
| **JOIN cross-graph** | Query que une triplas de `urn:doid` e `urn:hpoa` via BIND+REPLACE para converter MIM→OMIM | 🟢 CONFIRMADO |
| **Grounding** | Resolução de uma span de texto para um ID ontológico canônico (CURIE) | 🟢 CONFIRMADO |
| **Span** | Segmento de texto identificado como entidade pelo NER (início/fim em char offsets) | 🟢 CONFIRMADO |
| **Backend LLM** | Classe plugável que fornece geração de texto (LMStudio, Anthropic API, Claude CLI) | 🟢 CONFIRMADO |
| **Pós-processamento** | Correções regex aplicadas ao SPARQL gerado antes da validação | 🟢 CONFIRMADO |
| **Gate** | Script de validação de pré-condições por fase do projeto (gate0–gate6) | 🟢 CONFIRMADO |

---

## Regras de Negócio Implícitas

### RN-01 — Incompatibilidade MIM / OMIM (JOIN cross-graph)
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:build_prompt()` + `SEMANTIC_RETRY_FEEDBACK`

O DOID usa prefixo `MIM:` em `oboInOwl:hasDbXref` (`"MIM:154700"`), enquanto o HPOA usa `OMIM:` em `hpoa:source_id` (`"OMIM:154700"`). Qualquer query que una os dois grafos **deve** converter o prefixo com:

```sparql
BIND(REPLACE(STR(?mim), "^MIM:", "OMIM:") AS ?oid)
```

Abordagem `STRAFTER` foi testada e retornou 0 resultados — descartada (ADR-001).

---

### RN-02 — Labels em INGLÊS nos FILTER SPARQL
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:build_prompt()` (system prompt, regra explícita)

Embora as questões sejam formuladas em português, todos os `FILTER(CONTAINS(LCASE(?label), "..."))` devem usar termos em inglês, porque os labels das ontologias DOID, HPO e HPOA estão em inglês. O sistema prompt instrui explicitamente o LLM a traduzir PT→EN (febre→fever, dor→pain, hipertensão→hypertension).

---

### RN-03 — Separação de responsabilidades por grafo nomeado
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:build_prompt()` (system prompt, regras 2 e 4)

| Informação | Grafo correto |
|---|---|
| Definições e hierarquia de doenças | `urn:doid` |
| Labels e hierarquia de fenótipos | `urn:hpo` |
| Anotações doença→fenótipo (`hpoa:has_phenotype`) | `urn:hpoa` |
| Labels de doenças no contexto de anotações | `urn:hpoa` (via `rdfs:label`) |

---

### RN-04 — `doid:` e `hpo:` NÃO são prefixos válidos
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:_fix_common_errors()` (passos 4 e 6)

Os LLMs frequentemente alucinam os prefixos `doid:` e `hpo:` como namespaces, mas eles não existem no triplestore. O pós-processamento remove automaticamente declarações PREFIX errôneas com URNs de grafo e substitui usos diretos:
- `doid:Disease` → `obo:DOID_4`
- `hpo:HumanPhenotype` → `obo:HP_0000118`

---

### RN-05 — Qualificador "NOT" descartado na conversão HPOA
🟢 **CONFIRMADO** — `src/utils/hpoa_to_rdf.py:convert_hpoa_to_rdf()`

Linhas do TSV `phenotype.hpoa` com `qualifier=NOT` (associação negativa) são descartadas durante a conversão para Turtle. O triplestore contém apenas associações positivas doença→fenótipo.

---

### RN-06 — Validação permissiva quando schema ausente
🟢 **CONFIRMADO** — `src/pipeline/sparql_validator.py:SchemaValidator.__init__()`

Se `data/schemas.json` estiver ausente ou corrompido, o `SchemaValidator` entra em modo permissivo: faz apenas checagem de sintaxe e operações unsafe (DELETE/INSERT), ignorando validação de classes/predicados. O pipeline continua funcionando mas sem a camada de schema.

---

### RN-07 — Última tentativa executa mesmo com query inválida
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:run()` (linha ~463)

Quando esgotam as tentativas e a query ainda é inválida, o pipeline a executa mesmo assim no Fuseki, em vez de retornar erro imediato. Isso permite recuperar resultados parciais de queries com warnings não-fatais.

---

### RN-08 — Semantic retry dispara apenas uma vez por pergunta
🟢 **CONFIRMADO** — `src/pipeline/nl_to_sparql.py:run()` (flag `semantic_retry_used`)

O semantic retry (re-prompt especial para 0 resultados) é disparado no máximo uma vez por execução, mesmo que a segunda tentativa também retorne 0 resultados. Evita loop infinito de re-prompts.

---

### RN-09 — Modelos > 20B requerem verificação de memória prévia
🟡 **INFERIDO** — `CLAUDE.md` (regra documentada, não enforçada em código)

Devido ao hardware disponível (8GB VRAM + 16GB RAM), modelos com mais de 20B parâmetros não devem ser avaliados sem verificação manual de memória. A regra está documentada mas não há guard em código.

---

### RN-10 — Gold standard imutável com 30 questões
🟢 **CONFIRMADO** — `data/gold_standard/questions.json` + `CLAUDE.md`

O conjunto de avaliação tem exatamente 30 questões distribuídas em 3 dificuldades (10 easy / 10 medium / 10 hard). Não deve ser reduzido para garantir comparabilidade entre modelos e cenários de ablação.

---

### RN-11 — NER por scispaCy filtra ruídos por lista de stopwords + ratio alfa
🟢 **CONFIRMADO** — `src/pipeline/ner/scispacy_backend.py:_is_noise()`

Spans com menos de 4 caracteres, razão de caracteres alfabéticos abaixo de 50%, ou que constam em lista de ~80 stopwords PT+EN são descartados antes do grounding. Isso evita resolução SPARQL desnecessária para termos irrelevantes.

---

### RN-12 — LLM-as-NER não alucina IDs — apenas extrai texto
🟢 **CONFIRMADO** — `src/pipeline/ner/llm_backend.py`

No backend `LLMBackend`, o LLM é responsável apenas por identificar o texto das entidades (spans + tipo). A resolução para CURIEs é feita deterministicamente via Gilda (`gilda.ground(span_text)`) com score mínimo de 0.5. Isso elimina alucinação de IDs ontológicos.

---

## Invariantes do Sistema

| Invariante | Garantia | Confiança |
|---|---|---|
| Pipeline nunca gera queries DELETE/INSERT | Bloqueado por `SchemaValidator` (`UNSAFE_OPERATION`) | 🟢 CONFIRMADO |
| Grafos válidos fixos: `urn:doid`, `urn:hpo`, `urn:hpoa` | Hardcoded em `SchemaValidator.valid_graphs` | 🟢 CONFIRMADO |
| Pipeline singleton por processo | `get_pipeline()` usa global com lazy-init | 🟢 CONFIRMADO |
| NER com graceful fallback | Se scispaCy falhar, pipeline continua sem entidades | 🟢 CONFIRMADO |
| FAISS com graceful fallback | Se índice ausente, pipeline usa zero-shot | 🟢 CONFIRMADO |
| Pós-processamento é idempotente | Regex são não-destrutivas e aplicadas sequencialmente | 🟡 INFERIDO |
