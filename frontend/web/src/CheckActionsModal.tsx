import { useEffect, useState } from 'react'
import './CheckActionsModal.css'

export type ActionsLoadResult = {
  actions: string[]
  rationale?: string
}

interface CheckActionsModalProps {
  personaName: string
  initialActions: string[]
  onClose: () => void
  onSave: (actions: string[]) => Promise<void>
  /**
   * Optional async loader. When provided, it runs on mount and its result
   * replaces `initialActions` in the textarea. Used to hit the persona action
   * planner endpoint so the user gets a freshly-generated trait-weighted plan
   * to review.
   */
  onLoadActions?: () => Promise<ActionsLoadResult>
  submitLabel?: string
}

export function CheckActionsModal({
  personaName,
  initialActions,
  onClose,
  onSave,
  onLoadActions,
  submitLabel = 'Save Actions',
}: CheckActionsModalProps) {
  const [value, setValue] = useState('')
  const [rationale, setRationale] = useState('')
  const [loading, setLoading] = useState(Boolean(onLoadActions))
  const [loadError, setLoadError] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setValue((initialActions || []).join('\n'))
  }, [initialActions])

  useEffect(() => {
    let cancelled = false
    if (!onLoadActions) return
    setLoading(true)
    setLoadError('')
    onLoadActions()
      .then((result) => {
        if (cancelled) return
        if (result.actions && result.actions.length > 0) {
          setValue(result.actions.join('\n'))
        }
        if (result.rationale) setRationale(result.rationale)
      })
      .catch((err) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Failed to generate actions')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // onLoadActions is expected to be stable from the caller; we only want this
    // to run once when the modal opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  async function handleSave() {
    setSaving(true)
    setError('')
    try {
      const actions = value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)

      if (actions.length === 0) {
        throw new Error('At least one action is required')
      }

      await onSave(actions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save actions')
    } finally {
      // Always release the spinner. The parent may close the modal on success;
      // if it doesn't, the user can still interact (retry, edit, cancel).
      setSaving(false)
    }
  }

  return (
    <>
      <div className="ca-modal-backdrop" onClick={onClose} />
      <div className="ca-modal-dialog" role="dialog" aria-modal="true">
        <div className="ca-modal-header">
          <h3>Actions - {personaName}</h3>
          <button type="button" className="ca-close" onClick={onClose}>
            X
          </button>
        </div>

        <div className="ca-modal-body">
          {loading ? (
            <div className="ca-loading">
              <div className="ca-spinner" aria-hidden="true" />
              <p>Generating persona-specific actions with the LLM…</p>
              <small>Traits like speed, patience and impulsivity are shaping the plan.</small>
            </div>
          ) : (
            <>
              <p className="ca-help">
                Review and edit the generated actions. One action per line.
                When you submit, the Playwright script will be generated automatically.
              </p>
              {rationale && (
                <div className="ca-rationale">
                  <strong>Why this plan:</strong> {rationale}
                </div>
              )}
              {loadError && <p className="ca-error">Action generation failed: {loadError}</p>}
              <textarea
                className="ca-textarea"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="Step 1: Open home page&#10;Step 2: Click login&#10;Step 3: ..."
              />
              {error && <p className="ca-error">{error}</p>}
            </>
          )}
        </div>

        <div className="ca-modal-footer">
          <button type="button" className="ca-btn ca-cancel" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button
            type="button"
            className="ca-btn ca-save"
            onClick={handleSave}
            disabled={saving || loading}
          >
            {saving ? 'Submitting…' : submitLabel}
          </button>
        </div>
      </div>
    </>
  )
}
