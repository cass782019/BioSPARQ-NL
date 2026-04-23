import React, { useState } from 'react'

const EXAMPLES = [
  { label: 'Marfan', text: 'Quais sao os sintomas da Sindrome de Marfan?' },
  { label: 'Cardiovascular', text: 'Quais doencas cardiovasculares estao associadas a hipertensao?' },
  { label: 'Ehlers-Danlos', text: 'Quais fenotipos estao associados a Sindrome de Ehlers-Danlos?' },
  { label: 'Genetic diseases', text: 'Liste doencas geneticas que afetam o sistema nervoso.' },
]

const styles = {
  wrapper: {
    borderTop: '1px solid #ddd',
    background: '#fff',
    padding: '12px 24px 16px',
  },
  examples: {
    display: 'flex',
    gap: '8px',
    marginBottom: '10px',
    flexWrap: 'wrap',
  },
  exampleBtn: {
    padding: '5px 12px',
    borderRadius: '16px',
    border: '1px solid #dadce0',
    background: '#f8f9fa',
    color: '#1a73e8',
    fontSize: '12px',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  row: {
    display: 'flex',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '10px 16px',
    borderRadius: '24px',
    border: '1px solid #dadce0',
    fontSize: '14px',
    outline: 'none',
  },
  sendBtn: {
    padding: '10px 24px',
    borderRadius: '24px',
    border: 'none',
    background: '#1a73e8',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  sendBtnDisabled: {
    background: '#a8c7fa',
    cursor: 'not-allowed',
  },
}

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

  return (
    <div style={styles.wrapper}>
      <div style={styles.examples}>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            style={styles.exampleBtn}
            onClick={() => { setText(''); onSend(ex.text) }}
            disabled={loading}
            onMouseEnter={(e) => { e.target.style.background = '#e8f0fe' }}
            onMouseLeave={(e) => { e.target.style.background = '#f8f9fa' }}
          >
            {ex.label}
          </button>
        ))}
      </div>
      <div style={styles.row}>
        <input
          style={styles.input}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Faca uma pergunta em linguagem natural..."
          disabled={loading}
        />
        <button
          style={{
            ...styles.sendBtn,
            ...(loading ? styles.sendBtnDisabled : {}),
          }}
          onClick={submit}
          disabled={loading}
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
