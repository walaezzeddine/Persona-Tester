#!/usr/bin/env python3
"""
Test script for Calculator User persona - analytical stock research and trading
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_calculator():
    print("="*80)
    print("🧪 CALCULATOR USER - ANALYTICAL STOCK RESEARCH")
    print("="*80)

    # Load config
    config = Config()
    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/wallstreet_calculator_analysis.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")
    print(f"   Description: {scenario['description'][:100]}...")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create calculator persona
    analyst = {
        'nom': 'Alice',
        'prenom': 'Chen',
        'id': 'analytical_researcher',
        'objectif': 'Research and analyze stocks before making trading decisions',
        'description': 'Data-driven trader who analyzes multiple indicators',
        'style_navigation': 'methodique',
        'preferences_site': 'data-focused interface',
        'sensibilite_prix': 'faible',
        'tolerance_erreurs': 'faible',
        'patience_attente_sec': 15,
        'vitesse_navigation': 'lente',
        'device': 'desktop',
        'website_type': 'finance',
        'credentials': {
            'username': 'WALAEZZEDINE',
            'password': 'WALA@123'
        }
    }

    print(f"\n👤 Persona: {analyst['nom']} {analyst['prenom']}")
    print(f"   ID: {analyst['id']}")
    print(f"   Style: Methodical/Analytical")
    print(f"   Objective: {analyst['objectif']}")

    # Create agent
    agent = PersonaAgent(
        user=analyst,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"\n✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING ANALYTICAL RESEARCH TEST ({config.max_steps} steps max)")
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
            print("\n🎉 SUCCESS! Analytical research completed!")
            print("   ✓ Navigated to quotes section")
            print("   ✓ Searched for stock")
            print("   ✓ Reviewed performance indicators")
            print("   ✓ Made trading decision (buy/skip)")

        # Save results
        results_file = Path("test_calculator_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{analyst['nom']} {analyst['prenom']}",
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
    asyncio.run(test_calculator())
