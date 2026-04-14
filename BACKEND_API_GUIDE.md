# API Organization - Backend vs Frontend

## ✅ Correct Structure

### Backend (Backend/src/api/)
- **Backend/src/api/routes.py** - FastAPI app and ALL API endpoints
- Handles all business logic
- Database access
- Authentication
- Data processing

### Frontend (frontend/)
- **frontend/api_client.py** - Simple HTTP client to call Backend API
- ONLY makes requests to Backend
- No business logic
- No database access
- Just displays results

## Architecture

```
┌──────────────────────────────────────┐
│  Frontend (React/TypeScript)         │
│  ├─ Components                       │
│  ├─ Pages                            │
│  └─ api_client.py (HTTP calls only)  │
└──────────────┬───────────────────────┘
               │ HTTP Requests
               │ GET/POST/DELETE
               ↓
┌──────────────────────────────────────┐
│  Backend API (Backend/src/api/)      │
│  ├─ /api/personas                    │
│  ├─ /api/personas/generate           │
│  ├─ /api/personas/run                │
│  ├─ /api/results                     │
│  └─ Database access & business logic │
└──────────────────────────────────────┘
```

## File Organization

### Backend - API Implementation
```
Backend/src/api/
├── routes.py          # ⭐ ALL API ENDPOINTS HERE
├── __init__.py
└── [future auth.py, schemas.py, etc]
```

### Frontend - API Client Only
```
frontend/
├── api_client.py      # ⭐ Simple HTTP client
├── src/
│   ├── components/
│   ├── pages/
│   └── [UI code]
└── [React/TypeScript files]
```

## API Endpoints (Backend)

All these endpoints are in **Backend/src/api/routes.py**:

```python
@app.get("/api/personas")
async def list_personas():
    """List all personas"""
    
@app.post("/api/personas/generate")
async def generate_personas(request: GeneratePersonasRequest):
    """Generate new personas"""
    
@app.post("/api/personas/run")
async def run_persona(request: RunPersonaRequest):
    """Run a persona automation"""
    
@app.get("/api/results/{result_id}")
async def get_results(result_id: str):
    """Get execution results"""
    
@app.delete("/api/personas/{persona_id}")
async def delete_persona(persona_id: str):
    """Delete a persona"""
```

## Frontend - API Client Usage

**frontend/api_client.py** provides simple functions:

```python
# Get all personas
personas = await get_personas()

# Generate new personas
result = await generate_personas(
    url="https://example.com",
    num_personas=3,
    provider="groq"
)

# Run a persona
execution = await run_persona(
    persona_id="persona_123",
    start_url="https://example.com"
)

# Get results
results = await get_results(result_id="run_456")
```

## Why This Structure?

✅ **Backend owns API**
- Business logic in one place
- Can scale independently
- Easy to add authentication
- Easier to test
- Professional architecture

❌ **Frontend does NOT implement API**
- Frontend is only UI layer
- No direct database access
- No business logic
- Just displays Backend results

## Starting Both Services

```bash
# Terminal 1 - Backend API
cd Backend
python src/main.py
# Running on http://localhost:5000

# Terminal 2 - Frontend UI
cd frontend
npm start
# Running on http://localhost:3000

# Frontend calls Backend at:
# http://localhost:5000/api/personas
# http://localhost:5000/api/personas/generate
# etc.
```

## Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=...
LLM_PROVIDER=openai
```

### Frontend (.env.local)
```
REACT_APP_API_URL=http://localhost:5000
```

## What Was Changed

| Before | After | Location |
|--------|-------|----------|
| API in Frontend | API in Backend | Backend/src/api/routes.py |
| frontend/api/app.py | Moved to Backend | ✅ Now in Backend |
| Direct DB access from Frontend | No DB access in Frontend | ✅ Only in Backend |
| Mixed concerns | Clear separation | ✅ Clean architecture |

## Summary

- ✅ **API is now in Backend** (Backend/src/api/routes.py)
- ✅ **Frontend only has HTTP client** (frontend/api_client.py)
- ✅ **Clear separation of concerns**
- ✅ **Professional architecture**
- ✅ **Easy to scale and test**

