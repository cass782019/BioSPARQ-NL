import React from 'react'

const styles = {
  wrapper: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '6px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 500,
  },
  resolved: {
    background: '#e6f4ea',
    color: '#137333',
    border: '1px solid #a8dab5',
  },
  unresolved: {
    background: '#fef7e0',
    color: '#b06000',
    border: '1px solid #fdd663',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    display: 'inline-block',
  },
}

export default function EntityBadges({ entities }) {
  if (!entities || !Array.isArray(entities) || entities.length === 0) return null

  return (
    <div style={styles.wrapper}>
      {entities.map((ent, i) => {
        const hasUri = Boolean(ent.uri || ent.iri || ent.id)
        const label = ent.label || ent.text || ent.name || String(ent)
        return (
          <span
            key={i}
            style={{
              ...styles.badge,
              ...(hasUri ? styles.resolved : styles.unresolved),
            }}
            title={ent.uri || ent.iri || ent.id || 'Nao resolvido'}
          >
            <span
              style={{
                ...styles.dot,
                background: hasUri ? '#34a853' : '#f9ab00',
              }}
            />
            {label}
          </span>
        )
      })}
    </div>
  )
}
