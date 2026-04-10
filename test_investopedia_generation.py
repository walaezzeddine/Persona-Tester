#!/usr/bin/env python
"""
Test script: Generate personas for Investopedia
Shows complete pipeline output with web search and LLM generation
"""

import json
from src.website_analyzer import WebsiteAnalyzer
from src.persona_generator import PersonaGenerator

def main():
    url = "https://www.investopedia.com/simulator/portfolio"

    print("\n" + "="*80)
    print("🚀 INVESTOPEDIA PERSONA GENERATION TEST")
    print("="*80)
    print(f"\n📍 Target URL: {url}\n")

    # ========== STEP 1: ANALYZE WEBSITE ==========
    print("="*80)
    print("STEP 1: ANALYZE WEBSITE WITH WEB SEARCH")
    print("="*80)

    analyzer = WebsiteAnalyzer(provider="groq", enable_web_search=True)
    website_analysis = analyzer.analyze(url)

    print("\n✅ Website Analysis Complete!\n")
    print("Analysis Output:")
    print("-" * 80)
    print(json.dumps(website_analysis, indent=2, ensure_ascii=False)[:2000])
    print("\n... [analysis truncated for display]\n")

    # ========== STEP 2: GENERATE PERSONAS ==========
    print("="*80)
    print("STEP 2: GENERATE PERSONAS WITH LLM")
    print("="*80)
    print("\nGenerating 4 personas based on website analysis...\n")

    persona_gen = PersonaGenerator(provider="groq", model="llama-3.3-70b-versatile")
    personas = persona_gen.generate(
        website_analysis=website_analysis,
        num_personas=4,
        include_extremes=True,
        global_objective="Créer un compte sur Investopedia Simulator et faire ton premier trade virtuel avec les 100 000 $ offerts."
    )

    print(f"✅ Generated {len(personas)} personas!\n")

    # ========== STEP 3: DISPLAY PERSONAS ==========
    print("="*80)
    print("STEP 3: GENERATED PERSONAS")
    print("="*80)

    for i, persona in enumerate(personas, 1):
        print(f"\n{'─'*80}")
        print(f"👤 PERSONA {i}: {persona.get('nom', 'Unknown')}")
        print(f"{'─'*80}")
        print(f"ID: {persona.get('id')}")
        print(f"Type: {persona.get('persona_type', 'N/A')}")
        print(f"Objective: {persona.get('objectif')}")
        print(f"Device: {persona.get('device')}")
        print(f"Speed: {persona.get('vitesse_navigation')}")
        print(f"Style: {persona.get('style_navigation')}")
        print(f"Price Sensitivity: {persona.get('sensibilite_prix')}")
        print(f"Patience: {persona.get('patience_attente_sec')}s")
        print(f"Description: {persona.get('description')}")
        print(f"Main Motivation: {persona.get('motivation_principale')}")

        if persona.get('comportements_specifiques'):
            print(f"\nSpecific Behaviors:")
            for behavior in persona.get('comportements_specifiques', []):
                print(f"  • {behavior}")

        if persona.get('actions_site'):
            print(f"\nSite Actions:")
            for action in persona.get('actions_site', []):
                print(f"  • {action}")

        if persona.get('douleurs'):
            print(f"\nPain Points:")
            for pain in persona.get('douleurs', []):
                print(f"  • {pain}")

    # ========== STEP 4: SUMMARY ==========
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Analysis: Complete")
    print(f"✅ Personas Generated: {len(personas)}")
    print(f"✅ Persona Type Distribution:")
    for persona in personas:
        print(f"   • {persona.get('nom')} - {persona.get('persona_type', 'Unknown')}")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
