import React, { useRef, useEffect } from 'react'

const styles = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  bubble: {
    maxWidth: '70%',
    padding: '10px 16px',
    borderRadius: '16px',
    fontSize: '14px',
    lineHeight: '1.5',
    wordBreak: 'break-word',
    whiteSpace: 'pre-wrap',
  },
  user: {
    alignSelf: 'flex-end',
    background: '#1a73e8',
    color: '#fff',
    borderBottomRightRadius: '4px',
  },
  bot: {
    alignSelf: 'flex-start',
    background: '#e8eaed',
    color: '#202124',
    borderBottomLeftRadius: '4px',
  },
  loading: {
    alignSelf: 'flex-start',
    background: '#e8eaed',
    color: '#5f6368',
    borderBottomLeftRadius: '4px',
    fontStyle: 'italic',
  },
  empty: {
    textAlign: 'center',
    color: '#9aa0a6',
    marginTop: '80px',
    fontSize: '15px',
  },
}

export default function ChatPanel({ messages, loading }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>&#x1F9EC;</div>
          <div>Faca uma pergunta sobre doencas ou fenotipos.</div>
          <div style={{ fontSize: '13px', marginTop: '6px' }}>
            Use os exemplos abaixo ou escreva sua propria pergunta.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            ...styles.bubble,
            ...(msg.role === 'user' ? styles.user : styles.bot),
          }}
        >
          {msg.text}
        </div>
      ))}
      {loading && (
        <div style={{ ...styles.bubble, ...styles.loading }}>
          Processando...
        </div>
      )}
      <div ref={endRef} />
    </div>
  )
}
