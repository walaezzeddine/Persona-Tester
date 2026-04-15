#!/usr/bin/env python3
"""
Test Wall Street Survivor - REGISTRATION - DIRECT URL
Navigate directly to the registration page and fill in the form
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_wallstreet_registration_improved():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - DIRECT REGISTRATION TEST (Improved)")
    print("="*80)

    # Generate unique email for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_email = f"autotest_{timestamp}@test.com"
    username = f"autotest_{timestamp}"
    
    # Test user credentials (NEW account being created)
    test_credentials = {
        "first_name": "AutoTest",
        "last_name": "User",
        "email": unique_email,
        "username": username,
        "password": "WallStreet@2025",
        "password_confirm": "WallStreet@2025",
    }
    
    print(f"\n✅ Generating new test account:")
    print(f"   First Name: {test_credentials['first_name']}")
    print(f"   Last Name: {test_credentials['last_name']}")
    print(f"   Email: {test_credentials['email']}")
    print(f"   Username: {test_credentials['username']}")
    print(f"   Password: {'*' * len(test_credentials['password'])}")

    # Load config
    config = Config()
    print(f"\n✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load registration scenario
    scenario_path = Path("scenarios/wallstreet_registration_scenario.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")

    # Create registration test persona with DIRECT URL GUIDANCE
    test_persona = {
        'nom': 'New User',
        'prenom': 'AutoTest',
        'objectif': f'Register a new account with credentials: username={username}, email={unique_email}, password=WallStreet@2025',
        'style_navigation': 'direct',
        'preferences_site': 'prefer straightforward forms',
        'sensibilite_prix': 'low',
        'tolerance_erreurs': 'low',
        'credentials': test_credentials,
        'registration_url': 'https://app.wallstreetsurvivor.com/members/register',
    }
    print(f"\n✅ Registration persona created")
    print(f"   Name: {test_persona['prenom']} {test_persona['nom']}")
    print(f"   Direct URL: {test_persona['registration_url']}")

    # Create agent with MCP support
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING MCP AUTOMATION - REGISTRATION SCENARIO ({config.max_steps} steps max)")
    print("="*80 + "\n")

    # Run the test - navigate directly to registration page
    try:
        result = await agent.run_with_mcp(start_url="https://app.wallstreetsurvivor.com/members/register")

        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        print(f"Status: {result.get('status')}")
        print(f"Steps taken: {result.get('steps', 0)}/{config.max_steps}")

        if result.get('status') == 'done':
            print("\n🎉 Registration SUCCESSFUL!")
            print("\n📋 ACCOUNT DETAILS:")
            print(f"   Email: {unique_email}")
            print(f"   Username: {username}")
            print(f"   Password: WallStreet@2025")
            print(f"   Portfolio: My Practice Portfolio")
            print(f"   Virtual Money: $100,000")
            print(f"\n✅ Account is ready to use!")
        elif result.get('status') == 'max_steps':
            print("\n⏱️  Reached maximum steps")
            print(f"   Consider increasing max_steps in config")
        else:
            print(f"\n⚠️  Status: {result.get('response')}")

        # Save results
        registration_result = {
            'test_type': 'registration_direct_url',
            'status': result.get('status'),
            'steps_taken': result.get('steps', 0),
            'max_steps': config.max_steps,
            'account_created': {
                'email': unique_email,
                'username': username,
                'first_name': test_credentials['first_name'],
                'last_name': test_credentials['last_name'],
                'password': 'WallStreet@2025',
                'portfolio': 'My Practice Portfolio',
                'virtual_money': '$100,000',
                'timestamp': timestamp,
            },
            'full_result': result
        }
        
        results_file = Path("test_registration_results.json")
        with open(results_file, 'w') as f:
            json.dump(registration_result, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")
        print(f"📧 Save email: {unique_email}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet_registration_improved())
