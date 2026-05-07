# Flowchart — Módulo `frontend`

> Gerado pelo Arqueólogo em 2026-05-04

## Hierarquia de componentes e estado

```mermaid
flowchart TD
    APP[App.jsx\nstate: messages, xai, loading] --> CHAT[ChatPanel\nmessages, loading]
    APP --> INPUT[InputBar\nonSend, loading]
    APP --> XAI[XaiPanel\ndata=xai]

    XAI --> EB[EntityBadges\nentidades NER]
    XAI --> SB[SparqlBlock\nSPARQL + highlight]
    XAI --> VS[ValidationStatus\nvalid, errors, warnings]
    XAI --> TB[TimingBar\nner_s, retrieval_s, llm_s]
    XAI --> RT[ResultsTable\nresults_raw]
```

## Fluxo de interação

```mermaid
flowchart TD
    USER[usuário digita pergunta] --> SEND[InputBar.onSend text]
    SEND --> LOADING[setLoading true\nsetXai null]
    LOADING --> PUSH_USER[setMessages prev + userMsg]
    PUSH_USER --> POST[axios.POST /api/ask\nbody: question]
    POST -- sucesso --> DATA[data = res.data\nAskResponse]
    DATA --> PUSH_BOT[setMessages prev + botMsg\nsetXai data]
    POST -- erro --> ERR[setMessages prev + errorMsg\nerro HTTP ou rede]
    PUSH_BOT & ERR --> DONE[setLoading false]
```

## Layout visual

```
┌─ Header: BioSPARQL-NL ──────────────────────────────────────────┐
│ body                                                             │
│  ┌─ chatArea (flex:1) ──────┐  ┌─ xaiArea (420px) ──────────┐  │
│  │ ChatPanel                │  │ XaiPanel                    │  │
│  │  user: ...               │  │  EntityBadges               │  │
│  │  bot: ...                │  │  SparqlBlock (highlight)    │  │
│  │                          │  │  ValidationStatus           │  │
│  │ InputBar                 │  │  TimingBar                  │  │
│  │  [pergunta...]  [Enviar] │  │  ResultsTable               │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

Proxy Vite: `/api/*` → `http://localhost:8000` (configurado em `vite.config.js`).
