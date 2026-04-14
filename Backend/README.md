# Backend Structure

This is the reorganized backend following a standard Python project structure.

## Directory Structure

```
Backend/
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
├── config/                  # Configuration files
│   └── config.yaml
├── database/                # SQLite database
│   └── persona_automation.db
│
└── src/
    ├── main.py              # Entry point — run to start API server
    ├── __init__.py
    │
    ├── agents/              # Agent definitions and orchestration
    │   ├── __init__.py
    │   ├── persona_agent.py       # Main automation agent with MCP support
    │   ├── persona_generator.py   # LLM-powered persona generation
    │   └── website_context.py     # Website context analysis
    │
    ├── api/                 # API routes and endpoints
    │   ├── __init__.py
    │   └── routes.py        # FastAPI routes (when ready)
    │
    ├── schema/              # Pydantic validation schemas
    │   └── __init__.py
    │
    ├── models/              # Database models and ORM
    │   ├── __init__.py
    │   └── db_manager.py    # Database connection and queries
    │
    ├── tools/               # Tools and utilities for agents
    │   ├── __init__.py
    │   ├── dom_extractor.py      # Extract DOM structure from pages
    │   ├── parser.py             # Parse LLM responses
    │   ├── web_search_tool.py    # Web search integration
    │   └── website_analyzer.py   # LLM-powered website analysis
    │
    ├── prompts/             # System prompts and prompt builders
    │   ├── __init__.py
    │   └── builder.py       # Build system prompts for LLMs
    │
    ├── utils/               # Configuration and utilities
    │   ├── __init__.py
    │   └── config.py        # Configuration loader
    │
    └── logs/                # Auto-generated log files
        └── __init__.py
```

## Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
python src/main.py

# Server will be available at http://localhost:5000
```

## Module Organization

### `agents/`
Contains AI agent definitions:
- **PersonaAgent**: Main automation engine with MCP (Model Context Protocol) support for browser automation
- **PersonaGenerator**: Generates realistic user personas using LLMs
- **WebsiteContextAgent**: Analyzes websites and provides context

### `tools/`
Reusable tools and utilities:
- **dom_extractor.py**: Extracts page structure for LLM understanding
- **parser.py**: Parses and processes LLM responses
- **web_search_tool.py**: Integrates web search for information gathering
- **website_analyzer.py**: Analyzes websites using LLMs

### `prompts/`
Manages system prompts:
- **builder.py**: Builds context-aware system prompts for different scenarios

### `models/`
Database layer:
- **db_manager.py**: SQLite database connection and ORM

### `utils/`
Configuration and utilities:
- **config.py**: Loads configuration from `config/config.yaml` and environment variables

### `api/`
API endpoints (FastAPI):
- Routes for persona management
- Scenario execution
- Results retrieval

## Importing Modules

Use relative imports within the Backend:

```python
# From agents
from ..tools.parser import parse_response
from ..utils.config import Config
from ..prompts.builder import build_system_prompt

# From tools
from ..agents.persona_agent import PersonaAgent
```

## Environment Variables

Create a `.env` file with:

```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=...
GOOGLE_API_KEY=...
SERPER_API_KEY=...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
```

## Testing

```bash
# Test imports
python -c "from src.agents import PersonaAgent; print('✓ PersonaAgent OK')"
python -c "from src.tools import WebSearchTool; print('✓ WebSearchTool OK')"

# Run backend
python src/main.py
```

## Key Files Reference

- **Entry Point**: `src/main.py`
- **Main Agent**: `src/agents/persona_agent.py`
- **System Prompts**: `src/prompts/builder.py`
- **Database**: `src/models/db_manager.py`
- **Config**: `config/config.yaml`

