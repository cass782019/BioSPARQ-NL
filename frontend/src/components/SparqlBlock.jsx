import React from 'react'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import sql from 'react-syntax-highlighter/dist/esm/languages/hljs/sql'
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs'

SyntaxHighlighter.registerLanguage('sql', sql)

const styles = {
  wrapper: {
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid #dadce0',
    marginTop: '8px',
  },
  label: {
    background: '#e8eaed',
    padding: '6px 12px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#5f6368',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
}

export default function SparqlBlock({ sparql }) {
  if (!sparql) return null

  return (
    <div style={styles.wrapper}>
      <div style={styles.label}>SPARQL</div>
      <SyntaxHighlighter
        language="sql"
        style={docco}
        customStyle={{
          margin: 0,
          padding: '12px',
          fontSize: '12px',
          lineHeight: '1.5',
          background: '#fafbfc',
        }}
        wrapLongLines
      >
        {sparql}
      </SyntaxHighlighter>
    </div>
  )
}
