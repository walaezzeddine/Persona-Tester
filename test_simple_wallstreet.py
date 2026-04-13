#!/usr/bin/env python3
"""
Simple Wall Street Scenario Test - Direct Testing
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def main():
    print("\n" + "="*80)
    print("🧪 WALL STREET SURVIVOR - SCENARIO TEST")
    print("="*80)

    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")

    # Load scenario
    scenario_path = Path("scenarios/wallstreet_improved.yaml")
    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario loaded: {scenario.get('name')}")
    print(f"   Max steps: {scenario.get('constraints', {}).get('max_steps', 25)}")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create test persona - IMPORTANT: Must have 'objectif' field
    test_persona = {
        "id": "test_investor_001",
        "nom": "Test Investor",
        "description": "A test investor analyzing stocks on Wall Street Survivor",
        "objectif": "Search for Apple (AAPL) stock, analyze its metrics, and make a BUY or SELL decision",  # ← CRITICAL FIELD
        "device": "desktop",
        "heure_connexion": "14:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "normale",
        "tolerance_erreurs": "haute",
        "user_id": "test_001"
    }
    print(f"✅ Persona created: {test_persona['nom']}")
    print(f"   Objective: {test_persona['objectif']}")

    # Create agent
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"✅ Agent initialized with MCP support")

    # Run the MCP automation
    print("\n" + "="*80)
    print("🚀 STARTING MCP AUTOMATION (25 steps max)")
    print("="*80 + "\n")

    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        print("\n" + "="*80)
        print("📊 TEST RESULT")
        print("="*80)
        print(f"Status: {result.get('status')}")
        print(f"Steps completed: {result.get('steps')}")
        print(f"Success: {result.get('success', False)}")

        if result.get('success_message'):
            print(f"\n✅ Success message:\n{result['success_message']}")

        if result.get('error'):
            print(f"\n❌ Error:\n{result['error']}")

        # Summary
        print("\n" + "="*80)
        print("📈 SUMMARY")
        print("="*80)
        steps_detail = result.get('steps_detail', [])
        print(f"Total steps: {len(steps_detail)}")
        actions = [s.get('action') for s in steps_detail]
        from collections import Counter
        action_counts = Counter(actions)
        print(f"Actions taken: {dict(action_counts)}")

    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
