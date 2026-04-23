import React, { useState, useCallback } from 'react'
import axios from 'axios'
import ChatPanel from './components/ChatPanel.jsx'
import InputBar from './components/InputBar.jsx'
import XaiPanel from './components/XaiPanel.jsx'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#f5f7fa',
  },
  header: {
    background: 'linear-gradient(135deg, #1a73e8, #0d47a1)',
    color: '#fff',
    padding: '14px 24px',
    fontSize: '20px',
    fontWeight: 700,
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  headerSub: {
    fontSize: '12px',
    fontWeight: 400,
    opacity: 0.85,
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  chatArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  xaiArea: {
    width: '420px',
    minWidth: '320px',
    borderLeft: '1px solid #ddd',
    background: '#fff',
    overflowY: 'auto',
  },
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [xai, setXai] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSend = useCallback(async (text) => {
    if (!text.trim() || loading) return

    const userMsg = { role: 'user', text: text.trim() }
    setMessages((prev) => [...prev, userMsg])
    setXai(null)
    setLoading(true)

    try {
      const res = await axios.post('/api/ask', {
        question: text.trim(),
      })
      const data = res.data

      const botMsg = {
        role: 'bot',
        text: data.answer || data.natural_answer || 'Sem resposta.',
      }
      setMessages((prev) => [...prev, botMsg])
      setXai(data)
    } catch (err) {
      const errorMsg = {
        role: 'bot',
        text: `Erro: ${err.response?.data?.detail || err.message}`,
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }, [loading])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>BioSPARQL-NL</span>
        <span style={styles.headerSub}>
          Natural Language to SPARQL for Biomedical Ontologies
        </span>
      </div>
      <div style={styles.body}>
        <div style={styles.chatArea}>
          <ChatPanel messages={messages} loading={loading} />
          <InputBar onSend={handleSend} loading={loading} />
        </div>
        <div style={styles.xaiArea}>
          <XaiPanel data={xai} />
        </div>
      </div>
    </div>
  )
}
