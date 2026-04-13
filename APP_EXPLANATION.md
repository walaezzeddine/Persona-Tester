# 📄 Explication Complète: App.tsx et App.py

---

## 🎨 PARTIE 1: App.tsx (Frontend React)

### Fichier: `frontend/web/src/App.tsx`

**Responsabilité:** Component racine React qui affiche le DASHBOARD COMPLET

---

## 📦 Section 1: Imports & Types (Lines 1-71)

### Imports
```typescript
import { useEffect, useMemo, useState } from 'react'  // React hooks
import type { FormEvent } from 'react'               // Type TypeScript
import './App.css'                                   // Styles
import { TraceViewer } from './TraceViewer'         // Execution trace component
import { TestConfigurationWizard } from './...'     // 4-step form wizard
import { PersonaDetailModal } from './...'          // Click persona → details
```

### Type Definitions (8-69)

```typescript
type Stats = {
  websites: number         // Total websites tested
  personas: number         // Total personas generated
  test_runs: number        // Total test executions
  success_rate: number     // % of successful runs
}

type Website = {
  id: string              // website-amazon-fr
  domain: string          // amazon.fr
  type: string            // "ecommerce", "booking", etc.
  persona_count: number   // How many personas for this site
  analysis_count: number  // How many analyses done
  created_at: string      // Timestamp
}

type Persona = {
  id: string              // persona_<timestamp>_<index>_<uuid>
  name?: string           // English name (fallback)
  nom?: string            // French name (primary)
  speed?: string          // rapide/lente (fallback)
  vitesse_navigation?: string   // rapide/lente (primary)
  device: string          // mobile/desktop
  website_domain?: string // Which site
  objective?: string      // English (fallback)
  objectif?: string       // French (primary)
  is_active?: boolean     // Persona is active?
  description?: string    // How they pursue objective
  sensibilite_prix?: string        // haute/faible
  tolerance_erreurs?: string       // haute/faible
  patience_attente_sec?: number    // 5 to 30 seconds
  style_navigation?: string        // impulsif/normal/prudent
  comportements_specifiques?: string[]  // Quirks array
  motivation_principale?: string        // Why they do it
  douleurs?: string[]                   // Pain points array
  actions_site?: string[]               // Steps to perform
  patterns_comportement?: string[]      // Behavior patterns array
  exploration_fonctionnalites?: string[] // Features explored array
}

type Run = {
  id: string              // run_<uuid>
  persona_name: string    // "Léa Dupont"
  website: string         // Domain name
  status: string          // "success" / "failed" / "running"
  steps_count: number     // How many steps completed
  duration: number | null // Time in seconds
}

type GenerateResponse = {
  success: boolean         // Did it work?
  personas_generated: number  // How many made?
  message: string          // Status message
}

type StartRunResponse = {
  success: boolean         // Execution success?
  run_id: string          // ID of test run
  status: string          // Final status
  steps: number           // Steps performed
  duration_sec: number    // Total time
}

const API_BASE = 'http://localhost:5000/api'  // Backend URL
```

---

## 🎯 Section 2: State Management (Lines 73-93)

### All the State Variables

```typescript
// PRIMARY DATA (from API)
const [stats, setStats] = useState<Stats | null>(null)
  // Dashboard statistics (websites count, personas count, etc.)

const [websites, setWebsites] = useState<Website[]>([])
  // All websites tested

const [personas, setPersonas] = useState<Persona[]>([])
  // All personas generated (CRITICAL: max 20 loaded, .slice(0,8) displayed)

const [runs, setRuns] = useState<Run[]>([])
  // All test executions history

// UI STATE (for user interactions)
const [loading, setLoading] = useState(false)
  // Loading indicator

const [error, setError] = useState('')
  // Error messages from API

const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  // Which run's trace to show? (for TraceViewer)

const [showWizard, setShowWizard] = useState(false)
  // Is TestConfigurationWizard modal open?

const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  // Which persona was clicked? (for PersonaDetailModal)

const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  // Is PersonaDetailModal open?

// GENERATE FORM STATE (simple persona generation, not wizard)
const [url, setUrl] = useState('https://www.booking.com')
  // Website URL input

const [provider, setProvider] = useState('groq')
  // LLM provider (groq, openai, github, google)

const [numPersonas, setNumPersonas] = useState(20)
  // How many personas to generate (1-10 in form, but POST no limit)

const [submitting, setSubmitting] = useState(false)
  // Is form submitting?

const [submitMessage, setSubmitMessage] = useState('')
  // Status message after submit

const [runningPersonaId, setRunningPersonaId] = useState<string | null>(null)
  // Which persona is currently running test?

const [runMessage, setRunMessage] = useState('')
  // Status message from test execution

// COMPUTED VALUE
const activePersonas = useMemo(() => personas.filter((p) => p.is_active).length, [personas])
  // Count of active personas (memoized for performance)
```

---

## 🔌 Section 3: API Helper Functions (Lines 95-101)

### fetchJson<T>()
```typescript
async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  // Example: path="/stats" → "http://localhost:5000/api/stats"

  if (!response.ok) {
    throw new Error(`API ${path} failed (${response.status})`)
  }
  return response.json()
}
```

**Usage:** Generic helper to fetch JSON from API with error handling

---

## 📊 Section 4: Load Dashboard (Lines 103-126)

### loadDashboard()
```typescript
async function loadDashboard() {
  setLoading(true)
  setError('')

  try {
    // PARALLELIZE all 4 API calls at once
    const [statsData, websitesData, personasData, runsData] = await Promise.all([
      fetchJson<Stats>('/stats'),           // GET stats
      fetchJson<Website[]>('/websites'),    // GET all websites
      fetchJson<Persona[]>('/personas'),    // GET all personas
      fetchJson<Run[]>('/runs'),            // GET all test runs
    ])

    // Update all state at once
    setStats(statsData)
    setWebsites(websitesData)
    setPersonas(personasData)
    setRuns(runsData)

  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unexpected error')
  } finally {
    setLoading(false)
  }
}

// CALLED ON COMPONENT MOUNT (once)
useEffect(() => {
  loadDashboard()
}, [])
```

**When called:**
- On app startup (useEffect hook)
- After persona generation completes
- After test run completes
- When user clicks "Refresh Data"

---

## 🎬 Section 5: Handlers (Lines 128-193)

### handleGenerate() - Simple Persona Generation
```typescript
async function handleGenerate(event: FormEvent<HTMLFormElement>) {
  event.preventDefault()
  setSubmitting(true)
  setSubmitMessage('')

  try {
    // POST to /api/generate endpoint
    const response = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,              // https://www.booking.com
        provider,         // groq
        num_personas: numPersonas,  // 20
      }),
    })

    if (!response.ok) {
      const payload = (await response.json()) as { detail?: string }
      throw new Error(payload.detail || `Generation failed`)
    }

    const payload = (await response.json()) as GenerateResponse
    setSubmitMessage(`Generated ${payload.personas_generated} personas`)

    // Refresh dashboard to show new personas
    await loadDashboard()

  } catch (err) {
    setSubmitMessage(err instanceof Error ? err.message : 'Failed to generate')
  } finally {
    setSubmitting(false)
  }
}
```

**Used by:** "Generate New Personas" form (NOT the wizard)

---

### handleRunTest() - Execute Test for Persona
```typescript
async function handleRunTest(personaId: string) {
  setRunningPersonaId(personaId)  // Show "Running..." button
  setRunMessage('')

  try {
    // POST to /api/runs/start endpoint
    const response = await fetch(`${API_BASE}/runs/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona_id: personaId }),
    })

    if (!response.ok) {
      throw new Error('Run failed')
    }

    const payload = (await response.json()) as StartRunResponse

    // Show result
    setRunMessage(
      `Run ${payload.run_id} finished (${payload.status}) ` +
      `in ${payload.duration_sec.toFixed(1)}s with ${payload.steps} steps.`
    )

    // Refresh to show new run
    await loadDashboard()

  } catch (err) {
    setRunMessage(err instanceof Error ? err.message : 'Failed to run')
  } finally {
    setRunningPersonaId(null)  // Remove "Running..." button
  }
}
```

**Used by:** "Run test" button in Personas list

---

### handlePersonaClick() - Open Detail Modal
```typescript
function handlePersonaClick(persona: Persona) {
  setSelectedPersona(persona)      // Store which persona
  setIsDetailModalOpen(true)       // Open modal
}

// CALLED WHEN USER CLICKS on persona name/row
```

---

### handleCloseDetailModal() - Close Detail Modal
```typescript
function handleCloseDetailModal() {
  setIsDetailModalOpen(false)

  // Wait 300ms for animation to finish before clearing
  setTimeout(() => setSelectedPersona(null), 300)
}

// CALLED WHEN USER CLICKS:
// - ✕ button
// - Backdrop (outside modal)
// - Presses ESC key
```

---

## 🎨 Section 6: Render/JSX (Lines 195-421)

### Main Structure
```typescript
return (
  <main className="dashboard">

    {/* SECTION 1: Hero Panel */}
    <section className="hero-panel">
      Title + Description + Buttons
    </section>

    {/* SECTION 2: Stats Cards */}
    <section className="stats-grid">
      - Websites count
      - Personas count
      (REMOVED: Active Personas, Success Rate)
    </section>

    {/* SECTION 3: Generate Form */}
    <section className="generate-panel">
      URL + Provider + Persona Count form
    </section>

    {/* SECTION 4: Data Grid */}
    <section className="data-grid">
      - Websites Panel (first 8)
      - Personas Panel (first 8, CLICKABLE)
      - Recent Runs Table (first 12)
      - Trace Viewer (if run selected)
      - Modals (Wizard, Detail)
    </section>
  </main>
)
```

### Sub-component: Personas Panel (Lines 287-315)
```jsx
<article className="panel">
  <h2>Personas</h2>
  <ul className="list">
    {personas.slice(0, 8).map((persona) => (
      <li
        key={persona.id}
        style={{ cursor: 'pointer' }}  // Show it's clickable
        onClick={() => handlePersonaClick(persona)}  // Click → opens modal
      >
        <div>
          <strong>{persona.name || persona.nom}</strong>
          <span>{persona.device} | {persona.vitesse_navigation}</span>
        </div>

        <div className="persona-actions">
          <small>{persona.website_domain}</small>

          <button
            onClick={(e) => {
              e.stopPropagation()  // Don't trigger persona click
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
</article>
```

**Key Points:**
- `.slice(0, 8)` shows ONLY first 8 personas (out of potentially 50+)
- Click persona name → Modal shows full 15 fields
- Click "Run test" → Executes test for that persona
- `e.stopPropagation()` prevents opening modal when clicking "Run test"

### Modals (Lines 371-415)

**1. TestConfigurationWizard Modal** (4-step form)
```jsx
{showWizard && (
  <div className="modal-overlay">
    <div className="modal-content wizard-modal">
      <TestConfigurationWizard
        onComplete={() => {
          setShowWizard(false)
          loadDashboard()  // Refresh dashboard after generation
        }}
        onCancel={() => setShowWizard(false)}
      />
    </div>
  </div>
)}
```

**2. PersonaDetailModal** (shows all 15 fields)
```jsx
{isDetailModalOpen && selectedPersona && (
  <PersonaDetailModal
    persona={{
      id: selectedPersona.id,
      nom: selectedPersona.nom || selectedPersona.name,
      objectif: selectedPersona.objectif || selectedPersona.objective,
      description: selectedPersona.description,
      device: selectedPersona.device,
      vitesse_navigation: selectedPersona.vitesse_navigation || selectedPersona.speed,
      // ... all 15 fields mapped
    }}
    onClose={handleCloseDetailModal}
  />
)}
```

---

## 🎯 Summary: App.tsx Flow

```
User opens app
    ↓
useEffect() → loadDashboard()
    ↓
Fetch: stats + websites + personas + runs
    ↓
Display dashboard with all panels
    ↓
User can:
  1. Click "Refresh Data" → loadDashboard()
  2. Click "✨ New Test Configuration" → setShowWizard(true)
  3. Fill "Generate New Personas" form → handleGenerate()
  4. Click "Run test" → handleRunTest()
  5. Click persona name → handlePersonaClick() → PersonaDetailModal
  6. Click "View Trace" → setSelectedRunId() → TraceViewer
```

---

---

# 🔌 PARTIE 2: App.py (Backend FastAPI)

### Fichier: `frontend/api/app.py`

**Responsabilité:** REST API qui gère TOUTES les opérations backend

---

## 📦 Section 1: Setup & Imports (Lines 1-52)

### Imports
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.db_manager import get_db
from src.persona_generator import PersonaGenerator
from src.website_analyzer import WebsiteAnalyzer
from src.agent import PersonaAgent
```

### FastAPI Setup
```python
app = FastAPI(
    title="Persona Automation Dashboard API",
    version="1.0.0"
)

# CORS Configuration (allow frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        # (Vite dev servers)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, etc.
    allow_headers=["*"],  # All headers allowed
)

db = get_db()  # Singleton database connection
```

---

## 📋 Section 2: Request/Response Models (Lines 55-73)

### Pydantic Models (Data Validation)

```python
class DeleteWebsiteRequest(BaseModel):
    id: str

class GeneratePersonasRequest(BaseModel):
    url: str              # Website to analyze
    num_personas: int = 3 # How many personas (default 3)
    provider: str = "groq"               # Which LLM
    analyzer_model: str | None = None    # Optional analyzer model
    generator_model: str | None = None   # Optional generator model
    output_dir: str = "generated_personas"
    save_analysis: bool = False
    no_scraping: bool = False

class RunPersonaRequest(BaseModel):
    persona_id: str      # Which persona to test
    start_url: str | None = None  # Optional starting URL
```

---

## 🔌 Section 3: Endpoints (GET/POST)

### GET /api/stats
```python
@app.get("/api/stats")
def get_stats():
    """Get dashboard statistics."""

    # Query: Count total websites, personas, runs
    stats = db.get_stats()

    # Calculate success rate from test_runs
    cursor.execute("""
        SELECT COUNT(CASE WHEN status = 'success' THEN 1 END) as success,
               COUNT(*) as total
        FROM test_runs
    """)
    row = cursor.fetchone()
    success_rate = (row[0] / row[1] * 100) if row[1] > 0 else 0

    return {
        "websites": stats["websites"],
        "personas": stats["personas"],
        "test_runs": stats["test_runs"],
        "success_rate": success_rate
    }
```

**Called by:** Frontend on app startup + after any generation

---

### GET /api/websites
```python
@app.get("/api/websites")
def get_websites():
    """Get all websites."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, domain, type, persona_count, analysis_count, created_at
        FROM websites
        ORDER BY created_at DESC
    """)

    websites = []
    for row in cursor.fetchall():
        websites.append({
            "id": row[0],
            "domain": row[1],
            "type": row[2],
            "persona_count": row[3],
            "analysis_count": row[4],
            "created_at": row[5]
        })

    conn.close()
    return websites
```

**Called by:** Frontend on app startup + after generation

---

### GET /api/personas
```python
@app.get("/api/personas")
def get_personas():
    """Get all personas."""
    conn = db._connect()
    cursor = conn.cursor()

    # JOIN personas with websites
    cursor.execute("""
        SELECT p.id, p.nom, p.device, p.vitesse, p.patience_sec,
               p.objectif, p.website_id, p.is_active, p.created_at,
               w.domain, w.type as website_type, p.persona_json
        FROM personas p
        JOIN websites w ON p.website_id = w.id
        ORDER BY p.created_at DESC
    """)

    personas = []
    for row in cursor.fetchall():
        # Parse JSON to get all 15 fields
        persona_data = {}
        try:
            if row[11]:  # persona_json column
                persona_data = json.loads(row[11])
        except:
            pass

        personas.append({
            "id": row[0],
            "nom": row[1],
            "device": row[2],
            "vitesse_navigation": row[3],
            "patience_attente_sec": row[4],
            "objectif": row[5],
            "website_domain": row[9],
            "is_active": bool(row[7]),
            ...persona_data  # Merge all 15 fields
        })

    conn.close()
    return personas
```

**Called by:** Frontend on app startup + after generation

---

### GET /api/runs
```python
@app.get("/api/runs")
def get_runs():
    """Get test execution history."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, p.nom as persona_name, w.domain as website,
               r.status, r.steps_count, r.duration_sec
        FROM test_runs r
        JOIN personas p ON r.persona_id = p.id
        JOIN websites w ON p.website_id = w.id
        ORDER BY r.started_at DESC
    """)

    runs = []
    for row in cursor.fetchall():
        runs.append({
            "id": row[0],
            "persona_name": row[1],
            "website": row[2],
            "status": row[3],
            "steps_count": row[4],
            "duration": row[5]
        })

    conn.close()
    return runs
```

**Called by:** Frontend to show test execution history

---

### POST /api/generate
```python
@app.post("/api/generate")
async def generate_personas(request: GeneratePersonasRequest):
    """Generate personas for a website."""

    try:
        # 1. Add/Get website
        website_id = db.add_website(request.url, "auto")

        # 2. Analyze website (LLM 1)
        analyzer = WebsiteAnalyzer(provider=request.provider)
        website_analysis = analyzer.analyze(request.url)
        analysis_id = db.add_analysis(website_id, website_analysis, request.provider)

        # 3. Generate personas (LLM 2)
        persona_gen = PersonaGenerator(provider=request.provider)
        personas = persona_gen.generate(
            website_analysis,
            num_personas=request.num_personas
        )

        # 4. Save personas to DB
        session_id = db.start_generation_session(
            website_id, analysis_id, request.num_personas, request.provider
        )

        for persona in personas:
            db.add_persona(persona, website_id, session_id=session_id)

        db.complete_generation_session(session_id, len(personas), time.time())

        return {
            "success": True,
            "personas_generated": len(personas),
            "message": f"Generated {len(personas)} personas"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Called by:** "Generate New Personas" form

---

### POST /api/test-config
```python
@app.post("/api/test-config")
async def submit_test_configuration(config: TestConfigurationRequest):
    """
    Main endpoint: Test Configuration Wizard

    Steps:
    1. Analyze website
    2. Generate personas
    3. Save to database
    4. Return personas
    """

    try:
        print(f"📋 Processing test config for {config.url}")

        # STEP 1: Add website
        website_id = db.add_website(
            config.url,
            site_type="test",
            description=f"Task: {config.participantTask}"
        )

        # STEP 2: Analyze website (LLM 1)
        print("🔍 Analyzing website...")
        analyzer = WebsiteAnalyzer(provider="groq", enable_web_search=True)
        website_analysis = analyzer.analyze(config.url)
        analysis_id = db.add_analysis(website_id, website_analysis, "groq")

        # STEP 3: Generate personas (LLM 2)
        print(f"🧠 Generating {config.numParticipants} personas...")
        persona_gen = PersonaGenerator(provider="groq")
        personas = persona_gen.generate(
            website_analysis,
            num_personas=config.numParticipants,  # ← EXACTLY what user entered
            global_objective=config.participantTask,  # ← SHARED objective
            demographics_config={"demographics": [
                {
                    "label": field.label,
                    "values": [{"value": v.value, "weight": v.weight} for v in field.values]
                }
                for field in config.demographics
            ]}
        )

        # STEP 4: Save to database
        session_id = db.start_generation_session(
            website_id, analysis_id, config.numParticipants, "groq"
        )

        generated_count = 0
        persona_ids = []
        for persona in personas:
            persona_id = db.add_persona(persona, website_id, session_id=session_id)
            persona_ids.append(persona_id)
            generated_count += 1

        db.complete_generation_session(session_id, generated_count, time.time())

        print(f"✅ Created {generated_count} personas")

        # STEP 5: Return response
        return {
            "success": True,
            "message": f"Generated {generated_count} personas",
            "session_id": session_id,
            "personas_generated": generated_count,
            "personas": [
                {
                    "id": p.get("id"),
                    "nom": p.get("nom"),
                    "objectif": p.get("objectif"),
                    "description": p.get("description"),
                    "device": p.get("device"),
                    "vitesse_navigation": p.get("vitesse_navigation"),
                    # ... all 15 fields
                }
                for p in personas
            ]
        }

    except Exception as e:
        print(f"❌ Test configuration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Called by:** TestConfigurationWizard on Step 4 submission

---

### POST /api/runs/start
```python
@app.post("/api/runs/start")
async def start_test_run(request: RunPersonaRequest):
    """Execute test for a persona."""

    try:
        # Get persona from DB
        persona = db.get_persona(request.persona_id)

        # Get start URL (from request or from persona)
        start_url = request.start_url or persona.get("website_url")

        # Create agent and run test
        agent = PersonaAgent(persona)

        # Execute main test loop
        result, steps = agent.run()  # ← Autonomous browser testing

        # Save test run result to DB
        run_id = db.add_run(
            persona_id=request.persona_id,
            status=result.get("status"),
            steps_count=len(steps),
            duration_sec=result.get("duration")
        )

        # Save each step
        for i, step in enumerate(steps):
            db.add_step(
                run_id=run_id,
                step_number=i+1,
                thought=step.get("thought"),
                action=step.get("action"),
                result=step.get("result")
            )

        return {
            "success": True,
            "run_id": run_id,
            "status": result.get("status"),
            "steps": len(steps),
            "duration_sec": result.get("duration")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Called by:** "Run test" button in Personas list

---

### GET /api/runs/{run_id}/trace
```python
@app.get("/api/runs/{run_id}/trace")
def get_run_trace(run_id: str):
    """Get detailed execution trace for a test run."""

    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT step_number, thought, action, action_input, result, is_error
        FROM steps
        WHERE run_id = ?
        ORDER BY step_number
    """, (run_id,))

    steps = []
    for row in cursor.fetchall():
        steps.append({
            "number": row[0],
            "thought": row[1],
            "action": row[2],
            "input": row[3],
            "result": row[4],
            "error": bool(row[5])
        })

    conn.close()
    return {"steps": steps}
```

**Called by:** TraceViewer component when user clicks "View Trace"

---

## 🎯 Summary: App.py Endpoint Map

```
FRONTEND CALL          →    BACKEND ENDPOINT        →    WHAT IT DOES
─────────────────────────────────────────────────────────────────────
loadDashboard()        →    GET /api/stats          →    Return stats
                       →    GET /api/websites       →    Return websites
                       →    GET /api/personas       →    Return personas
                       →    GET /api/runs           →    Return runs

handleGenerate()       →    POST /api/generate      →    Generate personas
                                                        (simple form)

handleRunTest()        →    POST /api/runs/start    →    Execute persona test

TestConfigurationWizard →   POST /api/test-config   →    Full flow:
(Step 4 submit)                                      1. Analyze website
                                                      2. Generate personas
                                                      3. Save to DB
                                                      4. Return personas

TraceViewer click      →    GET /api/runs/{id}/trace → Get execution steps
```

---

## 📊 Data Flow Summary

```
FRONTEND (App.tsx)              BACKEND (app.py)            DATABASE (SQLite)
─────────────────────────────────────────────────────────────────────────
render dashboard          →     GET /stats            →     SELECT stats
render panels            →     GET /websites         →     SELECT websites
render personas list     →     GET /personas         →     SELECT personas + JSON
render runs table        →     GET /runs             →     SELECT runs

user submits wizard      →     POST /test-config     →
                                  ├─ LLM 1 analysis
                                  ├─ LLM 2 generation
                                  ├─ INSERT website
                                  ├─ INSERT personas (20)
                                  └─ return response    →     INSERT 20 rows

frontend loads results    ←     response_personas
user clicks persona       →     PersonaDetailModal shows all 15 fields

user clicks "Run test"   →     POST /runs/start      →
                                  ├─ Agent.run()
                                  ├─ Browser testing
                                  └─ return run_id     →     INSERT test_run + steps

user clicks "View Trace" →     GET /runs/{id}/trace  →     SELECT steps
trace display shows       ←     steps array
```

---

## 🎯 Final Concept Map

### Frontend (App.tsx)
**Role:** UI Layer - What user sees + clicks
**Manages:** State, navigation, form inputs, API calls
**Displays:** Dashboard with 4 panels + 2 modals

### Backend (app.py)
**Role:** Business Logic Layer - Processing + Data
**Manages:** LLMs, Database operations, Test execution
**Endpoints:** 6 GET/POST routes

### Together
**Frontend** sends requests → **Backend** executes logic → **Database** stores data
**Database** returns data → **Backend** formats response → **Frontend** displays results

```

