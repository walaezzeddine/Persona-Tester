#!/usr/bin/env python3
"""
Test Wall Street Survivor - REAL TRADING SCENARIO
Buy a stock and verify portfolio update
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

# 🔐 HARDCODED LOGIN CREDENTIALS
CREDENTIALS = {
    "username": "WALAEZZEDINE",
    "password": "WALA@123"
}

async def test_wallstreet_trading():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - REAL TRADING SCENARIO TEST")
    print("="*80)

    # Use hardcoded credentials
    credentials = CREDENTIALS
    print(f"\n✅ Using credentials for: {credentials['username']}")

    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load trading scenario
    scenario_path = Path("scenarios/wallstreet_trading_scenario.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario loaded: {scenario['name']}")
    print(f"   Target: {scenario['target_url']}")
    print(f"   Description: {scenario['description'][:100]}...")

    # Create trading persona
    test_persona = {
        'nom': 'Trader Professionnel',
        'prenom': 'Alex',
        'objectif': 'Buy a stock (e.g., AAPL) on Wall Street Survivor and verify portfolio',
        'style_navigation': 'directe',
        'preferences_site': 'prefer trading interface',
        'sensibilite_prix': 'basse',
        'tolerance_erreurs': 'basse',
        'credentials': credentials,
    }
    print(f"✅ Test persona created: {test_persona['nom']} {test_persona['prenom']}")
    print(f"   Objective: {test_persona['objectif']}")
    print(f"   Credentials: {credentials['username']}")

    # Create agent with MCP support
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING MCP AUTOMATION - TRADING SCENARIO ({config.max_steps} steps max)")
    print("="*80 + "\n")

    # Run the test
    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        print(f"Status: {result.get('status')}")
        print(f"Steps taken: {result.get('steps', 0)}/{config.max_steps}")

        if result.get('status') == 'done':
            print("🎉 Objective COMPLETED! Trading scenario successful!")
            print("\n📊 TRADING SUMMARY:")
            print("   ✅ Logged in")
            print("   ✅ Searched for stock")
            print("   ✅ Viewed stock details")
            print("   ✅ Placed BUY order")
            print("   ✅ Verified portfolio update")
        elif result.get('status') == 'max_steps':
            print("⏱️  Reached maximum steps - trading scenario incomplete")
            print("   Consider increasing max_steps in config")
        else:
            print(f"⚠️  Status: {result.get('response')}")

        # Save results
        results_file = Path("test_trading_results.json")
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet_trading())
