#!/usr/bin/env python3
"""
Quick diagnostic - test Impatient User persona alone
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

async def main():
    print("="*80)
    print("🎭 QUICK TEST - IMPATIENT USER PERSONA")
    print("="*80)
    
    # Load scenario
    scenario_path = 'scenarios/wallstreet_buy_stock_impatient.yaml'
    scenario = load_scenario(scenario_path)
    print(f"\n✅ Scenario: {scenario.get('name')}")
    
    # Load config
    config = Config()
    print(f"✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Max steps: {config.max_steps}")
    
    # Create persona
    persona = {
        'id': 'impatient_trader',
        'nom': 'Quick Trader',
        'prenom': 'Impatient',
        'objectif': 'Buy AAPL stock in under 20 seconds',
        'style_navigation': 'direct',
        'credentials': {
            'username': 'testuser',
            'password': 'WallStreet@2025',
            'portfolio': 'My Practice Portfolio',
            'target_stock': 'AAPL',
        },
    }
    
    print(f"\n✅ Persona: {persona['prenom']} {persona['nom']}")
    
    # Create agent
    agent = PersonaAgent(
        user=persona,
        scenario=scenario,
        config=config,
        use_mcp=True
    )
    
    print(f"\n🚀 Starting test... (max 30 steps)")
    start_time = time.time()
    
    # Run test
    result = await agent.run_with_mcp(
        start_url="https://www.wallstreetsurvivor.com/"
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("✅ TEST RESULTS")
    print(f"{'='*80}")
    print(f"Status: {result.get('status')}")
    print(f"Steps: {result.get('steps', 0)}")
    print(f"Time: {elapsed_time:.1f}s")
    print(f"\nResponse: {result.get('response', '')[:200]}...")
    
    # Save results
    report = {
        'timestamp': datetime.now().isoformat(),
        'persona': 'Impatient User',
        'status': result.get('status'),
        'steps': result.get('steps', 0),
        'elapsed_time': elapsed_time,
        'results': result.get('results', {}),
    }
    
    with open('test_impatient_quick.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Results saved to: test_impatient_quick.json")

if __name__ == "__main__":
    asyncio.run(main())
