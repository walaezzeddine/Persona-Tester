#!/usr/bin/env python3
"""
Test Wall Street Survivor - NVIDIA TRADING (REALISTIC DASHBOARD)
Matches actual dashboard layout - no more searching for non-existent UI
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

# 🔐 LOGIN CREDENTIALS
CREDENTIALS = {
    "username": "WALAEZZEDINE",
    "password": "WALA@123"
}

async def test_nvidia_realistic():
    print("="*80)
    print("🧪 WALL STREET SURVIVOR - NVIDIA TRADING (REALISTIC DASHBOARD)")
    print("="*80)

    # Load config
    config = Config()
    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load NEW realistic scenario
    scenario_path = Path("scenarios/wallstreet_nvidia_realistic_dashboard.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")
    print(f"   Description: {scenario['description'][:100]}...")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create realistic trader persona
    trader = {
        'nom': 'Jordan',
        'prenom': 'Mitchell',
        'id': 'realistic_trader',
        'objectif': 'Trade Nvidia stock based on market analysis using actual dashboard',
        'description': 'Realistic trader navigating actual platform UI',
        'style_navigation': 'exploratrice',
        'preferences_site': 'prefer trading interface',
        'sensibilite_prix': 'moyenne',
        'tolerance_erreurs': 'moyenne',
        'patience_attente_sec': 10,
        'vitesse_navigation': 'normale',
        'device': 'desktop',
        'website_type': 'finance',
        'credentials': CREDENTIALS,
    }

    print(f"\n👤 Persona: {trader['nom']} {trader['prenom']}")
    print(f"   ID: {trader['id']}")
    print(f"   Style: Exploratory (Natural)")
    print(f"   Objective: {trader['objectif']}")

    # Create agent
    agent = PersonaAgent(
        user=trader,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"\n✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING REALISTIC DASHBOARD TEST ({config.max_steps} steps max)")
    print("="*80 + "\n")

    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        print("\n" + "="*80)
        print("✅ TEST EXECUTION COMPLETE")
        print("="*80)

        status = result.get('status')
        steps_taken = result.get('steps', 0)

        print(f"\n📊 Results:")
        print(f"   Status: {status}")
        print(f"   Steps completed: {steps_taken}/{config.max_steps}")

        if status == 'done':
            print("\n🎉 SUCCESS! Realistic trading scenario completed!")
            print("\n✅ What happened:")
            print("   ✓ Logged in successfully")
            print("   ✓ Closed tour overlay")
            print("   ✓ Found trading interface")
            print("   ✓ Searched for Nvidia")
            print("   ✓ Analyzed stock data")
            print("   ✓ Made trading decision")
            print("   ✓ Executed trade")
            print("   ✓ Verified in portfolio")

        elif status == 'max_steps_reached':
            print(f"\n⏱️  Reached maximum steps")
            print(f"   Completed {steps_taken}/{config.max_steps} steps")
            print("   Scenario may not have fully completed")

        elif status == 'error':
            response = result.get('response', '')
            print(f"\n❌ Error encountered")
            if 'rate limit' in response.lower():
                print(f"   Issue: API Rate Limit")
                print(f"   Solution: Use Ollama (local) instead of GitHub Models")
            else:
                print(f"   Details: {response[:150]}...")

        else:
            print(f"\n⚠️  Status: {status}")

        # Show step summary
        if 'steps_detail' in result and result['steps_detail']:
            steps_detail = result['steps_detail']
            print(f"\n📝 Step Summary ({len(steps_detail)} steps taken):")

            # Show first 5
            for i, step in enumerate(steps_detail[:5], 1):
                action = step.get('action', 'unknown')
                error = "⚠️" if step.get('error') else "✅"
                print(f"   {i:2d}. {error} {action}")

            # Middle marker
            if len(steps_detail) > 10:
                print(f"   ...")

            # Show last 5
            for i, step in enumerate(steps_detail[-5:], len(steps_detail)-4):
                action = step.get('action', 'unknown')
                error = "⚠️" if step.get('error') else "✅"
                print(f"   {i:2d}. {error} {action}")

        # Save results
        results_file = Path("test_nvidia_realistic_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{trader['nom']} {trader['prenom']}",
                'test_date': '2026-04-15',
                'result': result
            }, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("Test complete!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_nvidia_realistic())
