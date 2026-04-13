#!/usr/bin/env python
"""
Test script to run a persona on a website
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from src.config_loader import Config
from src.agent import PersonaAgent


async def test_persona_on_website():
    """Test running a persona on a website"""

    # Load configuration
    config = Config()
    print(f"✓ Config loaded")
    print(f"  - Provider: {config.llm_provider}")
    print(f"  - Model: {config.llm_model}")
    print(f"  - Vision Enabled: {config.vision_enabled}")
    print(f"  - Max Steps: {config.max_steps}")

    # Load a persona
    persona_path = Path(__file__).parent / "generated_personas" / "voyageur_impulsif.json"

    if not persona_path.exists():
        print(f"✗ Persona file not found: {persona_path}")
        # List available personas
        personas_dir = Path(__file__).parent / "generated_personas"
        if personas_dir.exists():
            print(f"\nAvailable personas:")
            for p in personas_dir.glob("*.json"):
                print(f"  - {p.name}")
        return False

    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)

    print(f"\n✓ Loaded persona: {persona_data.get('nom')}")
    print(f"  - Objectif: {persona_data.get('objectif')}")
    print(f"  - Device: {persona_data.get('device')}")
    print(f"  - Website: {persona_data.get('website_url')}")

    # Create scenario
    scenario = {
        "name": "Test Persona Run",
        "objectif": persona_data.get("objectif", "Test website navigation")
    }

    # Target URL - use demo site for testing
    target_url = "https://automationexercise.com"

    print(f"\n🚀 Starting persona test...")
    print(f"  - Target URL: {target_url}")
    print(f"  - Using LLM: {config.llm_provider}/{config.llm_model}")
    print(f"  - Max Steps: {config.max_steps}")
    print(f"  - Headless: {config.headless}")
    print(f"  - Sandbox: {config.sandbox}")
    print(f"  - Vision Enabled: {config.vision_enabled}")

    try:
        # Create agent
        agent = PersonaAgent(
            user=persona_data,
            scenario=scenario,
            config=config,
            use_mcp=False  # Disable MCP for simple test
        )

        # Run the agent with limited steps
        print("\n⏳ Running agent...\n" + "="*60)
        result = await agent.run_with_mcp(start_url=target_url)

        print("\n" + "="*60)
        print(f"\n✅ Test completed!")

        if result:
            print(f"\nResult Summary:")
            if isinstance(result, dict):
                for key, value in result.items():
                    print(f"  - {key}: {value}")
            else:
                print(f"  - Result: {result}")

        return True

    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PERSONA WEBSITE TEST")
    print("=" * 60 + "\n")

    try:
        success = asyncio.run(test_persona_on_website())

        if success:
            print("\n🎉 Test passed!")
            sys.exit(0)
        else:
            print("\n⚠️ Test ended")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
