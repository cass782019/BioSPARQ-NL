# Spec Impact Matrix — BioSPARQL-NL

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Como ler esta matriz

Cada linha é um **componente que sofre impacto**. Cada coluna é um **componente que causa o impacto**.
- 🔴 **Alto** — mudança quase sempre quebra o componente afetado
- 🟡 **Médio** — mudança pode exigir adaptação
- 🟢 **Baixo** — dependência fraca, impacto isolado
- `—` — sem dependência direta

---

## Matriz de Impacto entre Componentes

| Afetado ↓ \ Causa → | nl_to_sparql | llm_backends | sparql_validator | entity_linker + NER | FAISS Index | FastAPI server | Frontend React | schemas.json | gold_standard | src2 |
|---|---|---|---|---|---|---|---|---|---|---|
| **nl_to_sparql** | — | 🔴 Alto | 🔴 Alto | 🟡 Médio | 🟡 Médio | 🟢 Baixo | — | 🔴 Alto | 🟡 Médio | 🟡 Médio |
| **llm_backends** | — | — | — | — | — | — | — | — | — | — |
| **sparql_validator** | — | — | — | — | — | — | — | 🔴 Alto | — | — |
| **entity_linker + NER** | — | 🟢 Baixo | — | — | — | — | — | — | — | — |
| **FAISS Index** | — | — | — | — | — | — | — | — | 🔴 Alto | — |
| **FastAPI server** | 🔴 Alto | — | — | — | — | — | — | — | — | — |
| **Frontend React** | — | — | — | — | — | 🔴 Alto | — | — | — | 🟡 Médio |
| **Evaluation Framework** | 🔴 Alto | 🔴 Alto | 🟡 Médio | 🟡 Médio | 🟡 Médio | — | — | — | 🔴 Alto | 🟡 Médio |
| **src2** | 🟡 Médio | 🔴 Alto | 🟡 Médio | — | — | — | 🔴 Alto | — | — | — |
| **gates** | 🟡 Médio | — | — | — | — | 🟡 Médio | — | 🟢 Baixo | 🟡 Médio | — |

---

## Análise por Componente

### nl_to_sparql — Ponto de Risco Central 🔴

**Impacta:** FastAPI server, Evaluation Framework, src2, gates
**Impactado por:** llm_backends, sparql_validator, schemas.json, entity_linker, FAISS

É o componente de maior risco do sistema. Qualquer alteração na interface `run()` quebra o server, o evaluation e o src2. Alterações no loop de autocorreção, nas transformações regex ou no `build_prompt()` afetam todos os cenários de avaliação.

**Regra de ouro:** Antes de alterar `nl_to_sparql.py`, verificar:
1. Interface `run(question) → dict` não muda
2. Loop de tentativas respeita `max_retries`
3. `_fix_common_errors()` continua idempotente
4. Testes de integração (gate2) passam

---

### llm_backends — Ponto de Extensão Crítico 🟡

**Impacta:** nl_to_sparql, Evaluation Framework, src2
**Impactado por:** nenhum componente interno

Mudanças de interface aqui (`generate(system, user_msg) → str`) afetam todos os pipelines. Adicionar um novo backend é seguro; alterar a assinatura é destrutivo.

**Risco adicional:** `src2/pipeline/llm_backends.py` é cópia separada — mudanças em `src/` não propagam automaticamente.

---

### schemas.json — Dado Crítico Estático 🔴

**Impacta:** sparql_validator, nl_to_sparql (via SchemaValidator permissive mode)

Se `schemas.json` for corrompido ou removido, o SchemaValidator entra em modo permissivo silenciosamente. Queries com predicados inválidos passarão pela validação e falharão apenas no Fuseki.

**Recomendação:** Tratar como arquivo protegido. Gerar sempre via `schema_extractor.py`, nunca editar manualmente.

---

### gold_standard — Imutável por Contrato 🔴

**Impacta:** FAISS Index (rebuild necessário), Evaluation Framework, gates
**Regra:** As 30 questões não devem ser alteradas ou reduzidas (RN-10). Qualquer mudança invalida comparações históricas entre modelos.

---

### Frontend React — Isolado do Core 🟢

**Impacta:** — (não impacta o pipeline)
**Impactado por:** FastAPI server (interface de contrato AskResponse)

O frontend consome apenas a interface REST `/api/ask`. Desde que o contrato `AskResponse` não mude, o frontend pode ser refatorado livremente. Mudanças no campo `xai` requerem atualização no `XaiPanel`.

---

### src2 — Acoplamento Duplo 🟡

**Impacta:** Evaluation multi-modelo (output2/), Frontend (via Playwright)
**Impactado por:** nl_to_sparql (interface), llm_backends (interface), Frontend (HTML/DOM para Playwright)

O src2 tem acoplamento duplo: depende do pipeline core (via Python) e do frontend (via DOM para Playwright). Se o Frontend mudar a estrutura do InputBar ou o endpoint `/api/ask`, o Playwright runner precisa ser atualizado.

---

## Mapa de Propagação de Falhas

```
[schemas.json corrompido]
    → SchemaValidator modo PERMISSIVE
    → Queries inválidas passam na validação
    → Falha silenciosa no Fuseki
    → success=False sem mensagem de validação clara

[LM Studio offline]
    → LMStudioBackend.generate() → LLMConnectionError
    → nl_to_sparql.run() → DONE_ERROR
    → FastAPI retorna 500 (ou AskResponse success=False)
    → Frontend exibe erro genérico

[Fuseki offline]
    → execute_sparql() → timeout/connection error
    → DONE_ERROR ou DONE_EMPTY (dependendo do código)
    → Avaliação registra success=False para todas as questões

[FAISS index ausente]
    → retrieve_examples() → [] (zero exemplos)
    → Pipeline funciona em zero-shot (sem few-shot)
    → Impacto de performance documentado no estudo de ablação

[NER falha (scispaCy crash)]
    → entity_linker retorna []
    → Pipeline continua sem entidades no prompt
    → Impacto menor: LLM gera sem grounding de IDs
```

---

## Matriz de Dependências Transitivas

| Componente | Dependências diretas | Dependências transitivas |
|---|---|---|
| Frontend React | FastAPI server | FastAPI → nl_to_sparql → llm_backends, validator, NER, FAISS, Fuseki |
| Evaluation Framework | nl_to_sparql | nl_to_sparql → (todos os componentes core) |
| src2 ClaudeCLIBackend | claude CLI (externo) | — |
| src2 PlaywrightRunner | Frontend, FastAPI | Frontend → FastAPI → pipeline → (todos) |
| gates | FastAPI, Fuseki, gold_standard | FastAPI → pipeline → (todos) |

---

## Hotspots de Manutenção

| Arquivo | Motivo | Prioridade de testes |
|---|---|---|
| `src/pipeline/nl_to_sparql.py` | Componente central, máquina de estados, 8 regex | 🔴 Crítica |
| `src/pipeline/sparql_validator.py` | Valida todo SPARQL gerado, 2 modos | 🔴 Alta |
| `src/pipeline/llm_backends.py` | Interface de todos os LLMs, retry logic | 🔴 Alta |
| `data/schemas.json` | Dado crítico, ausência muda comportamento | 🟡 Média |
| `src2/pipeline/llm_backends.py` | Cópia divergente — risco de drift | 🟡 Média |
| `gates/gate0_check.py` | Verifica Ollama em vez de LM Studio | 🟢 Baixa (bug conhecido) |
