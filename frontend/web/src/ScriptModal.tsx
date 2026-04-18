import { useEffect, useRef } from 'react'
import './ScriptModal.css'

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
}: ScriptModalProps) {
  const backdropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleCopyScript = async () => {
    try {
      await navigator.clipboard.writeText(script)
    } catch {
      // fallback
      const el = document.createElement('textarea')
      el.value = script
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([script], { type: 'text/javascript' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `playwright_test_${executionId?.slice(0, 8) ?? 'script'}.js`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <div
        className="script-modal-backdrop"
        ref={backdropRef}
        onClick={(e) => {
          if (e.target === backdropRef.current) onClose()
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
          </div>
          <div className="script-modal-actions">
            <button className="script-action-btn" onClick={handleCopyScript} title="Copy to clipboard">
              Copy
            </button>
            <button className="script-action-btn" onClick={handleDownload} title="Download .js file">
              Download
            </button>
            <button className="script-modal-close" onClick={onClose} title="Close">
              ✕
            </button>
          </div>
        </div>

        <div className="script-modal-body">
          {/* Left: Script */}
          <div className="script-pane">
            <div className="pane-label">Generated Script</div>
            <pre className="script-code">
              <code>{script}</code>
            </pre>
          </div>

          {/* Right: Logs + Screenshot */}
          <div className="output-pane">
            {/* Execution Logs */}
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

            {/* Screenshot */}
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
