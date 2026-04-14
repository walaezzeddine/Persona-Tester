# Backend Structure

Complete backend with organized code, data, and database storage.

## Directory Structure

```
Backend/
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
│
├── config/                  # Configuration files
│   └── config.yaml
│
├── database/                # Database storage
│   ├── persona_automation.db
│   ├── db_manager.py
│   ├── init_db.py
│   └── schema.sql
│
├── data/                    # ⭐ Generated data and resources
│   ├── personas/            # Generated personas (JSON)
│   ├── scenarios/           # Test scenarios (YAML)
│   └── logs/                # Application logs
│
└── src/
    ├── main.py              # Entry point
    ├── __init__.py
    │
    ├── agents/              # AI agents
    │   ├── persona_agent.py
    │   ├── persona_generator.py
    │   └── website_context.py
    │
    ├── api/                 # REST API (ready for expansion)
    ├── schema/              # Pydantic schemas (ready)
    ├── models/              # Database layer
    ├── tools/               # Utilities & tools
    ├── prompts/             # System prompt builder
    ├── utils/               # Configuration
    └── logs/                # Application logs
```

## Key Points

### ⭐ Data Organization

**All generated data lives in `Backend/data/`:**

- **data/personas/** - Generated user personas (JSON files)
  - Created by PersonaGenerator (LLM)
  - Stored in database too
  - Used by frontend via API
  
- **data/scenarios/** - Test scenarios and workflows (YAML files)
  - Drive automation execution
  - Define success criteria and steps
  - Used by PersonaAgent
  
- **data/logs/** - Application execution logs
  - Centralized logging
  - Test runs, agent executions
  - Debugging and monitoring

### Database vs Data Files

| Content | Location | Purpose |
|---------|----------|---------|
| Personas (generated) | `data/personas/` | Source files |
| Personas (metadata) | `database/persona_automation.db` | Indexed lookup |
| Scenarios | `data/scenarios/` | YAML configurations |
| Logs | `data/logs/` | Execution tracking |

### Why This Structure?

```
BACKEND-FRONTEND SEPARATION:

┌─────────────────────────────────────┐
│  FRONTEND (React/TypeScript)        │
│  - UI Components                    │
│  - User interactions                │
│  - Dashboard visualization          │
│  - WebSocket connections            │
└──────────────────┬──────────────────┘
                   │ REST API calls
                   ↓
┌─────────────────────────────────────┐
│  BACKEND (Backend/)                 │
│  ├── src/                           │
│  │   ├── agents/  (AI logic)        │
│  │   ├── api/     (routes)          │
│  │   └── tools/   (utilities)       │
│  ├── data/        (generated data)  │
│  ├── database/    (persistence)     │
│  └── config/      (settings)        │
└─────────────────────────────────────┘
```

**Backend handles:** Generation, Execution, Storage, Retrieval
**Frontend handles:** Display, User Input, Interaction

## Running the Backend

```bash
cd Backend

# Install dependencies
pip install -r requirements.txt

# Run API server
python src/main.py

# Server on http://localhost:5000
```

## API Endpoints (Future)

```
GET  /api/personas           # List all personas
POST /api/personas           # Generate new persona
GET  /api/personas/{id}      # Get persona details

GET  /api/scenarios          # List scenarios
POST /api/scenarios/run      # Execute scenario

GET  /api/results            # Get execution results
```

## Environment Variables

```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=...
GOOGLE_API_KEY=...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
```

## Backend vs Frontend Separation

### Frontend (`frontend/`)
- React/TypeScript
- React components
- API client calls
- Dashboard UI
- User interactions

### Backend (`Backend/`)
- Python FastAPI
- AI agents and automation
- Generated data storage
- Database persistence
- Business logic

**Communication:** Frontend → REST API → Backend

## File Organization

| Layer | Location | Purpose |
|-------|----------|---------|
| **API** | `src/api/` | Route definitions |
| **Logic** | `src/agents/` | AI agents, orchestration |
| **Tools** | `src/tools/` | Utilities, extractors |
| **Prompts** | `src/prompts/` | LLM system prompts |
| **Data** | `data/` | Generated personas, scenarios |
| **Storage** | `database/` | SQLite persistence |
| **Config** | `config/` | Application settings |

## Importing in Backend

```python
# From different modules
from ..agents.persona_agent import PersonaAgent
from ..tools.parser import parse_response
from ..utils.config import Config
```

## Next Steps

1. **Add API routes** in `src/api/routes.py`
2. **Connect database** in `src/models/db_manager.py`
3. **Add validation schemas** in `src/schema/`
4. **Create tests** directory
5. **Add logging** configuration to `src/utils/`

