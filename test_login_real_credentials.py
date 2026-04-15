#!/usr/bin/env python3
"""
Test Wall Street Survivor login with real user credentials
Username: WALAEZZEDINE
Password: WALA@123
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
    print("🧪 WALL STREET SURVIVOR - LOGIN TEST")
    print("="*80)
    
    # Real user credentials
    username = "WALAEZZEDINE"
    password = "WALA@123"
    
    print(f"\n✅ Test Credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")
    
    # Load config
    config = Config()
    print(f"\n✅ Config: {config.llm_provider} - {config.llm_model}")
    print(f"   Headless: {config.headless}")
    print(f"   Max steps: {config.max_steps}")
    
    # Create a simple login scenario
    scenario = {
        'name': 'Wall Street Survivor - Login Test',
        'description': f'Test login with credentials: {username}',
        'objectif': 'Login to Wall Street Survivor and access dashboard',
        'context': {
            'username': username,
            'password': password,
        },
        'key_actions': [
            'Navigate to login page',
            'Enter credentials (auto-filled)',
            'Click login button',
            'Verify dashboard access',
        ],
        'success_criteria': [
            'Successfully logged in',
            'Dashboard visible',
            'Portfolio accessible'
        ]
    }
    
    # Create persona
    persona = {
        'id': 'test_user_wala',
        'nom': 'Test User',
        'prenom': 'WALA',
        'objectif': 'Login and access trading dashboard',
        'credentials': {
            'username': username,
            'password': password,
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
    
    print(f"\n🚀 Starting login test...")
    start_time = time.time()
    
    # Run test
    result = await agent.run_with_mcp(
        start_url="https://www.wallstreetsurvivor.com/"
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("✅ TEST COMPLETED")
    print(f"{'='*80}")
    print(f"Status: {result.get('status')}")
    print(f"Steps: {result.get('steps', 0)}")
    print(f"Time: {elapsed_time:.1f}s")
    print(f"\nResponse preview: {result.get('response', '')[:300]}...")
    
    # Check if login was successful
    if result.get('status') == 'done':
        print(f"\n✅ SUCCESS - Login and task completed!")
    elif 'dashboard' in result.get('response', '').lower():
        print(f"\n✅ Dashboard appears to be accessible")
    elif 'login' in result.get('response', '').lower():
        print(f"\n⚠️ Still on login page - credentials may not be working or login flow incomplete")
    
    # Save detailed results
    report = {
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'status': result.get('status'),
        'steps': result.get('steps', 0),
        'elapsed_time': elapsed_time,
        'results': result.get('results', {}),
        'response_preview': result.get('response', '')[:500],
    }
    
    with open('test_login_walaezzedine.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: test_login_walaezzedine.json")
    print("\n✨ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
