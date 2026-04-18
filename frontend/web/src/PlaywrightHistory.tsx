import { useEffect, useState, useCallback } from 'react'
import { ScriptModal } from './ScriptModal'
import './PlaywrightHistory.css'

interface PlaywrightExecution {
  id: string
  persona_id: string
  website_id: string
  run_id: string | null
  url: string
  generated_script: string
  browser_name: string
  status: string
  execution_log: string[]
  error_message: string | null
  screenshot_base64: string | null
  duration_ms: number
  created_at: string
  completed_at: string | null
  persona_name: string | null
  website_domain: string | null
  dom_size: number | null
}

const API_BASE = 'http://localhost:5000/api'

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`pw-status-badge pw-status-${status}`}>
      {status === 'success' ? '✓ Passed' : status === 'error' ? '✗ Failed' : status}
    </span>
  )
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

interface PlaywrightHistoryProps {
  onBack?: () => void
}

export function PlaywrightHistory({ onBack }: PlaywrightHistoryProps) {
  const [executions, setExecutions] = useState<PlaywrightExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedExecution, setSelectedExecution] = useState<PlaywrightExecution | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  const fetchExecutions = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/playwright/executions?limit=100`)
      if (!res.ok) throw new Error(`API error (${res.status})`)
      const data = (await res.json()) as PlaywrightExecution[]
      setExecutions(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load executions')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchExecutions()
  }, [fetchExecutions])

  const filtered = executions.filter(ex => {
    const matchesStatus = filterStatus === 'all' || ex.status === filterStatus
    const searchLower = search.toLowerCase()
    const matchesSearch = !search ||
      (ex.persona_name?.toLowerCase().includes(searchLower)) ||
      (ex.website_domain?.toLowerCase().includes(searchLower)) ||
      ex.url.toLowerCase().includes(searchLower)
    return matchesStatus && matchesSearch
  })

  const stats = {
    total: executions.length,
    passed: executions.filter(e => e.status === 'success').length,
    failed: executions.filter(e => e.status === 'error').length,
    avgDuration: executions.length > 0
      ? Math.round(executions.reduce((s, e) => s + (e.duration_ms || 0), 0) / executions.length)
      : 0,
  }

  const openModal = (ex: PlaywrightExecution) => {
    setSelectedExecution(ex)
    setModalOpen(true)
  }

  return (
    <div className="pw-history">
      {/* Page Header */}
      <div className="pw-header">
        <div className="pw-header-left">
          {onBack && (
            <button className="pw-back-btn" onClick={onBack}>
              ← Back
            </button>
          )}
          <div>
            <h1 className="pw-title">Playwright Test History</h1>
            <p className="pw-subtitle">Generated scripts, execution logs, and screenshots</p>
          </div>
        </div>
        <button className="pw-refresh-btn" onClick={fetchExecutions} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {/* Stats Row */}
      <div className="pw-stats-row">
        <div className="pw-stat">
          <span className="pw-stat-value">{stats.total}</span>
          <span className="pw-stat-label">Total Runs</span>
        </div>
        <div className="pw-stat pw-stat-success">
          <span className="pw-stat-value">{stats.passed}</span>
          <span className="pw-stat-label">Passed</span>
        </div>
        <div className="pw-stat pw-stat-error">
          <span className="pw-stat-value">{stats.failed}</span>
          <span className="pw-stat-label">Failed</span>
        </div>
        <div className="pw-stat">
          <span className="pw-stat-value">
            {stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0}%
          </span>
          <span className="pw-stat-label">Pass Rate</span>
        </div>
        <div className="pw-stat">
          <span className="pw-stat-value">{formatDuration(stats.avgDuration)}</span>
          <span className="pw-stat-label">Avg Duration</span>
        </div>
      </div>

      {/* Filters */}
      <div className="pw-filters">
        <input
          className="pw-search"
          type="text"
          placeholder="Search by persona, domain, URL…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="pw-filter-tabs">
          {(['all', 'success', 'error'] as const).map(s => (
            <button
              key={s}
              className={`pw-filter-tab ${filterStatus === s ? 'active' : ''}`}
              onClick={() => setFilterStatus(s)}
            >
              {s === 'all' ? 'All' : s === 'success' ? '✓ Passed' : '✗ Failed'}
              <span className="pw-tab-count">
                {s === 'all' ? executions.length
                  : executions.filter(e => e.status === s).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && <div className="pw-error">{error}</div>}

      {/* Table */}
      {loading ? (
        <div className="pw-loading">Loading executions…</div>
      ) : filtered.length === 0 ? (
        <div className="pw-empty">
          {executions.length === 0
            ? 'No playwright test executions yet. Click "Run Script" on a persona to generate one.'
            : 'No executions match your filters.'}
        </div>
      ) : (
        <div className="pw-table-wrap">
          <table className="pw-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Persona</th>
                <th>Website</th>
                <th>Browser</th>
                <th>Duration</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(ex => (
                <>
                  <tr key={ex.id} className={`pw-row pw-row-${ex.status}`}>
                    <td><StatusBadge status={ex.status} /></td>
                    <td className="pw-cell-persona">
                      <span className="pw-persona-name">{ex.persona_name ?? '—'}</span>
                    </td>
                    <td className="pw-cell-domain">
                      <span className="pw-domain">{ex.website_domain ?? '—'}</span>
                      <span className="pw-url" title={ex.url}>
                        {ex.url.length > 45 ? ex.url.slice(0, 45) + '…' : ex.url}
                      </span>
                    </td>
                    <td>
                      <span className="pw-browser-badge">{ex.browser_name}</span>
                    </td>
                    <td className="pw-cell-duration">{formatDuration(ex.duration_ms)}</td>
                    <td className="pw-cell-date">{formatDate(ex.created_at)}</td>
                    <td className="pw-cell-actions">
                      <button
                        className="pw-action-btn pw-btn-script"
                        onClick={() => openModal(ex)}
                        title="View script and logs"
                      >
                        View Script
                      </button>
                      <button
                        className={`pw-action-btn pw-btn-log ${expandedLog === ex.id ? 'active' : ''}`}
                        onClick={() => setExpandedLog(expandedLog === ex.id ? null : ex.id)}
                        title="Toggle quick log"
                      >
                        {expandedLog === ex.id ? 'Hide Log' : 'Quick Log'}
                      </button>
                    </td>
                  </tr>
                  {expandedLog === ex.id && (
                    <tr key={`${ex.id}-log`} className="pw-log-row">
                      <td colSpan={7}>
                        <div className="pw-inline-log">
                          {ex.execution_log.length === 0 ? (
                            <span className="pw-log-empty">No log entries</span>
                          ) : (
                            ex.execution_log.map((line, i) => (
                              <div key={i} className={`pw-log-line ${line.toLowerCase().startsWith('error') ? 'pw-log-error' : ''}`}>
                                <span className="pw-log-num">{i + 1}</span>
                                {line}
                              </div>
                            ))
                          )}
                          {ex.error_message && (
                            <div className="pw-log-line pw-log-error">
                              <span className="pw-log-num">!</span>
                              {ex.error_message}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Script Modal */}
      {modalOpen && selectedExecution && (
        <ScriptModal
          executionId={selectedExecution.id}
          script={selectedExecution.generated_script}
          logs={selectedExecution.execution_log}
          status={selectedExecution.status}
          url={selectedExecution.url}
          personaName={selectedExecution.persona_name ?? 'Unknown'}
          browserName={selectedExecution.browser_name}
          durationMs={selectedExecution.duration_ms}
          errorMessage={selectedExecution.error_message}
          screenshotBase64={selectedExecution.screenshot_base64}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  )
}
