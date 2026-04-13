#!/usr/bin/env python3
"""
Test Wall Street Survivor with the proper scenario
"""

import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def main():
    print("=" * 80)
    print("🧪 WALL STREET SURVIVOR - SCENARIO TEST")
    print("=" * 80)

    # Load configuration
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/wallstreet_proper.yaml")
    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario: {scenario.get('name')}")
    print(f"   Max steps: {scenario.get('constraints', {}).get('time_limit', 'N/A')} seconds")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create test persona
    test_persona = {
        "id": "wallstreet_test_001",
        "nom": "Stock Market Explorer",
        "description": "Testing Wall Street Survivor platform navigation",
        "objectif": "Navigate to Stock Game and explore the trading simulator",
        "device": "desktop",
        "heure_connexion": "12:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "moyenne",
        "tolerance_erreurs": "haute",
    }
    print(f"✅ Persona: {test_persona['nom']}")
    print(f"   Objective: {test_persona['objectif']}")

    # Create agent
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"✅ Agent initialized with MCP support\n")

    # Run test
    print("=" * 80)
    print("🚀 STARTING MCP AUTOMATION (25 steps max)")
    print("=" * 80 + "\n")

    try:
        result = await agent.run_with_mcp(
            start_url="https://www.wallstreetsurvivor.com/"
        )

        print("\n" + "=" * 80)
        print("✅ TEST COMPLETED")
        print("=" * 80)

        # Display results
        print(f"\nStatus: {result.get('status')}")
        print(f"Steps completed: {result.get('steps', 0)}")

        if result.get('error'):
            print(f"Error: {result.get('error')}")

        if result.get('response'):
            print(f"\nAgent response:\n{result.get('response')}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
