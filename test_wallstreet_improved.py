#!/usr/bin/env python3
"""
Test the improved Wall Street Survivor scenario
Run with: python test_wallstreet_improved.py
"""

import asyncio
import json
from pathlib import Path

from src.config_loader import Config, load_scenario, load_persona
from src.agent import PersonaAgent

async def test_wallstreet_scenario():
    """Test the improved scenario with a persona"""

    # Load configuration
    config = Config()
    print(f"✅ Config loaded: {config.llm_provider} - {config.llm_model}")

    # Load improved scenario
    scenario_path = Path("scenarios/wallstreet_improved.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario loaded: {scenario.get('name')}")
    print(f"   Max steps: 25")
    print(f"   Success criteria: {len(scenario.get('success_criteria', []))} defined")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps provided")

    # Create a simple persona for testing
    test_persona = {
        "id": "test_wallstreet_001",
        "nom": "Test Investor",
        "description": "A test persona analyzing stocks",
        "objectif": "Analyze Apple (AAPL) stock and decide whether to buy or sell",
        "device": "desktop",
        "heure_connexion": "12:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "haute",
        "tolerance_erreurs": "haute",
    }

    print(f"✅ Test persona created: {test_persona['nom']}")

    # Create agent
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )

    print("\n" + "="*80)
    print("🚀 STARTING TEST - Wall Street Survivor with Improved Scenario")
    print("="*80 + "\n")

    # Run the test
    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")
        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        print(f"Steps executed: {result.get('steps_completed', 0)}")
        print(f"Status: {result.get('status', 'unknown')}")
        if result.get('final_message'):
            print(f"Final message: {result['final_message']}")
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📋 Wall Street Survivor Scenario Test")
    print("="*80)
    asyncio.run(test_wallstreet_scenario())
