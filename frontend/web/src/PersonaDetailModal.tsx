import { useEffect } from 'react'

interface PersonaData {
  id: string
  nom?: string
  persona_type?: string
  objectif?: string
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
  actions_site?: string[]
  patterns_comportement?: string[]
  exploration_fonctionnalites?: string[]
}

interface PersonaDetailModalProps {
  persona: PersonaData
  onClose: () => void
}

export function PersonaDetailModal({ persona, onClose }: PersonaDetailModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h2 className="modal-title">{persona.nom ? `${persona.nom}${persona.persona_type ? ` - ${persona.persona_type}` : ''}` : persona.persona_type || 'Unknown Persona'}</h2>
            <button
              type="button"
              className="modal-close"
              onClick={onClose}
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          <div className="modal-body">
            {/* Header Section - Show Persona Type and Name */}
            <div className="detail-section">
              <div className="detail-row">
                <span className="detail-label">Type:</span>
                <span className="detail-value mono">{persona.persona_type || 'Unknown Type'}</span>
              </div>
            </div>

            {/* Primary Objective */}
            {persona.objectif && (
              <div className="detail-section">
                <h3 className="section-title">🎯 Objective</h3>
                <p className="detail-text">{persona.objectif}</p>
              </div>
            )}

            {/* Description */}
            {persona.description && (
              <div className="detail-section">
                <h3 className="section-title">📝 Description</h3>
                <p className="detail-text">{persona.description}</p>
              </div>
            )}

            {/* Core Profile */}
            <div className="detail-section">
              <h3 className="section-title">👤 Profile</h3>
              <div className="profile-grid">
                {persona.device && (
                  <div className="profile-item">
                    <span className="profile-label">Device Preference</span>
                    <span className="profile-value">{persona.device}</span>
                  </div>
                )}
                {persona.vitesse_navigation && (
                  <div className="profile-item">
                    <span className="profile-label">Navigation Speed</span>
                    <span className="profile-value">{persona.vitesse_navigation}</span>
                  </div>
                )}
                {persona.style_navigation && (
                  <div className="profile-item">
                    <span className="profile-label">Navigation Style</span>
                    <span className="profile-value">{persona.style_navigation}</span>
                  </div>
                )}
                {persona.patience_attente_sec && (
                  <div className="profile-item">
                    <span className="profile-label">Wait Patience</span>
                    <span className="profile-value">{persona.patience_attente_sec}s</span>
                  </div>
                )}
                {persona.sensibilite_prix && (
                  <div className="profile-item">
                    <span className="profile-label">Price Sensitivity</span>
                    <span className="profile-value">{persona.sensibilite_prix}</span>
                  </div>
                )}
                {persona.tolerance_erreurs && (
                  <div className="profile-item">
                    <span className="profile-label">Error Tolerance</span>
                    <span className="profile-value">{persona.tolerance_erreurs}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Motivation */}
            {persona.motivation_principale && (
              <div className="detail-section">
                <h3 className="section-title">💡 Motivation</h3>
                <p className="detail-text">{persona.motivation_principale}</p>
              </div>
            )}

            {/* Test Actions - Step by step what they'll do */}
            {persona.actions_site && Array.isArray(persona.actions_site) && persona.actions_site.length > 0 && (
              <div className="detail-section">
                <h3 className="section-title">⚡ Test Actions (Steps)</h3>
                <ol className="detail-list actions-list">
                  {persona.actions_site.map((action, idx) => (
                    <li key={idx}>{action}</li>
                  ))}
                </ol>
              </div>
            )}

            {/* Behavior Patterns */}
            {persona.patterns_comportement && Array.isArray(persona.patterns_comportement) && persona.patterns_comportement.length > 0 && (
              <div className="detail-section">
                <h3 className="section-title">📊 Behavior Patterns</h3>
                <ul className="detail-list">
                  {persona.patterns_comportement.map((pattern, idx) => (
                    <li key={idx}>{pattern}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Feature Exploration */}
            {persona.exploration_fonctionnalites && Array.isArray(persona.exploration_fonctionnalites) && persona.exploration_fonctionnalites.length > 0 && (
              <div className="detail-section">
                <h3 className="section-title">🔍 Feature Exploration</h3>
                <ul className="detail-list">
                  {persona.exploration_fonctionnalites.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Specific Behaviors/Quirks */}
            {persona.comportements_specifiques && Array.isArray(persona.comportements_specifiques) && persona.comportements_specifiques.length > 0 && (
              <div className="detail-section">
                <h3 className="section-title">🔄 Specific Behaviors</h3>
                <ul className="detail-list">
                  {persona.comportements_specifiques.map((behavior, idx) => (
                    <li key={idx}>{behavior}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Pain Points */}
            {persona.douleurs && Array.isArray(persona.douleurs) && persona.douleurs.length > 0 && (
              <div className="detail-section">
                <h3 className="section-title">⚠️ Pain Points & Frustrations</h3>
                <ul className="detail-list pain-points">
                  {persona.douleurs.map((pain, idx) => (
                    <li key={idx}>{pain}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-primary"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
