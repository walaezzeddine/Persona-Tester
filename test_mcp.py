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
from src.config_loader import Config, load_persona

# Load environment variables
load_dotenv()


async def main():
    """
    Test the MCP integration by running a persona-driven navigation session.
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
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Load Persona
    # ═══════════════════════════════════════════════════════════════
    print("\n[2] Loading persona...")
    persona_name = sys.argv[1] if len(sys.argv) > 1 else "acheteur_impatient"
    persona_path = Path(__file__).parent / "personas" / f"{persona_name}.json"
    persona = load_persona(str(persona_path))
    print(f"  ✓ Persona: {persona['id']}")
    print(f"  ✓ Objectif: {persona['objectif']}")
    print(f"  ✓ Vitesse: {persona['vitesse_navigation']}")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: Create MCP-enabled Agent
    # ═══════════════════════════════════════════════════════════════
    print("\n[3] Creating MCP-enabled agent...")
    
    # Create a simple scenario for MCP mode
    scenario = {
        "name": "Test MCP - Find cheapest t-shirt",
        "objectif": "Find the cheapest t-shirt and add it to cart",
        "critere_succes": "Product added to cart successfully"
    }
    
    agent = PersonaAgent(
        user=persona,
        scenario=scenario,
        config=config,
        use_mcp=True  # Enable MCP mode
    )
    print(f"  ✓ Agent created with MCP support")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: Run MCP Session
    # ═══════════════════════════════════════════════════════════════
    print("\n[4] Running MCP session...")
    print("  🚀 Starting autonomous navigation via Playwright MCP...")
    print("  ⏳ This may take a few minutes...")
    
    start_time = datetime.now()
    target_url = "https://automationexercise.com"
    
    try:
        result = await agent.run_with_mcp(start_url=target_url)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # ═══════════════════════════════════════════════════════════════
        # PHASE 5: Display Results
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "═" * 60)
        print("                    RESULTS")
        print("═" * 60)
        print(f"  Status      : {result['status']}")
        print(f"  Persona     : {persona['id']}")
        print(f"  Steps       : {result['steps']}")
        print(f"  Duration    : {duration:.1f}s")
        print("\n  Agent Response (preview):")
        print("  " + "─" * 56)
        response_preview = result['response'][:400] + "..." if len(result['response']) > 400 else result['response']
        for line in response_preview.split('\n'):
            print(f"  {line}")
        print("  " + "─" * 56)
        
        # ═══════════════════════════════════════════════════════════════
        # PHASE 6: Save Report
        # ═══════════════════════════════════════════════════════════════
        print("\n[6] Saving report...")
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        report_filename = f"mcp_test_{persona['id']}_{timestamp}.json"
        report_path = reports_dir / report_filename
        
        report_data = {
            "test_type": "MCP Integration Test",
            "timestamp": start_time.isoformat(),
            "persona": {
                "id": persona['id'],
                "objectif": persona['objectif'],
                "vitesse_navigation": persona['vitesse_navigation'],
                "sensibilite_prix": persona['sensibilite_prix']
            },
            "scenario": scenario,
            "target_url": target_url,
            "config": {
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "headless": config.headless
            },
            "result": {
                "status": result['status'],
                "steps": result['steps'],
                "duration_sec": round(duration, 1),
                "response": result['response'],
                "steps_detail": result.get('steps_detail', [])
            }
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Report saved: {report_path}")
        
        # ═══════════════════════════════════════════════════════════════
        # FINAL SUMMARY
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "═" * 60)
        if result['status'] == 'completed':
            print("  ✅ MCP TEST PASSED")
        elif result['status'] == 'max_steps_reached':
            print("  ⚠️ MCP TEST INCOMPLETE — max steps reached")
        else:
            print("  ❌ MCP TEST FAILED")
        print("═" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during MCP session: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error report
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        error_report_path = reports_dir / f"mcp_test_error_{timestamp}.json"
        
        error_data = {
            "test_type": "MCP Integration Test",
            "timestamp": start_time.isoformat(),
            "persona": persona['id'],
            "target_url": target_url,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        with open(error_report_path, "w", encoding="utf-8") as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Error report saved: {error_report_path}")


if __name__ == "__main__":
    asyncio.run(main())
