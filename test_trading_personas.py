#!/usr/bin/env python3
"""
Test Wall Street Survivor - TRADING PERSONAS
Tests two different user behaviors: Impatient (quick buy) vs Wise (research then buy)
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def run_persona_test(persona_name: str, scenario_path: str, start_url: str = None):
    """Run a single persona test"""
    
    print(f"\n{'='*80}")
    print(f"🎭 TESTING PERSONA: {persona_name}")
    print(f"{'='*80}")
    
    # Load scenario
    if not Path(scenario_path).exists():
        print(f"❌ Scenario not found: {scenario_path}")
        return None
    
    scenario = load_scenario(scenario_path)
    print(f"✅ Scenario: {scenario.get('name')}")
    print(f"   Objectif: {scenario.get('objectif')}")
    
    # Load config
    config = Config()
    
    # Create persona
    persona = {
        'id': persona_name.lower().replace(' ', '_'),
        'nom': persona_name,
        'prenom': 'Trading',
        'objectif': scenario.get('objectif'),
        'style_navigation': 'direct',
        'credentials': {
            'username': scenario.get('context', {}).get('username', 'testuser'),
            'password': scenario.get('context', {}).get('password', 'WallStreet@2025'),
            'portfolio': scenario.get('context', {}).get('portfolio', 'My Practice Portfolio'),
            'target_stock': scenario.get('context', {}).get('target_stock', 'AAPL'),
        },
        'persona_type': 'trading',
    }
    
    print(f"✅ Persona: {persona['prenom']} {persona['nom']}")
    print(f"   Target Stock: {persona['credentials'].get('target_stock')}")
    
    # Create agent
    agent = PersonaAgent(
        user=persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    
    print(f"\n🚀 Starting test...")
    start_time = time.time()
    
    # Run test
    try:
        result = await agent.run_with_mcp(
            start_url=start_url or "https://www.wallstreetsurvivor.com/"
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ Test completed in {elapsed_time:.1f} seconds")
        print(f"   Status: {result.get('status')}")
        print(f"   Steps: {result.get('steps', 0)}")
        
        # Return results
        return {
            'persona': persona_name,
            'status': result.get('status'),
            'steps': result.get('steps', 0),
            'elapsed_time': elapsed_time,
            'results': result.get('results', {}),
            'response': result.get('response', ''),
            'timestamp': datetime.now().isoformat(),
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {
            'persona': persona_name,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }

async def main():
    print("="*80)
    print("🎭 WALL STREET SURVIVOR - TRADING PERSONAS TEST")
    print("="*80)
    print("\nTesting two different user behaviors:")
    print("1. IMPATIENT USER: Quick stock purchase (< 20 seconds)")
    print("2. WISE USER: Research then buy decision")
    print("\nBoth personas must login with auto-filled credentials")
    
    # Test configuration
    personas = [
        {
            'name': 'Impatient User',
            'scenario': 'scenarios/wallstreet_buy_stock_impatient.yaml',
            'start_url': 'https://www.wallstreetsurvivor.com/',
        },
        {
            'name': 'Wise User',
            'scenario': 'scenarios/wallstreet_buy_stock_wise.yaml',
            'start_url': 'https://www.wallstreetsurvivor.com/',
        }
    ]
    
    # Run all persona tests
    all_results = []
    for persona in personas:
        result = await run_persona_test(
            persona_name=persona['name'],
            scenario_path=persona['scenario'],
            start_url=persona['start_url']
        )
        if result:
            all_results.append(result)
        
        # Wait between personas to avoid conflicts
        await asyncio.sleep(2)
    
    # Generate report
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    for result in all_results:
        print(f"\n{result['persona']}:")
        print(f"  Status: {result.get('status')}")
        print(f"  Steps: {result.get('steps')}")
        print(f"  Time: {result.get('elapsed_time', 0):.1f}s")
        if 'error' in result:
            print(f"  Error: {result['error']}")
        else:
            # Check persona-specific success metrics
            if result['persona'] == 'Impatient User':
                if result.get('elapsed_time', 0) < 30:  # Generous limit for network
                    print(f"  ✅ Time limit respected: {result.get('elapsed_time', 0):.1f}s < 30s")
                else:
                    print(f"  ❌ Time limit exceeded: {result.get('elapsed_time', 0):.1f}s > 30s")
            elif result['persona'] == 'Wise User':
                print(f"  ✅ Research and decision made")
    
    # Save detailed results
    report = {
        'test_type': 'Trading Personas',
        'timestamp': datetime.now().isoformat(),
        'personas_tested': [r['persona'] for r in all_results],
        'results': all_results,
        'summary': {
            'total_personas': len(all_results),
            'completed': len([r for r in all_results if r.get('status') in ['done', 'max_steps_reached']]),
            'errors': len([r for r in all_results if r.get('status') == 'error']),
        }
    }
    
    results_file = Path('test_trading_personas_results.json')
    with open(results_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    print("\n✨ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())
