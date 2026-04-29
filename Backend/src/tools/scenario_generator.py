"""
Scenario Generator - LLM-powered scenario generation for ReAct agent

Instead of generating executable Playwright scripts, this module generates
structured scenario JSON that guides the ReAct agent's navigation behavior.

The scenario includes high-level WHAT-to-do steps (not HOW), allowing the
agent to use its own reasoning and tools to accomplish each step.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class ScenarioGenerator:
    """
    LLM-powered scenario generator that:
    1. Takes persona + website analysis
    2. Generates a structured scenario with high-level steps
    3. Returns scenario JSON for ReAct agent guidance
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str = None,
        temperature: float = 0.4
    ):
        """
        Initialize the Scenario Generator with an LLM.

        Args:
            provider: LLM provider ('ollama', 'openai', 'github', 'google')
            model: Model name (defaults based on provider)
            temperature: LLM temperature for creativity (0.3-0.7 recommended)
        """
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        """Initialize LLM based on provider."""
        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            return ChatOpenAI(
                model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:cloud"),
                base_url=base_url,
                api_key="ollama",
                temperature=self.temperature,
                max_tokens=2500,
            )
        if provider == "google":
            google_key = os.getenv("GOOGLE_API_KEY")
            if not google_key:
                raise ValueError("GOOGLE_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=google_key,
                temperature=self.temperature,
                max_output_tokens=2500,
            )
        elif provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            if not api_key:
                raise ValueError("GITHUB_TOKEN not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4.1-mini",
                base_url="https://models.github.ai/inference",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2500,
            )
        else:  # openai (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2500,
            )

    def _build_llm_context(self, website_analysis: Dict[str, Any], max_chars: int = 2000) -> str:
        """
        Extract and truncate the LLM context from website analysis.
        Prefers llm_context markdown; falls back to structured fields.
        """
        if not website_analysis:
            return "No website analysis available."

        # Try llm_context first (compact markdown from WebsiteAnalyzer)
        llm_ctx = website_analysis.get("llm_context")
        if isinstance(llm_ctx, str) and llm_ctx.strip():
            return llm_ctx.strip()[:max_chars]

        # Fallback: build from structured fields
        parts = []

        site_type = website_analysis.get("site_type") or website_analysis.get("type", "website")
        parts.append(f"Site type: {site_type}")

        purpose = website_analysis.get("primary_purpose")
        if purpose:
            parts.append(f"Purpose: {purpose}")

        features = website_analysis.get("key_features", [])
        if features:
            parts.append(f"Key features: {', '.join(str(f) for f in features[:8])}")

        user_actions = website_analysis.get("user_actions", [])
        if user_actions:
            parts.append(f"User actions: {', '.join(str(a) for a in user_actions[:6])}")

        forms = website_analysis.get("forms_and_inputs", [])
        if forms:
            parts.append(f"Forms/inputs: {', '.join(str(f) for f in forms[:5])}")

        return "\n".join(parts)[:max_chars]

    def _build_persona_context(self, persona: Dict[str, Any]) -> str:
        """Build persona context section for the prompt."""
        lines = []

        nom = persona.get("nom", "Unknown")
        lines.append(f"Name: {nom}")

        objectif = persona.get("objectif", "Complete the task")
        lines.append(f"Objective: {objectif}")

        vitesse = persona.get("vitesse_navigation", "moyenne")
        lines.append(f"Navigation speed: {vitesse}")

        style = persona.get("style_navigation", "normal")
        lines.append(f"Navigation style: {style}")

        device = persona.get("device", "desktop")
        lines.append(f"Device: {device}")

        patience = persona.get("patience_attente_sec", 15)
        lines.append(f"Patience (seconds): {patience}")

        sensibilite_prix = persona.get("sensibilite_prix", "faible")
        lines.append(f"Price sensitivity: {sensibilite_prix}")

        tolerance = persona.get("tolerance_erreurs", "haute")
        lines.append(f"Error tolerance: {tolerance}")

        return "\n".join(lines)

    def _build_scenario_with_user_actions(
        self,
        persona: Dict[str, Any],
        user_actions: List[str],
        website_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a scenario using user-edited actions directly.
        Only use LLM to enhance metadata (name, success_criteria).
        """
        objectif = persona.get("objectif", "Complete the task")
        vitesse = persona.get("vitesse_navigation", "moyenne")
        style = persona.get("style_navigation", "normal")

        # Build context sections for metadata generation
        llm_context = self._build_llm_context(website_analysis)
        persona_context = self._build_persona_context(persona)

        # Build a lightweight prompt just for scenario metadata
        prompt = f"""You are enhancing a test scenario with user-provided actions.

## PERSONA
{persona_context}

## WEBSITE CONTEXT
{llm_context}

## USER-PROVIDED ACTIONS (Do NOT modify)
{"".join(f"- {a}\n" for a in user_actions)}

## YOUR TASK

Generate ONLY the scenario metadata (name, success_criteria, description).
DO NOT regenerate the actions - use the user-provided actions exactly as given.

Return JSON with ONLY these fields:
{{
  "name": "A descriptive name for this scenario",
  "description": "One sentence description of what this persona does",
  "success_criteria": [
    "Observable outcome 1",
    "Observable outcome 2"
  ]
}}

IMPORTANT: Do NOT include key_actions in your response - they are already provided by the user.
Return ONLY valid JSON, no other text.
"""

        try:
            messages = [
                SystemMessage(
                    content="""You are a test scenario enhancer. You generate scenario metadata
while respecting pre-defined user actions. Return ONLY valid JSON."""
                ),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)
            response_text = response.content

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                metadata = json.loads(json_match.group(0))
            else:
                metadata = json.loads(response_text.strip())

            # Build final scenario with user actions + LLM metadata
            scenario = {
                "name": metadata.get("name", f"{style.title()} User"),
                "objectif": objectif,
                "description": metadata.get("description", f"This persona navigates to accomplish: {objectif}"),
                "key_actions": user_actions[:10],  # Use user-edited actions directly
                "success_criteria": metadata.get("success_criteria", [
                    f"Task '{objectif}' is completed",
                    "Final confirmation or success state is visible"
                ]),
                "strict_done_validation": False
            }

            print(f"✅ Scenario enhanced with user actions")
            return scenario

        except Exception as e:
            print(f"⚠️  Metadata generation failed: {e}, using defaults")
            # Fallback: use user actions with minimal metadata
            return {
                "name": f"{style.title()} User",
                "objectif": objectif,
                "description": f"This persona navigates to accomplish: {objectif}",
                "key_actions": user_actions[:10],
                "success_criteria": [
                    f"Task '{objectif}' is completed",
                    "Final confirmation or success state is visible"
                ],
                "strict_done_validation": False
            }

    def _build_actions_inspiration(self, persona: Dict[str, Any]) -> str:
        """Extract actions_site as inspiration (not to be copied verbatim)."""
        actions = persona.get("actions_site", [])
        if not actions:
            return "No specific actions provided."

        return "\n".join(f"- {a}" for a in actions[:10])

    def generate(self, persona: Dict[str, Any], website_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a structured scenario for the ReAct agent.

        Args:
            persona: Persona dict from PersonaGenerator
            website_analysis: Website analysis from WebsiteAnalyzer

        Returns:
            Scenario dict with name, objectif, key_actions, success_criteria
        """
        print(f"\n📝 Generating scenario for persona: {persona.get('nom', 'Unknown')}...")

        # Extract key persona attributes
        nom = persona.get("nom", "Unknown")
        objectif = persona.get("objectif", "Complete the task")
        vitesse = persona.get("vitesse_navigation", "moyenne")
        style = persona.get("style_navigation", "normal")

        # Check if user has already edited and saved actions
        user_edited_actions = persona.get("actions_site", [])
        if user_edited_actions and isinstance(user_edited_actions, list) and len(user_edited_actions) > 0:
            print(f"✅ Using user-edited actions ({len(user_edited_actions)} actions)")
            # Skip LLM generation of actions, use user edits directly
            return self._build_scenario_with_user_actions(persona, user_edited_actions, website_analysis)

        # Build context sections for LLM (only if generating new actions)
        llm_context = self._build_llm_context(website_analysis)
        persona_context = self._build_persona_context(persona)
        actions_inspiration = self._build_actions_inspiration(persona)

        # Build the prompt
        prompt = f"""You are generating a test scenario for a ReAct agent that will navigate a website.

## PERSONA
{persona_context}

## WEBSITE CONTEXT
{llm_context}

## ACTION INSPIRATION (reference only)
The persona has these suggested actions (use as inspiration, do NOT copy verbatim):
{actions_inspiration}

## YOUR TASK

Generate a scenario with this exact JSON structure:

{{
  "name": "A descriptive name like 'Quick Mobile Shopper' or 'Careful Price Comparator'",
  "objectif": "{objectif}",
  "description": "One sentence describing what this persona does on the website",
  "key_actions": [
    // 5-10 HIGH LEVEL steps in plain language
    // MUST be WHAT to do, NOT HOW to do it
    // NO CSS selectors, NO XPath, NO page.click(), NO code
    // Examples of GOOD steps:
    //   - "Log in with provided credentials"
    //   - "Search for a product using the search bar"
    //   - "Compare prices across different options"
    //   - "Add selected item to cart"
    //   - "Proceed to checkout and enter shipping info"
    // Examples of BAD steps (DO NOT generate these):
    //   - "await page.click('#login-btn')"
    //   - "Fill input[name=username] with 'john'"
    //   - "Click element at XPath //button[@id='submit']"
  ],
  "success_criteria": [
    // 2-4 observable outcomes proving the objective was achieved
    // Examples:
    //   - "Order confirmation page is displayed"
    //   - "Shopping cart shows the selected item"
    //   - "User dashboard shows the new position"
  ],
  "strict_done_validation": false
}}

## BEHAVIORAL ADAPTATION RULES

Adapt the key_actions to match the persona's behavioral style:

- If vitesse_navigation = "rapide":
  → Use fewer steps (5-7), more direct path
  → Skip comparison/verification steps
  → Focus on getting to the goal quickly

- If vitesse_navigation = "lente":
  → Use more steps (8-10), thorough exploration
  → Add verification steps like "Verify the product details"
  → Add comparison steps like "Compare multiple options"

- If style_navigation = "impulsif":
  → Skip research and comparison steps
  → Go with first reasonable option
  → Use phrases like "Quickly select" and "Immediately proceed"

- If style_navigation = "prudent":
  → Add "Verify" and "Check" steps
  → Add "Read reviews" or "Compare specifications" steps
  → Use phrases like "Carefully review" and "Double-check"

## CRITICAL CONSTRAINTS

1. The "objectif" field MUST be exactly: "{objectif}"
   Do NOT modify it. Do NOT rephrase it. Use it verbatim.

2. Steps must be HIGH-LEVEL what-to-do instructions.
   The ReAct agent will figure out HOW using its tools.

3. Steps should reflect the persona's behavioral style above.

4. Return ONLY valid JSON. No prose. No markdown code fences.
   Your entire response must be parseable as JSON.

Generate the scenario now:
"""

        try:
            messages = [
                SystemMessage(
                    content="""You are a test scenario designer. You create structured scenarios
that guide autonomous agents. You always return valid JSON only, no additional text.
Steps must be high-level 'what to do' instructions, never 'how to do it' code."""
                ),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)
            response_text = response.content

            # Extract JSON from response (handle markdown code fences if present)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                scenario = json.loads(json_match.group(0))
            else:
                # Try to parse the whole response as JSON
                scenario = json.loads(response_text.strip())

            # Validate and normalize the scenario
            scenario = self._validate_scenario(scenario, persona)

            print(f"✅ Scenario generated: {scenario.get('name', 'Unnamed')}")
            print(f"   Actions: {len(scenario.get('key_actions', []))} steps")
            print(f"   Success criteria: {len(scenario.get('success_criteria', []))} items")

            return scenario

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print(f"   Raw response: {response_text[:500]}...")
            return self._fallback_scenario(persona)

        except Exception as e:
            print(f"❌ Scenario generation failed: {e}")
            return self._fallback_scenario(persona)

    def _validate_scenario(self, scenario: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize the generated scenario.

        Ensures:
        - objectif matches persona objectif exactly
        - key_actions is a list of strings
        - success_criteria is a list of strings
        - Missing fields get safe defaults
        """
        # Force objectif to match persona exactly — no exceptions
        persona_objectif = persona.get("objectif", "Complete the task")
        scenario["objectif"] = persona_objectif

        # Validate key_actions
        key_actions = scenario.get("key_actions", [])
        if not isinstance(key_actions, list):
            key_actions = []
        key_actions = [str(a) for a in key_actions if isinstance(a, str) and a.strip()]
        if not key_actions:
            # Use actions_site as fallback
            key_actions = list(persona.get("actions_site", ["Complete the objective"]))
        # Cap key_actions at 10 steps to avoid token overflow
        scenario["key_actions"] = key_actions[:10]

        # Validate success_criteria
        success_criteria = scenario.get("success_criteria", [])
        if not isinstance(success_criteria, list):
            success_criteria = []
        success_criteria = [str(c) for c in success_criteria if isinstance(c, str) and c.strip()]
        if not success_criteria:
            # Default success criteria based on objective
            success_criteria = [
                f"Task '{persona_objectif}' is completed",
                "Final confirmation or success state is visible"
            ]
        scenario["success_criteria"] = success_criteria[:6]  # Cap at 6 criteria

        # Ensure name exists
        if not scenario.get("name"):
            vitesse = persona.get("vitesse_navigation", "moyenne")
            style = persona.get("style_navigation", "normal")
            if vitesse == "rapide":
                scenario["name"] = "Quick Navigator"
            elif style == "prudent":
                scenario["name"] = "Careful Explorer"
            else:
                scenario["name"] = "Standard User"

        # Ensure description exists
        if not scenario.get("description"):
            scenario["description"] = f"This persona navigates to accomplish: {persona_objectif}"

        # Ensure strict_done_validation is boolean
        scenario["strict_done_validation"] = bool(scenario.get("strict_done_validation", False))

        return scenario

    def _fallback_scenario(self, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a minimal valid scenario if LLM fails.
        Uses persona actions_site directly as key_actions.
        """
        print("⚠️  Using fallback scenario template...")

        objectif = persona.get("objectif", "Complete the task")
        actions_site = persona.get("actions_site", [])

        # Use actions_site as key_actions, or generate generic steps
        if actions_site:
            key_actions = list(actions_site[:10])
        else:
            key_actions = [
                "Navigate to the website homepage",
                "Find and use the main feature",
                "Complete the primary action",
                "Verify the result",
            ]

        vitesse = persona.get("vitesse_navigation", "moyenne")
        style = persona.get("style_navigation", "normal")

        if vitesse == "rapide":
            name = "Quick Navigator"
        elif style == "prudent":
            name = "Careful Explorer"
        elif style == "impulsif":
            name = "Impulsive User"
        else:
            name = "Standard User"

        scenario = {
            "name": name,
            "objectif": objectif,
            "description": f"This persona navigates to accomplish: {objectif}",
            "key_actions": key_actions,
            "success_criteria": [
                f"Task '{objectif}' is completed",
                "Final confirmation or success state is visible"
            ],
            "strict_done_validation": False
        }

        print(f"✅ Fallback scenario created: {name}")
        return scenario

    def save_scenario(self, scenario: Dict[str, Any], output_path: str) -> None:
        """Save scenario to a JSON file."""
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

        print(f"✅ Scenario saved: {output_path}")
