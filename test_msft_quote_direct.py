#!/usr/bin/env python3
"""
Direct Microsoft Quote Page Analysis -
Navigate directly to MSFT quote page and analyze Company Profile, News, Ratings, Price History, Financials
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_microsoft_quote():
    print("="*100)
    print("🧪 MICROSOFT QUOTE PAGE - DIRECT ANALYSIS")
    print("="*100)

    config = Config()
    print(f"\n✅ Configuration:")
    print(f"   Headless: {config.headless} ← BROWSER VISIBLE!")
    print(f"   Max steps: {config.max_steps}")

    # Load scenario - use the detailed one
    scenario_path = Path("scenarios/microsoft_detailed_analysis.yaml")
    scenario = load_scenario(str(scenario_path))
    print(f"\n✅ Scenario: {scenario['name']}")

    analyst = {
        'nom': 'Marcus',
        'prenom': 'Williams',
        'id': 'stock_researcher',
        'objectif': 'Analyze MSFT stock data: Profile, News, Ratings, Price History, Statements',
        'description': 'Analyst who reads all available financial data sections',
        'style_navigation': 'methodique',
        'preferences_site': 'detailed company data',
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

    agent = PersonaAgent(
        user=analyst,
        scenario=scenario,
        config=config,
        use_mcp=True
    )

    print("\n" + "="*100)
    print("🚀 STARTING - DIRECT QUOTE PAGE ANALYSIS")
    print("="*100)
    print("\n📍 Direct Navigation:")
    print("   → Going directly to MSFT quote page")
    print("   → Then analyzing all available data sections")
    print("   → Looking for: Profile, News, Analyst Rating, Price History, Financials")
    print("\n" + "-"*100 + "\n")

    try:
        # Direct URL to MSFT quote page
        msft_url = "https://app.wallstreetsurvivor.com/quotes/quotes?type=fullnewssummary&symbol=MSFT&exchange=US"

        print(f"🔗 Opening: {msft_url}\n")

        result = await agent.run_with_mcp(start_url=msft_url)

        print("\n" + "="*100)
        print("✅ TEST COMPLETE")
        print("="*100)

        status = result.get('status')
        steps = result.get('steps', 0)

        print(f"\n📊 Results:")
        print(f"   Status: {status}")
        print(f"   Steps: {steps}/{config.max_steps}")

        if result.get('steps_detail'):
            steps_detail = result['steps_detail']

            # Count actions
            actions = {}
            for step in steps_detail:
                action = step.get('action', '')
                actions[action] = actions.get(action, 0) + 1

            print(f"\n📊 Actions:")
            for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
                if action:
                    print(f"   • {action}: {count}x")

            # Find what tabs/sections were clicked
            print(f"\n🔍 Sections Found & Clicked:")
            sections = ['Company Profile', 'Company News', 'Analyst', 'Price History', 'Financial']
            for section in sections:
                found = any(section.lower() in str(s.get('thought', '')).lower() for s in steps_detail)
                status = '✅' if found else '❌'
                print(f"   {status} {section}")

            # Final decision
            if steps_detail[-1].get('thought'):
                thought = steps_detail[-1]['thought']
                if 'buy' in thought.lower():
                    decision = '✅ BUY'
                elif 'not buy' in thought.lower() or 'do not buy' in thought.lower():
                    decision = '❌ DO NOT BUY'
                else:
                    decision = '❓ UNCLEAR'
                print(f"\n💡 Final Decision: {decision}")
                print(f"   Reasoning: {thought[:200]}...")

        # Save results
        with open('test_msft_quote_results.json', 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{analyst['nom']} {analyst['prenom']}",
                'start_url': msft_url,
                'result': result
            }, f, indent=2)

        print(f"\n📁 Results saved to: test_msft_quote_results.json")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_microsoft_quote())
