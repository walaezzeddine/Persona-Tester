#!/usr/bin/env python3
"""
Final Microsoft Menu Sections Test
Navigate to MSFT quote page and click the menu items:
Company Profile → Company News → Analyst Ratings → Price History → Financial Statements
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def test_msft_menu():
    print("="*100)
    print("🎯 FINAL TEST: MICROSOFT QUOTE PAGE - CLICK ALL MENU SECTIONS")
    print("="*100)

    config = Config()
    print(f"\n✅ Configuration: headless={config.headless} (BROWSER VISIBLE)")

    scenario = load_scenario("scenarios/microsoft_menu_sections.yaml")

    analyst = {
        'nom': 'Jennifer',
        'prenom': 'Anderson',
        'id': 'menu_analyst',
        'objectif': 'Click through all menu sections and analyze MSFT stock data',
        'description': 'Analyst who systematically reviews all available data',
        'style_navigation': 'methodique',
        'preferences_site': 'organized financial menus',
        'sensibilite_prix': 'basse',
        'tolerance_erreurs': 'tres_faible',
        'patience_attente_sec': 15,
        'vitesse_navigation': 'normale',
        'device': 'desktop',
        'website_type': 'finance',
        'credentials': {
            'username': 'WALAEZZEDINE',
            'password': 'WALA@123'
        }
    }

    print(f"👤 Persona: {analyst['nom']} {analyst['prenom']}")

    agent = PersonaAgent(user=analyst, scenario=scenario, config=config, use_mcp=True)

    print("\n" + "="*100)
    print("🚀 STARTING - CLICK MENU SECTIONS")
    print("="*100)
    print("\n📍 Expected actions:")
    print("   1. Navigate to MSFT Quote Page")
    print("   2. Find menu with: Company Profile, Company News, Analyst Ratings, Price History, Financial Statements")
    print("   3. Click each menu item and read data")
    print("   4. Make BUY/NO BUY decision")
    print("\n" + "-"*100)

    try:
        msft_url = "https://app.wallstreetsurvivor.com/quotes/quotes?type=fullnewssummary&symbol=MSFT&exchange=US"
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

            # Track which sections were clicked
            sections_found = {
                'Company Profile': False,
                'Company News': False,
                'Analyst Ratings': False,
                'Price History': False,
                'Financial Statements': False
            }

            for step in steps_detail:
                thought = step.get('thought', '').lower()
                for section in sections_found:
                    if section.lower() in thought and 'click' in thought:
                        sections_found[section] = True

            print(f"\n🔍 Sections Clicked:")
            for section, clicked in sections_found.items():
                status_icon = '✅' if clicked else '❌'
                print(f"   {status_icon} {section}")

            # Final decision
            if steps_detail[-1].get('thought'):
                thought = steps_detail[-1]['thought'].lower()
                if 'buy' in thought and 'not' not in thought:
                    print(f"\n💡 Final Decision: ✅ BUY MSFT")
                elif 'not buy' in thought or 'do not buy' in thought:
                    print(f"\n💡 Final Decision: ❌ DO NOT BUY MSFT")
                else:
                    print(f"\n💡 Final Decision: ❓ UNDECIDED")

        # Save results
        with open('test_msft_menu_results.json', 'w') as f:
            json.dump({
                'scenario': scenario['name'],
                'persona': f"{analyst['nom']} {analyst['prenom']}",
                'url': msft_url,
                'result': result
            }, f, indent=2)

        print(f"\n📁 Results: test_msft_menu_results.json")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_msft_menu())
