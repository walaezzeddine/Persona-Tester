"""Integration test for screenshot-driven reasoning in MCP mode.

This test checks two things:
1) a screenshot image was attached to at least one LLM observation
2) the model reasoning includes a visual cue requested by scenario
"""

import asyncio
from pathlib import Path

import pytest

from src.agent import PersonaAgent, BROWSER_USE_AVAILABLE
from src.config_loader import Config, load_persona, load_scenario


def _provider_supports_vision(provider: str) -> bool:
    return provider.lower() in {"openai", "github", "google", "ollama"}


def _runtime_skip_if_not_ready(config: Config) -> None:
    if not BROWSER_USE_AVAILABLE:
        pytest.skip("browser-use is not installed or not importable")

    if not _provider_supports_vision(config.vision_provider):
        pytest.skip(
            f"vision provider '{config.vision_provider}' is not suitable for screenshot vision test"
        )


@pytest.mark.integration
def test_browseruse_screenshot_is_attached_and_used_in_reasoning():
    root = Path(__file__).resolve().parents[1]

    config = Config(str(root / "config" / "config.yaml"))
    # Force vision path for this test without changing project defaults.
    config._config.setdefault("browser", {})["vision_enabled"] = True
    config._config.setdefault("browser", {})["sandbox"] = True
    config._config.setdefault("navigation", {})["max_steps"] = 10

    _runtime_skip_if_not_ready(config)

    persona = load_persona(str(root / "personas" / "acheteur_impatient.json"))
    scenario = load_scenario(str(root / "scenarios" / "screenshot_comprehension_test.yaml"))

    agent = PersonaAgent(user=persona, scenario=scenario, config=config, use_mcp=True)

    if not agent._attach_observation_images:
        pytest.skip(
            "vision image attachment is disabled at runtime (check provider setup and sandbox)"
        )

    try:
        result = asyncio.run(agent.run_with_mcp(start_url="https://automationexercise.com/products"))
    except Exception as exc:
        text = str(exc).lower()
        infra_markers = (
            "npx",
            "playwright",
            "mcp",
            "cdp",
            "browser use",
            "connection",
            "not found",
            "enoent",
        )
        if any(marker in text for marker in infra_markers):
            pytest.skip(f"integration runtime unavailable: {exc}")
        raise

    assert result["status"] in {"completed", "max_steps_reached"}, result

    steps = result.get("steps_detail", [])
    assert steps, "Expected non-empty step trace"

    image_attached = any(bool(step.get("vision_image_attached")) for step in steps)
    assert image_attached, "No step reported screenshot attachment to LLM messages"

    visual_markers = (
        "top-left",
        "top left",
        "visual",
        "position",
        "screenshot",
        "upper-left",
        "upper left",
    )
    thought_text = "\n".join(str(step.get("thought", "")).lower() for step in steps)
    assert any(marker in thought_text for marker in visual_markers), (
        "No visual reasoning cue found in thoughts. "
        "Expected mention of scenario visual signal such as 'top-left'."
    )
