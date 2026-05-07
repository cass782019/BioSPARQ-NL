# Requisitos — ner

> Unit: `src/pipeline/ner/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `ner` |
| Caminho legado | `src/pipeline/ner/base.py`, `factory.py`, `scispacy_backend.py`, `llm_backend.py`, `src/pipeline/entity_linker.py` |
| Responsabilidade | Extração plugável de entidades biomédicas (doenças e fenótipos) e resolução a IDs ontológicos (CURIEs DOID/HP) |
| Complexidade | 🟡 Média |

---

## Requisitos Funcionais

### RF-01 — Extração de entidades biomédicas de texto livre
🟢 **CONFIRMADO** — `scispacy_backend.py:ScispaCyBackend.extract()`

**Must**

Dado um texto em linguagem natural (pergunta do usuário), o módulo NER deve identificar spans de texto que representem doenças ou fenótipos humanos.

**Critérios de Aceitação:**

```gherkin
Dado o texto "Quais fenótipos estão associados ao mal de Parkinson?"
Quando ScispaCyBackend.extract(texto) é chamado
Então retorna lista com ao menos uma Entity com text contendo "Parkinson"
E cada Entity tem campos text, start, end, type, ontology_ids, scores, backend preenchidos
```

```gherkin
Dado o texto "Qual é a definição de febre?"
Quando extract() é chamado
Então "febre" NÃO é retornado como entidade (span < 4 chars ou em stoplist)
```

---

### RF-02 — Resolução de entidades para CURIEs ontológicos (DOID/HP)
🟢 **CONFIRMADO** — `scispacy_backend.py:_resolve()`

**Must**

Cada entidade extraída deve ter seus `ontology_ids` preenchidos com CURIEs válidos do triplestore (ex: `DOID:14330`, `HP:0001250`).

**Critérios de Aceitação:**

```gherkin
Dado que "Parkinson disease" foi extraído como entidade
Quando _resolve("Parkinson disease") é chamado
Então retorna dict com curie="DOID:14330", uri=<URI completa>, graph="urn:doid"
E o CURIE é verificado via SPARQL no Fuseki (rdfs:label LCASE match)
```

```gherkin
Dado que a resolução SPARQL não encontra correspondência
Quando _resolve() é chamado
Então tenta Gilda como fallback: gilda.ground(entity_text) com score >= 0.5
E se Gilda também falhar, retorna None (entidade sem ID)
```

---

### RF-03 — Filtragem de spans ruidosos
🟢 **CONFIRMADO** — `scispacy_backend.py:_is_noise()`

**Must**

Spans que não representam entidades biomédicas válidas devem ser descartados antes da resolução.

**Critérios de Aceitação:**

```gherkin
Dado um span com menos de 4 caracteres (ex: "de", "ou")
Quando _is_noise(span) é avaliado
Então retorna True e o span é descartado

Dado um span com menos de 50% de caracteres alfabéticos (ex: "123a")
Quando _is_noise(span) é avaliado
Então retorna True e o span é descartado

Dado um span que consta na stoplist PT+EN (~80 termos, ex: "doença", "disease", "patient")
Quando _is_noise(span) é avaliado
Então retorna True e o span é descartado
```

---

### RF-04 — Deduplicação de spans sobrepostos
🟢 **CONFIRMADO** — `base.py:merge_overlaps()`

**Must**

Quando dois spans se sobrepõem (ex: "Parkinson" e "mal de Parkinson"), apenas o de maior score deve ser mantido.

**Critérios de Aceitação:**

```gherkin
Dado duas entidades com spans sobrepostos: [5,14] score=0.8 e [0,18] score=0.9
Quando merge_overlaps([e1, e2]) é chamado
Então retorna apenas [e2] (maior score)
E e1 é descartado
```

---

### RF-05 — Backend NER plugável via factory
🟢 **CONFIRMADO** — `ner/factory.py:get_backend()`

**Must**

O backend NER deve ser selecionável via configuração sem alterar o código do pipeline. Interface comum: `extract(text: str) → list[Entity]`.

**Backends disponíveis:**
- `"scispacy"` — padrão; usa modelo `en_ner_bc5cdr_md`
- `"llm"` — usa LLM para extrair spans; grounding via Gilda
- `"gilda"` — resolução apenas (sem extração de spans)

**Critérios de Aceitação:**

```gherkin
Dado BIOSPARQL_NER_BACKEND="scispacy" (env var ou config)
Quando get_backend("scispacy") é chamado duas vezes
Então retorna a mesma instância (lru_cache singleton)
E a instância é ScispaCyBackend
```

---

### RF-06 — Graceful fallback quando NER falha
🟢 **CONFIRMADO** — `nl_to_sparql.py:__init__()` — try/except no init do EntityLinker

**Must**

Se o backend NER falhar ao inicializar (ex: modelo scispaCy não instalado), o pipeline deve continuar sem extração de entidades — não deve lançar exceção fatal.

**Critérios de Aceitação:**

```gherkin
Dado que o modelo en_ner_bc5cdr_md não está instalado
Quando BioSPARQLPipeline é inicializado
Então entity_linker = None (sem exceção)
E pipeline.run() funciona retornando entities=[] no resultado
```

---

### RF-07 — LLMBackend não alucina IDs ontológicos
🟢 **CONFIRMADO** — `ner/llm_backend.py` — RN-12

**Should**

No backend LLM, o LLM extrai apenas texto (spans + tipo). A resolução para CURIEs é sempre delegada ao Gilda deterministicamente, nunca ao LLM diretamente.

**Critérios de Aceitação:**

```gherkin
Dado o texto "febre amarela"
Quando LLMBackend.extract(texto) é chamado
Então o LLM retorna apenas spans como [{"text": "febre amarela", "type": "DISEASE"}]
E Gilda.ground("febre amarela") resolve o CURIE (ou retorna None se score < 0.5)
E nenhum CURIE é gerado diretamente pelo LLM
```

---

## Requisitos Não Funcionais

### RNF-01 — Singleton via lru_cache
🟢 **CONFIRMADO** — `factory.py:get_backend()` decorado com `@lru_cache`

O backend NER deve ser instanciado apenas uma vez por processo. Carregamento de modelos spaCy (~200MB) ocorre apenas na primeira chamada.

### RNF-02 — Latência de extração
🟡 **INFERIDO** — sem medição explícita no código

Extração NER deve ser concluída em tempo compatível com uso interativo. scispaCy com modelo pré-carregado típico: < 100ms por texto curto.

### RNF-03 — Resolução SPARQL com retry
🟢 **CONFIRMADO** — `scispacy_backend.py:_resolve()` — retry exponencial herdado de utils

Resolução de entidades via SPARQL usa retry exponencial (3 tentativas, backoff 2^n) para tolerar instabilidades do Fuseki.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Extração de entidades | **Must** | Sem entidades, prompt não tem ancoragem ontológica |
| RF-02 Resolução para CURIEs | **Must** | IDs ontológicos guiam o LLM para termos corretos |
| RF-03 Filtragem de ruído | **Must** | Sem filtro, SPARQL de resolução é chamado para termos triviais |
| RF-04 Deduplicação de spans | **Must** | Spans duplicados poluem o prompt com CURIEs redundantes |
| RF-05 Backend plugável | **Should** | Permite experimentos com diferentes NER backends |
| RF-06 Graceful fallback | **Must** | Pipeline não pode quebrar em setup sem scispaCy |
| RF-07 LLM não alucina IDs | **Must** | Alucinação de CURIEs invalidaria as queries geradas |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| scispaCy `en_ner_bc5cdr_md` | Modelo Python | Não (graceful fallback) |
| Apache Jena Fuseki em `:3030` | Serviço externo | Não (fallback para Gilda) |
| Gilda (Python package) | Biblioteca | Não (fallback para sem ID) |
| `BIOSPARQL_NER_BACKEND` env var | Configuração | Não (padrão: `"scispacy"`) |
