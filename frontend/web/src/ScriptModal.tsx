import { useEffect, useRef, useState } from 'react'
import './ScriptModal.css'

const API_BASE = 'http://localhost:5000/api'

export interface ScriptRunResult {
  execution_id: string
  status: string
  generated_script: string
  execution_log: string[]
  error_message: string | null
  duration_ms: number
  screenshot_base64: string | null
}

interface ScriptModalProps {
  executionId: string | null
  script: string
  logs: string[]
  status: string
  url: string
  personaName: string
  browserName: string
  durationMs: number
  errorMessage?: string | null
  screenshotBase64?: string | null
  onClose: () => void
  /** Called after a successful save so the parent can refresh its local state. */
  onScriptUpdated?: (newScript: string) => void
  /** Called after a save-and-run, with the fresh execution result. */
  onRunResult?: (result: ScriptRunResult) => void
}

export function ScriptModal({
  executionId,
  script,
  logs,
  status,
  url,
  personaName,
  browserName,
  durationMs,
  errorMessage,
  screenshotBase64,
  onClose,
  onScriptUpdated,
  onRunResult,
}: ScriptModalProps) {
  const backdropRef = useRef<HTMLDivElement>(null)
  const [editedScript, setEditedScript] = useState(script)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'info' | 'error'; text: string } | null>(null)

  useEffect(() => {
    setEditedScript(script)
  }, [script, executionId])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  const isDirty = editedScript !== script
  const canEdit = Boolean(executionId)
  const busy = saving || running

  const handleCopyScript = async () => {
    try {
      await navigator.clipboard.writeText(editedScript)
    } catch {
      const el = document.createElement('textarea')
      el.value = editedScript
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([editedScript], { type: 'text/javascript' })
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = `playwright_test_${executionId?.slice(0, 8) ?? 'script'}.js`
    a.click()
    URL.revokeObjectURL(objectUrl)
  }

  const persistScript = async (): Promise<boolean> => {
    if (!executionId) {
      setFeedback({ kind: 'error', text: 'No execution to update' })
      return false
    }
    if (!editedScript.trim()) {
      setFeedback({ kind: 'error', text: 'Script cannot be empty' })
      return false
    }

    setSaving(true)
    setFeedback(null)
    try {
      const res = await fetch(`${API_BASE}/playwright/executions/${executionId}/script`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ generated_script: editedScript }),
      })
      if (!res.ok) {
        const payload = (await res.json().catch(() => ({}))) as { detail?: string }
        throw new Error(payload.detail || `Save failed (${res.status})`)
      }
      onScriptUpdated?.(editedScript)
      return true
    } catch (err) {
      setFeedback({ kind: 'error', text: err instanceof Error ? err.message : 'Save failed' })
      return false
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    const ok = await persistScript()
    if (ok) setFeedback({ kind: 'info', text: 'Script saved' })
  }

  const handleSaveAndRun = async () => {
    if (!executionId) return
    const saved = isDirty ? await persistScript() : true
    if (!saved) return

    setRunning(true)
    setFeedback({ kind: 'info', text: 'Running updated script…' })
    try {
      const res = await fetch(`${API_BASE}/playwright/run-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          execution_id: executionId,
          provider: 'ollama',
          browser_name: browserName || 'chromium',
        }),
      })
      if (!res.ok) {
        const payload = (await res.json().catch(() => ({}))) as { detail?: string }
        throw new Error(payload.detail || `Run failed (${res.status})`)
      }
      const result = (await res.json()) as ScriptRunResult
      onRunResult?.(result)
      setFeedback({
        kind: result.status === 'success' ? 'info' : 'error',
        text: `Run ${result.status === 'success' ? 'passed ✓' : 'failed ✗'} in ${(result.duration_ms / 1000).toFixed(1)}s`,
      })
    } catch (err) {
      setFeedback({ kind: 'error', text: err instanceof Error ? err.message : 'Run failed' })
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <div
        className="script-modal-backdrop"
        ref={backdropRef}
        onClick={(e) => {
          if (e.target === backdropRef.current && !busy) onClose()
        }}
      />
      <div className="script-modal" role="dialog" aria-modal="true">
        {/* Header */}
        <div className="script-modal-header">
          <div className="script-modal-meta">
            <span className={`script-status-badge script-status-${status}`}>
              {status === 'success' ? '✓ Passed' : status === 'error' ? '✗ Failed' : status}
            </span>
            <span className="script-modal-persona">{personaName}</span>
            <span className="script-modal-sep">·</span>
            <span className="script-modal-url" title={url}>
              {url.length > 50 ? url.slice(0, 50) + '…' : url}
            </span>
            <span className="script-modal-sep">·</span>
            <span className="script-modal-browser">{browserName}</span>
            <span className="script-modal-sep">·</span>
            <span className="script-modal-duration">{(durationMs / 1000).toFixed(1)}s</span>
            {isDirty && <span className="script-dirty-dot" title="Unsaved changes">● unsaved</span>}
          </div>
          <div className="script-modal-actions">
            <button
              className="script-action-btn script-action-primary"
              onClick={handleSave}
              disabled={!canEdit || !isDirty || busy}
              title={!canEdit ? 'No execution to save to' : isDirty ? 'Save changes' : 'No changes to save'}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              className="script-action-btn script-action-primary"
              onClick={handleSaveAndRun}
              disabled={!canEdit || busy}
              title="Save (if needed) then run this script"
            >
              {running ? 'Running…' : isDirty ? 'Save & Run' : 'Run'}
            </button>
            <button className="script-action-btn" onClick={handleCopyScript} title="Copy to clipboard" disabled={busy}>
              Copy
            </button>
            <button className="script-action-btn" onClick={handleDownload} title="Download .js file" disabled={busy}>
              Download
            </button>
            <button className="script-modal-close" onClick={onClose} title="Close" disabled={busy}>
              ✕
            </button>
          </div>
        </div>

        {feedback && (
          <div className={`script-modal-feedback script-modal-feedback-${feedback.kind}`}>
            {feedback.text}
          </div>
        )}

        <div className="script-modal-body">
          {/* Left: Editable script */}
          <div className="script-pane">
            <div className="pane-label">Generated Script {canEdit ? '(editable)' : ''}</div>
            <textarea
              className="script-code script-code-editor"
              value={editedScript}
              onChange={(e) => setEditedScript(e.target.value)}
              spellCheck={false}
              disabled={!canEdit || busy}
              wrap="off"
            />
          </div>

          {/* Right: Logs + Screenshot */}
          <div className="output-pane">
            <div className="pane-label">Execution Log</div>
            <div className="execution-log">
              {logs.length === 0 ? (
                <span className="log-empty">No log entries</span>
              ) : (
                logs.map((line, i) => (
                  <div key={i} className={`log-line ${line.toLowerCase().startsWith('error') ? 'log-error' : line.toLowerCase().startsWith('warning') ? 'log-warn' : ''}`}>
                    <span className="log-index">{String(i + 1).padStart(2, '0')}</span>
                    <span className="log-text">{line}</span>
                  </div>
                ))
              )}
              {errorMessage && (
                <div className="log-line log-error">
                  <span className="log-index">!!</span>
                  <span className="log-text">{errorMessage}</span>
                </div>
              )}
            </div>

            {screenshotBase64 && (
              <>
                <div className="pane-label" style={{ marginTop: '1.5rem' }}>
                  {status === 'error' ? 'Error Screenshot' : 'Final State'}
                </div>
                <div className="screenshot-container">
                  <img
                    src={`data:image/png;base64,${screenshotBase64}`}
                    alt="Test execution screenshot"
                    className="execution-screenshot"
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
