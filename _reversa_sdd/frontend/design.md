# Design — frontend

> Unit: `frontend/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Visão Geral

O módulo `frontend` é uma SPA React servida pelo Vite na porta 3000. Implementa uma interface de chat com painel lateral de explicabilidade (XAI) para o pipeline NL→SPARQL. Toda a lógica de estado centraliza-se em `App.jsx`; os componentes filhos são puramente apresentacionais (recebem props, emitem callbacks). Não há gerenciador de estado global (sem Redux/Zustand/Context).

---

## Estrutura de Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/main.jsx` | Entry point — monta `<App />` em `#root` |
| `frontend/src/App.jsx` | Root component — estado global, lógica de envio |
| `frontend/src/components/ChatPanel.jsx` | Histórico de mensagens com auto-scroll |
| `frontend/src/components/InputBar.jsx` | Campo de entrada, botões de exemplo, envio |
| `frontend/src/components/XaiPanel.jsx` | Container do painel XAI — orquestra subcomponentes |
| `frontend/src/components/EntityBadges.jsx` | Badges de entidades NER (resolvidas/não resolvidas) |
| `frontend/src/components/SparqlBlock.jsx` | Bloco de código com syntax highlight (sql via hljs) |
| `frontend/src/components/ValidationStatus.jsx` | Badge valid/invalid + lista de erros e avisos |
| `frontend/src/components/TimingBar.jsx` | Barra proporcional NER / Retrieval / LLM + legenda |
| `frontend/src/components/ResultsTable.jsx` | Tabela dinâmica com cabeçalhos derivados do Fuseki |
| `frontend/vite.config.js` | Proxy `/api → localhost:8000`, porta 3000 |

---

## Hierarquia de Componentes e Props

```
App
├── ChatPanel     { messages: Message[], loading: bool }
├── InputBar      { onSend: (text: string) => void, loading: bool }
└── XaiPanel      { data: AskResponse | null }
    ├── EntityBadges      { entities: Entity[] }
    ├── SparqlBlock       { sparql: string }
    ├── ValidationStatus  { validation: ValidationInfo }
    ├── TimingBar         { timing: TimingInfo }
    └── ResultsTable      { results: any[] }
```

🟢 **CONFIRMADO** — extraído de `App.jsx` e `XaiPanel.jsx`

---

## Estado Global — `App.jsx`

```typescript
// Tipos inferidos
type Message = { role: 'user' | 'bot'; text: string }
type AskResponse = { answer?: string; natural_answer?: string; xai?: any; [key: string]: any }

// Estados
const [messages, setMessages] = useState<Message[]>([])
const [xai, setXai] = useState<AskResponse | null>(null)
const [loading, setLoading] = useState<boolean>(false)
```

🟢 **CONFIRMADO** — `App.jsx:50-53`

---

## Fluxo — Envio de Pergunta

```mermaid
flowchart TD
    USER[usuário digita e pressiona Enter ou clica Enviar] --> GUARD{text.trim() && !loading?}
    GUARD -- não --> IGNORE[retorna sem ação]
    GUARD -- sim --> PUSH_USER[setMessages prev + userMsg]
    PUSH_USER --> RESET[setXai null\nsetLoading true]
    RESET --> POST["axios.post('/api/ask', {question: text})"]

    POST -- sucesso --> DATA[data = res.data]
    DATA --> PUSH_BOT["setMessages prev + {role:'bot', text: data.answer || data.natural_answer}"]
    PUSH_BOT --> SET_XAI[setXai data]

    POST -- erro --> ERR_MSG["setMessages prev + {role:'bot', text: 'Erro: ...' }"]

    SET_XAI & ERR_MSG --> DONE[setLoading false]

    style IGNORE fill:#eee
    style DONE fill:#8f8
```

🟢 **CONFIRMADO** — `App.jsx:55-84`

---

## Componente: ChatPanel

**Arquivo:** `frontend/src/components/ChatPanel.jsx`

- Renderiza lista de `messages` como bubbles coloridas (azul=usuário, cinza=bot).
- Quando `loading=true`, exibe bubble "Processando..." em itálico.
- Quando histórico vazio e `!loading`, exibe tela de boas-vindas com emoji 🧬.
- Usa `useRef + useEffect` para auto-scroll ao final após cada atualização.

```javascript
// Auto-scroll
const endRef = useRef(null)
useEffect(() => {
  endRef.current?.scrollIntoView({ behavior: 'smooth' })
}, [messages, loading])
```

🟢 **CONFIRMADO** — `ChatPanel.jsx:48-90`

---

## Componente: InputBar

**Arquivo:** `frontend/src/components/InputBar.jsx`

- Estado local: `text` (string do campo de entrada).
- 4 botões de exemplo predefinidos: Marfan, Cardiovascular, Ehlers-Danlos, Genetic diseases.
- Botão de exemplo aciona `onSend(ex.text)` diretamente (sem passar pelo campo).
- Enter (sem Shift) aciona `submit()`.
- Campo e botões ficam `disabled` quando `loading=true`.

```javascript
const EXAMPLES = [
  { label: 'Marfan',         text: 'Quais sao os sintomas da Sindrome de Marfan?' },
  { label: 'Cardiovascular', text: 'Quais doencas cardiovasculares estao associadas a hipertensao?' },
  { label: 'Ehlers-Danlos',  text: 'Quais fenotipos estao associados a Sindrome de Ehlers-Danlos?' },
  { label: 'Genetic diseases', text: 'Liste doencas geneticas que afetam o sistema nervoso.' },
]
```

🟢 **CONFIRMADO** — `InputBar.jsx:3-8`

---

## Componente: XaiPanel

**Arquivo:** `frontend/src/components/XaiPanel.jsx`

- Estado local: `collapsed` (bool) — controlado pelo botão "Recolher/Expandir".
- Quando `data=null`: exibe placeholder.
- Resolução de campos com múltiplos nomes de chave (robustez a variações do backend):

```javascript
const entities  = data.entities || data.ner_entities || []
const examples  = data.examples || data.similar_examples || data.retrieved_examples || []
const sparql    = data.sparql || data.generated_sparql || data.query || ''
const validation= data.validation || null
const retries   = data.retries ?? data.retry_count ?? null
const retryErrors= data.retry_errors || data.correction_log || []
const results   = data.results_raw || data.results || []
const timing    = data.timing || data.timings || null
```

🟢 **CONFIRMADO** — `XaiPanel.jsx:76-83`

---

## Componente: EntityBadges

**Arquivo:** `frontend/src/components/EntityBadges.jsx`

- Cada entidade pode ser objeto `{uri?, iri?, id?, label?, text?, name?}` ou string.
- **Badge verde** (resolved): entidade tem `uri`, `iri` ou `id`.
- **Badge amarelo** (unresolved): entidade sem URI.
- Tooltip (`title`) exibe o URI ou "Não resolvido".

```javascript
const hasUri = Boolean(ent.uri || ent.iri || ent.id)
const label  = ent.label || ent.text || ent.name || String(ent)
```

🟢 **CONFIRMADO** — `EntityBadges.jsx:43-44`

---

## Componente: SparqlBlock

**Arquivo:** `frontend/src/components/SparqlBlock.jsx`

- Usa `react-syntax-highlighter` (Light build, linguagem `sql`, tema `docco`).
- SPARQL não tem highlighter dedicado no hljs — usa `sql` como aproximação.
- `wrapLongLines=true` evita scroll horizontal.

🟢 **CONFIRMADO** — `SparqlBlock.jsx`

---

## Componente: ValidationStatus

**Arquivo:** `frontend/src/components/ValidationStatus.jsx`

- Detecta validade por `validation.valid === true` OU `validation.status === 'valid'` (robustez a duas formas de API).
- Badge verde "Valid" ou vermelho "Invalid".
- Lista de erros (vermelho) e avisos (laranja) em `<ul>`.

🟢 **CONFIRMADO** — `ValidationStatus.jsx:40`

---

## Componente: TimingBar

**Arquivo:** `frontend/src/components/TimingBar.jsx`

- Exibe 3 segmentos: NER (verde), Retrieval (azul), LLM (amarelo).
- Largura proporcional ao tempo relativo de cada segmento.
- Segmentos com < 1% do total são omitidos da barra.
- Legenda exibe valor em segundos (2 casas) para cada segmento + total.
- Acessa `timing[key]` com fallback para `timing[key + '_time']`.

```javascript
const SEGMENTS = [
  { key: 'ner',      label: 'NER',      color: '#34a853' },
  { key: 'retrieval',label: 'Retrieval',color: '#4285f4' },
  { key: 'llm',      label: 'LLM',      color: '#f9ab00' },
]
```

🟢 **CONFIRMADO** — `TimingBar.jsx:3-7`

---

## Componente: ResultsTable

**Arquivo:** `frontend/src/components/ResultsTable.jsx`

- Cabeçalhos derivados dinamicamente de `Object.keys(results[0])`.
- Limite de exibição: **15 linhas** (`MAX_ROWS = 15`).
- URIs são encurtadas pela função `shortenUri()` — extrai a última parte após `/` ou `#`.
- Zebra-striping: linhas alternadas branco/#f8f9fa.
- Nota de truncamento exibida se `results.length > 15`.

```javascript
function shortenUri(val) {
  if (typeof val !== 'string') return String(val ?? '')
  if (val.startsWith('http://') || val.startsWith('https://')) {
    const parts = val.replace(/#/g, '/').split('/')
    return parts[parts.length - 1] || val
  }
  return val
}
```

🟢 **CONFIRMADO** — `ResultsTable.jsx:5-12`

---

## Configuração Vite

**Arquivo:** `frontend/vite.config.js`

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

- Porta: **3000** (não 5173 padrão do Vite) — necessário para compatibilidade com Playwright runner que espera `localhost:3000`.
- Proxy `/api/*` → `http://localhost:8000` — elimina CORS em desenvolvimento.

🟢 **CONFIRMADO** — `vite.config.js`

---

## Layout Visual

```
┌─ Header (gradient azul) ─────────────────────────────────────────┐
│  BioSPARQL-NL   Natural Language to SPARQL for Biomedical...     │
├──────────────────────────────────────────────────────────────────┤
│  chatArea (flex:1)              │  xaiArea (420px fixo)          │
│  ┌─ ChatPanel (overflow auto) ─┐│  ┌─ XaiPanel ───────────────┐  │
│  │  [bubble usuário]           ││  │  Explainability (XAI) [⌃] │  │
│  │  [bubble bot]               ││  │  Entidades detectadas      │  │
│  │  Processando...             ││  │  Exemplos similares        │  │
│  └─────────────────────────────┘│  │  SPARQL gerado             │  │
│  ┌─ InputBar ──────────────────┐│  │  Validação                 │  │
│  │  [Marfan][Cardiovascular]...││  │  Autocorreção              │  │
│  │  [campo texto...] [Enviar]  ││  │  Resultados (N linhas)     │  │
│  └─────────────────────────────┘│  │  Tempos de execução        │  │
│                                  │  └───────────────────────────┘  │
└──────────────────────────────────┴─────────────────────────────────┘
```
