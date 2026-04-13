#!/usr/bin/env python3
"""
Test Wall Street Survivor with FIXED scenario
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

def get_login_credentials():
    """
    Prompt user for Wall Street Survivor login credentials
    """
    print("\n" + "="*80)
    print("🔐 LOGIN CREDENTIALS SETUP")
    print("="*80)
    print("\nPlease enter your Wall Street Survivor credentials:")
    print("(These will be used for the login test)\n")
    
    email = input("📧 Email address: ").strip()
    password = input("🔒 Password: ").strip()
    
    if not email or not password:
        print("❌ Email and password are required!")
        exit(1)
    
    print(f"\n✅ Credentials saved for: {email}")
    return {"email": email, "password": password}

async def test_wallstreet_fixed():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - FIXED SCENARIO TEST")
    print("="*80)

    # Get login credentials from user
    credentials = get_login_credentials()

    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load Wall Street scenario with login focus
    scenario_path = Path("scenarios/wallstreet_login_simple.yaml")
    scenario = load_scenario(str(scenario_path))
    print(f"✅ Scenario loaded: {scenario.get('name')}")
    print(f"   Description: {scenario.get('description', '').split(chr(10))[0][:60]}...")
    print(f"   Max steps: {config.max_steps}")
    print(f"   Success criteria: {len(scenario.get('success_criteria', []))} defined")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps provided")

    # Create test persona with login credentials
    test_persona = {
        "id": "test_wallstreet_login",
        "nom": "New Investor",
        "description": "First-time user registering on Wall Street Survivor",
        "objectif": "Register an account and log in to Wall Street Survivor",
        "device": "desktop",
        "heure_connexion": "14:00",
        "vitesse_navigation": "normale",
        "sensibilite_prix": "normale",
        "tolerance_erreurs": "haute",
        "credentials": credentials,
    }
    print(f"✅ Test persona created: {test_persona['nom']}")
    print(f"   Objective: {test_persona['objectif']}")
    print(f"   Credentials: {credentials['email']}")

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
