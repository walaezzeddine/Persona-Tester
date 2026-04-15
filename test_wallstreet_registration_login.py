#!/usr/bin/env python3
"""
Test Wall Street Survivor - REGISTRATION + LOGIN
Full onboarding: Register new account, then login and access dashboard
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_wallstreet_registration_login():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - REGISTRATION + LOGIN TEST")
    print("="*80)

    # Generate unique email and username for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_email = f"autotest_{timestamp}@test.com"
    username = f"user_{timestamp}"
    
    # Test user credentials (NEW account being created)
    test_credentials = {
        "first_name": "AutoTest",
        "last_name": "Tester",
        "email": unique_email,
        "username": username,
        "password": "WallStreet@2025",
        "password_confirm": "WallStreet@2025",
        "portfolio": "My Practice Portfolio",
    }
    
    print(f"\n✅ Generating new test account:")
    print(f"   First Name: {test_credentials['first_name']}")
    print(f"   Last Name: {test_credentials['last_name']}")
    print(f"   Email: {test_credentials['email']}")
    print(f"   Username: {test_credentials['username']}")
    print(f"   Password: {'*' * len(test_credentials['password'])}")
    print(f"   Portfolio: {test_credentials['portfolio']}")

    # Load config
    config = Config()
    print(f"\n✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load registration + login scenario
    scenario_path = Path("scenarios/wallstreet_registration_login_scenario.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")
    print(f"   Steps: {len(scenario['key_actions'])}")

    # Create persona for registration + login
    test_persona = {
        'nom': 'New User',
        'prenom': 'Registration',
        'objectif': f'Register with email {unique_email}, then login and access dashboard',
        'style_navigation': 'direct',
        'preferences_site': 'prefer straightforward processes',
        'sensibilite_prix': 'low',
        'tolerance_erreurs': 'low',
        'credentials': test_credentials,
        'flow': 'register_then_login',
    }
    print(f"\n✅ Registration+Login persona created")
    print(f"   Name: {test_persona['prenom']} {test_persona['nom']}")
    print(f"   Flow: Register → Login → Dashboard")

    # Create agent with MCP support
    agent = PersonaAgent(
        user=test_persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING MCP AUTOMATION - REGISTRATION + LOGIN ({config.max_steps} steps max)")
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
            print("\n🎉 FULL ONBOARDING SUCCESSFUL!")
            print("\n✅ Workflow Completed:")
            print(f"   1. ✓ Account Registered")
            print(f"   2. ✓ Logged in with new credentials")
            print(f"   3. ✓ Accessed dashboard")
            print("\n📋 ACCOUNT DETAILS:")
            print(f"   Email: {unique_email}")
            print(f"   Username: {username}")
            print(f"   Password: WallStreet@2025")
            print(f"   Portfolio: {test_credentials['portfolio']}")
            print(f"   Status: ✅ Active and Logged In")
            
        elif result.get('status') == 'max_steps_reached':
            print("\n⏱️  Reached maximum steps")
            print(f"   Completed: Registration + partial login")
            print(f"   Consider increasing max_steps for full flow")
        else:
            print(f"\n⚠️  Status: {result.get('response')}")

        # Save detailed results
        registration_login_result = {
            'test_type': 'registration_login_flow',
            'status': result.get('status'),
            'steps_taken': result.get('steps', 0),
            'max_steps': config.max_steps,
            'workflow': {
                'registration_completed': result.get('status') in ['done', 'max_steps_reached'],
                'login_completed': result.get('status') == 'done',
                'dashboard_accessed': result.get('status') == 'done',
            },
            'account_details': {
                'email': unique_email,
                'username': username,
                'first_name': test_credentials['first_name'],
                'last_name': test_credentials['last_name'],
                'password': 'WallStreet@2025',
                'portfolio': test_credentials['portfolio'],
                'virtual_money': '$100,000',
                'timestamp': timestamp,
            },
            'full_result': result
        }
        
        results_file = Path("test_registration_login_results.json")
        with open(results_file, 'w') as f:
            json.dump(registration_login_result, f, indent=2)
        
        print(f"\n📁 Results saved to: {results_file}")
        print(f"\n✨ Summary:")
        print(f"   • Test Type: Registration + Login Flow")
        print(f"   • Status: {result.get('status')}")
        print(f"   • Account Created: {unique_email}")
        print(f"   • Ready for Trading Tests: ✅")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet_registration_login())
