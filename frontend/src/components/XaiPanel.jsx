import React, { useState } from 'react'
import EntityBadges from './EntityBadges.jsx'
import SparqlBlock from './SparqlBlock.jsx'
import ValidationStatus from './ValidationStatus.jsx'
import ResultsTable from './ResultsTable.jsx'
import TimingBar from './TimingBar.jsx'

const styles = {
  panel: {
    padding: '16px 18px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#202124',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  toggle: {
    fontSize: '12px',
    color: '#1a73e8',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    fontWeight: 500,
  },
  section: {
    marginBottom: '14px',
  },
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#5f6368',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '4px',
  },
  empty: {
    padding: '40px 20px',
    textAlign: 'center',
    color: '#9aa0a6',
    fontSize: '13px',
  },
  exampleItem: {
    padding: '6px 10px',
    background: '#f8f9fa',
    borderRadius: '6px',
    marginBottom: '4px',
    fontSize: '12px',
    color: '#3c4043',
    borderLeft: '3px solid #4285f4',
  },
  retryInfo: {
    fontSize: '12px',
    color: '#e37400',
    background: '#fef7e0',
    padding: '6px 10px',
    borderRadius: '6px',
    marginTop: '4px',
  },
}

export default function XaiPanel({ data }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!data) {
    return (
      <div style={styles.empty}>
        Envie uma pergunta para ver os detalhes de explicabilidade (XAI).
      </div>
    )
  }

  const entities = data.entities || data.ner_entities || []
  const examples = data.examples || data.similar_examples || data.retrieved_examples || []
  const sparql = data.sparql || data.generated_sparql || data.query || ''
  const validation = data.validation || null
  const retries = data.retries ?? data.retry_count ?? null
  const retryErrors = data.retry_errors || data.correction_log || []
  const results = data.results_raw || data.results || []
  const timing = data.timing || data.timings || null

  return (
    <div style={styles.panel}>
      <div style={styles.title}>
        <span>Explainability (XAI)</span>
        <button style={styles.toggle} onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? 'Expandir' : 'Recolher'}
        </button>
      </div>

      {collapsed ? null : (
        <>
          {/* Entities */}
          {entities.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Entidades detectadas</div>
              <EntityBadges entities={entities} />
            </div>
          )}

          {/* Similar examples */}
          {examples.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Exemplos similares (few-shot)</div>
              {examples.map((ex, i) => (
                <div key={i} style={styles.exampleItem}>
                  <strong>Q:</strong> {ex.question || ex.nl || ex.text || String(ex)}
                  {(ex.sparql || ex.query) && (
                    <div style={{ marginTop: '3px', opacity: 0.7, fontFamily: 'monospace', fontSize: '11px' }}>
                      {(ex.sparql || ex.query).slice(0, 120)}...
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* SPARQL */}
          {sparql && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>SPARQL gerado</div>
              <SparqlBlock sparql={sparql} />
            </div>
          )}

          {/* Validation */}
          {validation && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Validacao</div>
              <ValidationStatus validation={validation} />
            </div>
          )}

          {/* Retry info */}
          {retries !== null && retries > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Autocorrecao</div>
              <div style={styles.retryInfo}>
                {retries} tentativa(s) de correcao realizadas.
              </div>
              {retryErrors.map((err, i) => (
                <div key={i} style={{ ...styles.retryInfo, marginTop: '4px', borderLeft: '3px solid #f9ab00' }}>
                  Tentativa {i + 1}: {typeof err === 'string' ? err : JSON.stringify(err)}
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {Array.isArray(results) && results.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Resultados ({results.length} linhas)</div>
              <ResultsTable results={results} />
            </div>
          )}

          {/* Timing */}
          {timing && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Tempos de execucao</div>
              <TimingBar timing={timing} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
