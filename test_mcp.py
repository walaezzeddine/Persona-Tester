"""
Test MCP Integration
Tests the PersonaAgent MCP mode with Playwright MCP server.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from src.agent import PersonaAgent
from src.config_loader import Config, load_persona, load_scenario

# Load environment variables
load_dotenv()


def _resolve_runtime_config(argv: list[str]) -> tuple[str, str, dict]:
    """Resolve persona, target URL, and scenario from CLI/env with safe fallbacks.

        CLI format:
            python test_mcp.py [persona|both] [target_url] [scenario_yaml]
            python test_mcp.py acheteur_impatient https://www.demoblaze.com
            python test_mcp.py acheteur_prudent https://www.demoblaze.com
            python test_mcp.py both https://www.demoblaze.com
    """
    persona_arg = argv[1] if len(argv) > 1 else "acheteur_impatient"

    default_url = os.getenv("TARGET_URL", "https://automationexercise.com").strip()
    target_url = default_url.rstrip("/")

    default_scenario = {
        "name": "Test MCP - Generic objective",
        "objectif": "Navigate the target site and complete the persona objective",
        "critere_succes": "Objective completed successfully",
    }

    scenario_path = os.getenv("SCENARIO_FILE", "").strip()

    # DEMOBLAZE SUPPORT — START
    # Optional second CLI argument: target URL
    # sys.argv[1] = persona, sys.argv[2] = target URL (if provided)
    if len(argv) > 2 and argv[2].strip():
        target_url = argv[2].strip().rstrip("/")
    # DEMOBLAZE SUPPORT — END
    if len(argv) > 3 and argv[3].strip():
        scenario_path = argv[3].strip()

    # DEMOBLAZE SUPPORT — START
    # If testing Demoblaze and no scenario was explicitly provided,
    # use scenarios/demoblaze.yaml as the default scenario context.
    if not scenario_path and "demoblaze.com" in target_url.lower():
        demoblaze_default = Path(__file__).parent / "scenarios" / "demoblaze.yaml"
        if demoblaze_default.exists():
            scenario_path = str(demoblaze_default)
    # DEMOBLAZE SUPPORT — END

    # PARABANK — START
    if not scenario_path and "parabank" in target_url.lower():
        parabank_default = Path(__file__).parent / "scenarios" / "parabank.yaml"
        if parabank_default.exists():
            scenario_path = str(parabank_default)
    # PARABANK — END

    scenario = default_scenario
    if scenario_path:
        candidate = Path(scenario_path)
        if not candidate.is_absolute():
            candidate = Path(__file__).parent / scenario_path
        if candidate.exists():
            loaded = load_scenario(str(candidate))
            if isinstance(loaded, dict):
                scenario = loaded
                scenario.setdefault("name", candidate.stem)
                scenario.setdefault(
                    "objectif",
                    "Navigate the target site and complete the persona objective",
                )
                scenario.setdefault("critere_succes", "Objective completed successfully")
        else:
            print(f"  ⚠ Scenario file not found: {candidate}. Using default scenario.")

    return persona_arg, target_url, scenario


async def run_one_persona(persona_name: str, target_url: str, scenario: dict, config, start_time) -> dict:
    """Run a single persona test and return the report data dict."""
    persona_path = Path(__file__).parent / "personas" / f"{persona_name}.json"
    persona = load_persona(str(persona_path))

    print(f"\n  ✓ Persona     : {persona['id']}")
    print(f"  ✓ Objectif    : {persona['objectif']}")
    print(f"  ✓ Vitesse     : {persona['vitesse_navigation']}")
    print(f"  ✓ Prix sens.  : {persona['sensibilite_prix']}")
    print(f"  ✓ Tolérance   : {persona['tolerance_erreurs']}")
    print(f"  ✓ Patience    : {persona['patience_attente_sec']}s")
    print(f"  ✓ Device      : {persona['device']}")

    agent = PersonaAgent(user=persona, scenario=scenario, config=config, use_mcp=True)

    try:
        result = await agent.run_with_mcp(start_url=target_url)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n  Status   : {result['status']}")
        print(f"  Steps    : {result['steps']}")
        print(f"  Duration : {duration:.1f}s")

        report_data = {
            "test_type": "MCP Integration Test",
            "timestamp": start_time.isoformat(),
            "persona": {
                "id": persona["id"],
                "objectif": persona["objectif"],
                "vitesse_navigation": persona["vitesse_navigation"],
                "sensibilite_prix": persona["sensibilite_prix"],
                "tolerance_erreurs": persona["tolerance_erreurs"],
                "patience_attente_sec": persona["patience_attente_sec"],
                "device": persona["device"],
            },
            "scenario": scenario,
            "target_url": target_url,
            "config": {
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "headless": config.headless,
            },
            "result": {
                "status": result["status"],
                "steps": result["steps"],
                "duration_sec": round(duration, 1),
                "response": result["response"],
                "steps_detail": result.get("steps_detail", []),
            },
        }

        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        ts = start_time.strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"mcp_test_{persona['id']}_{ts}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"  Report   : {report_path}")
        return report_data

    except Exception as e:
        import traceback
        duration = (datetime.now() - start_time).total_seconds()
        print(f"\n  ❌ Error: {e}")
        traceback.print_exc()
        return {"persona": {"id": persona["id"]}, "result": {"status": "error", "steps": 0, "duration_sec": round(duration,1), "response": str(e)}}


async def main():
    """
    Test the MCP integration by running a persona-driven navigation session.
    Usage:
      python test_mcp.py                     → acheteur_impatient
      python test_mcp.py acheteur_prudent    → acheteur_prudent
      python test_mcp.py both                → both personas, side-by-side comparison
    """
    print("\n" + "═" * 60)
    print("           MCP INTEGRATION TEST")
    print("═" * 60)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: Load Configuration
    # ═══════════════════════════════════════════════════════════════
    print("\n[1] Loading configuration...")
    config_path = Path(__file__).parent / "config" / "config.yaml"
    config = Config(str(config_path))
    print(f"  ✓ LLM: {config.llm_provider}/{config.llm_model}")
    print(f"  ✓ Headless: {config.headless}")

    persona_arg, target_url, scenario = _resolve_runtime_config(sys.argv)
    print(f"  ✓ Target URL: {target_url}")
    print(f"  ✓ Scenario  : {scenario.get('name', 'default')}")

    if persona_arg == "both":
        # ── Run BOTH personas sequentially ──────────────────────
        results = []
        for name in ["acheteur_impatient", "acheteur_prudent"]:
            sep = "⚡" if name == "acheteur_impatient" else "🔍"
            print(f"\n{'═'*60}")
            print(f" {sep} Running: {name}")
            print(f"{'═'*60}")
            r = await run_one_persona(name, target_url, scenario, config, datetime.now())
            results.append(r)

        # ── Side-by-side comparison ──────────────────────────────
        print("\n" + "═" * 60)
        print("  COMPARISON: acheteur_impatient vs acheteur_prudent")
        print("═" * 60)
        labels = ["Persona", "Status", "Steps", "Duration", "Vitesse", "Sensibilite prix", "Tolerance erreurs", "Patience (sec)", "Device"]
        def pval(r, key, sub=None):
            if sub:
                return str(r.get(sub, {}).get(key, "N/A"))
            return str(r.get("result", {}).get(key, "N/A"))
        rows = [
            ("Persona",            lambda r: r["persona"]["id"]),
            ("Status",             lambda r: r["result"]["status"]),
            ("Steps",              lambda r: str(r["result"]["steps"])),
            ("Duration (s)",       lambda r: str(r["result"]["duration_sec"])),
            ("Vitesse",            lambda r: r["persona"]["vitesse_navigation"]),
            ("Sensibilite prix",   lambda r: r["persona"]["sensibilite_prix"]),
            ("Tolerance erreurs",  lambda r: r["persona"]["tolerance_erreurs"]),
            ("Patience (sec)",     lambda r: str(r["persona"]["patience_attente_sec"])),
            ("Device",             lambda r: r["persona"]["device"]),
        ]
        col = 22
        print(f"  {'Attribut':<{col}} {'Impatient':<20} {'Prudent':<20}")
        print(f"  {'-'*col} {'-'*20} {'-'*20}")
        for label, fn in rows:
            v1 = fn(results[0]) if results else "N/A"
            v2 = fn(results[1]) if len(results) > 1 else "N/A"
            print(f"  {label:<{col}} {v1:<20} {v2:<20}")
        print("═" * 60)
        return

    # ── Single persona ────────────────────────────────────────────
    print(f"\n[2] Running persona: {persona_arg}...")
    start_time = datetime.now()
    report = await run_one_persona(persona_arg, target_url, scenario, config, start_time)

    print("\n" + "═" * 60)
    status = report["result"]["status"]
    if status == "completed":
        print("  ✅ MCP TEST PASSED")
    elif status == "max_steps_reached":
        print("  ⚠️  MCP TEST INCOMPLETE — max steps reached")
    else:
        print("  ❌ MCP TEST FAILED")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
