#!/usr/bin/env python3
"""
Test Wall Street Survivor - AMD Momentum Trade (Market Movers Path)
Alternative navigation flow for A/B comparison vs NVIDIA scenario.
"""
import asyncio
import json
from pathlib import Path
from src.config_loader import Config, load_scenario
from src.agent import PersonaAgent

CREDENTIALS = {
    "username": "WALAEZZEDINE",
    "password": "WALA@123",
}


async def test_amd_market_movers() -> None:
    print("=" * 80)
    print("AMD MOMENTUM TRADE - MARKET MOVERS PATH")
    print("=" * 80)

    config = Config()
    print("\nConfiguration:")
    print(f"  Provider: {config.llm_provider} - {config.llm_model}")
    print(f"  Headless: {config.headless}")
    print(f"  Max steps: {config.max_steps}")

    scenario_path = Path("scenarios/wallstreet_amd_market_movers_trade.yaml")
    if not scenario_path.exists():
        print(f"Scenario file not found: {scenario_path}")
        return

    scenario = load_scenario(str(scenario_path))
    print(f"\nScenario loaded: {scenario['name']}")

    trader = {
        "nom": "Rayan",
        "prenom": "Bennett",
        "id": "amd_momentum_trader",
        "objectif": "Trade AMD using Market Movers path and momentum analysis",
        "description": "Momentum trader using market movers navigation",
        "style_navigation": "methodique",
        "preferences_site": "market movers first",
        "sensibilite_prix": "moyenne",
        "tolerance_erreurs": "moyenne",
        "patience_attente_sec": 10,
        "vitesse_navigation": "normale",
        "device": "desktop",
        "website_type": "finance",
        "credentials": CREDENTIALS,
    }

    agent = PersonaAgent(user=trader, scenario=scenario, config=config, use_mcp=True)

    print("\n" + "=" * 80)
    print(f"STARTING AMD MARKET MOVERS TEST ({config.max_steps} steps max)")
    print("=" * 80 + "\n")

    try:
        result = await agent.run_with_mcp(start_url="https://www.wallstreetsurvivor.com/")

        status = result.get("status")
        steps_taken = result.get("steps", 0)

        print("\n" + "=" * 80)
        print("TEST EXECUTION COMPLETE")
        print("=" * 80)
        print(f"\nStatus: {status}")
        print(f"Steps completed: {steps_taken}/{config.max_steps}")

        results_file = Path("test_amd_market_movers_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "scenario": scenario["name"],
                    "persona": f"{trader['nom']} {trader['prenom']}",
                    "result": result,
                },
                f,
                indent=2,
            )
        print(f"\nResults saved to: {results_file}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_amd_market_movers())
