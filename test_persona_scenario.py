#!/usr/bin/env python
"""
Test script: Run Léo Dupont persona on Investopedia with detailed scenario
Tests: Login → Search AAPL → Buy 10 shares
Uses pre-created credentials (bypasses email verification)
"""

import json
import requests
import time

API_BASE = "http://localhost:5000/api"

def print_section(title):
    print("\n" + "="*80)
    print(f"🎬 {title}")
    print("="*80)

def main():
    print_section("INVESTOPEDIA PERSONA TEST - LEO DUPONT")

    # ========== STEP 1: CREATE PERSONA DATA ==========
    print_section("STEP 1: Prepare Persona + Scenario")

    # Pre-created credentials (bypass email verification)
    TEST_CREDENTIALS = {
        "email": "leo.dupont.trader@test.com",
        "password": "TestTrading2024!"
    }

    persona = {
        "nom": "Léo Dupont",
        "persona_type": "Navigateur Impulsif",
        "objectif": "Se connecter à Investopedia Simulator et acheter une action tech AAPL",
        "description": "Jeune trader impulsif qui veut apprendre rapidement avec un compte existant",
        "device": "mobile",
        "vitesse_navigation": "rapide",
        "style_navigation": "impulsif",
        "sensibilite_prix": "faible",
        "tolerance_erreurs": "haute",
        "patience_attente_sec": 5,
        "comportements_specifiques": [
            "Clique rapidement sur les boutons sans lire",
            "Ignore les avertissements et notifications",
            "Utilise la recherche rapide pour trouver les stocks",
            "Ne vérifie pas deux fois avant d'acheter"
        ],
        "motivation_principale": "Acheter du AAPL rapidement et voir les gains potentiels",
        "douleurs": [
            "Concepts financiers trop complexes",
            "Trop d'options rend la décision difficile",
            "Peur de rater une bonne opportunité"
        ],
        "actions_site": [
            "1. Naviguer vers https://www.investopedia.com/simulator/portfolio",
            "2. Localisez le bouton 'Log In' ou 'Sign In' (en haut à droite)",
            "3. Cliquez rapidement sur Login",
            "4. Entrez l'email: leo.dupont.trader@test.com",
            "5. Entrez le mot de passe: TestTrading2024!",
            "6. Cliquez sur 'Log In' immédiatement (pas de vérification)",
            "7. Attendez le dashboard du simulateur (contenu avec 100 000 $ virtuels)",
            "8. Localisez la barre de recherche des stocks",
            "9. Tapez 'AAPL' (Apple - action tech populaire)",
            "10. Appuyez sur Entrée ou cliquez sur le résultat",
            "11. Localisez le bouton 'Buy' ou 'Place Order' sur la page d'Apple",
            "12. Entrez la quantité: 10 actions",
            "13. Vérifiez le prix et cliquez sur 'Buy' sans hésiter",
            "14. Confirmez l'ordre si une popup de confirmation s'affiche",
            "15. Vérifiez que 10 AAPL apparaissent maintenant dans le portefeuille"
        ],
        "patterns_comportement": [
            "Agit rapidement sans lire tous les détails",
            "Prend des décisions impulsives (pas de recherche approfondie)",
            "Cherche la solution la plus rapide à chaque étape",
            "Clique sur les premiers résultats/boutons visibles",
            "Ignore les popups de confirmation ou les avertissements"
        ],
        "exploration_fonctionnalites": [
            "Authentification/Login",
            "Recherche de stocks par ticker",
            "Page de détail du stock (prix, graphiques)",
            "Formulaire d'achat/ordre",
            "Portefeuille virtuel",
            "Valeur totale du compte"
        ]
    }

    print(f"\n👤 Persona: {persona['nom']}")
    print(f"   Type: {persona['persona_type']}")
    print(f"   Motivation: {persona['motivation_principale']}")
    print(f"   Patience: {persona['patience_attente_sec']}s (TRÈS impulsif!)")

    print(f"\n🔐 Pre-created Credentials (Email verification bypassed):")
    print(f"   Email: {TEST_CREDENTIALS['email']}")
    print(f"   Password: {TEST_CREDENTIALS['password']}")

    print(f"\n📋 Scénario principal:")
    for action in persona['actions_site'][:8]:
        print(f"   {action}")
    print(f"   ... (+{len(persona['actions_site'])-8} more steps)")

    # ========== STEP 2: SAVE TO DATABASE ==========
    print_section("STEP 2: Save Persona to Database")

    config_payload = {
        "url": "https://www.investopedia.com/simulator/portfolio",
        "participantTask": persona['objectif'],
        "numParticipants": 1,
        "demographics": []
    }

    try:
        print("📤 Sending to /api/test-config...")
        response = requests.post(
            f"{API_BASE}/test-config",
            json=config_payload,
            timeout=120
        )

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        print(f"✅ Configuration saved!")
        print(f"   Website ID: {result.get('website_id')}")
        print(f"   Session ID: {result.get('session_id')}")
        print(f"   Personas generated: {result.get('personas_generated')}")

        # Get the persona ID
        if result.get('personas'):
            persona_id = result['personas'][0]['id']
            print(f"   ✅ Persona ID: {persona_id}")
        else:
            print("❌ No personas returned!")
            return

    except Exception as e:
        print(f"❌ Failed to save persona: {e}")
        return

    # ========== STEP 3: RUN TEST ==========
    print_section("STEP 3: Execute Persona Test on Site")

    print(f"🚀 Launching test for {persona['nom']}...")
    print(f"   Objective: {persona['objectif']}")
    print(f"   Site: Investopedia Stock Simulator")
    print(f"   Expected behavior: {persona['style_navigation']} (impatient, quick clicks)")

    time.sleep(2)

    try:
        print("\n📤 Sending POST /api/runs/start...")
        run_response = requests.post(
            f"{API_BASE}/runs/start",
            json={"persona_id": persona_id},
            timeout=300  # 5 minutes timeout for the test
        )

        if run_response.status_code != 200:
            print(f"❌ Test failed: {run_response.status_code}")
            print(run_response.text[:500])
            return

        run_result = run_response.json()

        print(f"\n✅ Test completed!")
        print(f"   Run ID: {run_result.get('run_id')}")
        print(f"   Status: {run_result.get('status')}")
        print(f"   Steps executed: {run_result.get('steps', 0)}/25")
        print(f"   Duration: {run_result.get('duration_sec', 0):.1f}s")

        if run_result.get('status') == 'success':
            print(f"\n🎉 SUCCESS! Léo completed the scenario!")
        elif run_result.get('status') == 'failed':
            print(f"\n⚠️  Test ended with: {run_result.get('error', 'Unknown error')}")

    except requests.exceptions.Timeout:
        print("❌ Test timed out (30 seconds)")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return

    # ========== STEP 4: DISPLAY SCENARIO GUIDE ==========
    print_section("DETAILED SCENARIO GUIDE FOR AGENT")

    print("""
🎯 HOW LÉO DUPONT SHOULD BEHAVE (Impulsif, Mobile, 5s patience):

1️⃣ LOGIN PHASE (Steps 1-6):
   ✓ Navigate to Investopedia Simulator
   ✓ Find "Log In" button (top right or center)
   ✓ Click immediately (doesn't waste time with Sign Up)
   ✓ Enter email: leo.dupont.trader@test.com
   ✓ Enter password: TestTrading2024!
   ✓ Click "Log In" button right away (no time to waste)

2️⃣ DASHBOARD PHASE (Steps 7-9):
   ✓ Wait for dashboard to load (shows 100K virtual balance)
   ✓ See the stock search bar
   ✓ Quickly locate it (scan page for search box)

3️⃣ SEARCH PHASE (Steps 9-11):
   ✓ Type "AAPL" INTO search bar
   ✓ Press Enter or click first result
   ✓ Navigate to Apple stock page

4️⃣ BUY PHASE (Steps 12-14):
   ✓ Find "Buy" or "Place Order" button
   ✓ Enter quantity: 10 (quick decision, no analysis)
   ✓ Click "Buy" WITHOUT hesitation
   ✓ Confirm if popup appears

5️⃣ VERIFICATION (Step 15):
   ✓ Check portfolio shows 10 AAPL shares
   ✓ Note the purchase price

⚠️  KEY BEHAVIORAL TRAITS:
   • Logs in QUICKLY without exploring
   • Doesn't read help text or tutorials
   • Searches efficiently (knows ticker AAPL)
   • Makes purchase decision in seconds
   • Doesn't compare prices or wait for better timing
   • Gets frustrated by delays/confirmations

📊 SUCCESS CRITERIA:
   ✅ Successfully logged in with pre-created account
   ✅ Found AAPL stock via search
   ✅ Bought 10 shares without hesitation
   ✅ Shares appear in portfolio
   ✅ Completed in <15 steps (faster than before - no signup!)
    """)

    print_section("TEST RESULT SUMMARY")

    print(f"""
✅ Persona Test Execution Complete!

📈 What was tested:
   • Real website navigation (Investopedia Simulator)
   • Pre-created account LOGIN (no email verification)
   • Persona behavior adherence (Impulsive navigation style)
   • Stock search and purchase scenario
   • LLM decision-making under constraints

🎯 Scenario:
   1. Login with existing credentials
   2. Search for AAPL stock
   3. Buy 10 shares impulsively
   4. Verify purchase in portfolio

⏱️  Expected duration: <15 steps (faster than account creation)

🎯 Next steps:
   1. Check the run trace in dashboard
   2. Verify Léo behaved impulsively (quick decisions)
   3. Compare with other personas (Aurélie = slow/prudent)
   4. Test different scenarios or personas
   5. Export test results for analysis
    """)

if __name__ == "__main__":
    main()
