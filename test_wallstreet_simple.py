#!/usr/bin/env python3
"""
Simple Wall Street Survivor test with better error handling
"""

import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_wallstreet():
    """Test persona on Wall Street Survivor with stock analysis task"""

    print("\n" + "="*80)
    print("📋 WALL STREET SURVIVOR - SIMPLE TEST")
    print("="*80)

    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/wallstreet_improved.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario: {scenario.get('name', 'Unknown')}")

    # Create test persona
    test_persona = {
        "id": "test_wallstreet_simple",
        "nom": "Stock Analyzer",
        "description": "Analyzes stocks on Wall Street Survivor",
        "objectif": "Search for Apple stock, analyze it, then decide to BUY or SELL",
        "device": "desktop",
        "heure_connexion": "14:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "moyenne",
        "tolerance_erreurs": "moyenne",
    }
    print(f"✅ Persona: {test_persona['nom']}")
    print(f"   Objective: {test_persona['objectif']}\n")

    # Create agent
    try:
        agent = PersonaAgent(
            user=test_persona,
            scenario=scenario,
            config=config,
            use_mcp=True
        )
        print("✅ Agent initialized with MCP support\n")

        # Run the test
        print("="*80)
        print("🚀 RUNNING TEST (max 10 steps)")
        print("="*80 + "\n")

        result = await agent.run_with_mcp(
            start_url="https://www.wallstreetsurvivor.com/"
        )

        # Display results
        print("\n" + "="*80)
        print("📊 TEST RESULTS")
        print("="*80)

        if result.get("status") == "success":
            print("✅ SUCCESS!")
        else:
            print(f"⚠️  Status: {result.get('status', 'unknown')}")

        print(f"Steps completed: {result.get('steps', 0)}")
        print(f"Response: {result.get('response', 'N/A')[:200]}...")

        if result.get("steps_detail"):
            print(f"\nStep details ({len(result['steps_detail'])} steps):")
            for i, step in enumerate(result['steps_detail'][-5:], 1):
                print(f"  {i}. {step.get('action', 'unknown')} - {step.get('status', 'unknown')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet())
