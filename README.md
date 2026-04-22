# Persona Automation - Test Configuration System

A sophisticated persona-based website testing framework that generates realistic user personas and automates behavioral testing across websites.

## 🎯 Project Structure

```
├── frontend/
│   ├── web/                    # React/TypeScript UI Dashboard
│   │   ├── src/
│   │   │   ├── App.tsx        # Main dashboard
│   │   │   ├── TestConfigurationWizard.tsx  # Multi-step form wizard
│   │   │   ├── TraceViewer.tsx # Execution trace viewer
│   │   │   └── App.css / TestConfigurationWizard.css
│   │   └── package.json
│   └── api/
│       └── app.py            # FastAPI backend server
│
├── src/
│   ├── persona_generator.py   # LLM-powered persona generation
│   ├── website_analyzer.py    # Website feature extraction
│   ├── agent.py              # PersonaAgent ReAct loop
│   └── prompt_builder.py      # Prompt construction
│
├── database/
│   ├── db_manager.py         # SQLite operations
│   └── schema.sql            # Database schema
│
├── config/
│   └── config.yaml           # Configuration settings
│
└── requirements.txt          # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) running locally (primary LLM runtime) — optional fallback keys for OpenAI / Google / GitHub Models

### Setup

1. **Backend Setup**
```bash
cd "c:\Users\Lenovo\part1 pfe"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. **Frontend Setup**
```bash
cd frontend/web
npm install
```

3. **Configure environment**
Create `.env` file with:
```env
# Primary — local Ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3.5:cloud

# Optional fallbacks (only needed if you switch provider on a specific request)
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
GITHUB_TOKEN=your_token
```
Then start Ollama and pull the model:
```bash
ollama serve
ollama pull qwen3.5:cloud
```

### Run

**Terminal 1 - Backend API:**
```bash
python frontend/api/app.py
# API runs on http://localhost:5000
```

**Terminal 2 - Frontend UI:**
```bash
cd frontend/web
npm run dev
# Dashboard runs on http://localhost:5173
```

## 📋 Features

### Multi-Step Test Configuration
1. **Participant Recruitment** - Set URL, number of participants, task objective
2. **Demographics Configuration** - Define demographic distributions with weighted values
3. **Review** - Confirm all settings before execution
4. **Personas Visualization** - View generated personas with descriptions and behaviors

### Personas Generation
- LLM-powered (Ollama by default; OpenAI / Google / GitHub Models as fallbacks)
- Realistic, behavior-driven personas
- Demographic constraints applied
- Same objective across all personas
- Detailed behavioral profiles (speed, style, patience, motivations)

### Test Execution
- Automated browser navigation using Playwright
- ReAct-style thought + action + observation loops
- Real-time trace visualization
- Database tracking of all runs and steps

## 🗄️ Database

SQLite database stores:
- **Websites** - URLs and metadata
- **Personas** - Generated user profiles with behaviors
- **Test Runs** - Execution history with status
- **Steps** - Detailed traces of each interaction
- **Website Analyses** - LLM analysis results

## 🔧 Key Modules

### PersonaGenerator
- Generates diverse personas from website analysis
- Respects demographic constraints
- Creates realistic, typed behaviors
- Used during test configuration submission

### WebsiteAnalyzer
- Extracts features, structure, and content
- Uses LLM for intelligent analysis
- Optional web search for enrichment

### PersonaAgent
- Executes personas' navigation behaviors
- ReAct pattern: Thought → Action → Observation
- Uses MCP tools for browser automation
- Tracks all steps in database

## 📊 API Endpoints

- `POST /api/test-config` - Submit test configuration and generate personas
- `GET /api/test-config/status/{session_id}` - Get generated personas status
- `POST /api/runs/start` - Start a test run for a persona
- `GET /api/runs/{run_id}/steps` - Get execution steps
- `GET /api/stats` - Get dashboard statistics
- `GET /api/personas` - List all personas
- `GET /api/websites` - List all websites

## ✨ Technologies

**Backend:**
- FastAPI - REST API framework
- SQLite - Local database
- LangChain - LLM integration
- Pydantic - Data validation

**Frontend:**
- React 18 - UI framework
- TypeScript - Type safety
- Vite - Build tool

**Automation:**
- Playwright - Browser automation
- MCP - Model Context Protocol for tools

---

Developed for persona-based website testing and UX research automation.
