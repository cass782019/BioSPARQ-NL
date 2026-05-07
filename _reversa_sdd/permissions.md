# Permissões e Controle de Acesso — BioSPARQL-NL

> Gerado pelo Detetive em 2026-05-04 | doc_level: detalhado

---

## Contexto

BioSPARQL-NL é um sistema de pesquisa acadêmica (PPG UNISINOS) sem autenticação de usuário. Não há RBAC, sessões, tokens JWT ou sistema de login. O controle de acesso é feito por restrição de rede (localhost-only) e bloqueio de operações SPARQL destrutivas.

---

## Modelo de Acesso

### Camada 1 — CORS (API FastAPI)

**Localização:** `src/api/server.py` (middleware `CORSMiddleware`)

| Origem permitida | Propósito |
|---|---|
| `http://localhost:5173` | Frontend React (Vite dev server) |
| `http://localhost:3000` | Playwright E2E runner |

Qualquer origem externa (incluindo outros hosts na rede local) é **bloqueada pelo CORS**. Não há credenciais transmitidas (`allow_credentials=True` está presente mas sem sistema de autenticação real — é permissivo para chamadas cross-origin do localhost).

---

### Camada 2 — Operações SPARQL bloqueadas

**Localização:** `src/pipeline/sparql_validator.py:validate()` (checagem `UNSAFE_OPERATION`)

| Operação | Status |
|---|---|
| `SELECT` | ✅ Permitido |
| `ASK` | ✅ Permitido |
| `CONSTRUCT` | ✅ Permitido |
| `DESCRIBE` | ✅ Permitido |
| `INSERT` | ❌ Bloqueado — `UNSAFE_OPERATION` error |
| `DELETE` | ❌ Bloqueado — `UNSAFE_OPERATION` error |
| `UPDATE` | ❌ Bloqueado (via regex `DELETE\|INSERT`) |

O Fuseki também está configurado com `--update` habilitado, mas o pipeline nunca chega a enviar queries de escrita ao triplestore (bloqueadas antes da execução).

---

### Camada 3 — Grafos nomeados válidos

**Localização:** `src/pipeline/sparql_validator.py:SchemaValidator.valid_graphs`

Queries que referenciam grafos fora da lista abaixo são rejeitadas:

| Grafo | Conteúdo |
|---|---|
| `urn:doid` | Disease Ontology |
| `urn:hpo` | Human Phenotype Ontology |
| `urn:hpoa` | Anotações doença→fenótipo |

---

### Camada 4 — Acesso a serviços por componente

| Componente | Serviço acessado | Credencial necessária |
|---|---|---|
| `BioSPARQLPipeline` | Fuseki `localhost:3030` | Nenhuma |
| `LMStudioBackend` | LM Studio `localhost:1234` | `api_key="lm-studio"` (fake, apenas para SDK) |
| `AnthropicBackend` | Anthropic Cloud API | `ANTHROPIC_API_KEY` (env var) |
| `ClaudeCLIBackend` | Claude CLI (OAuth local) | Sessão OAuth pré-autenticada no Claude Code |
| `ScispaCyBackend` | Fuseki `localhost:3030` | Nenhuma |
| `Playwright runner` | Frontend `localhost:3000` | Nenhuma |

---

## Matriz de Papéis (Funcional)

Não há papéis de usuário no sistema. A distinção é por **ponto de entrada**:

| Ponto de entrada | Quem usa | Capacidades |
|---|---|---|
| Frontend React (`:5173`) | Pesquisador / usuário final | Fazer perguntas, ver XAI |
| API FastAPI direta (`:8000`) | Desenvolvedor / integrador | Idem via HTTP |
| `run_evaluation.py` | Pesquisador | Avaliação em lote (30 questões) |
| `playwright_runner.py` | CI / pesquisador | Teste E2E via browser |
| `gate*.py` | Pesquisador / CI | Verificação de pré-condições |

---

## Lacunas de Segurança (para referência futura)

| Lacuna | Risco | Confiança |
|---|---|---|
| Sem rate limiting no `/api/ask` | DoS / uso excessivo de LLM | 🟡 INFERIDO |
| `allow_credentials=True` sem autenticação real | Potencial CSRF se implantado em rede não-local | 🟡 INFERIDO |
| Fuseki sem senha | Qualquer processo local pode alterar o triplestore diretamente via porta 3030 | 🟢 CONFIRMADO |
| `LLM_MODEL` e `LLM_TIMEOUT` via env sem validação | Injection via env no processo | 🔴 LACUNA — impacto não avaliado |

> **Nota:** estas lacunas são aceitáveis para um sistema de pesquisa acadêmica rodando em localhost. Qualquer implantação pública requereria autenticação, HTTPS e rate limiting.
