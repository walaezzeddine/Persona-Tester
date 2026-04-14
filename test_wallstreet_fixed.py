#!/usr/bin/env python3
"""
Test Wall Street Survivor with FIXED scenario
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

async def test_wallstreet_fixed():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - FIXED SCENARIO TEST")
    print("="*80)

    # Use hardcoded credentials
    credentials = CREDENTIALS
    print(f"\n✅ Using hardcoded credentials for: {credentials['username']}")

    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load Wall Street scenario - LOGIN ONLY (no registration)
    scenario_path = Path("scenarios/wallstreet_login_only.yaml")
    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario loaded: {scenario.get('name')}")
    print(f"   Description: {scenario.get('description', '').split(chr(10))[0][:60]}...")
    print(f"   Max steps: {config.max_steps}")
    print(f"   Success criteria: {len(scenario.get('success_criteria', []))} defined")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps provided")

    # Create test persona for LOGIN ONLY (not registration)
    test_persona = {
        "id": "test_wallstreet_login",
        "nom": "Existing User",
        "description": "Existing user logging into Wall Street Survivor and exploring courses",
        "objectif": "Login to Wall Street Survivor and select a course from the Courses section",
        "device": "desktop",
        "heure_connexion": "14:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "normale",
        "tolerance_erreurs": "haute",
        "credentials": credentials,
    }
    print(f"✅ Test persona created: {test_persona['nom']}")
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
    print(f"🚀 STARTING MCP AUTOMATION ({config.max_steps} steps max)")
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
            print("🎉 Objective COMPLETED!")
        elif result.get('status') == 'max_steps':
            print("⏱️  Reached maximum steps")
        else:
            print(f"⚠️  Status: {result.get('response')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet_fixed())
