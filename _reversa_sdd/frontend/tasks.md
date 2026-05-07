# Tasks — frontend

> Unit: `frontend/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Implementar App root com estado global e lógica de envio

**Origem:** `frontend/src/App.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```jsx
import React, { useState, useCallback } from 'react'
import axios from 'axios'

export default function App() {
  const [messages, setMessages] = useState([])   // { role: 'user'|'bot', text: string }[]
  const [xai, setXai] = useState(null)           // AskResponse | null
  const [loading, setLoading] = useState(false)

  const handleSend = useCallback(async (text) => {
    if (!text.trim() || loading) return

    setMessages(prev => [...prev, { role: 'user', text: text.trim() }])
    setXai(null)
    setLoading(true)

    try {
      const res = await axios.post('/api/ask', { question: text.trim() })
      const data = res.data
      setMessages(prev => [...prev, {
        role: 'bot',
        text: data.answer || data.natural_answer || 'Sem resposta.'
      }])
      setXai(data)
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'bot',
        text: `Erro: ${err.response?.data?.detail || err.message}`
      }])
    } finally {
      setLoading(false)
    }
  }, [loading])

  // Layout: header + body (chatArea + xaiArea)
}
```

**Critério de pronto:**
- `handleSend('')` não dispara POST
- `handleSend('texto')` com `loading=true` não dispara POST
- Sucesso → `messages` cresce em 2 entradas (user + bot) e `xai` é populado
- Erro → `messages` cresce em 2 entradas (user + mensagem de erro) e `xai` permanece null

---

## T-02 — Implementar ChatPanel com auto-scroll

**Origem:** `frontend/src/components/ChatPanel.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```jsx
import React, { useRef, useEffect } from 'react'

export default function ChatPanel({ messages, loading }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return <div>{/* tela de boas-vindas com emoji 🧬 */}</div>
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {messages.map((msg, i) => (
        <div key={i} style={msg.role === 'user' ? userBubbleStyle : botBubbleStyle}>
          {msg.text}
        </div>
      ))}
      {loading && <div style={loadingBubbleStyle}>Processando...</div>}
      <div ref={endRef} />
    </div>
  )
}
```

**Critério de pronto:**
- Histórico vazio + `!loading` → tela de boas-vindas visível
- Mensagem de usuário → bubble alinhada à direita (azul)
- Mensagem de bot → bubble alinhada à esquerda (cinza)
- `loading=true` → bubble "Processando..." visível em itálico
- Após cada nova mensagem, o scroll desce automaticamente ao final

---

## T-03 — Implementar InputBar com exemplos predefinidos

**Origem:** `frontend/src/components/InputBar.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```jsx
const EXAMPLES = [
  { label: 'Marfan',           text: 'Quais sao os sintomas da Sindrome de Marfan?' },
  { label: 'Cardiovascular',   text: 'Quais doencas cardiovasculares estao associadas a hipertensao?' },
  { label: 'Ehlers-Danlos',    text: 'Quais fenotipos estao associados a Sindrome de Ehlers-Danlos?' },
  { label: 'Genetic diseases', text: 'Liste doencas geneticas que afetam o sistema nervoso.' },
]

export default function InputBar({ onSend, loading }) {
  const [text, setText] = useState('')

  const submit = () => {
    if (text.trim() && !loading) {
      onSend(text)
      setText('')
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }
  // ...renderiza botões EXAMPLES + input + botão Enviar
}
```

**Critério de pronto:**
- Enter (sem Shift) aciona `submit()`
- Shift+Enter não aciona `submit()` (permite quebra de linha se aplicável)
- Clique em botão de exemplo aciona `onSend(ex.text)` imediatamente (sem depender do campo)
- Campo e botões ficam `disabled` quando `loading=true`
- Após `submit()`, campo é limpo (`setText('')`)

---

## T-04 — Implementar XaiPanel com colapso e resolução de campos

**Origem:** `frontend/src/components/XaiPanel.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```jsx
export default function XaiPanel({ data }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!data) return <div>Envie uma pergunta para ver os detalhes...</div>

  // Resolução robusta de campos:
  const entities   = data.entities || data.ner_entities || []
  const examples   = data.examples || data.similar_examples || data.retrieved_examples || []
  const sparql     = data.sparql || data.generated_sparql || data.query || ''
  const validation = data.validation || null
  const retries    = data.retries ?? data.retry_count ?? null
  const retryErrors= data.retry_errors || data.correction_log || []
  const results    = data.results_raw || data.results || []
  const timing     = data.timing || data.timings || null

  // Renderiza subcomponentes condicionalmente:
  // entities.length > 0 → EntityBadges
  // examples.length > 0 → lista de exemplos
  // sparql → SparqlBlock
  // validation → ValidationStatus
  // retries > 0 → seção Autocorreção
  // results.length > 0 → ResultsTable
  // timing → TimingBar
}
```

**Critério de pronto:**
- `data=null` → placeholder visível, sem erros
- `collapsed=true` → subcomponentes não renderizados
- Botão alterna entre "Recolher" e "Expandir" corretamente
- Cada subcomponente só renderiza se seus dados estão presentes

---

## T-05 — Implementar EntityBadges com distinção resolved/unresolved

**Origem:** `frontend/src/components/EntityBadges.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```jsx
export default function EntityBadges({ entities }) {
  if (!entities || !Array.isArray(entities) || entities.length === 0) return null

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {entities.map((ent, i) => {
        const hasUri = Boolean(ent.uri || ent.iri || ent.id)
        const label  = ent.label || ent.text || ent.name || String(ent)
        return (
          <span key={i}
            style={hasUri ? resolvedStyle : unresolvedStyle}
            title={ent.uri || ent.iri || ent.id || 'Nao resolvido'}
          >
            <DotIndicator color={hasUri ? '#34a853' : '#f9ab00'} />
            {label}
          </span>
        )
      })}
    </div>
  )
}
```

**Critério de pronto:**
- Entidade com `uri` → badge verde com dot verde
- Entidade sem URI → badge amarelo com dot amarelo
- Entidade como string simples → `String(ent)` exibido
- `entities=[]` ou `null` → retorna null sem erro

---

## T-06 — Implementar SparqlBlock com syntax highlight

**Origem:** `frontend/src/components/SparqlBlock.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```jsx
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import sql from 'react-syntax-highlighter/dist/esm/languages/hljs/sql'
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs'

SyntaxHighlighter.registerLanguage('sql', sql)

export default function SparqlBlock({ sparql }) {
  if (!sparql) return null

  return (
    <div style={{ borderRadius: '8px', border: '1px solid #dadce0' }}>
      <div style={labelStyle}>SPARQL</div>
      <SyntaxHighlighter
        language="sql"
        style={docco}
        wrapLongLines
        customStyle={{ margin: 0, padding: '12px', fontSize: '12px' }}
      >
        {sparql}
      </SyntaxHighlighter>
    </div>
  )
}
```

**Critério de pronto:**
- `sparql=''` ou falsy → retorna null sem erro
- Query longa não causa scroll horizontal (`wrapLongLines=true`)
- Label "SPARQL" visível acima do bloco de código

---

## T-07 — Implementar ValidationStatus com erros e avisos

**Origem:** `frontend/src/components/ValidationStatus.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```jsx
export default function ValidationStatus({ validation }) {
  if (!validation) return null

  const isValid = validation.valid === true || validation.status === 'valid'
  const errors   = validation.errors || []
  const warnings = validation.warnings || []

  return (
    <div>
      <span style={isValid ? validBadgeStyle : invalidBadgeStyle}>
        {isValid ? 'Valid' : 'Invalid'}
      </span>
      {errors.length > 0 && (
        <ul>{errors.map((err, i) => <li key={i} style={errorStyle}>{err}</li>)}</ul>
      )}
      {warnings.length > 0 && (
        <ul>{warnings.map((w, i) => <li key={i} style={warningStyle}>{w}</li>)}</ul>
      )}
    </div>
  )
}
```

**Critério de pronto:**
- `valid=true` → badge verde "Valid"
- `valid=false` → badge vermelho "Invalid" + lista de erros
- `status='valid'` (forma alternativa) → badge verde
- `warnings` presentes → exibidos em laranja separados dos erros

---

## T-08 — Implementar TimingBar com barras proporcionais

**Origem:** `frontend/src/components/TimingBar.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Could

### Comportamento esperado

```jsx
const SEGMENTS = [
  { key: 'ner',      label: 'NER',      color: '#34a853' },
  { key: 'retrieval',label: 'Retrieval',color: '#4285f4' },
  { key: 'llm',      label: 'LLM',      color: '#f9ab00' },
]

export default function TimingBar({ timing }) {
  if (!timing) return null

  const values = SEGMENTS.map(s => timing[s.key] ?? timing[s.key + '_time'] ?? 0)
  const total  = values.reduce((a, b) => a + b, 0)
  if (total === 0) return null

  // Renderiza barra proporcional + legenda com valores em segundos
}
```

**Critério de pronto:**
- Segmentos com < 1% do total são omitidos da barra visual
- Label com tempo exibido dentro do segmento apenas se pct > 12%
- Legenda exibe todos os valores em `N.XXs` + Total
- `timing=null` ou total=0 → retorna null sem erro

---

## T-09 — Implementar ResultsTable com encurtamento de URIs

**Origem:** `frontend/src/components/ResultsTable.jsx`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```jsx
const MAX_ROWS = 15

function shortenUri(val) {
  if (typeof val !== 'string') return String(val ?? '')
  if (val.startsWith('http://') || val.startsWith('https://')) {
    const parts = val.replace(/#/g, '/').split('/')
    return parts[parts.length - 1] || val
  }
  return val
}

export default function ResultsTable({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) {
    return <div>Sem resultados.</div>
  }

  const keys = Object.keys(results[0])   // cabeçalhos dinâmicos
  const rows = results.slice(0, MAX_ROWS)
  const truncated = results.length > MAX_ROWS

  // Renderiza <table> com cabeçalhos dinâmicos + zebra-striping
  // Cada célula: shortenUri(row[k]), title={valor completo}
  // Se truncated: nota "Mostrando 15 de N resultados."
}
```

**Critério de pronto:**
- URI `http://purl.obolibrary.org/obo/DOID_14330` → exibe `DOID_14330`
- URI com `#` (ex: `.../DOID#14330`) → trata `#` como `/` antes de split
- Mais de 15 resultados → nota de truncamento visível
- `results=[]` → exibe "Sem resultados." sem erro
- Cabeçalhos derivados do primeiro objeto (colunas SPARQL)

---

## T-10 — Configurar Vite com proxy e porta 3000

**Origem:** `frontend/vite.config.js`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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

**Critério de pronto:**
- `npx vite dev` inicia na porta 3000 (não 5173)
- `POST /api/ask` é proxiado para `http://localhost:8000/api/ask`
- Sem erros CORS em desenvolvimento
- Playwright conecta em `localhost:3000` sem configuração adicional
