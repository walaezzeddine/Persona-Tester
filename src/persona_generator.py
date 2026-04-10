"""
Persona Generator - LLM 2
Generates realistic personas based on website analysis.

Input: Website description (from WebsiteAnalyzer)
Output: Multiple personas with tailored behaviors (JSON)
"""

import os
import json
import uuid
import time
from typing import Dict, Any, List
from copy import deepcopy
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class PersonaGenerator:
    """
    LLM-powered persona generator that:
    1. Takes website analysis
    2. Generates multiple personas with different behavioral profiles
    3. Tailors behaviors to the website's specific features and user segments
    """

    def __init__(self, provider: str = "openai", model: str = None, temperature: float = 0.8):
        """
        Initialize the Persona Generator with an LLM.

        Args:
            provider: LLM provider ('openai', 'groq', 'github', 'google')
            model: Model name (defaults based on provider)
            temperature: LLM temperature for creativity
        """
        self.provider = provider
        self.temperature = temperature
        self.llm = self._init_llm(provider, model)

    def _init_llm(self, provider: str, model: str = None) -> ChatOpenAI:
        """Initialize LLM based on provider."""
        if provider == "google":
            google_key = os.getenv("GOOGLE_API_KEY")
            if not google_key:
                raise ValueError("GOOGLE_API_KEY not set in .env")
            return ChatGoogleGenerativeAI(
                model=model or "gemini-1.5-flash",
                google_api_key=google_key,
                temperature=self.temperature,
                max_output_tokens=3000,
            )
        elif provider == "groq":
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set in .env")
            return ChatGroq(
                model=model or "llama-3.3-70b-versatile",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=3000,
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
                max_tokens=3000,
            )
        else:  # openai (default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in .env")
            return ChatOpenAI(
                model=model or "gpt-4.1-mini",
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=3000,
            )

    def _format_demographic_constraints(self, demographics_config: Dict[str, Any] | None) -> str:
        """Format demographic constraints for the LLM prompt."""
        if not demographics_config or "demographics" not in demographics_config:
            return ""

        demographics = demographics_config.get("demographics", [])
        if not demographics:
            return ""

        constraints = "\n## Demographic Constraints\nDistribute personas according to these demographics:\n"
        for field in demographics:
            label = field.get("label", "Unknown")
            values = field.get("values", [])
            if values:
                constraints += f"- **{label}**: "
                constraints += ", ".join([f"{v.get('value', '')} (weight: {v.get('weight', 1)})" for v in values])
                constraints += "\n"

        return constraints

    def generate(
        self,
        website_analysis: Dict[str, Any],
        num_personas: int = 20,
        include_extremes: bool = True,
        demographics_config: Dict[str, Any] | None = None,
        global_objective: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate personas based on website analysis.

        Args:
            website_analysis: Website analysis from WebsiteAnalyzer
            num_personas: Number of personas to generate (default: 3)
            include_extremes: Include extreme personas (impatient/patient) if True
            demographics_config: Optional demographic constraints from test configuration
            global_objective: The main objective all personas should share

        Returns:
            List of persona dictionaries
        """
        print(f"\n🧠 Generating {num_personas} personas for {website_analysis.get('domain', 'website')}...")
        if global_objective:
            print(f"🎯 All personas will share objective: {global_objective}")

        # Minimal site info - only domain
        site_domain = website_analysis.get("domain", "website")
        shared_objective = global_objective if global_objective else "Use this website"

        # SIMPLIFIED PROMPT - Focus on shared objective, minimize site analysis influence
        persona_prompt = f"""
You are generating user personas. CRITICAL: All personas MUST have the SAME objective.

MANDATORY OBJECTIVE FOR ALL {num_personas} PERSONAS:
"{shared_objective}"

This is the goal. Do NOT change it. Do NOT create alternative objectives.
If ANY persona has a different objective, you FAIL.

===

Generate {num_personas} realistic personas who all want to: "{shared_objective}"

They will be DIFFERENT in:
- How fast they navigate (rapide vs lente)
- Their style (impulsif vs prudent)
- Their device (mobile vs desktop)
- Their attention to details
- Specific action sequences

But they ALL pursue: "{shared_objective}"

===

For each persona, output this JSON structure exactly:

[
  {{
    "id": "persona_1",
    "nom": "French Name",
    "objectif": "{shared_objective}",
    "description": "How this person uniquely pursues: {shared_objective}",
    "device": "mobile or desktop",
    "vitesse_navigation": "rapide or lente",
    "style_navigation": "impulsif, normal, or prudent",
    "patience_attente_sec": number between 3-30,
    "sensibilite_prix": "haute or faible",
    "tolerance_erreurs": "haute or faible",
    "actions_site": ["Step 1 to accomplish {shared_objective}", "Step 2", "Step 3"],
    "patterns_comportement": ["How they behave while pursuing {shared_objective}", "Another behavior"],
    "exploration_fonctionnalites": ["Feature they use", "Another feature"],
    "comportements_specifiques": ["Specific quirk", "Another quirk"],
    "motivation_principale": "Why they want {shared_objective}",
    "douleurs": ["Pain point 1", "Pain point 2"]
  }}
]

===

CRITICAL VALIDATION:
Every persona MUST have:
  objectif = "{shared_objective}"

If you violate this, the output is INVALID.

===

Examples of CORRECT personas for "{shared_objective}":
- Persona A: Quick mobile buyer - searches, adds first option to cart, buys
- Persona B: Careful desktop buyer - compares 3 options, reads reviews, buys
- Persona C: Price-conscious - uses filters, finds best deal, buys

All have objective = "{shared_objective}" ✓

Examples of WRONG personas:
- Persona A: "{shared_objective}"
- Persona B: "Learn about products" (WRONG - different objective)

===

Generate {num_personas} diverse personas now.
Only respond with valid JSON array. No other text.
"""

        print("🤖 Calling LLM for persona generation...")
        messages = [
            SystemMessage(
                content="""You are a UX research expert who creates detailed user personas.
Generate realistic, diverse personas that represent actual user segments.
Personas should have distinct behavioral profiles (e.g., patient vs impatient, price-conscious vs quality-focused).
Always respond with valid JSON array only, no additional text."""
            ),
            HumanMessage(content=persona_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            response_text = response.content

            # Extract JSON array from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                personas = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON array found in LLM response")

            # CRITICAL: Enforce shared objective - fix any personas that have wrong objective
            if global_objective:
                for i, persona in enumerate(personas):
                    if persona.get("objectif") != global_objective:
                        print(f"⚠️  Persona {i+1} had wrong objective: '{persona.get('objectif')}'")
                        print(f"   Fixing to: '{global_objective}'")
                        persona["objectif"] = global_objective

            # Validate and enhance personas
            personas = self._validate_personas(personas)

            # Generate UNIQUE IDs for each persona (not persona_1, persona_2, ...)
            # This ensures different generation sessions don't overwrite each other
            timestamp = int(time.time() * 1000)  # milliseconds
            for i, persona in enumerate(personas, 1):
                # Old way: persona_1, persona_2 (gets overwritten!)
                # New way: persona_<timestamp>_<index> (unique per generation)
                unique_id = f"persona_{timestamp}_{i}_{str(uuid.uuid4())[:8]}"
                persona["id"] = unique_id

                # Generate a descriptive type based on behavior
                persona_type = self._generate_persona_type(persona, website_analysis)
                persona["persona_type"] = persona_type

                persona["website_domain"] = website_analysis.get("domain")
                persona["website_url"] = website_analysis.get("url")
                persona["index"] = i

            return personas

        except Exception as e:
            print(f"❌ Persona generation failed: {e}")
            # Return fallback personas
            return self._generate_fallback_personas(website_analysis, num_personas)

    def _validate_personas(self, personas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and normalize persona data."""
        required_fields = [
            "id",
            "nom",
            "objectif",
            "vitesse_navigation",
            "sensibilite_prix",
            "tolerance_erreurs",
            "patience_attente_sec",
            "device",
        ]

        valid_personas = []
        for p in personas:
            if not isinstance(p, dict):
                continue

            # Check required fields
            if all(field in p for field in required_fields):
                # Normalize some fields
                p["vitesse_navigation"] = (
                    "rapide" if p.get("vitesse_navigation") == "rapide" else "lente"
                )
                p["device"] = "mobile" if p.get("device") == "mobile" else "desktop"
                p["sensibilite_prix"] = (
                    "haute" if p.get("sensibilite_prix") == "haute" else "faible"
                )
                p["tolerance_erreurs"] = (
                    "haute" if p.get("tolerance_erreurs") == "haute" else "faible"
                )

                # Ensure patience is in valid range
                try:
                    p["patience_attente_sec"] = min(30, max(2, int(p.get("patience_attente_sec", 5))))
                except (ValueError, TypeError):
                    p["patience_attente_sec"] = 5

                valid_personas.append(p)

        # If we filtered out invalid personas, at least keep originals if any are valid
        return valid_personas if valid_personas else personas[:1] if personas else []

    def _generate_persona_type(self, persona: Dict[str, Any], website_analysis: Dict[str, Any]) -> str:
        """Generate a descriptive type/category for a persona based on their behavior."""
        # Extract behavioral attributes
        vitesse = persona.get("vitesse_navigation", "").lower()
        prix = persona.get("sensibilite_prix", "").lower()
        style = persona.get("style_navigation", "").lower()
        patience = persona.get("patience_attente_sec", 15)

        # Determine speed category
        if vitesse in ["rapide", "fast"]:
            speed_adj = "Rapide"
        elif vitesse in ["lente", "slow"]:
            speed_adj = "Prudent"
        else:
            speed_adj = "Normal"

        # Determine price sensitivity
        if "haute" in prix or "high" in prix:
            price_adj = "Économe"
        elif "faible" in prix or "low" in prix:
            price_adj = "Généreux"
        else:
            price_adj = "Équilibré"

        # Determine navigation style
        if "impulsif" in style or "impulsive" in style:
            style_adj = "Impulsif"
        elif "prudent" in style or "careful" in style:
            style_adj = "Prudent"
        else:
            style_adj = "Réfléchi"

        # Based on website type, create meaningful categories
        website_type = website_analysis.get("type", "").lower()

        if "e-commerce" in website_type or "shopping" in website_type or "achat" in website_type.lower():
            # For shopping sites: Acheteur [Impulsif/Prudent/Économe]
            if "impulsif" in style.lower():
                return f"Acheteur Impulsif"
            elif "haute" in prix.lower():
                return f"Acheteur Économe"
            else:
                return f"Acheteur {style_adj}"

        elif "voyage" in website_type.lower() or "travel" in website_type.lower() or "booking" in website_type.lower():
            # For travel sites: Voyageur [Aventureux/Prudent/Économe]
            if "rapide" in vitesse.lower():
                return f"Voyageur Aventureux"
            elif "haute" in prix.lower():
                return f"Voyageur Économe"
            else:
                return f"Voyageur {style_adj}"

        elif "banc" in website_type.lower() or "finance" in website_type.lower() or "bank" in website_type.lower():
            # For banking sites: Client [Impulsif/Prudent/Réfléchi]
            if "rapide" in vitesse.lower():
                return f"Client Impulsif"
            else:
                return f"Client {style_adj}"

        else:
            # Default: use the descriptive adjectives
            return f"Navigateur {style_adj}"

    def _generate_fallback_personas(
        self, website_analysis: Dict[str, Any], num_personas: int
    ) -> List[Dict[str, Any]]:
        """Generate fallback personas when LLM generation fails."""
        print("⚠️  Using fallback persona templates...")

        templates = [
            {
                "id": "utilisateur_impatient",
                "nom": "Utilisateur Pressé",
                "objectif": "Accomplir la tâche rapidement sans détails",
                "vitesse_navigation": "rapide",
                "sensibilite_prix": "faible",
                "tolerance_erreurs": "haute",
                "patience_attente_sec": 5,
                "device": "mobile",
                "comportements_specifiques": ["Click quickly", "No research", "Accept first option"],
                "motivation_principale": "Speed over quality",
                "douleurs": ["Slow pages", "Too many options"],
            },
            {
                "id": "utilisateur_prudent",
                "nom": "Utilisateur Méthodique",
                "objectif": "Faire le meilleur choix après recherche approfondie",
                "vitesse_navigation": "lente",
                "sensibilite_prix": "haute",
                "tolerance_erreurs": "faible",
                "patience_attente_sec": 30,
                "device": "desktop",
                "comportements_specifiques": ["Read reviews", "Compare prices", "Check details"],
                "motivation_principale": "Quality and value",
                "douleurs": ["Hidden fees", "Unclear information"],
            },
            {
                "id": "utilisateur_explorateur",
                "nom": "Utilisateur Curieux",
                "objectif": "Découvrir nouvelles fonctionnalités et possibilités",
                "vitesse_navigation": "lente",
                "sensibilite_prix": "faible",
                "tolerance_erreurs": "haute",
                "patience_attente_sec": 20,
                "device": "desktop",
                "comportements_specifiques": ["Browse widely", "Try new features", "Explore options"],
                "motivation_principale": "Discovery and learning",
                "douleurs": ["Limited content", "Confusing UI"],
            },
        ]

        personas = templates[:num_personas]

        # Generate UNIQUE IDs for fallback personas too
        timestamp = int(time.time() * 1000)
        for i, persona in enumerate(personas, 1):
            # Replace old ID with unique one
            unique_id = f"persona_fallback_{timestamp}_{i}_{str(uuid.uuid4())[:8]}"
            persona["id"] = unique_id

            persona["website_domain"] = website_analysis.get("domain")
            persona["website_url"] = website_analysis.get("url")
            persona["index"] = i

        return personas

    def save_personas(self, personas: List[Dict[str, Any]], output_dir: str = "personas") -> None:
        """Save personas to individual JSON files."""
        os.makedirs(output_dir, exist_ok=True)

        for persona in personas:
            filename = f"{persona.get('id', 'persona')}.json"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(persona, f, indent=2, ensure_ascii=False)

            print(f"✅ Saved: {filepath}")

    def print_personas(self, personas: List[Dict[str, Any]]) -> None:
        """Print personas in readable format."""
        print("\n" + "=" * 80)
        print("Generated Personas")
        print("=" * 80 + "\n")

        for i, persona in enumerate(personas, 1):
            print(f"[Persona {i}/{len(personas)}]")
            print(f"  ID: {persona.get('id')}")
            print(f"  Name: {persona.get('nom')}")
            print(f"  Objective: {persona.get('objectif')}")
            print(f"  Speed: {persona.get('vitesse_navigation')} | Price sense: {persona.get('sensibilite_prix')}")
            print(f"  Device: {persona.get('device')} | Tolerance: {persona.get('tolerance_erreurs')}")
            print(f"  Patience: {persona.get('patience_attente_sec')}s")

            if persona.get("comportements_specifiques"):
                print(f"  Behaviors:")
                for behavior in persona.get("comportements_specifiques", [])[:3]:
                    print(f"    • {behavior}")

            print()

        print("=" * 80 + "\n")
