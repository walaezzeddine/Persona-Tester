"""
PersonaActionPlanner - LLM 3
Generates a persona-trait-weighted action plan for a specific persona + site pair.

Pipeline position
-----------------
    WebsiteAnalyzer  →  PersonaGenerator  →  **PersonaActionPlanner**  →  (user review/edit)  →  PlaywrightTestAgent

Input  : a single persona dict + the website analysis (incl. `llm_context`)
Output : {
    "persona_id":  "...",
    "objectif":    "...",
    "actions":     ["Step 1 ...", "Step 2 ...", ...],
    "rationale":   "Why this plan fits the persona's traits (shown to the user, not persisted).",
    "model":       "qwen3.5:cloud",
    "provider":    "ollama"
}

Design notes
------------
- The planner DOES NOT persist anything. The frontend shows `actions` to the user,
  who accepts or edits them, then saves via the existing `PUT /api/personas/{id}/actions`
  endpoint. This keeps the user firmly in the loop.
- The prompt aggressively maps persona traits → concrete action-level behaviors
  (hesitation, impulsivity, retries, price-comparison, etc.) so the generated plan
  actually differs between personas that share the same objective.
- Grounded in the real site: actions reference features/forms/flows detected by
  WebsiteAnalyzer (via `llm_context`). No inventing UI that doesn't exist.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


# Hard cap on actions per plan — keeps downstream Playwright scripts tractable.
_MAX_ACTIONS = 18
_MIN_ACTIONS = 4


class PersonaActionPlanner:
    """
    Generates a persona-specific, site-grounded action plan that feeds the
    Playwright script generator.
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: Optional[str] = None,
        temperature: float = 0.5,
    ):
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)
        # Record what we actually ended up using, for the response payload.
        self.model_name = getattr(self.llm, "model_name", None) or getattr(self.llm, "model", None) or model or "unknown"

    # ──────────────────────────────────────────────────────────────────────
    # LLM init — same pattern as the other agents, Ollama is the default here
    # ──────────────────────────────────────────────────────────────────────

    def _init_llm(self, provider: str, model: Optional[str]) -> ChatOpenAI:
        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            return ChatOpenAI(
                model=model or os.getenv("OLLAMA_MODEL", "qwen3.5:cloud"),
                base_url=base_url,
                api_key="ollama",
                temperature=self.temperature,
                max_tokens=2000,
            )
        if provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set in .env")
            return ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2000,
            )
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=api_key,
                temperature=self.temperature,
                max_output_tokens=2000,
            )
        if provider == "github":
            api_key = os.getenv("GITHUB_TOKEN")
            if not api_key:
                raise ValueError("GITHUB_TOKEN not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                base_url="https://models.github.ai/inference",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=2000,
            )
        # openai default
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,
            temperature=self.temperature,
            max_tokens=2000,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def plan(
        self,
        persona: Dict[str, Any],
        website_analysis: Dict[str, Any],
        start_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a trait-weighted action plan for the given persona.
        """
        persona_id = persona.get("id", "unknown")
        objectif = persona.get("objectif") or "Use the website"
        target_url = start_url or persona.get("website_url") or website_analysis.get("url", "")

        site_block = self._format_site_block(website_analysis)
        persona_block = self._format_persona_block(persona)
        behavior_hints = self._behavior_hints(persona)

        prompt = f"""
You are generating the step-by-step **action plan** a specific persona would follow on a specific website to achieve their objective.

# TARGET SITE
URL: {target_url}

{site_block}

# PERSONA
{persona_block}

## How the persona's traits translate to navigation behavior
{behavior_hints}

# OBJECTIVE
The persona wants to: "{objectif}"

# YOUR TASK
Produce a JSON object with EXACTLY this shape:

{{
  "actions": [
    "Each item is ONE concrete, user-visible step this persona would take.",
    "Write in the imperative, ~8-18 words per step.",
    "Include trait-driven micro-behaviors (hesitation, re-reading, comparing, retrying, abandoning) as separate steps when they materially change navigation.",
    "Reference real UI: buttons, links, form fields you can infer from the SITE CONTEXT."
  ],
  "rationale": "2-4 sentences explaining why these steps fit THIS persona's traits. Will be shown to the human reviewer."
}}

# HARD RULES
1. Between {_MIN_ACTIONS} and {_MAX_ACTIONS} steps.
2. First action MUST describe arriving at the site (e.g. "Open {target_url}" or "Land on the homepage").
3. Last action MUST describe the success or abandon outcome (e.g. "Submit the booking and verify confirmation" OR "Give up after two failed attempts").
4. Every step must be something a Playwright script could translate into a real browser action.
5. Do NOT invent features that aren't suggested by the SITE CONTEXT.
6. Two personas with the SAME objective but DIFFERENT traits must produce VISIBLY DIFFERENT plans — impulsivity, patience, price-sensitivity, and device MUST shape the steps.
7. Return ONLY the JSON object. No prose, no code fences.
"""

        messages = [
            SystemMessage(content=(
                "You are a UX testing expert who writes realistic, trait-driven "
                "action plans for synthetic personas. You always return strict JSON. "
                "The plans are consumed downstream by a Playwright script generator, "
                "so steps must be concrete, ordered, and grounded in the real site."
            )),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
        payload = self._extract_json_object(response_text)

        actions = self._sanitize_actions(payload.get("actions", []))
        rationale = str(payload.get("rationale", "")).strip() or self._fallback_rationale(persona)

        return {
            "persona_id": persona_id,
            "objectif": objectif,
            "actions": actions,
            "rationale": rationale,
            "provider": self.provider,
            "model": self.model_name,
            "target_url": target_url,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Prompt building blocks
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_site_block(website_analysis: Dict[str, Any]) -> str:
        if not website_analysis:
            return "# SITE CONTEXT\n(No analysis available.)"
        llm_ctx = website_analysis.get("llm_context")
        if isinstance(llm_ctx, str) and llm_ctx.strip():
            return "# SITE CONTEXT\n" + llm_ctx.strip()[:4000]
        # Compact fallback from structured fields.
        lines = ["# SITE CONTEXT"]
        for key in ("site_type", "primary_purpose", "industry", "navigation_patterns"):
            val = website_analysis.get(key)
            if val:
                lines.append(f"- **{key}**: {val}")
        for plural_key in ("key_features", "user_actions", "forms_and_inputs", "user_pain_points"):
            items = website_analysis.get(plural_key) or []
            if items:
                lines.append(f"- **{plural_key}**:")
                for item in items[:6]:
                    lines.append(f"  - {item}")
        journey = website_analysis.get("user_journey") or {}
        if isinstance(journey, dict) and journey.get("key_steps"):
            lines.append("- **typical journey**: " + " → ".join(str(s) for s in journey["key_steps"][:6]))
        return "\n".join(lines)

    @staticmethod
    def _format_persona_block(persona: Dict[str, Any]) -> str:
        name = persona.get("nom") or persona.get("name") or "Persona"
        lines = [
            f"**Name:** {name}",
            f"**Persona type:** {persona.get('persona_type', 'unspecified')}",
            f"**Device:** {persona.get('device', 'desktop')}",
            f"**Navigation speed:** {persona.get('vitesse_navigation', 'normale')}",
            f"**Navigation style:** {persona.get('style_navigation', 'normal')}",
            f"**Price sensitivity:** {persona.get('sensibilite_prix', 'normale')}",
            f"**Error tolerance:** {persona.get('tolerance_erreurs', 'normale')}",
            f"**Patience (seconds before giving up on a wait):** {persona.get('patience_attente_sec', 15)}",
        ]
        if persona.get("description"):
            lines.append(f"**Description:** {persona['description']}")
        if persona.get("motivation_principale"):
            lines.append(f"**Motivation:** {persona['motivation_principale']}")
        pains = persona.get("douleurs") or []
        if pains:
            lines.append("**Known pain points:** " + "; ".join(str(p) for p in pains[:4]))
        behaviors = persona.get("comportements_specifiques") or []
        if behaviors:
            lines.append("**Specific behaviors:** " + "; ".join(str(b) for b in behaviors[:4]))
        patterns = persona.get("patterns_comportement") or []
        if patterns:
            lines.append("**Behavior patterns:** " + "; ".join(str(p) for p in patterns[:4]))
        creds = persona.get("credentials") or {}
        if creds.get("username") and creds.get("password"):
            lines.append(f"**Login credentials (use EXACTLY):** username=`{creds['username']}`, password=`{creds['password']}`")
        return "\n".join(lines)

    @staticmethod
    def _behavior_hints(persona: Dict[str, Any]) -> str:
        """
        Turn persona traits into explicit behavior directives so the LLM can't
        ignore them. This is the lever that makes two personas with the same
        objective produce different plans.
        """
        hints: List[str] = []

        vitesse = str(persona.get("vitesse_navigation", "")).lower()
        if vitesse == "lente":
            hints.append("- **Slow**: scrolls the whole page before deciding; reads labels; adds a 'pause and re-read' step where a normal user wouldn't.")
        elif vitesse == "rapide":
            hints.append("- **Fast**: skips long scroll, clicks the first viable option, no re-reading.")
        else:
            hints.append("- **Normal speed**: scans above the fold, clicks with brief consideration.")

        style = str(persona.get("style_navigation", "")).lower()
        if "impulsif" in style or "impulsive" in style:
            hints.append("- **Impulsive**: commits to the first acceptable option; skips comparison/review steps.")
        elif "prudent" in style or "careful" in style:
            hints.append("- **Careful**: compares at least 2-3 alternatives; reads reviews/FAQ/details before acting; may open a second tab mentally (extra verification step).")

        patience = persona.get("patience_attente_sec")
        try:
            patience_val = int(patience) if patience is not None else 15
        except (TypeError, ValueError):
            patience_val = 15
        if patience_val <= 6:
            hints.append(f"- **Low patience ({patience_val}s)**: if a page/action feels slow, persona abandons or retries once — encode that explicitly as an action.")
        elif patience_val >= 20:
            hints.append(f"- **High patience ({patience_val}s)**: will wait, retry multiple times, and try a different path before giving up.")

        prix = str(persona.get("sensibilite_prix", "")).lower()
        if "haute" in prix or "high" in prix:
            hints.append("- **Price-sensitive**: opens pricing/filter/sort, compares at least two prices, picks the cheapest matching option.")
        elif "faible" in prix or "low" in prix:
            hints.append("- **Price-insensitive**: ignores price; picks based on features or the first-match.")

        erreurs = str(persona.get("tolerance_erreurs", "")).lower()
        if "faible" in erreurs or "low" in erreurs:
            hints.append("- **Low error tolerance**: on the first failure, ABANDON as the final step.")
        elif "haute" in erreurs or "high" in erreurs:
            hints.append("- **High error tolerance**: retries with a different input/selector; tries at least one alternative path.")

        device = str(persona.get("device", "")).lower()
        if device == "mobile":
            hints.append("- **Mobile**: prefers scrolling and tapping over hovering; expects compact navigation (menu toggle, bottom CTAs).")
        else:
            hints.append("- **Desktop**: uses full-width nav, can hover dropdowns, multi-column layouts.")

        return "\n".join(hints) if hints else "- (no trait-specific hints available)"

    # ──────────────────────────────────────────────────────────────────────
    # Output parsing + sanitation
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any]:
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {"actions": [], "rationale": ""}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"actions": [], "rationale": ""}

    @staticmethod
    def _sanitize_actions(actions: Any) -> List[str]:
        if not isinstance(actions, list):
            return []
        cleaned: List[str] = []
        for a in actions:
            if isinstance(a, str):
                s = a.strip()
            elif isinstance(a, dict):
                # Some models emit {"step": "...", ...} — recover the text.
                s = (a.get("step") or a.get("text") or a.get("action") or "").strip()
            else:
                s = str(a).strip()
            if s:
                cleaned.append(s[:280])
            if len(cleaned) >= _MAX_ACTIONS:
                break
        return cleaned

    @staticmethod
    def _fallback_rationale(persona: Dict[str, Any]) -> str:
        name = persona.get("nom") or persona.get("name") or "this persona"
        vitesse = persona.get("vitesse_navigation", "normal")
        style = persona.get("style_navigation", "normal")
        return (
            f"Plan tuned to {name}'s profile: {vitesse} navigation speed and "
            f"{style} decision style drive the step granularity and retry policy."
        )
