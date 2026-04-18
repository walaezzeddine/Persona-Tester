import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { TraceViewer } from './TraceViewer'
import { TestConfigurationWizard } from './TestConfigurationWizard'
import { PersonaDetailModal } from './PersonaDetailModal'
import { ScriptModal } from './ScriptModal'
import { PlaywrightHistory } from './PlaywrightHistory'

type Stats = {
  websites: number
  personas: number
  test_runs: number
  playwright_executions?: number
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
  website_id?: string
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

type PlaywrightRunResponse = {
  success: boolean
  execution_id: string
  status: string
  generated_script: string
  execution_log: string[]
  error_message: string | null
  duration_ms: number
  has_screenshot: boolean
  screenshot_base64: string | null
}

type PlaywrightExecution = {
  id: string
  persona_id: string
  url: string
  generated_script: string
  browser_name: string
  status: string
  execution_log: string[]
  error_message: string | null
  screenshot_base64: string | null
  duration_ms: number
}

const API_BASE = 'http://localhost:5000/api'

// View type: 'dashboard' | 'playwright-history'
type View = 'dashboard' | 'playwright-history'

function App() {
  const [view, setView] = useState<View>('dashboard')
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

  // Playwright run state
  const [runningScriptPersonaId, setRunningScriptPersonaId] = useState<string | null>(null)
  const [scriptResult, setScriptResult] = useState<PlaywrightRunResponse | null>(null)
  const [scriptModalOpen, setScriptModalOpen] = useState(false)
  const [scriptPersonaName, setScriptPersonaName] = useState('')
  const [scriptPersonaUrl, setScriptPersonaUrl] = useState('')
  const [pwRunMessage, setPwRunMessage] = useState('')

  const [url, setUrl] = useState('https://www.booking.com')
  const [provider, setProvider] = useState('groq')
  const [numPersonas, setNumPersonas] = useState(20)
  const [submitting, setSubmitting] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')
  const [runningPersonaId, setRunningPersonaId] = useState<string | null>(null)
  const [runMessage, setRunMessage] = useState('')

  async function fetchJson<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`)
    if (!response.ok) throw new Error(`API ${path} failed (${response.status})`)
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
        body: JSON.stringify({ url, provider, num_personas: numPersonas }),
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
      const response = await fetch(`${API_BASE}/playwright/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          persona_id: personaId,
          provider: 'groq',
          browser_name: 'chromium',
        }),
      })
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string }
        throw new Error(payload.detail || `Generate script failed (${response.status})`)
      }
      const payload = (await response.json()) as PlaywrightRunResponse
      setRunMessage(
        payload.status === 'error'
          ? `Script generation failed: ${payload.error_message || 'Unknown error'}`
          : `Script generated and saved (${payload.execution_id.slice(0, 8)}).`
      )
      await loadDashboard()
    } catch (err) {
      setRunMessage(err instanceof Error ? err.message : 'Failed to generate script')
    } finally {
      setRunningPersonaId(null)
    }
  }

  async function getLatestExecutionForPersona(personaId: string): Promise<PlaywrightExecution | null> {
    const response = await fetch(
      `${API_BASE}/playwright/executions?persona_id=${encodeURIComponent(personaId)}&limit=1`
    )
    if (!response.ok) {
      const payload = (await response.json()) as { detail?: string }
      throw new Error(payload.detail || `Failed to fetch script (${response.status})`)
    }

    const list = (await response.json()) as Array<{ id: string }>
    if (!Array.isArray(list) || list.length === 0) return null

    const detailResponse = await fetch(`${API_BASE}/playwright/executions/${list[0].id}`)
    if (!detailResponse.ok) {
      const payload = (await detailResponse.json()) as { detail?: string }
      throw new Error(payload.detail || `Failed to fetch script detail (${detailResponse.status})`)
    }

    return (await detailResponse.json()) as PlaywrightExecution
  }

  async function handleViewScript(persona: Persona) {
    setPwRunMessage('')
    setScriptPersonaName(persona.nom || persona.name || 'Unknown')
    setScriptPersonaUrl(persona.website_domain ? `https://${persona.website_domain}` : '')

    try {
      const execution = await getLatestExecutionForPersona(persona.id)
      if (!execution) {
        throw new Error('No script found. Click Run test first to generate one.')
      }

      setScriptResult({
        success: execution.status === 'success',
        execution_id: execution.id,
        status: execution.status,
        generated_script: execution.generated_script,
        execution_log: execution.execution_log || [],
        error_message: execution.error_message,
        duration_ms: execution.duration_ms || 0,
        has_screenshot: Boolean(execution.screenshot_base64),
        screenshot_base64: execution.screenshot_base64,
      })
      setScriptModalOpen(true)
    } catch (err) {
      setPwRunMessage(err instanceof Error ? err.message : 'Failed to open script')
    }
  }

  async function handleRunScript(persona: Persona) {
    setRunningScriptPersonaId(persona.id)
    setPwRunMessage('')
    setScriptPersonaName(persona.nom || persona.name || 'Unknown')
    setScriptPersonaUrl(persona.website_domain ? `https://${persona.website_domain}` : '')

    try {
      const execution = await getLatestExecutionForPersona(persona.id)
      if (!execution) {
        throw new Error('No script available. Click Run test first to generate and save a script.')
      }

      const response = await fetch(`${API_BASE}/playwright/run-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          execution_id: execution.id,
          provider: 'groq',
          browser_name: 'chromium',
        }),
      })
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string }
        throw new Error(payload.detail || `Script run failed (${response.status})`)
      }
      const result = (await response.json()) as PlaywrightRunResponse
      setScriptResult(result)
      setScriptModalOpen(true)
      setPwRunMessage(`Script ${result.status === 'success' ? 'passed ✓' : 'failed ✗'} in ${(result.duration_ms / 1000).toFixed(1)}s`)
      await loadDashboard()
    } catch (err) {
      setPwRunMessage(err instanceof Error ? err.message : 'Failed to run script')
    } finally {
      setRunningScriptPersonaId(null)
    }
  }

  function handlePersonaClick(persona: Persona) {
    setSelectedPersona(persona)
    setIsDetailModalOpen(true)
  }

  function handleCloseDetailModal() {
    setIsDetailModalOpen(false)
    setTimeout(() => setSelectedPersona(null), 300)
  }

  // Playwright History view
  if (view === 'playwright-history') {
    return <PlaywrightHistory onBack={() => setView('dashboard')} />
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
          <button className="wizard-btn" onClick={() => setShowWizard(true)}>
            ✨ New Test Configuration
          </button>
          <button
            className="pw-history-nav-btn"
            onClick={() => setView('playwright-history')}
          >
            🎭 Script History
            {stats?.playwright_executions !== undefined && stats.playwright_executions > 0 && (
              <span className="pw-history-count">{stats.playwright_executions}</span>
            )}
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
        <article className="stat-card">
          <h3>Test Runs</h3>
          <p>{stats?.test_runs ?? 0}</p>
        </article>
        <article className="stat-card">
          <h3>Script Runs</h3>
          <p>{stats?.playwright_executions ?? 0}</p>
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
              <li
                key={persona.id}
                style={{ cursor: 'pointer' }}
                onClick={() => handlePersonaClick(persona)}
              >
                <div>
                  <strong>
                    {persona.nom
                      ? `${persona.nom}${persona.persona_type ? ` - ${persona.persona_type}` : ''}`
                      : persona.persona_type || persona.name || 'Unknown'}
                  </strong>
                  <span>
                    {persona.device} | {persona.speed || persona.vitesse_navigation}
                  </span>
                </div>
                <div className="persona-actions">
                  <small>{persona.website_domain}</small>
                  <div className="persona-btn-row">
                    {/* Run Test button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRunTest(persona.id)
                      }}
                      disabled={runningPersonaId === persona.id || runningScriptPersonaId === persona.id}
                    >
                      {runningPersonaId === persona.id ? 'Running...' : 'Run test'}
                    </button>

                    {/* View Script button */}
                    <button
                      type="button"
                      className="run-script-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleViewScript(persona)
                      }}
                      disabled={runningPersonaId === persona.id || runningScriptPersonaId === persona.id}
                      title="View latest generated script"
                    >
                      View Script
                    </button>

                    {/* Run Script button */}
                    <button
                      type="button"
                      className="run-script-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRunScript(persona)
                      }}
                      disabled={runningPersonaId === persona.id || runningScriptPersonaId === persona.id}
                      title="Run latest saved script on Playwright MCP server"
                    >
                      {runningScriptPersonaId === persona.id ? 'Running…' : 'Run Script'}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {runMessage && <p className="status">{runMessage}</p>}
          {pwRunMessage && (
            <p className={`status ${pwRunMessage.includes('✗') ? 'error' : ''}`}>
              {pwRunMessage}
            </p>
          )}
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
              <button type="button" className="close-btn" onClick={() => setSelectedRunId(null)}>
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
              <button className="modal-close-btn" onClick={() => setShowWizard(false)}>
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

      {/* Script Result Modal */}
      {scriptModalOpen && scriptResult && (
        <ScriptModal
          executionId={scriptResult.execution_id}
          script={scriptResult.generated_script || '// No script generated'}
          logs={scriptResult.execution_log}
          status={scriptResult.status}
          url={scriptPersonaUrl}
          personaName={scriptPersonaName}
          browserName="chromium"
          durationMs={scriptResult.duration_ms}
          errorMessage={scriptResult.error_message}
          screenshotBase64={scriptResult.screenshot_base64}
          onClose={() => setScriptModalOpen(false)}
        />
      )}
    </main>
  )
}

export default App
