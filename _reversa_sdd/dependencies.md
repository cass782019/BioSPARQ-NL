# Dependências — proj1 (BioSPARQL-NL)

> Gerado pelo Scout em 2026-05-04

---

## Backend Python (requirements.txt)

### Núcleo do Pipeline

| Pacote | Versão | Propósito |
|---|---|---|
| `fastapi` | 0.135.3 | Framework REST API |
| `uvicorn` | 0.44.0 | Servidor ASGI |
| `starlette` | 1.0.0 | Base HTTP (dependência FastAPI) |
| `pydantic` | 2.12.5 | Validação de dados / schemas |
| `openai` | 2.31.0 | Cliente LM Studio (API compat OpenAI) |
| `anthropic` | >=0.45.0 | Cliente Anthropic API (Claude) |
| `SPARQLWrapper` | 2.0.0 | Execução de queries SPARQL |
| `rdflib` | 7.6.0 | Processamento RDF (conversão HPOA) |
| `owlready2` | 0.50 | Leitura de ontologias OWL |

### NER & Embeddings

| Pacote | Versão | Propósito |
|---|---|---|
| `scispacy` | 0.6.2 | NER biomédico (backend padrão) |
| `spacy` | 3.7.5 | Framework NLP base |
| `en_core_sci_sm` | 0.5.4 | Modelo spaCy biomédico (S3 AI2) |
| `sentence-transformers` | 5.4.0 | Embeddings semânticos (all-MiniLM-L6-v2) |
| `faiss-cpu` | 1.13.2 | Busca por similaridade (FAISS) |
| `torch` | 2.11.0 | Backend PyTorch (sentence-transformers) |
| `transformers` | 5.5.2 | Modelos HuggingFace |
| `huggingface_hub` | 1.10.1 | Download de modelos HF |

### Avaliação & Dados

| Pacote | Versão | Propósito |
|---|---|---|
| `numpy` | 1.26.4 | Arrays numéricos |
| `scikit-learn` | 1.8.0 | Métricas (P/R/F1) |
| `scipy` | 1.17.1 | Cálculos científicos |
| `tabulate` | 0.10.0 | Formatação de tabelas |

### Infraestrutura

| Pacote | Versão | Propósito |
|---|---|---|
| `python-dotenv` | 1.2.2 | Leitura de .env |
| `requests` | 2.33.1 | HTTP (health checks, LM Studio) |
| `httpx` | 0.28.1 | HTTP assíncrono |
| `psutil` | 7.2.2 | Métricas de sistema |
| `rich` | 14.3.3 | Output colorido no terminal |

### Testes

| Pacote | Versão | Propósito |
|---|---|---|
| `pytest` | 9.0.3 | Framework de testes |
| `pytest-timeout` | 2.4.0 | Timeout por teste |

### NER Backends Opcionais (não incluídos no requirements.txt base)

| Pacote | Ativação |
|---|---|
| `gilda>=1.2` | `NER_BACKEND=gilda` ou `NER_BACKEND=llm` |
| `medcat>=1.12` | `NER_BACKEND=medcat` |

---

## Frontend Node (frontend/package.json)

### Dependências de Produção

| Pacote | Versão | Propósito |
|---|---|---|
| `react` | ^18.3.1 | UI library |
| `react-dom` | ^18.3.1 | Renderização React |
| `axios` | ^1.7.0 | HTTP client (chamadas `/api/ask`) |
| `react-syntax-highlighter` | ^15.5.0 | Highlight de SPARQL |

### Dependências de Desenvolvimento

| Pacote | Versão | Propósito |
|---|---|---|
| `vite` | ^5.4.0 | Build tool / dev server |
| `@vitejs/plugin-react` | ^4.3.0 | Plugin React para Vite |
| `@types/react` | ^18.3.0 | Tipos TypeScript (React) |
| `@types/react-dom` | ^18.3.0 | Tipos TypeScript (ReactDOM) |

---

## Infraestrutura Externa (não gerenciada pelo pip/npm)

| Componente | Versão | Instalação |
|---|---|---|
| Apache Jena Fuseki | 6.0.0 | `tools/apache-jena-fuseki-6.0.0/` (zip incluído) |
| Java (JDK) | 21+ (Eclipse Adoptium) | Sistema operacional |
| LM Studio | — | Aplicativo GUI (não versionado) |
| Node.js | 24+ | Sistema operacional |
| MiKTeX | — | Compilação LaTeX |
| Playwright | — | Instalado via pip para src2 E2E |

---

## Variáveis de Ambiente (.env.example)

| Variável | Valor padrão | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Chave Anthropic (opcional) |
| `NER_BACKEND` | `scispacy` | Backend NER: `scispacy`, `gilda`, `llm`, `medcat` |
| `FUSEKI_ENDPOINT` | `http://localhost:3030/biomedical/sparql` | URL SPARQL |
| `LLM_BASE_URL` | `http://localhost:1234/v1` | URL LM Studio |
| `LLM_MODEL` | `auto` | Modelo LM Studio (auto-detectado) |
| `LLM_TIMEOUT` | `300` | Timeout LLM em segundos |
| `LLM_MAX_TOKENS` | `3000` | Máximo de tokens gerados |
