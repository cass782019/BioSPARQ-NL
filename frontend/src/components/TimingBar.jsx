import React from 'react'

const SEGMENTS = [
  { key: 'ner', label: 'NER', color: '#34a853' },
  { key: 'retrieval', label: 'Retrieval', color: '#4285f4' },
  { key: 'llm', label: 'LLM', color: '#f9ab00' },
]

const styles = {
  wrapper: {
    marginTop: '8px',
  },
  bar: {
    display: 'flex',
    height: '22px',
    borderRadius: '6px',
    overflow: 'hidden',
    background: '#e8eaed',
  },
  segment: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#fff',
    fontSize: '10px',
    fontWeight: 600,
    minWidth: '20px',
    transition: 'width 0.3s',
  },
  legend: {
    display: 'flex',
    gap: '16px',
    marginTop: '6px',
    fontSize: '11px',
    color: '#5f6368',
  },
  dot: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    marginRight: '4px',
  },
}

export default function TimingBar({ timing }) {
  if (!timing) return null

  const values = SEGMENTS.map((s) => timing[s.key] ?? timing[s.key + '_time'] ?? 0)
  const total = values.reduce((a, b) => a + b, 0)

  if (total === 0) return null

  return (
    <div style={styles.wrapper}>
      <div style={styles.bar}>
        {SEGMENTS.map((seg, i) => {
          const val = values[i]
          const pct = (val / total) * 100
          if (pct < 1) return null
          return (
            <div
              key={seg.key}
              style={{
                ...styles.segment,
                background: seg.color,
                width: `${pct}%`,
              }}
            >
              {pct > 12 ? `${val.toFixed(1)}s` : ''}
            </div>
          )
        })}
      </div>
      <div style={styles.legend}>
        {SEGMENTS.map((seg, i) => (
          <span key={seg.key}>
            <span style={{ ...styles.dot, background: seg.color }} />
            {seg.label}: {(values[i] ?? 0).toFixed(2)}s
          </span>
        ))}
        <span style={{ marginLeft: 'auto', fontWeight: 600 }}>
          Total: {total.toFixed(2)}s
        </span>
      </div>
    </div>
  )
}
