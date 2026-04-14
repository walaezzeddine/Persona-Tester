"""
Persona Automation Dashboard - FastAPI Backend
Professional REST API for the persona generation system
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"📝 Loading .env from: {env_path}")
print(f"📝 .env exists: {env_path.exists()}")

# Backend relative imports
from ..models.db_manager import get_db
from ..agents.persona_generator import PersonaGenerator
from ..tools.website_analyzer import WebsiteAnalyzer
from ..agents.persona_agent import PersonaAgent

try:
    from ..utils.config import Config
except Exception as config_error:
    print(f"Warning: Could not import Config: {config_error}")
    Config = None


app = FastAPI(
    title="Persona Automation Dashboard API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db = get_db()


class DeleteWebsiteRequest(BaseModel):
    id: str


class GeneratePersonasRequest(BaseModel):
    url: str
    num_personas: int = 3
    provider: str = "groq"
    analyzer_model: str | None = None
    generator_model: str | None = None
    output_dir: str = "Backend/data/personas"
    save_analysis: bool = False
    no_scraping: bool = False


class RunPersonaRequest(BaseModel):
    persona_id: str
    start_url: str | None = None


@app.get("/api/stats")
def get_stats():
    """Get dashboard statistics."""
    print("\n🔍 Fetching stats from database...")
    stats = db.get_stats()
    print(f"✅ Stats retrieved: {stats}")

    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(CASE WHEN status = 'success' THEN 1 END) as success,
            COUNT(*) as total
        FROM test_runs
        """
    )
    row = cursor.fetchone()
    success_rate = (row[0] / row[1] * 100) if row[1] > 0 else 0

    cursor.execute(
        """
        SELECT w.type, COUNT(p.id) as count
        FROM personas p
        JOIN websites w ON p.website_id = w.id
        GROUP BY w.type
        """
    )
    personas_by_type = [{"type": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT 'persona' as type, nom as title, created_at as timestamp
        FROM personas
        UNION ALL
        SELECT 'website' as type, domain as title, created_at as timestamp
        FROM websites
        UNION ALL
        SELECT 'analysis' as type, 'Analysis for ' || website_id as title, analyzed_at as timestamp
        FROM website_analyses
        ORDER BY timestamp DESC
        LIMIT 10
        """
    )
    recent_activity = [{"type": row[0], "title": row[1], "timestamp": row[2]} for row in cursor.fetchall()]

    conn.close()

    return {
        "websites": stats["websites"],
        "personas": stats["personas"],
        "test_runs": stats["test_runs"],
        "success_rate": round(success_rate, 1),
        "personas_by_type": personas_by_type,
        "recent_activity": recent_activity,
    }


@app.get("/api/websites")
def get_websites():
    """Get all websites."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT w.id, w.url, w.domain, w.type, w.description, w.created_at,
               COUNT(DISTINCT p.id) as persona_count,
               COUNT(DISTINCT a.id) as analysis_count
        FROM websites w
        LEFT JOIN personas p ON w.id = p.website_id
        LEFT JOIN website_analyses a ON w.id = a.website_id
        GROUP BY w.id
        ORDER BY w.created_at DESC
        """
    )

    websites = []
    for row in cursor.fetchall():
        websites.append(
            {
                "id": row[0],
                "url": row[1],
                "domain": row[2],
                "type": row[3],
                "description": row[4],
                "created_at": row[5],
                "persona_count": row[6],
                "analysis_count": row[7],
            }
        )

    conn.close()
    return websites


@app.get("/api/websites/{website_id}")
def get_website(website_id: str):
    """Get website details."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM websites WHERE id = ?", (website_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Website not found")

    website = {
        "id": row[0],
        "url": row[1],
        "domain": row[2],
        "type": row[3],
        "description": row[4],
        "created_at": row[5],
    }

    cursor.execute(
        """
        SELECT id, description, llm_provider, llm_model, analyzed_at
        FROM website_analyses WHERE website_id = ?
        ORDER BY analyzed_at DESC
        """,
        (website_id,),
    )
    website["analyses"] = [
        {"id": r[0], "description": r[1], "provider": r[2], "model": r[3], "date": r[4]}
        for r in cursor.fetchall()
    ]

    cursor.execute(
        """
        SELECT id, nom, type_persona, device, vitesse, objectif
        FROM personas WHERE website_id = ?
        """,
        (website_id,),
    )
    website["personas"] = [
        {"id": r[0], "name": r[1], "type": r[2], "device": r[3], "speed": r[4], "objective": r[5]}
        for r in cursor.fetchall()
    ]

    conn.close()
    return website


@app.delete("/api/websites")
def delete_website(payload: DeleteWebsiteRequest):
    """Delete a website and its related data."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM personas WHERE website_id = ?", (payload.id,))
    cursor.execute("DELETE FROM website_analyses WHERE website_id = ?", (payload.id,))
    cursor.execute("DELETE FROM generation_sessions WHERE website_id = ?", (payload.id,))
    cursor.execute("DELETE FROM websites WHERE id = ?", (payload.id,))

    conn.commit()
    conn.close()

    return {"success": True}


def _generate_persona_type_from_behavior(persona: dict) -> str:
    """Generate a descriptive type for a persona based on their behavior."""
    # Extract behavior attributes
    vitesse = str(persona.get("vitesse_navigation", "")).lower()
    style = str(persona.get("style_navigation", "")).lower()
    prix = str(persona.get("sensibilite_prix", "")).lower()

    # Determine navigation style
    if "impulsif" in style or "impulsive" in style:
        style_adj = "Impulsif"
    elif "prudent" in style or "careful" in style:
        style_adj = "Prudent"
    else:
        style_adj = "Réfléchi"

    # Price sensitivity
    if "haute" in prix or "high" in prix:
        price_type = "Économe"
    else:
        price_type = "Généreux"

    # Website type
    website_type = str(persona.get("website_type", "")).lower()

    if "e-commerce" in website_type or "shopping" in website_type or "achat" in website_type:
        if "impulsif" in style.lower():
            return "Acheteur Impulsif"
        elif "haute" in prix.lower():
            return "Acheteur Économe"
        else:
            return f"Acheteur {style_adj}"

    elif "voyage" in website_type or "travel" in website_type or "booking" in website_type:
        if "haute" in prix.lower():
            return "Voyageur Économe"
        else:
            return f"Voyageur {style_adj}"

    elif "banc" in website_type or "finance" in website_type or "bank" in website_type:
        if "impulsif" in style.lower():
            return "Client Impulsif"
        else:
            return f"Client {style_adj}"

    else:
        # Default
        return f"Navigateur {style_adj}"


@app.get("/api/personas")
def get_personas():
    """Get all personas."""
    print("\n🔍 Fetching personas from database...")
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT p.id, p.nom, p.type_persona, p.device, p.vitesse, p.patience_sec,
               p.objectif, p.website_id, p.is_active, p.created_at,
               w.domain, w.type as website_type, p.persona_json
        FROM personas p
        JOIN websites w ON p.website_id = w.id
        ORDER BY p.created_at DESC
        """
    )

    personas = []
    for row in cursor.fetchall():
        # Try to parse persona_json
        persona_data = {}
        try:
            if row[12]:
                persona_data = json.loads(row[12])
        except:
            pass

        # Build response - prioritize persona_type from persona_json
        response = {
            "id": row[0],
            "name": row[1],
            "nom": row[1],
            "type": row[2],
            "device": row[3],
            "speed": row[4],
            "vitesse_navigation": row[4],
            "patience": row[5],
            "patience_attente_sec": row[5],
            "objective": row[6],
            "objectif": row[6],
            "website_id": row[7],
            "is_active": bool(row[8]),
            "created_at": row[9],
            "website_domain": row[10],
            "website_type": row[11],
            # Include all detailed fields from persona_json
            **persona_data
        }

        # Ensure persona_type exists - generate it if missing
        if "persona_type" not in response or not response["persona_type"]:
            # Generate persona_type from behavior if missing
            persona_type = _generate_persona_type_from_behavior(response)
            response["persona_type"] = persona_type

        personas.append(response)

    conn.close()
    print(f"✅ Found {len(personas)} personas in database")
    return personas


@app.get("/api/personas/{persona_id}")
def get_persona(persona_id: str):
    """Get persona details."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT p.*, w.domain, w.type as website_type
        FROM personas p
        JOIN websites w ON p.website_id = w.id
        WHERE p.id = ?
        """,
        (persona_id,),
    )

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Persona not found")

    columns = [desc[0] for desc in cursor.description]
    persona = dict(zip(columns, row))

    cursor.execute(
        """
        SELECT id, status, steps_count, duration_sec, started_at
        FROM test_runs WHERE persona_id = ?
        ORDER BY started_at DESC
        """,
        (persona_id,),
    )
    persona["test_runs"] = [
        {"id": r[0], "status": r[1], "steps": r[2], "duration": r[3], "date": r[4]}
        for r in cursor.fetchall()
    ]

    conn.close()
    return persona


@app.post("/api/personas/{persona_id}/toggle")
def toggle_persona(persona_id: str):
    """Toggle persona active status."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute("UPDATE personas SET is_active = NOT is_active WHERE id = ?", (persona_id,))
    conn.commit()

    cursor.execute("SELECT is_active FROM personas WHERE id = ?", (persona_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")

    return {"is_active": bool(row[0])}


@app.post("/api/generate")
def generate_personas(payload: GeneratePersonasRequest):
    """Generate personas for a website URL."""
    if not payload.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        start_time = time.time()
        url = payload.url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        analyzer = WebsiteAnalyzer(
            provider=payload.provider,
            model=payload.analyzer_model,
            temperature=0.5,
            enable_web_search=True,
        )
        website_analysis = analyzer.analyze(url=url, enable_scraping=not payload.no_scraping)

        website_id = db.add_website(
            url,
            website_analysis.get("site_type", website_analysis.get("type", "unknown")),
            website_analysis.get("primary_purpose", ""),
        )
        analysis_id = db.add_analysis(website_id, website_analysis, payload.provider, payload.analyzer_model)

        session_id = db.start_generation_session(
            website_id=website_id,
            analysis_id=analysis_id,
            personas_requested=payload.num_personas,
            llm_provider=payload.provider,
            llm_model=payload.generator_model,
        )

        generator = PersonaGenerator(
            provider=payload.provider,
            model=payload.generator_model,
            temperature=0.8,
        )
        personas = generator.generate(
            website_analysis=website_analysis,
            num_personas=payload.num_personas,
            include_extremes=True,
        )

        output_path = Path(payload.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        generator.save_personas(personas, str(output_path))

        for persona in personas:
            persona_id = persona.get("id", "unknown")
            json_path = str(output_path / f"{persona_id}.json")
            persona["website_type"] = website_analysis.get("site_type", "other")
            db.add_persona(
                persona_data=persona,
                website_id=website_id,
                json_file_path=json_path,
                session_id=session_id,
            )

        duration = time.time() - start_time
        db.complete_generation_session(session_id, len(personas), duration)

        if payload.save_analysis:
            analyzer.save_analysis(website_analysis, str(output_path / "website_analysis.json"))

        return {
            "success": True,
            "website_id": website_id,
            "analysis_id": analysis_id,
            "session_id": session_id,
            "personas_generated": len(personas),
            "duration_sec": round(duration, 1),
            "message": f"Generated {len(personas)} personas for {url}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
def get_runs():
    """Get all test runs."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT r.id, r.persona_id, r.status, r.steps_count, r.duration_sec,
               r.started_at, r.completed_at, p.nom as persona_name, w.domain
        FROM test_runs r
        JOIN personas p ON r.persona_id = p.id
        JOIN websites w ON p.website_id = w.id
        ORDER BY r.started_at DESC
        """
    )

    runs = []
    for row in cursor.fetchall():
        runs.append(
            {
                "id": row[0],
                "persona_id": row[1],
                "status": row[2],
                "steps_count": row[3],
                "duration": row[4],
                "started_at": row[5],
                "completed_at": row[6],
                "persona_name": row[7],
                "website": row[8],
            }
        )

    conn.close()
    return runs


@app.post("/api/runs/start")
def start_persona_run(payload: RunPersonaRequest):
    """Run a navigation test for one persona and store run + steps in DB."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT p.id, p.nom, p.objectif, p.device, p.vitesse, p.patience_sec,
               p.type_persona, p.json_file_path, w.url, w.type
        FROM personas p
        JOIN websites w ON p.website_id = w.id
        WHERE p.id = ?
        """,
        (payload.persona_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Persona not found")

    persona_id = row[0]
    json_file_path = row[7]
    website_url = row[8]
    website_type = row[9]

    persona_data = {
        "id": row[0],
        "nom": row[1],
        "objectif": row[2],
        "device": row[3],
        "vitesse_navigation": row[4],
        "patience_attente_sec": row[5],
        "type_persona": row[6],
        "website_type": website_type,
    }

    if json_file_path and Path(json_file_path).exists():
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    persona_data.update(loaded)
        except Exception:
            pass

    target_url = payload.start_url or website_url
    scenario = {
        "name": "Dashboard persona run",
        "objectif": persona_data.get("objectif") or "Test website navigation",
    }

    config_path = Path(__file__).resolve().parents[2] / "config" / "config.yaml"
    try:
        if Config:
            config = Config(str(config_path))
        else:
            raise ImportError("Config not available")
    except Exception as e:
        print(f"Warning: Could not load config: {e}. Using defaults.")
        # Create a simple config object with defaults
        class SimpleConfig:
            llm_provider = "groq"
            llm_model = "llama-3.3-70b-versatile"
            vision_enabled = False
        config = SimpleConfig()

    run_id = db.start_test_run(
        persona_id=persona_id,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        vision_enabled=bool(getattr(config, "vision_enabled", False)),
    )

    started = time.time()
    try:
        agent = PersonaAgent(user=persona_data, scenario=scenario, config=config, use_mcp=True)
        result = asyncio.run(agent.run_with_mcp(start_url=target_url))

        steps_detail = result.get("steps_detail", []) or []
        for item in steps_detail:
            try:
                # Défensive serialization of action_input
                action_input = item.get("input")
                if isinstance(action_input, (dict, list)):
                    try:
                        action_input = json.dumps(action_input, ensure_ascii=False)
                    except (TypeError, ValueError):
                        action_input = str(action_input)
                elif action_input is None:
                    action_input = ""
                else:
                    action_input = str(action_input)

                # Safe extraction of result text
                result_text = item.get("result_preview") or item.get("reason") or item.get("raw") or ""
                if not isinstance(result_text, str):
                    result_text = str(result_text)

                # Safe extraction of error info
                error_msg = item.get("error")
                error_message = str(error_msg) if error_msg else None

                # Safe int conversion for step number
                try:
                    step_number = int(item.get("step", 0) or 0)
                except (TypeError, ValueError):
                    step_number = 0

                # Save step with defensive handling
                db.add_step(
                    run_id=run_id,
                    step_number=step_number,
                    thought=str(item.get("thought", ""))[:2000],  # Limit length
                    action=str(item.get("action", ""))[:200],
                    action_input=str(action_input)[:2000],
                    result=str(result_text)[:4000],
                    is_error=bool(item.get("error")),
                    error_message=error_message[:500] if error_message else None,
                )
            except Exception as step_error:
                # Log step error but continue (don't crash entire run)
                print(f"⚠️  Failed to save step {item.get('step', '?')}: {step_error}")
                continue

        # Safely determine final status
        try:
            status = "success" if result.get("status") == "completed" else result.get("status", "error")
            final_step_count = int(result.get("steps", len(steps_detail)) or 0)
        except (TypeError, ValueError):
            status = "completed"
            final_step_count = len(steps_detail)

        duration = time.time() - started
        
        try:
            db.complete_test_run(
                run_id=run_id,
                status=status,
                steps_count=final_step_count,
                duration_sec=duration,
                error_message=None,
            )
        except Exception as db_error:
            print(f"⚠️  Failed to complete test run in DB: {db_error}")

        return {
            "success": True,
            "run_id": run_id,
            "status": status,
            "steps": final_step_count,
            "duration_sec": round(duration, 1),
        }
    except Exception as e:
        duration = time.time() - started
        error_str = str(e)[:500]  # Limit error message length
        
        try:
            db.complete_test_run(
                run_id=run_id,
                status="error",
                steps_count=0,
                duration_sec=duration,
                error_message=error_str,
            )
        except Exception as db_error:
            print(f"⚠️  Failed to save error to DB: {db_error}")
        
        print(f"❌ Run failed: {error_str}")
        raise HTTPException(status_code=500, detail=error_str)


@app.get("/api/runs/{run_id}/steps")
def get_run_steps(run_id: str):
    """Get steps for a test run."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT step_number, thought, action, action_input, result, is_error, error_message, duration_ms
        FROM steps WHERE run_id = ?
        ORDER BY step_number
        """,
        (run_id,),
    )

    steps = []
    for row in cursor.fetchall():
        steps.append(
            {
                "step": row[0],
                "thought": row[1],
                "action": row[2],
                "input": row[3],
                "result": row[4],
                "is_error": bool(row[5]),
                "error": row[6],
                "duration_ms": row[7],
            }
        )

    conn.close()
    return steps


@app.get("/api/runs/{run_id}/trace")
def get_run_trace(run_id: str):
    """Get trace entries for a test run (one row = up to 3 trace entries)."""
    import json
    
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT step_number, thought, action, action_input, result, is_error
        FROM steps WHERE run_id = ?
        ORDER BY step_number
        """,
        (run_id,),
    )

    trace_entries = []
    for row in cursor.fetchall():
        step_num, thought, action, action_input, result, is_error = row
        
        # Parse action_input JSON if it exists
        parsed_input = {}
        if action_input:
            try:
                parsed_input = json.loads(action_input)
            except (json.JSONDecodeError, TypeError):
                parsed_input = {"raw": action_input}
        
        # 1. Add action entry (always present)
        # Include the thought as description for frontend to use
        trace_entries.append({
            "timestamp": step_num,
            "kind": "action",
            "importance": 1.0,
            "content": thought if thought and thought.strip() else f"Executing {action}",
            "description": thought if thought and thought.strip() else f"Executing {action}",
            "action": action,
            "target": action_input,
            "parsed_input": parsed_input,
            "is_error": bool(is_error),
        })
        
        # 2. Add thought entry (if thought is not empty)
        if thought and thought.strip():
            trace_entries.append({
                "timestamp": step_num,
                "kind": "thought",
                "importance": 0.8,
                "content": thought,
                "action": action,
                "target": None,
                "is_error": bool(is_error),
            })
        
        # 3. Add observation entry (if result is not empty, truncated to 200 chars)
        if result and result.strip():
            truncated_result = result[:200] + "..." if len(result) > 200 else result
            trace_entries.append({
                "timestamp": step_num,
                "kind": "observation",
                "importance": 0.8,
                "content": truncated_result,
                "action": action,
                "target": None,
                "is_error": bool(is_error),
            })

    conn.close()
    return trace_entries


@app.get("/api/analytics")
def get_analytics():
    """Get analytics data."""
    conn = db._connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT w.domain, COUNT(p.id) as count
        FROM websites w
        LEFT JOIN personas p ON w.id = p.website_id
        GROUP BY w.id
        ORDER BY count DESC
        """
    )
    personas_per_website = [{"website": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT device, COUNT(*) as count
        FROM personas
        GROUP BY device
        """
    )
    personas_by_device = [{"device": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT vitesse, COUNT(*) as count
        FROM personas
        GROUP BY vitesse
        """
    )
    personas_by_speed = [{"speed": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        """
        SELECT DATE(created_at) as date, SUM(personas_generated) as count
        FROM generation_sessions
        GROUP BY DATE(created_at)
        ORDER BY date
        """
    )
    generation_over_time = [{"date": r[0], "count": r[1]} for r in cursor.fetchall()]

    conn.close()

    return {
        "personas_per_website": personas_per_website,
        "personas_by_device": personas_by_device,
        "personas_by_speed": personas_by_speed,
        "generation_over_time": generation_over_time,
    }


# ============================================================================
# NEW ENDPOINT: Test Configuration Wizard
# ============================================================================

class DemographicValue(BaseModel):
    id: str
    value: str
    weight: int


class DemographicField(BaseModel):
    id: str
    name: str
    label: str
    values: list[DemographicValue]


class TestConfigurationRequest(BaseModel):
    url: str
    numParticipants: int
    participantTask: str
    examplePersona: str = ""
    demographics: list[DemographicField]


@app.post("/api/test-config")
async def submit_test_configuration(config: TestConfigurationRequest):
    """
    Submit test configuration and generate personas for the test.
    This will:
    1. Analyze the website at the given URL
    2. Generate personas (optionally seeded with demographics constraints)
    3. Return run information for monitoring
    """
    try:
        print(f"\n📋 Processing test configuration for {config.url}")

        # Add website to database
        website_id = db.add_website(config.url, site_type="test", description=f"Task: {config.participantTask}")

        # Analyze website
        print("🔍 Analyzing website...")
        analyzer = WebsiteAnalyzer(provider="groq", enable_web_search=True)
        website_analysis = analyzer.analyze(config.url)

        # Save analysis
        analysis_id = db.add_analysis(website_id, website_analysis, llm_provider="groq", llm_model="llama-3.3-70b-versatile")

        # Generate personas
        print(f"🧠 Generating {config.numParticipants} personas...")
        persona_gen = PersonaGenerator(provider="groq", model="llama-3.3-70b-versatile")
        personas = persona_gen.generate(
            website_analysis,
            num_personas=config.numParticipants,  # Generate EXACTLY what user asked for
            include_extremes=True,
            global_objective=config.participantTask,
            demographics_config={"demographics": [
                {
                    "label": field.label,
                    "values": [{"value": v.value, "weight": v.weight} for v in field.values]
                }
                for field in config.demographics
            ]}
        )

        # Save personas to database
        session_id = db.start_generation_session(
            website_id=website_id,
            analysis_id=analysis_id,
            personas_requested=config.numParticipants,
            llm_provider="groq",
            llm_model="llama-3.3-70b-versatile"
        )

        generated_count = 0
        persona_ids = []
        for persona in personas:
            persona_id = db.add_persona(persona, website_id, session_id=session_id)
            persona_ids.append(persona_id)
            generated_count += 1
            print(f"✅ Saved persona {generated_count}/{len(personas)}: {persona_id} - {persona.get('nom')}")

        # Update session
        db.complete_generation_session(session_id, generated_count, time.time())

        print(f"📊 All {generated_count} personas saved to database")

        # Return success with summary
        return {
            "success": True,
            "message": f"Configuration saved! Generated {generated_count} personas for {config.numParticipants} participants.",
            "website_id": website_id,
            "analysis_id": analysis_id,
            "session_id": session_id,
            "personas_generated": generated_count,
            "persona_ids": persona_ids,
            "personas": [
                {
                    "id": p.get("id", f"persona_{i}"),
                    "nom": p.get("nom", "Unknown"),
                    "persona_type": p.get("persona_type", ""),
                    "objectif": p.get("objectif", ""),
                    "description": p.get("description", ""),
                    "device": p.get("device", ""),
                    "vitesse_navigation": p.get("vitesse_navigation", ""),
                    "style_navigation": p.get("style_navigation", ""),
                    "sensibilite_prix": p.get("sensibilite_prix", ""),
                    "tolerance_erreurs": p.get("tolerance_erreurs", ""),
                    "patience_attente_sec": p.get("patience_attente_sec", ""),
                    "comportements_specifiques": p.get("comportements_specifiques", []),
                    "motivation_principale": p.get("motivation_principale", ""),
                    "douleurs": p.get("douleurs", []),
                    "actions_site": p.get("actions_site", []),
                    "patterns_comportement": p.get("patterns_comportement", []),
                    "exploration_fonctionnalites": p.get("exploration_fonctionnalites", []),
                }
                for i, p in enumerate(personas)
            ],
            "configuration": {
                "url": config.url,
                "task": config.participantTask,
                "demographics_fields": len(config.demographics),
            }
        }

    except Exception as e:
        print(f"❌ Test configuration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test-config/status/{session_id}")
async def get_test_status(session_id: str):
    """Get status of test configuration and persona generation."""
    try:
        conn = db._connect()
        cursor = conn.cursor()

        # Get session info
        cursor.execute("SELECT * FROM generation_sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()

        if not session:
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")

        # Get associated personas
        cursor.execute("SELECT id, nom, device, vitesse FROM personas WHERE generation_session_id = ?", (session_id,))
        personas = cursor.fetchall()

        # Get test runs for these personas
        cursor.execute("""
            SELECT p.id, COUNT(tr.id) as run_count,
                   SUM(CASE WHEN tr.status = 'completed' THEN 1 ELSE 0 END) as completed_count
            FROM personas p
            LEFT JOIN test_runs tr ON p.id = tr.persona_id
            WHERE p.generation_session_id = ?
            GROUP BY p.id
        """, (session_id,))
        run_stats = {row[0]: {"total": row[1], "completed": row[2]} for row in cursor.fetchall()}

        conn.close()

        return {
            "session_id": session_id,
            "website_id": session[1],
            "personas_generated": session[5],
            "duration_sec": session[7],
            "personas": [
                {
                    "id": p[0],
                    "nom": p[1],
                    "device": p[2],
                    "vitesse": p[3],
                    "runs": run_stats.get(p[0], {"total": 0, "completed": 0})
                }
                for p in personas
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("🚀 Persona Automation API starting...")
    print("📊 Dashboard: http://localhost:5173")
    print("🔌 API: http://localhost:5000")

    import uvicorn

    uvicorn.run("frontend.api.app:app", host="0.0.0.0", port=5000, reload=True)
