import React from 'react'

const MAX_ROWS = 15

function shortenUri(val) {
  if (typeof val !== 'string') return String(val ?? '')
  if (val.startsWith('http://') || val.startsWith('https://')) {
    const parts = val.replace(/#/g, '/').split('/')
    return parts[parts.length - 1] || val
  }
  return val
}

const styles = {
  wrapper: {
    marginTop: '8px',
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '12px',
  },
  th: {
    background: '#e8f0fe',
    padding: '6px 10px',
    textAlign: 'left',
    fontWeight: 600,
    color: '#1a73e8',
    borderBottom: '2px solid #c5d7f7',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '5px 10px',
    borderBottom: '1px solid #e8eaed',
    color: '#3c4043',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  note: {
    fontSize: '11px',
    color: '#9aa0a6',
    marginTop: '4px',
  },
}

export default function ResultsTable({ results }) {
  if (!results || !Array.isArray(results) || results.length === 0) {
    return <div style={{ color: '#9aa0a6', fontSize: '13px', marginTop: '8px' }}>Sem resultados.</div>
  }

  const keys = Object.keys(results[0])
  const rows = results.slice(0, MAX_ROWS)
  const truncated = results.length > MAX_ROWS

  return (
    <div style={styles.wrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k} style={styles.th}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8f9fa' }}>
              {keys.map((k) => (
                <td key={k} style={styles.td} title={String(row[k] ?? '')}>
                  {shortenUri(row[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {truncated && (
        <div style={styles.note}>
          Mostrando {MAX_ROWS} de {results.length} resultados.
        </div>
      )}
    </div>
  )
}
