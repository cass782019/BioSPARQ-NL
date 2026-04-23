import React from 'react'

const styles = {
  wrapper: {
    marginTop: '8px',
  },
  badge: {
    display: 'inline-block',
    padding: '3px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: 600,
  },
  valid: {
    background: '#e6f4ea',
    color: '#137333',
  },
  invalid: {
    background: '#fce8e6',
    color: '#c5221f',
  },
  errorList: {
    marginTop: '6px',
    paddingLeft: '16px',
    fontSize: '12px',
  },
  error: {
    color: '#c5221f',
    marginBottom: '3px',
  },
  warning: {
    color: '#e37400',
    marginBottom: '3px',
  },
}

export default function ValidationStatus({ validation }) {
  if (!validation) return null

  const isValid = validation.valid === true || validation.status === 'valid'
  const errors = validation.errors || []
  const warnings = validation.warnings || []

  return (
    <div style={styles.wrapper}>
      <span style={{ ...styles.badge, ...(isValid ? styles.valid : styles.invalid) }}>
        {isValid ? 'Valid' : 'Invalid'}
      </span>
      {errors.length > 0 && (
        <ul style={styles.errorList}>
          {errors.map((err, i) => (
            <li key={i} style={styles.error}>{err}</li>
          ))}
        </ul>
      )}
      {warnings.length > 0 && (
        <ul style={styles.errorList}>
          {warnings.map((w, i) => (
            <li key={i} style={styles.warning}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
