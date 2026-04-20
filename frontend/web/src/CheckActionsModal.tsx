import { useEffect, useState } from 'react'
import './CheckActionsModal.css'

interface CheckActionsModalProps {
  personaName: string
  initialActions: string[]
  onClose: () => void
  onSave: (actions: string[]) => Promise<void>
}

export function CheckActionsModal({
  personaName,
  initialActions,
  onClose,
  onSave,
}: CheckActionsModalProps) {
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setValue((initialActions || []).join('\n'))
  }, [initialActions])

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

      await onSave(actions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save actions')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="ca-modal-backdrop" onClick={onClose} />
      <div className="ca-modal-dialog" role="dialog" aria-modal="true">
        <div className="ca-modal-header">
          <h3>Check Actions - {personaName}</h3>
          <button type="button" className="ca-close" onClick={onClose}>
            X
          </button>
        </div>

        <div className="ca-modal-body">
          <p className="ca-help">
            Review and edit actions before sending persona + test context to the LLM.
            One action per line.
          </p>
          <textarea
            className="ca-textarea"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Step 1: Open home page\nStep 2: Click login\nStep 3: ..."
          />
          {error && <p className="ca-error">{error}</p>}
        </div>

        <div className="ca-modal-footer">
          <button type="button" className="ca-btn ca-cancel" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className="ca-btn ca-save" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Actions'}
          </button>
        </div>
      </div>
    </>
  )
}
