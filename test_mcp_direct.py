"""
Test run_with_mcp_direct() — hybrid approach:
Python drives navigation, LLM only analyses the snapshot.
"""

import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from src.agent import PersonaAgent
from src.config_loader import Config, load_persona

load_dotenv()


async def main():
    print("\n" + "═" * 60)
    print("     MCP DIRECT TEST — hybrid navigation")
    print("═" * 60)

    config_path = Path(__file__).parent / "config" / "config.yaml"
    config = Config(str(config_path))
    print(f"\n✓ LLM : {config.llm_provider}/{config.llm_model}")
    print(f"✓ Headless : {config.headless}")

    persona_path = Path(__file__).parent / "personas" / "acheteur_impatient.json"
    persona = load_persona(str(persona_path))
    print(f"✓ Persona : {persona['id']}")

    scenario = {
        "name": "Find cheapest t-shirt",
        "objectif": "Find the cheapest t-shirt and add it to cart",
    }

    agent = PersonaAgent(user=persona, scenario=scenario, config=config)

    result = await agent.run_with_mcp_direct(
        url="https://automationexercise.com/products",
        objectif="Find the cheapest t-shirt and add it to cart",
    )

    print("\n" + "═" * 60)
    print("FINAL RESULT")
    print("═" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
