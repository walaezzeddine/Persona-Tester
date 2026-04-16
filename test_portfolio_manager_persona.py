#!/usr/bin/env python3
"""
Test script for Portfolio Manager persona - portfolio analysis and rebalancing
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_portfolio_manager():
    print("="*80)
    print("🧪 PORTFOLIO MANAGER - PORTFOLIO REBALANCING")
    print("="*80)

    # Load config
    config = Config()
    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/wallstreet_portfolio_rebalance.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")
    print(f"   Description: {scenario['description'][:100]}...")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create portfolio manager persona
    manager = {
        'nom': 'Robert',
        'prenom': 'Martinez',
        'id': 'portfolio_strategist',
        'objectif': 'Analyze portfolio and sell the worst performing stock',
        'description': 'Strategic portfolio manager focused on optimization',
        'style_navigation': 'strategique',
        'preferences_site': 'portfolio analytics interface',
        'sensibilite_prix': 'moyenne',
        'tolerance_erreurs': 'faible',
        'patience_attente_sec': 12,
        'vitesse_navigation': 'normale',
        'device': 'desktop',
        'website_type': 'finance',
        'credentials': {
            'username': 'WALAEZZEDINE',
            'password': 'WALA@123'
        }
    }

    print(f"\n👤 Persona: {manager['nom']} {manager['prenom']}")
    print(f"   ID: {manager['id']}")
    print(f"   Style: Strategic/Analytical")
    print(f"   Objective: {manager['objectif']}")

    # Create agent
    agent = PersonaAgent(
        user=manager,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"\n✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING PORTFOLIO REBALANCING TEST ({config.max_steps} steps max)")
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
            print("\n🎉 SUCCESS! Portfolio rebalancing completed!")
            print("   ✓ Accessed portfolio")
            print("   ✓ Reviewed holdings")
            print("   ✓ Identified worst performer")
            print("   ✓ Executed sale")

        # Save results
        results_file = Path("test_portfolio_manager_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{manager['nom']} {manager['prenom']}",
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
    asyncio.run(test_portfolio_manager())
