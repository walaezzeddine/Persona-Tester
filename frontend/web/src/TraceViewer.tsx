import { useEffect, useState } from 'react'

type TraceEntry = {
  timestamp: number
  kind: 'action' | 'thought' | 'observation'
  importance: number
  content: string
  description?: string
  action: string
  target: string | null
  parsed_input?: Record<string, any>
  is_error: boolean
}

type TraceViewerProps = {
  runId: string
}

const API_BASE = 'http://localhost:5000/api'

/**
 * Extract field name from thought text using common patterns
 */
function extractFieldNameFromThought(thought: string): string | null {
  if (!thought) return null
  
  // Look for patterns: "field name" field, "field name" input, "field name" textbox
  const patterns = [
    /['"]([^'"]+)['"]\s+(?:field|input|textbox|dropdown)/i,
    /(?:field|input|textbox)\s+['"]([^'"]+)['"]\s+/i,
    /into\s+(?:the\s+)?['"]?([^'"\n]+?)['"]?\s+(?:field|input|textbox)/i,
    /from\s+(?:the\s+)?['"]?([^'"\n]+?)['"]?\s+(?:dropdown|select)/i,
  ]
  
  for (const pattern of patterns) {
    const match = thought.match(pattern)
    if (match && match[1]) return match[1].trim()
  }
  return null
}

/**
 * Extract quoted text or element description from thought
 */
function extractElementFromThought(thought: string): string | null {
  if (!thought) return null
  
  // Look for quoted text like "Allow all" or 'Pricing'
  const quotedMatch = thought.match(/['"]([^'"]+)['"](?:\s+(?:button|link|item))?/)
  if (quotedMatch && quotedMatch[1]) return quotedMatch[1].trim()
  
  // Look for words followed by "button" or "link"
  const buttonMatch = thought.match(/(\w+\s+\w+)\s+(?:button|link|item)/i)
  if (buttonMatch && buttonMatch[1]) return buttonMatch[1].trim()
  
  return null
}

/**
 * Format action step with human-readable description
 * Primarily uses thought/description field, with fallback to parsed JSON
 */
function formatActionStep(
  action: string,
  target: string | null,
  description?: string,
  parsedInput?: Record<string, any>,
): string {
  let parsed: any = parsedInput
  
  // If no parsedInput provided, try to parse target
  if (!parsed && target) {
    try {
      parsed = JSON.parse(target)
    } catch {
      parsed = null
    }
  }

  switch (action) {
    case 'browser_navigate': {
      const url = parsed?.url
      if (url) return `Navigating to ${url}`
      if (description) return description.substring(0, 80)
      return 'Navigating to website'
    }

    case 'browser_click': {
      // First try to extract element from thought
      const element = description ? extractElementFromThought(description) : null
      if (element) return `Clicking '${element}'`
      if (description) return description.substring(0, 80)
      return 'Clicking on element'
    }

    case 'browser_snapshot':
      return 'Reading page content'

    case 'browser_type': {
      const text = parsed?.text || ''
      const fieldName = description ? extractFieldNameFromThought(description) : null
      if (text && fieldName) return `Typing '${text}' into ${fieldName}`
      if (text && description) return `Typing '${text}' into field`
      if (description) return description.substring(0, 80)
      return 'Typing text into field'
    }

    case 'browser_evaluate': {
      // Check if it's a scroll action
      if (description && description.toLowerCase().includes('scroll')) {
        return 'Scrolling down the page'
      }
      if (description) return description.substring(0, 60)
      return 'Evaluating page'
    }

    case 'browser_select_option': {
      const values = parsed?.values || parsed?.value
      const valueStr = Array.isArray(values) ? values[0] : values
      const fieldName = description ? extractFieldNameFromThought(description) : null
      
      if (valueStr && fieldName) return `Selecting '${valueStr}' in ${fieldName}`
      if (valueStr) return `Selecting '${valueStr}'`
      if (description) return description.substring(0, 80)
      return 'Selecting option'
    }

    case 'browser_fill_form': {
      const fieldCount = parsed?.fields?.length || 0
      if (fieldCount > 0) return `Filling ${fieldCount} form field${fieldCount !== 1 ? 's' : ''}`
      return 'Filling form fields'
    }

    case 'browser_handle_dialog':
      return 'Handling dialog popup'

    case 'browser_press_key': {
      const key = parsed?.key
      if (key) return `Pressing ${key} key`
      return 'Pressing key'
    }

    case 'browser_wait_for':
      return 'Waiting for page to load'

    case 'browser_navigate_back':
      return 'Going back to previous page'

    case 'browser_take_screenshot':
      return 'Taking screenshot'

    case 'DONE':
      if (description) return description.substring(0, 100)
      return 'Task completed'

    case 'DONE_REJECTED':
      return 'Completion rejected'

    default: {
      if (description) return description.substring(0, 80)
      return `Executing ${action.replace('browser_', '').replace(/_/g, ' ')}`
    }
  }
}

/**
 * Get shortened badge label for action type
 */
function getActionBadgeLabel(action: string): string {
  const actionMap: Record<string, string> = {
    browser_navigate: 'navigate',
    browser_click: 'click',
    browser_snapshot: 'read',
    browser_type: 'type',
    browser_evaluate: 'scroll',
    browser_select_option: 'select',
    browser_fill_form: 'fill',
    browser_wait_for: 'wait',
    browser_navigate_back: 'back',
    browser_take_screenshot: 'capture',
    browser_press_key: 'press',
    browser_handle_dialog: 'dialog',
    DONE: 'done',
    DONE_REJECTED: 'done',
  }

  return actionMap[action] || action.replace('browser_', '').replace(/_/g, ' ')
}

export function TraceViewer({ runId }: TraceViewerProps) {
  const [traceEntries, setTraceEntries] = useState<TraceEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'action' | 'reasoning'>('action')

  useEffect(() => {
    async function fetchTrace() {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${API_BASE}/runs/${runId}/trace`)
        if (!response.ok) {
          throw new Error(`Failed to fetch trace (${response.status})`)
        }
        const data = (await response.json()) as TraceEntry[]
        setTraceEntries(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load trace')
      } finally {
        setLoading(false)
      }
    }

    fetchTrace()
  }, [runId])

  if (loading) {
    return <div className="trace-viewer">Loading trace...</div>
  }

  if (error) {
    return <div className="trace-viewer error">{error}</div>
  }

  // Action Trace: one card per step, showing action and target
  const actionTrace = Array.from(
    new Map(
      traceEntries
        .filter((e) => e.kind === 'action')
        .map((e) => [e.timestamp, e]),
    ).values(),
  )

  // Reasoning Trace: all entries with kind, importance, content
  const reasoningTrace = traceEntries

  return (
    <div className="trace-viewer">
      <div className="trace-tabs">
        <button
          className={`trace-tab ${activeTab === 'action' ? 'active' : ''}`}
          onClick={() => setActiveTab('action')}
        >
          Action Trace
        </button>
        <button
          className={`trace-tab ${activeTab === 'reasoning' ? 'active' : ''}`}
          onClick={() => setActiveTab('reasoning')}
        >
          Reasoning Trace
        </button>
      </div>

      {activeTab === 'action' && (
        <div className="action-list">
          {actionTrace.length === 0 ? (
            <p className="empty-state">No actions recorded</p>
          ) : (
            actionTrace.map((entry, idx) => (
              <div key={idx} className={`action-item ${entry.is_error ? 'error' : ''}`}>
                <div className="action-header">
                  <span className="action-num">Step {entry.timestamp}</span>
                  <span className={`action-badge ${entry.is_error ? 'error' : ''}`}>
                    {entry.is_error ? '✗ Error' : '✓'} {getActionBadgeLabel(entry.action)}
                  </span>
                </div>
                <div className="action-description">
                  {formatActionStep(entry.action, entry.target, entry.description, entry.parsed_input)}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'reasoning' && (
        <div className="reasoning-table-container">
          <table className="reasoning-table">
            <thead>
              <tr>
                <th>Step</th>
                <th>Kind</th>
                <th>Importance</th>
                <th>Content</th>
              </tr>
            </thead>
            <tbody>
              {reasoningTrace.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', color: 'var(--muted)' }}>
                    No reasoning trace available
                  </td>
                </tr>
              ) : (
                reasoningTrace.map((entry, idx) => (
                  <tr key={idx}>
                    <td className="step-cell">{entry.timestamp}</td>
                    <td>
                      <span
                        className={`kind-badge kind-${entry.kind}`}
                      >
                        {entry.kind === 'thought' ? '💭' : entry.kind === 'observation' ? '👁' : '⚙'}
                        {' '}
                        {entry.kind}
                      </span>
                    </td>
                    <td className="importance-cell">{(entry.importance * 100).toFixed(0)}%</td>
                    <td className="content-cell">{entry.content}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
