#!/usr/bin/env python3
"""
Test Wall Street Survivor - USER REGISTRATION SCENARIO
Create a new account and verify registration
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_wallstreet_registration():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - USER REGISTRATION TEST")
    print("="*80)

    # Generate unique email for this test run (critical for registration!)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_email = f"autotest_{timestamp}@wallstreettest.com"
    
    # Test user credentials (NEW account being created)
    test_credentials = {
        "first_name": "AutoTest",
        "last_name": "User",
        "email": unique_email,
        "password": "WallStreet@2025",
        "password_confirm": "WallStreet@2025",
    }
    
    print(f"\n✅ Generating new test account:")
    print(f"   First Name: {test_credentials['first_name']}")
    print(f"   Last Name: {test_credentials['last_name']}")
    print(f"   Email: {test_credentials['email']}")
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
    print(f"   Target: {scenario['target_url']}")
    print(f"   Description: {scenario['description'][:80]}...")

    # Create registration test persona
    test_persona = {
        'nom': 'New User',
        'prenom': 'Registration Test',
        'objectif': f'Register a new account with email {unique_email}',
        'style_navigation': 'cautious',
        'preferences_site': 'prefer clear forms',
        'sensibilite_prix': 'moyenne',
        'tolerance_erreurs': 'moyenne',
        'credentials': test_credentials,
    }
    print(f"\n✅ Registration persona created")
    print(f"   Name: {test_persona['prenom']} {test_persona['nom']}")
    print(f"   Objective: {test_persona['objectif']}")

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

    # Run the test
    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        print("\n" + "="*80)
        print("✅ TEST COMPLETED")
        print("="*80)
        print(f"Status: {result.get('status')}")
        print(f"Steps taken: {result.get('steps', 0)}/{config.max_steps}")

        if result.get('status') == 'done':
            print("🎉 Registration SUCCESSFUL!")
            print("\n📋 ACCOUNT CREATED:")
            print(f"   Email: {unique_email}")
            print(f"   Password: WallStreet@2025")
            print(f"   Status: Ready to use")
            print("\n💡 Next Steps:")
            print(f"   • Account verification may be required via email")
            print(f"   • Email address: {unique_email}")
            print(f"   • Check spam folder if confirmation not received")
            print(f"   • Can login with email + password on next test")
        elif result.get('status') == 'max_steps':
            print("⏱️  Reached maximum steps - registration incomplete")
            print("   Consider increasing max_steps in config")
        else:
            print(f"⚠️  Status: {result.get('response')}")

        # Save results with registration details
        registration_result = {
            'test_type': 'registration',
            'status': result.get('status'),
            'steps_taken': result.get('steps', 0),
            'max_steps': config.max_steps,
            'account_created': {
                'email': unique_email,
                'first_name': test_credentials['first_name'],
                'last_name': test_credentials['last_name'],
                'password': 'WallStreet@2025',
                'timestamp': timestamp,
            },
            'full_result': result
        }
        
        results_file = Path("test_registration_results.json")
        with open(results_file, 'w') as f:
            json.dump(registration_result, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")
        print(f"📧 Save the email {unique_email} for future login tests!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_wallstreet_registration())
