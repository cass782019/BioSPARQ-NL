# C4 — Nível 1: Contexto do Sistema

> Gerado pelo Arquiteto em 2026-05-04 | doc_level: detalhado

---

## Diagrama

```mermaid
C4Context
    title BioSPARQL-NL — Diagrama de Contexto (C4 Nível 1)

    Person(pesquisador, "Pesquisador Biomédico", "Formula perguntas em português sobre doenças e fenótipos humanos")

    System(biosparql, "BioSPARQL-NL", "Pipeline NL→SPARQL sobre ontologias biomédicas. Traduz perguntas em linguagem natural para queries SPARQL e retorna respostas com explicabilidade (XAI).")

    System_Ext(fuseki, "Apache Jena Fuseki", "Triplestore RDF local. Armazena DOID, HPO e HPOA (~1.5M triplas). Responde queries SPARQL 1.1.")
    System_Ext(lmstudio, "LM Studio", "Servidor LLM local com API OpenAI-compat. Hospeda modelos como Gemma, Nemotron, Qwen.")
    System_Ext(anthropic, "Anthropic API", "API cloud Claude Sonnet. Usado como upper bound de desempenho nos experimentos.")
    System_Ext(huggingface, "HuggingFace Hub", "Fonte dos modelos sentence-transformers (all-MiniLM-L6-v2) e scispaCy baixados em setup-time.")

    Rel(pesquisador, biosparql, "Faz pergunta em português", "HTTP/Browser")
    Rel(biosparql, fuseki, "Executa queries SPARQL SELECT", "HTTP SPARQL 1.1 :3030")
    Rel(biosparql, lmstudio, "Gera SPARQL via LLM", "HTTP OpenAI-compat :1234")
    Rel(biosparql, anthropic, "Gera SPARQL via Claude (opcional)", "HTTPS REST")
    Rel(biosparql, huggingface, "Baixa modelos de embeddings e NER", "HTTPS (setup-time)")
    Rel(biosparql, pesquisador, "Retorna resposta + painel XAI (entidades, SPARQL, timing)", "HTTP/Browser")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## Personas

### Pesquisador Biomédico
- **Perfil:** Pesquisador, estudante ou clínico que precisa consultar bases de conhecimento biomédico (DOID, HPO) sem conhecer SPARQL.
- **Necessidade:** Formular perguntas em linguagem natural e obter respostas estruturadas com rastreabilidade das fontes.
- **Interação:** Via interface web (browser), porta 5173.

---

## Sistemas Externos

| Sistema | Tipo | Localização | Protocolo | Confiança |
|---|---|---|---|---|
| Apache Jena Fuseki 6.0.0 | Triplestore RDF (TDB2) | localhost:3030 | SPARQL 1.1 over HTTP | 🟢 CONFIRMADO |
| LM Studio | LLM local server | localhost:1234 | OpenAI-compat REST | 🟢 CONFIRMADO |
| Anthropic API | LLM cloud | api.anthropic.com | HTTPS REST | 🟢 CONFIRMADO |
| HuggingFace Hub | Repositório de modelos | huggingface.co | HTTPS (setup-time apenas) | 🟢 CONFIRMADO |

---

## Fronteiras do Sistema

**Dentro do sistema BioSPARQL-NL:**
- Frontend React (SPA + painel XAI)
- FastAPI Backend
- Pipeline NL→SPARQL (NER, FAISS, geração, validação, correção)
- Dados estáticos: gold standard, schemas.json, FAISS index

**Fora do sistema (externos):**
- Triplestore Fuseki (dado como infra pré-existente)
- Modelos LLM (servidos externamente via LM Studio ou cloud)
- Ontologias brutas (doid.owl, hp.owl, phenotype.hpoa) — dados de entrada pré-carregados
