import { useState, useEffect } from 'react'
import './TestConfigurationWizard.css'

interface DemographicField {
  id: string
  name: string
  label: string
  values: DemographicValue[]
}

interface DemographicValue {
  id: string
  value: string
  weight: number
}

interface PersonaData {
  id: string
  nom: string
  persona_type?: string
  objectif: string
  description?: string
  device?: string
  vitesse_navigation?: string
  sensibilite_prix?: string
  tolerance_erreurs?: string
  patience_attente_sec?: number
  style_navigation?: string
  comportements_specifiques?: string[]
  motivation_principale?: string
  douleurs?: string[]
}

interface WizardState {
  url: string
  numParticipants: number
  participantTask: string
  examplePersona: string
  demographics: DemographicField[]
}

interface Props {
  onComplete?: (config: WizardState) => void
  onCancel?: () => void
}

export function TestConfigurationWizard({ onComplete, onCancel }: Props) {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<WizardState>({
    url: 'https://www.booking.com',
    numParticipants: 20,
    participantTask: 'Book a hotel for a weekend trip',
    examplePersona:
      'Persona: Clara\nBackground: Clara is a PhD student in Computer Science at a top university...',
    demographics: [
      {
        id: 'age_1',
        name: 'age',
        label: 'Age',
        values: [{ id: 'age_val_1', value: '18-25', weight: 1 }],
      },
      {
        id: 'gender_1',
        name: 'gender',
        label: 'Gender',
        values: [
          { id: 'gender_val_1', value: 'Male', weight: 1 },
          { id: 'gender_val_2', value: 'Female', weight: 1 },
        ],
      },
    ],
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')
  const [generatedPersonas, setGeneratedPersonas] = useState<PersonaData[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)

  // Auto-fetch personas if we have a session ID but no personas yet
  useEffect(() => {
    if (sessionId && currentStep === 4 && generatedPersonas.length === 0) {
      const fetchPersonas = async () => {
        try {
          const response = await fetch(`http://localhost:5000/api/test-config/status/${sessionId}`)
          if (response.ok) {
            const data = await response.json()
            if (data.personas) {
              console.log('📊 Fetched personas from session:', data.personas)
              // Map session personas to PersonaData format if needed
              setGeneratedPersonas(data.personas as PersonaData[])
            }
          }
        } catch (err) {
          console.log('⚠️ Could not fetch personas:', err)
        }
      }
      fetchPersonas()
    }
  }, [sessionId, currentStep, generatedPersonas.length])

  const handleInputChange = (field: keyof Omit<WizardState, 'demographics'>, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }))
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const validateStep1 = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.url.trim()) {
      newErrors.url = 'URL is required'
    } else if (!isValidUrl(formData.url)) {
      newErrors.url = 'Invalid URL format'
    }

    if (formData.numParticipants < 1 || formData.numParticipants > 1000) {
      newErrors.numParticipants = 'Number should be between 1 and 1000'
    }

    if (!formData.participantTask.trim()) {
      newErrors.participantTask = 'Task is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateStep2 = () => {
    const newErrors: Record<string, string> = {}

    if (formData.demographics.length === 0) {
      newErrors.demographics = 'At least one demographic field is required'
    } else {
      for (const field of formData.demographics) {
        if (field.values.length === 0) {
          newErrors[`field_${field.id}`] = `${field.label} must have at least one value`
        }
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (currentStep === 1 && validateStep1()) {
      setCurrentStep(2)
    } else if (currentStep === 2 && validateStep2()) {
      setCurrentStep(3)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
      setErrors({})
    }
  }

  const handleReset = () => {
    if (confirm('Are you sure you want to reset the form?')) {
      setFormData({
        url: '',
        numParticipants: 20,
        participantTask: '',
        examplePersona: '',
        demographics: [
          {
            id: 'age_1',
            name: 'age',
            label: 'Age',
            values: [{ id: 'age_val_1', value: '18-25', weight: 1 }],
          },
        ],
      })
      setCurrentStep(1)
      setErrors({})
      setSubmitMessage('')
    }
  }

  const addDemographicField = () => {
    const newFieldId = `field_${Date.now()}`
    const newField: DemographicField = {
      id: newFieldId,
      name: `field_${formData.demographics.length + 1}`,
      label: 'New Field',
      values: [{ id: `${newFieldId}_val_1`, value: '', weight: 1 }],
    }
    setFormData((prev) => ({
      ...prev,
      demographics: [...prev.demographics, newField],
    }))
  }

  const removeDemographicField = (fieldId: string) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.filter((f) => f.id !== fieldId),
    }))
  }

  const updateFieldLabel = (fieldId: string, label: string) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId ? { ...f, label } : f,
      ),
    }))
  }

  const addValueToField = (fieldId: string) => {
    const newValueId = `${fieldId}_val_${Date.now()}`
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? {
              ...f,
              values: [
                ...f.values,
                { id: newValueId, value: '', weight: 1 },
              ],
            }
          : f,
      ),
    }))
  }

  const removeValueFromField = (fieldId: string, valueId: string) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? { ...f, values: f.values.filter((v) => v.id !== valueId) }
          : f,
      ),
    }))
  }

  const updateFieldValue = (
    fieldId: string,
    valueId: string,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? {
              ...f,
              values: f.values.map((v) =>
                v.id === valueId ? { ...v, value } : v,
              ),
            }
          : f,
      ),
    }))
  }

  const updateFieldWeight = (
    fieldId: string,
    valueId: string,
    weight: number,
  ) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? {
              ...f,
              values: f.values.map((v) =>
                v.id === valueId
                  ? { ...v, weight: Math.max(0, weight) }
                  : v,
              ),
            }
          : f,
      ),
    }))
  }

  const incrementWeight = (fieldId: string, valueId: string) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? {
              ...f,
              values: f.values.map((v) =>
                v.id === valueId ? { ...v, weight: v.weight + 1 } : v,
              ),
            }
          : f,
      ),
    }))
  }

  const decrementWeight = (fieldId: string, valueId: string) => {
    setFormData((prev) => ({
      ...prev,
      demographics: prev.demographics.map((f) =>
        f.id === fieldId
          ? {
              ...f,
              values: f.values.map((v) =>
                v.id === valueId
                  ? { ...v, weight: Math.max(0, v.weight - 1) }
                  : v,
              ),
            }
          : f,
      ),
    }))
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setSubmitMessage('')

    try {
      const response = await fetch('http://localhost:5000/api/test-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string }
        throw new Error(payload.detail || `Request failed (${response.status})`)
      }

      const result = await response.json()
      console.log('✅ API Response:', result)

      setSubmitMessage('✓ Configuration saved and personas generated!')

      // Store session ID for later reference
      if (result.session_id) {
        setSessionId(result.session_id)
      }

      // Extract and store personas from result
      if (result.personas && Array.isArray(result.personas) && result.personas.length > 0) {
        console.log('📊 Setting personas:', result.personas)
        setGeneratedPersonas(result.personas)
        // Move to step 4 after a small delay to ensure state update
        setTimeout(() => {
          setCurrentStep(4)
        }, 100)
      } else {
        // Still move to step 4 even if personas aren't in response
        console.log('⚠️ No personas in response, moving to step 4 anyway')
        setCurrentStep(4)
      }

      // Don't call onComplete here - let it be called when user clicks "Done" on step 4
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to submit'
      console.error('❌ Error:', errorMsg)
      setSubmitMessage(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDone = () => {
    if (onComplete) {
      onComplete(formData)
    }
    if (onCancel) {
      onCancel()
    }
  }

  return (
    <div className="wizard-container">
      {/* Step Indicators */}
      <div className="step-indicators">
        <div className={`step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
          <span className="step-number">1</span>
          <span className="step-label">Participant Recruitment</span>
        </div>
        <div className="step-connector" />
        <div className={`step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
          <span className="step-number">2</span>
          <span className="step-label">Demographics</span>
        </div>
        <div className="step-connector" />
        <div className={`step ${currentStep >= 3 ? 'active' : ''} ${currentStep > 3 ? 'completed' : ''}`}>
          <span className="step-number">3</span>
          <span className="step-label">Review</span>
        </div>
        <div className="step-connector" />
        <div className={`step ${currentStep >= 4 ? 'active' : ''}`}>
          <span className="step-number">4</span>
          <span className="step-label">Personas</span>
        </div>
      </div>

      <div className="wizard-content">
        {/* Step 1: Recruitment Configuration */}
        {currentStep === 1 && (
          <div className="step-panel">
            <h2>Participant Task Config</h2>
            <div className="form-section">
              <div className="form-group">
                <label htmlFor="url">
                  URL of website being tested <span className="required">*</span>
                </label>
                <input
                  id="url"
                  type="url"
                  placeholder="https://www.example.com"
                  value={formData.url}
                  onChange={(e) => handleInputChange('url', e.target.value)}
                  className={errors.url ? 'error' : ''}
                />
                {errors.url && <span className="error-message">{errors.url}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="numParticipants">
                  Number of Participants <span className="required">*</span>
                </label>
                <div className="input-group">
                  <input
                    id="numParticipants"
                    type="number"
                    min="1"
                    max="1000"
                    value={formData.numParticipants}
                    onChange={(e) => handleInputChange('numParticipants', parseInt(e.target.value) || 1)}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      handleInputChange('numParticipants', formData.numParticipants - 1)
                    }
                  >
                    −
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      handleInputChange('numParticipants', formData.numParticipants + 1)
                    }
                  >
                    +
                  </button>
                </div>
                {errors.numParticipants && (
                  <span className="error-message">{errors.numParticipants}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="participantTask">
                  Participant Task <span className="required">*</span>
                </label>
                <input
                  id="participantTask"
                  type="text"
                  placeholder="e.g., Buy a jacket, Book a hotel"
                  value={formData.participantTask}
                  onChange={(e) =>
                    handleInputChange('participantTask', e.target.value)
                  }
                  className={errors.participantTask ? 'error' : ''}
                />
                {errors.participantTask && (
                  <span className="error-message">
                    {errors.participantTask}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="examplePersona">Example Persona</label>
                <textarea
                  id="examplePersona"
                  placeholder="Persona: Clara&#10;Background: Clara is a PhD student..."
                  value={formData.examplePersona}
                  onChange={(e) =>
                    handleInputChange('examplePersona', e.target.value)
                  }
                  rows={6}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Demographics Configuration */}
        {currentStep === 2 && (
          <div className="step-panel">
            <h2>Demographics</h2>
            <div className="form-section demographics-section">
              {formData.demographics.map((field) => (
                <div key={field.id} className="demographic-field">
                  <div className="field-header">
                    <label>Field Name</label>
                    <input
                      type="text"
                      value={field.label}
                      onChange={(e) =>
                        updateFieldLabel(field.id, e.target.value)
                      }
                      placeholder="e.g., Age, Gender"
                    />
                  </div>

                  <table className="values-table">
                    <thead>
                      <tr>
                        <th>Value</th>
                        <th>Weight</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {field.values.map((val) => (
                        <tr key={val.id}>
                          <td>
                            <input
                              type="text"
                              value={val.value}
                              onChange={(e) =>
                                updateFieldValue(field.id, val.id, e.target.value)
                              }
                              placeholder="e.g., 18-25"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              value={val.weight}
                              onChange={(e) =>
                                updateFieldWeight(
                                  field.id,
                                  val.id,
                                  parseInt(e.target.value) || 0,
                                )
                              }
                            />
                          </td>
                          <td className="actions-cell">
                            <button
                              type="button"
                              className="btn-icon decrement"
                              onClick={() =>
                                decrementWeight(field.id, val.id)
                              }
                              title="Decrease"
                            >
                              −
                            </button>
                            <button
                              type="button"
                              className="btn-icon increment"
                              onClick={() =>
                                incrementWeight(field.id, val.id)
                              }
                              title="Increase"
                            >
                              +
                            </button>
                            <button
                              type="button"
                              className="btn-remove-value"
                              onClick={() =>
                                removeValueFromField(field.id, val.id)
                              }
                            >
                              Remove Value
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="field-actions">
                    <button
                      type="button"
                      className="btn-add-choice"
                      onClick={() => addValueToField(field.id)}
                    >
                      + Add Choice
                    </button>
                    <button
                      type="button"
                      className="btn-remove-field"
                      onClick={() => removeDemographicField(field.id)}
                    >
                      Remove Field
                    </button>
                  </div>
                </div>
              ))}

              {errors.demographics && (
                <div className="error-message" style={{ marginTop: '1rem' }}>
                  {errors.demographics}
                </div>
              )}

              <button
                type="button"
                className="btn-add-field"
                onClick={addDemographicField}
              >
                + Add Field
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {currentStep === 3 && (
          <div className="step-panel review-panel">
            <h2>Review Configuration</h2>
            <div className="review-content">
              <div className="review-section">
                <h3>Test Parameters</h3>
                <dl>
                  <dt>Website URL:</dt>
                  <dd>{formData.url}</dd>
                  <dt>Number of Participants:</dt>
                  <dd>{formData.numParticipants}</dd>
                  <dt>Participant Task:</dt>
                  <dd>{formData.participantTask}</dd>
                </dl>
              </div>

              <div className="review-section">
                <h3>Demographics Configuration</h3>
                {formData.demographics.map((field) => (
                  <div key={field.id} className="review-demographic">
                    <h4>{field.label}</h4>
                    <ul>
                      {field.values.map((val) => (
                        <li key={val.id}>
                          {val.value} (weight: {val.weight})
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              {formData.examplePersona && (
                <div className="review-section">
                  <h3>Example Persona</h3>
                  <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {formData.examplePersona}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 4: Generated Personas */}
        {currentStep === 4 && (
          <div className="step-panel">
            <h2>Generated Personas</h2>
            <div className="personas-grid">
              {generatedPersonas.length > 0 ? (
                generatedPersonas.map((persona) => (
                  <div key={persona.id} className="persona-card">
                    <div className="persona-header">
                      <h3>{persona.nom ? `${persona.nom}${persona.persona_type ? ` - ${persona.persona_type}` : ''}` : persona.persona_type || 'Unknown'}</h3>
                    </div>
                    <div className="persona-content">
                      <div className="persona-section">
                        <strong>Objectif:</strong>
                        <p>{persona.objectif}</p>
                      </div>
                      {persona.description && (
                        <div className="persona-section">
                          <strong>Description:</strong>
                          <p>{persona.description}</p>
                        </div>
                      )}
                      <div className="persona-attributes">
                        {persona.device && (
                          <div className="attribute">
                            <span className="attr-label">Device:</span>
                            <span className="attr-value">{persona.device}</span>
                          </div>
                        )}
                        {persona.vitesse_navigation && (
                          <div className="attribute">
                            <span className="attr-label">Speed:</span>
                            <span className="attr-value">{persona.vitesse_navigation}</span>
                          </div>
                        )}
                        {persona.style_navigation && (
                          <div className="attribute">
                            <span className="attr-label">Style:</span>
                            <span className="attr-value">{persona.style_navigation}</span>
                          </div>
                        )}
                        {persona.patience_attente_sec && (
                          <div className="attribute">
                            <span className="attr-label">Patience:</span>
                            <span className="attr-value">{persona.patience_attente_sec}s</span>
                          </div>
                        )}
                      </div>
                      {persona.comportements_specifiques && persona.comportements_specifiques.length > 0 && (
                        <div className="persona-section">
                          <strong>Behaviors:</strong>
                          <ul className="behaviors-list">
                            {persona.comportements_specifiques.map((behavior, idx) => (
                              <li key={idx}>{behavior}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {persona.motivation_principale && (
                        <div className="persona-section">
                          <strong>Motivation:</strong>
                          <p>{persona.motivation_principale}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-personas-message">
                  <p>Fetching personas... This may take a moment.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="wizard-controls">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleReset}
        >
          Reset Form
        </button>

        <div className="nav-buttons">
          {currentStep > 1 && currentStep < 4 && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handlePrevious}
            >
              ← Previous
            </button>
          )}

          {currentStep < 3 && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleNext}
            >
              Next →
            </button>
          )}

          {currentStep === 3 && (
            <button
              type="button"
              className="btn btn-success"
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Submitting...' : 'Submit & Run'}
            </button>
          )}

          {currentStep === 4 && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleDone}
            >
              ✓ Done
            </button>
          )}
        </div>

        {onCancel && currentStep === 1 && (
          <button
            type="button"
            className="btn btn-outline"
            onClick={onCancel}
          >
            Cancel
          </button>
        )}
      </div>

      {submitMessage && (
        <div className={`message ${submitMessage.includes('✓') ? 'success' : 'error'}`}>
          {submitMessage}
        </div>
      )}
    </div>
  )
}

function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}
