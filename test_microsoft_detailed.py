#!/usr/bin/env python3
"""
Microsoft Detailed Analysis Test - VISUALIZE EVERY ACTION
Shows exactly what the agent clicks and does on the website
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_microsoft_detailed():
    print("="*100)
    print("🧪 MICROSOFT DETAILED ANALYSIS TEST - VISUAL ACTIONS")
    print("="*100)

    # Load config
    config = Config()
    nav_cfg = config._config.setdefault("navigation", {})
    nav_cfg["max_steps"] = max(int(nav_cfg.get("max_steps", 0) or 0), 70)
    print(f"\n✅ Configuration:")
    print(f"   Provider: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless} ← YOU SHOULD SEE THE BROWSER!")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario
    scenario_path = Path("scenarios/microsoft_detailed_analysis.yaml")
    if not scenario_path.exists():
        print(f"❌ Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario loaded: {scenario['name']}")

    # Create analyst persona
    analyst = {
        'nom': 'Sarah',
        'prenom': 'Chen',
        'id': 'research_analyst',
        'objectif': 'Analyze Microsoft through Company Profile, News, Ratings, Price History, and Financials',
        'description': 'Thorough financial analyst who reads and analyzes every data source',
        'style_navigation': 'methodique',
        'preferences_site': 'detailed financial data',
        'sensibilite_prix': 'basse',
        'tolerance_erreurs': 'tres_faible',
        'patience_attente_sec': 20,
        'vitesse_navigation': 'lente',
        'device': 'desktop',
        'website_type': 'finance',
        'credentials': {
            'username': 'WALAEZZEDINE',
            'password': 'WALA@123'
        }
    }

    print(f"\n👤 Persona: {analyst['nom']} {analyst['prenom']}")
    print(f"   Style: Methodical/Thorough")
    print(f"   Objective: Deep financial analysis")

    # Create agent
    agent = PersonaAgent(
        user=analyst,
        scenario=scenario,
        config=config,
        use_mcp=True
    )

    print("\n" + "="*100)
    print(f"🚀 STARTING TEST - WATCH THE BROWSER WINDOW FOR ACTIONS")
    print("="*100)
    print("\n📍 Expected sequence:")
    print("   1. Login with credentials")
    print("   2. Navigate to Stocks section")
    print("   3. Search for 'MSFT'")
    print("   4. Click Company Profile tab")
    print("   5. Click Company News")
    print("   6. Click Analyst Rating")
    print("   7. Click Price History")
    print("   8. Click Financial Statements")
    print("   9. Make BUY/NO BUY decision")
    print("\n" + "-"*100 + "\n")

    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        print("\n" + "="*100)
        print("✅ TEST EXECUTION COMPLETE")
        print("="*100)

        status = result.get('status')
        steps_taken = result.get('steps', 0)

        print(f"\n📊 Summary:")
        print(f"   Status: {status}")
        print(f"   Steps completed: {steps_taken}/{config.max_steps}")

        if result.get('steps_detail'):
            steps_detail = result['steps_detail']

            # Count action types
            actions = {}
            for step in steps_detail:
                action = step.get('action', 'unknown')
                actions[action] = actions.get(action, 0) + 1

            print(f"\n📊 Actions used:")
            for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
                if action not in ['DONE', 'None']:
                    print(f"   • {action}: {count}x")

            # Show key steps
            print(f"\n🔍 Key Steps Executed:")
            for i, step in enumerate(steps_detail[:10], 1):
                action = step.get('action', 'unknown')
                if action and action != 'DONE':
                    thought = step.get('thought', '')[:150]
                    if thought:
                        print(f"   Step {i}: {action}")
                        print(f"      → {thought}...")

            # Check if found MSFT
            msft_found = any('MSFT' in str(s.get('thought', '')) or 'Microsoft' in str(s.get('thought', '')) for s in steps_detail)
            print(f"\n🎯 Did agent find Microsoft? {('✅ YES' if msft_found else '❌ NO')}")

            # Check final decision
            if steps_detail[-1].get('thought'):
                final = steps_detail[-1]['thought'][:300]
                if 'buy' in final.lower() or 'not buy' in final.lower():
                    print(f"\n💡 Final Decision Found: YES")
                    print(f"   {final}...")
                else:
                    print(f"\n⚠️ Final Decision: Not clear")

        # Save results
        with open('test_microsoft_detailed_results.json', 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{analyst['nom']} {analyst['prenom']}",
                'result': result
            }, f, indent=2)

        print(f"\n📁 Results saved to: test_microsoft_detailed_results.json")

    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_microsoft_detailed())
