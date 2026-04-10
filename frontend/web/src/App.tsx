import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { TraceViewer } from './TraceViewer'
import { TestConfigurationWizard } from './TestConfigurationWizard'
import { PersonaDetailModal } from './PersonaDetailModal'

type Stats = {
  websites: number
  personas: number
  test_runs: number
  success_rate: number
}

type Website = {
  id: string
  domain: string
  type: string
  persona_count: number
  analysis_count: number
  created_at: string
}

type Persona = {
  id: string
  name?: string
  nom?: string
  persona_type?: string
  speed?: string
  vitesse_navigation?: string
  device: string
  website_domain?: string
  objective?: string
  objectif?: string
  is_active?: boolean
  description?: string
  sensibilite_prix?: string
  tolerance_erreurs?: string
  patience_attente_sec?: number
  style_navigation?: string
  comportements_specifiques?: string[]
  motivation_principale?: string
  douleurs?: string[]
  actions_site?: string[]
  patterns_comportement?: string[]
  exploration_fonctionnalites?: string[]
}

type Run = {
  id: string
  persona_name: string
  website: string
  status: string
  steps_count: number
  duration: number | null
}

type GenerateResponse = {
  success: boolean
  personas_generated: number
  message: string
}

type StartRunResponse = {
  success: boolean
  run_id: string
  status: string
  steps: number
  duration_sec: number
}

const API_BASE = 'http://localhost:5000/api'

function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [websites, setWebsites] = useState<Website[]>([])
  const [personas, setPersonas] = useState<Persona[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [showWizard, setShowWizard] = useState(false)
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)

  const [url, setUrl] = useState('https://www.booking.com')
  const [provider, setProvider] = useState('groq')
  const [numPersonas, setNumPersonas] = useState(20)
  const [submitting, setSubmitting] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')
  const [runningPersonaId, setRunningPersonaId] = useState<string | null>(null)
  const [runMessage, setRunMessage] = useState('')

  const activePersonas = useMemo(() => personas.filter((p) => p.is_active).length, [personas])

  async function fetchJson<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`)
    if (!response.ok) {
      throw new Error(`API ${path} failed (${response.status})`)
    }
    return response.json()
  }

  async function loadDashboard() {
    setLoading(true)
    setError('')
    try {
      const [statsData, websitesData, personasData, runsData] = await Promise.all([
        fetchJson<Stats>('/stats'),
        fetchJson<Website[]>('/websites'),
        fetchJson<Persona[]>('/personas'),
        fetchJson<Run[]>('/runs'),
      ])
      setStats(statsData)
      setWebsites(websitesData)
      setPersonas(personasData)
      setRuns(runsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error while loading data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setSubmitMessage('')
    try {
      const response = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          provider,
          num_personas: numPersonas,
        }),
      })

      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string }
        throw new Error(payload.detail || `Generation failed (${response.status})`)
      }

      const payload = (await response.json()) as GenerateResponse
      setSubmitMessage(payload.message || `Generated ${payload.personas_generated} personas`)
      await loadDashboard()
    } catch (err) {
      setSubmitMessage(err instanceof Error ? err.message : 'Failed to generate personas')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRunTest(personaId: string) {
    setRunningPersonaId(personaId)
    setRunMessage('')
    try {
      const response = await fetch(`${API_BASE}/runs/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona_id: personaId }),
      })

      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string }
        throw new Error(payload.detail || `Run failed (${response.status})`)
      }

      const payload = (await response.json()) as StartRunResponse
      setRunMessage(
        `Run ${payload.run_id} finished (${payload.status}) in ${payload.duration_sec.toFixed(1)}s with ${payload.steps} steps.`,
      )
      await loadDashboard()
    } catch (err) {
      setRunMessage(err instanceof Error ? err.message : 'Failed to run persona test')
    } finally {
      setRunningPersonaId(null)
    }
  }

  function handlePersonaClick(persona: Persona) {
    setSelectedPersona(persona)
    setIsDetailModalOpen(true)
  }

  function handleCloseDetailModal() {
    setIsDetailModalOpen(false)
    setTimeout(() => setSelectedPersona(null), 300) // Wait for animation
  }

  return (
    <main className="dashboard">
      <section className="hero-panel">
        <p className="eyebrow">Persona Automation</p>
        <h1>Behavior Testing Command Center</h1>
        <p className="subtitle">
          Generate realistic personas, monitor website coverage, and inspect execution runs from one place.
        </p>
        <div className="hero-actions">
          <button className="refresh-btn" onClick={loadDashboard} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
          <button
            className="wizard-btn"
            onClick={() => setShowWizard(true)}
          >
            ✨ New Test Configuration
          </button>
        </div>
        {error && <p className="status error">{error}</p>}
      </section>

      <section className="stats-grid">
        <article className="stat-card">
          <h3>Websites</h3>
          <p>{stats?.websites ?? 0}</p>
        </article>
        <article className="stat-card">
          <h3>Personas</h3>
          <p>{stats?.personas ?? 0}</p>
        </article>
      </section>

      <section className="generate-panel">
        <h2>Generate New Personas</h2>
        <form className="generate-form" onSubmit={handleGenerate}>
          <label>
            Website URL
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              required
            />
          </label>

          <label>
            Provider
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="groq">Groq</option>
              <option value="openai">OpenAI</option>
              <option value="github">GitHub Models</option>
              <option value="google">Google</option>
            </select>
          </label>

          <label>
            Persona Count
            <input
              type="number"
              min={1}
              max={10}
              value={numPersonas}
              onChange={(e) => setNumPersonas(Number(e.target.value))}
            />
          </label>

          <button type="submit" disabled={submitting}>
            {submitting ? 'Generating...' : 'Generate'}
          </button>
        </form>
        {submitMessage && <p className="status">{submitMessage}</p>}
      </section>

      <section className="data-grid">
        <article className="panel">
          <h2>Websites</h2>
          <ul className="list">
            {websites.slice(0, 8).map((site) => (
              <li key={site.id}>
                <div>
                  <strong>{site.domain}</strong>
                  <span>{site.type}</span>
                </div>
                <small>
                  Personas {site.persona_count} | Analyses {site.analysis_count}
                </small>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h2>Personas</h2>
          <ul className="list">
            {personas.slice(0, 8).map((persona) => (
              <li key={persona.id} style={{ cursor: 'pointer' }} onClick={() => handlePersonaClick(persona)}>
                <div>
                  <strong>{persona.nom ? `${persona.nom}${persona.persona_type ? ` - ${persona.persona_type}` : ''}` : persona.persona_type || persona.name || 'Unknown'}</strong>
                  <span>
                    {persona.device} | {persona.speed || persona.vitesse_navigation}
                  </span>
                </div>
                <div className="persona-actions">
                  <small>{persona.website_domain}</small>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRunTest(persona.id)
                    }}
                    disabled={runningPersonaId === persona.id}
                  >
                    {runningPersonaId === persona.id ? 'Running...' : 'Run test'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {runMessage && <p className="status">{runMessage}</p>}
        </article>

        <article className="panel full-width">
          <h2>Recent Runs</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Persona</th>
                  <th>Website</th>
                  <th>Status</th>
                  <th>Steps</th>
                  <th>Duration</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 12).map((run) => (
                  <tr key={run.id}>
                    <td>{run.persona_name}</td>
                    <td>{run.website}</td>
                    <td>{run.status}</td>
                    <td>{run.steps_count}</td>
                    <td>{run.duration ? `${run.duration.toFixed(1)}s` : '-'}</td>
                    <td>
                      <button
                        type="button"
                        className="trace-btn"
                        onClick={() => setSelectedRunId(run.id)}
                      >
                        View Trace
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        {selectedRunId && (
          <div className="trace-panel">
            <div className="trace-panel-header">
              <h2>Trace Viewer</h2>
              <button
                type="button"
                className="close-btn"
                onClick={() => setSelectedRunId(null)}
              >
                ✕
              </button>
            </div>
            <TraceViewer runId={selectedRunId} />
          </div>
        )}

        {/* Test Configuration Wizard Modal */}
        {showWizard && (
          <div className="modal-overlay">
            <div className="modal-content wizard-modal">
              <button
                className="modal-close-btn"
                onClick={() => setShowWizard(false)}
              >
                ✕
              </button>
              <TestConfigurationWizard
                onComplete={() => {
                  setShowWizard(false)
                  loadDashboard()
                }}
                onCancel={() => setShowWizard(false)}
              />
            </div>
          </div>
        )}

        {/* Persona Detail Modal */}
        {isDetailModalOpen && selectedPersona && (
          <PersonaDetailModal
            persona={{
              id: selectedPersona.id,
              nom: selectedPersona.nom || selectedPersona.name,
              persona_type: selectedPersona.persona_type,
              objectif: selectedPersona.objectif || selectedPersona.objective,
              description: selectedPersona.description,
              device: selectedPersona.device,
              vitesse_navigation: selectedPersona.vitesse_navigation || selectedPersona.speed,
              sensibilite_prix: selectedPersona.sensibilite_prix,
              tolerance_erreurs: selectedPersona.tolerance_erreurs,
              patience_attente_sec: selectedPersona.patience_attente_sec,
              style_navigation: selectedPersona.style_navigation,
              comportements_specifiques: selectedPersona.comportements_specifiques,
              motivation_principale: selectedPersona.motivation_principale,
              douleurs: selectedPersona.douleurs,
              actions_site: selectedPersona.actions_site,
              patterns_comportement: selectedPersona.patterns_comportement,
              exploration_fonctionnalites: selectedPersona.exploration_fonctionnalites,
            }}
            onClose={handleCloseDetailModal}
          />
        )}
      </section>
    </main>
  )
}

export default App
