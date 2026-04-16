#!/usr/bin/env python3
"""
Test script for Microsoft Deep Analysis persona
Searches for Microsoft, reviews financial data, and makes investment decision
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_microsoft_analyst():
    print("="*80)
    print("🧪 MICROSOFT DEEP ANALYSIS TEST")
    print("="*80)

    # Load config
    config = Config()
    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/microsoft_deep_analysis.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")
    print(f"   Description: {scenario['description'][:100]}...")
    print(f"   Key actions: {len(scenario.get('key_actions', []))} steps")

    # Create analyst persona - someone methodical and thorough
    analyst = {
        'nom': 'David',
        'prenom': 'Thornton',
        'id': 'financial_analyst',
        'objectif': 'Perform comprehensive analysis of Microsoft stock before investment decision',
        'description': 'Data-driven financial analyst who thoroughly researches stocks',
        'style_navigation': 'methodique',
        'preferences_site': 'detailed financial analysis tools',
        'sensibilite_prix': 'basse',
        'tolerance_erreurs': 'tres_faible',
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
    print(f"   Style: Methodical/Thorough")
    print(f"   Objective: {analyst['objectif']}")
    print(f"   Tolerance for errors: Very Low (precision focused)")

    # Create agent
    agent = PersonaAgent(
        user=analyst,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    print(f"\n✅ Agent initialized with MCP support")

    print("\n" + "="*80)
    print(f"🚀 STARTING MICROSOFT ANALYSIS TEST ({config.max_steps} steps max)")
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

        if result.get('steps_detail'):
            steps_detail = result['steps_detail']

            # Count action types
            actions = {}
            for step in steps_detail:
                action = step.get('action', 'unknown')
                actions[action] = actions.get(action, 0) + 1

            print(f"\n📊 Actions breakdown:")
            for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {action}: {count}x")

            # Extract final thoughts
            if steps_detail[-1].get('thought'):
                final_thought = steps_detail[-1]['thought'][:300]
                print(f"\n💭 Final Analysis:")
                print(f"   {final_thought}...")

        # Save results
        with open('test_microsoft_analyst_results.json', 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{analyst['nom']} {analyst['prenom']}",
                'result': result
            }, f, indent=2)

        print(f"\n📁 Results saved to: test_microsoft_analyst_results.json")

    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_microsoft_analyst())
