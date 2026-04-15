#!/usr/bin/env python3
"""
Test Wall Street Survivor - LOGIN ONLY
Test the login flow with known credentials (no registration complexity)
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_wallstreet_login_only():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - LOGIN ONLY TEST")
    print("="*80)

    # Use known test account credentials
    test_credentials = {
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "WallStreet@2025",
        "portfolio": "My Practice Portfolio",
    }
    
    print(f"\n✅ Using test account:")
    print(f"   Username: {test_credentials['username']}")
    print(f"   Password: {'*' * len(test_credentials['password'])}")
    print(f"   Portfolio: {test_credentials['portfolio']}")

    # Load config
    config = Config()
    print(f"\n✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load login scenario
    scenario_path = Path("scenarios/wallstreet_login_scenario.yaml")
    if not scenario_path.exists():
        print(f"⚠️  Scenario not found at {scenario_path}, using default")
        scenario = {
            "name": "Wall Street Survivor - Login Test",
            "description": "Test login functionality",
            "objectif": "Login to Wall Street Survivor and access dashboard",
            "success_criteria": ["Successfully logged in", "Dashboard visible"]
        }
    else:
        scenario = load_scenario(scenario_path)
    
    print(f"\n✅ Scenario loaded: {scenario.get('name', 'Unknown')}")
    print(f"   Objectif: {scenario.get('objectif', 'No objective')}")

    # Create persona agent
    persona = {
        "id": "test_login_user",
        "nom": "Test Login User",
        "device": "desktop",
        "vitesse": "normal",
        "tolerance": "normal",
        "sensibilite": "normal",
        "patience_sec": 10,
        "credentials": test_credentials
    }

    print(f"\n✅ Login persona created")
    print(f"   Name: {persona['nom']}")
    print(f"   Flow: Login → Dashboard")

    # Initialize agent
    agent = PersonaAgent(
        user=persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )

    # Run the test
    print("\n" + "="*80)
    print("🚀 STARTING LOGIN TEST")
    print("="*80)

    result = await agent.run_with_mcp(
        start_url="https://www.wallstreetsurvivor.com/members/login"
    )

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "status": result.get("status"),
        "test_type": "Login Only",
        "account": test_credentials["username"],
        "steps_taken": result.get("steps"),
        "results": result.get("results", {}),
        "response": result.get("response"),
    }

    results_file = Path("test_login_only_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📁 Results saved to: {results_file}")
    print(f"\n✨ Summary:")
    print(f"   • Test Type: {results.get('test_type')}")
    print(f"   • Status: {results.get('status')}")
    print(f"   • Steps: {results.get('steps_taken')}")
    print(f"   • Ready for Trading Tests: ✅" if "login_success" in results.get("results", {}) else "   • Login Failed ❌")

    # Check if login was successful
    if "login_success" in result.get("results", {}):
        print(f"\n🎉 LOGIN SUCCESSFUL!")
        print(f"   • Dashboard accessible: {result.get('results', {}).get('dashboard_accessible', False)}")
    else:
        print(f"\n❌ LOGIN FAILED")
        print(f"   • Response: {result.get('response', 'No response')}")

if __name__ == "__main__":
    asyncio.run(test_wallstreet_login_only())
