# Arquitetura — BioSPARQL-NL

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Visão Geral

**BioSPARQL-NL** é um pipeline de tradução de linguagem natural para SPARQL (NL→SPARQL) sobre ontologias biomédicas. Dado uma pergunta em português sobre doenças ou fenótipos, o sistema gera e executa automaticamente uma query SPARQL contra o triplestore Apache Jena Fuseki, respondendo com dados de DOID, HPO e HPOA.

### Premissas arquiteturais fundamentais

| Premissa | Decisão | Consequência |
|---|---|---|
| SPARQL labels são em inglês | LLM instrui PT→EN no prompt | Usuário escreve em PT, queries usam EN |
| JOIN DOID↔HPOA requer transform | `BIND(REPLACE(MIM:→OMIM:))` obrigatório | Nenhum JOIN direto entre os grafos funciona sem a conversão |
| Nenhum serviço cloud mandatório | LLM local (LM Studio) é o padrão | Anthropic API e Claude CLI são opcionais/upper bound |
| Modelo cometeu erros frequentes | Loop de autocorreção com até 4 tentativas | Latência cresce com max_retries, mas precisão melhora |
| Testes E2E sobre o frontend real | Playwright intercepta `/api/ask` | Validação end-to-end sem mock de HTTP |

---

## Estilo Arquitetural

**Pipeline Pattern** com estratégia plugável para backends LLM, organizado em camadas:

```
[Frontend React]
      │ HTTP POST /api/ask
      ▼
[FastAPI Backend]
      │ singleton lazy-init
      ▼
[BioSPARQLPipeline]
      ├── NER (scispaCy / LLM / Gilda)
      ├── Few-shot RAG (FAISS + sentence-transformers)
      ├── LLM Backend (LM Studio / Anthropic / Claude CLI)
      ├── Pós-processamento SPARQL (8 transforms regex)
      ├── SchemaValidator
      └── Loop de autocorreção (máx 4 tentativas)
            │ SPARQL query
            ▼
      [Apache Jena Fuseki / TDB2]
            └── urn:doid (~302K triplas)
            └── urn:hpo (~908K triplas)
            └── urn:hpoa (~320K triplas)
```

---

## Módulos e Responsabilidades

| Módulo | Camada | Responsabilidade | Complexidade |
|---|---|---|---|
| `src/pipeline` | Core | Orquestração NL→SPARQL, loop de autocorreção | 🔴 Alta |
| `src/pipeline/ner` | Core | Extração e grounding de entidades biomédicas | 🟡 Média |
| `src/api` | Interface | REST API FastAPI — bridge frontend↔pipeline | 🟢 Baixa |
| `src/evaluation` | Tooling | Avaliação multi-modelo, ablação, tabelas LaTeX | 🟡 Média |
| `src/utils` | Tooling | Preparação de dados: HPOA→RDF, FAISS, schema | 🟡 Média |
| `frontend` | Interface | SPA React com painel XAI (entidades, SPARQL, timing) | 🟢 Baixa |
| `src2` | Extension | ClaudeCLIBackend + Playwright E2E runner | 🟡 Média |
| `gates` | Quality | Scripts de validação de pré-condições por fase | 🟢 Baixa |

---

## Fluxo de Dados Principal

```
Usuário (PT) → ChatPanel → POST /api/ask
  → BioSPARQLPipeline.run(question)
    → NER: extrai entidades (doenças, fenótipos) → curie IDs
    → FAISS: recupera 3 exemplos similares do gold standard
    → build_prompt(): system + user_msg (entidades + exemplos + schema)
    → LLM Backend: gera SPARQL bruto
    → _fix_common_errors(): 8 transforms regex
    → SchemaValidator.validate(): erro → re-prompt (loop)
    → execute_sparql(): Fuseki → bindings JSON
    → Resultado 0 → semantic retry (1x)
  → AskResponse(answer, xai{entities, sparql, validation, timing})
→ XaiPanel: exibe painel explicável
```

---

## Integrações Externas

| Sistema | Protocolo | Direção | Obrigatoriedade |
|---|---|---|---|
| Apache Jena Fuseki 6.0.0 | HTTP SPARQL 1.1 | Leitura (SELECT) | 🔴 Obrigatório |
| LM Studio (localhost:1234) | OpenAI-compat REST | Escrita (generate) | 🟡 Padrão (local) |
| Anthropic API (cloud) | HTTPS REST | Escrita (generate) | 🟢 Opcional (upper bound) |
| Claude CLI (subprocess) | stdin/stdout | Escrita (generate) | 🟢 Opcional (src2) |
| sentence-transformers (HuggingFace) | Python lib | Leitura (embeddings) | 🟡 Setup-time |
| scispaCy / Gilda | Python lib | Leitura (NER+grounding) | 🟡 Padrão NER |

---

## Dívidas Técnicas

### DT-01 — Gate 0 verifica Ollama (sistema migrado para LM Studio)
🟡 **INFERIDO** — `gates/gate0_check.py`

O gate ainda verifica `http://localhost:11434` (Ollama) mas o sistema usa LM Studio em `localhost:1234`. Gate pode dar falso-negativo mesmo com LM Studio rodando.

**Impacto:** Baixo (CI/CD não configurado), mas confuso para novos desenvolvedores.

---

### DT-02 — Dois módulos de pipeline paralelos (src/ e src2/)
🟢 **CONFIRMADO** — estrutura de pastas

`src/pipeline` e `src2/pipeline` têm código duplicado com diferenças pontuais (ClaudeCLIBackend). Não há herança entre eles. Se `src/` evoluir, `src2/` precisa ser manualmente atualizado.

**Impacto:** Médio — divergência silenciosa de comportamento.

---

### DT-03 — Ausência de CI/CD
🟢 **CONFIRMADO** — `surface.json.ci_cd: []`

Nenhum pipeline de CI detectado. Tests, gates e avaliação são executados manualmente. Resultados de avaliação dependem do ambiente local.

**Impacto:** Médio — reprodutibilidade limitada.

---

### DT-04 — CORS hardcoded para localhost
🟢 **CONFIRMADO** — `src/api/server.py`

Permitidos apenas `localhost:5173` e `localhost:3000`. Qualquer deploy em outro domínio requer alteração de código.

**Impacto:** Baixo (sistema é prova de conceito acadêmica).

---

### DT-05 — Pós-processamento SPARQL sem cobertura de testes
🟡 **INFERIDO** — ausência de testes unitários em `_fix_common_errors`

As 8 transformações regex são críticas mas não têm testes unitários visíveis. Interações entre transforms em queries complexas são uma lacuna documentada pelo Detetive.

**Impacto:** Alto — bugs silenciosos em edge cases.

---

### DT-06 — `LLM_MODEL` e `LLM_TIMEOUT` sem validação de env var
🔴 **LACUNA** — detectado pelo Detetive, não confirmado em código

Variáveis de ambiente para modelo e timeout podem não ter fallback robusto documentado. Sem validação, erro de configuração pode ser silencioso.

**Impacto:** Baixo a médio dependendo do deploy.

---

## Resumo de Confiança

| Aspecto | Confiança | Base |
|---|---|---|
| Pipeline NL→SPARQL (fluxo principal) | 🟢 CONFIRMADO | Código lido diretamente |
| Loop de autocorreção (4 tentativas) | 🟢 CONFIRMADO | `nl_to_sparql.py:run()` |
| Incompatibilidade MIM/OMIM | 🟢 CONFIRMADO | Código + ADR-001 |
| Backend LLM plugável | 🟢 CONFIRMADO | `llm_backends.py` ambos módulos |
| Dois módulos paralelos (src/src2) | 🟢 CONFIRMADO | Estrutura de pastas |
| Gate 0 desatualizado (Ollama→LM Studio) | 🟡 INFERIDO | Contexto histórico |
| Validação env vars LLM | 🔴 LACUNA | Não verificado em código |
