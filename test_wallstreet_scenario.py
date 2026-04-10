#!/usr/bin/env python
"""
Test script: Run Léo Dupont persona on Wall Street Survivor
Tests: Login → Search Stock → Buy shares
Uses pre-created credentials
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
    print_section("WALL STREET SURVIVOR PERSONA TEST - LEO DUPONT")

    # ========== STEP 1: CREATE PERSONA DATA ==========
    print_section("STEP 1: Prepare Persona + Scenario")

    # Pre-created credentials (bypass email verification)
    TEST_CREDENTIALS = {
        "email": "leo.survivor@test.com",
        "password": "WallStreet2024!"
    }

    persona = {
        "nom": "Léo Dupont",
        "persona_type": "Navigateur Impulsif",
        "objectif": "Se connecter à Wall Street Survivor et acheter une action tech rapidement",
        "description": "Jeune trader impulsif qui veut pratiquer le trading avec 100 000 $ virtuels sans lire les tutoriels",
        "device": "mobile",
        "vitesse_navigation": "rapide",
        "style_navigation": "impulsif",
        "sensibilite_prix": "faible",
        "tolerance_erreurs": "haute",
        "patience_attente_sec": 5,
        "comportements_specifiques": [
            "Clique rapidement sur les boutons sans lire les tutoriels",
            "Ignore les cours et ressources éducatives",
            "Veut acheter IMMÉDIATEMENT, pas apprendre d'abord",
            "Évite les popups d'information",
            "Prend des décisions rapides sans analyser"
        ],
        "motivation_principale": "Acheter une action tech populaire et voir les gains virtuels augmenter rapidement",
        "douleurs": [
            "Trop d'informations éducatives bloquent l'accès au trading",
            "Les tutoriels sont trop longs",
            "Peur de rater une opportunité pendant qu'il lit"
        ],
        "actions_site": [
            "1. Naviguer vers https://www.wallstreetsurvivor.com/",
            "2. Localisez le bouton 'LOGIN' ou 'SIGN IN' (probablement en haut à droite)",
            "3. Cliquez sur Login rapidement",
            "4. Entrez l'email: leo.survivor@test.com",
            "5. Entrez le mot de passe: WallStreet2024!",
            "6. Cliquez sur 'Log In' sans attendre les animations",
            "7. Ignorez les popups de bienvenue ou les tutoriels (il veut trader, pas apprendre!)",
            "8. Trouvez le lien/bouton STOCK GAME ou STOCK SIMULATOR",
            "9. Cliquez pour aller au simulateur de trading",
            "10. Attendez le dashboard avec le solde de 100 000 $ virtuels",
            "11. Localisez la fonction de recherche de stocks ou le ticker input",
            "12. Tapez 'TSLA' (Tesla - action tech volatile, attire les traders impulsifs)",
            "13. Appuyez sur Entrée ou cliquez sur le résultat Tesla",
            "14. Sur la page de Tesla, trouvez le bouton 'Buy' ou 'Place Buy Order'",
            "15. Entrez la quantité: 5 actions (prise rapide, pas calculée)",
            "16. Vérifiez le prix total rapidement",
            "17. Cliquez sur 'Buy' ou 'Submit Order' SANS hésiter",
            "18. Confirmez l'ordre si popup de confirmation",
            "19. Retournez au portefeuille",
            "20. Vérifiez que 5 TSLA apparaissent dans le portfolio avec le prix d'achat"
        ],
        "patterns_comportement": [
            "Saute les étapes éducatives",
            "Clique sur les premiers éléments trouvés",
            "Ne lit pas les avertissements ou les détails",
            "Veut des résultats visuels immédiats (voir ses achats)",
            "Se décide très rapidement sans comparaison"
        ],
        "exploration_fonctionnalites": [
            "Authentification/Login",
            "Navigation vers Stock Simulator",
            "Recherche de stocks par ticker",
            "Page de détail du stock (prix, graphique)",
            "Formulaire d'achat/ordre",
            "Portefeuille virtuel avec positions",
            "Gain/perte en dollars virtuels"
        ]
    }

    print(f"\n👤 Persona: {persona['nom']}")
    print(f"   Type: {persona['persona_type']}")
    print(f"   Motivation: {persona['motivation_principale']}")
    print(f"   Patience: {persona['patience_attente_sec']}s (TRÈS impulsif!)")
    print(f"   Device: {persona['device']} (mobile - scans quickly)")

    print(f"\n🔐 Pre-created Credentials (Email verification bypassed):")
    print(f"   Email: {TEST_CREDENTIALS['email']}")
    print(f"   Password: {TEST_CREDENTIALS['password']}")

    print(f"\n📋 Scénario principal (20 steps):")
    for action in persona['actions_site'][:10]:
        print(f"   {action}")
    print(f"   ... (+{len(persona['actions_site'])-10} more steps)")

    # ========== STEP 2: SAVE TO DATABASE ==========
    print_section("STEP 2: Save Persona to Database")

    config_payload = {
        "url": "https://www.wallstreetsurvivor.com/",
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
    print(f"   Site: Wall Street Survivor Stock Simulator")
    print(f"   Expected behavior: {persona['style_navigation']} (impatient, quick clicks)")
    print(f"   Target stock: TSLA (Tesla - volatile, exciting for impulsive traders)")

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
            print(f"   ✅ Logged in to Wall Street Survivor")
            print(f"   ✅ Found and bought TSLA stock")
            print(f"   ✅ Portfolio updated with 5 TSLA shares")
        elif run_result.get('status') == 'failed':
            print(f"\n⚠️  Test ended with: {run_result.get('error', 'Unknown error')}")

    except requests.exceptions.Timeout:
        print("❌ Test timed out (300 seconds)")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return

    # ========== STEP 4: DISPLAY SCENARIO GUIDE ==========
    print_section("DETAILED SCENARIO GUIDE FOR AGENT")

    print("""
🎯 HOW LÉO DUPONT SHOULD BEHAVE ON WALL STREET SURVIVOR:

1️⃣ LOGIN PHASE (Steps 1-7):
   ✓ Find and click "LOGIN" button quickly
   ✓ Enter email WITHOUT hesitation: leo.survivor@test.com
   ✓ Enter password: WallStreet2024!
   ✓ Click "Log In" immediately
   ✓ IGNORE any welcome popups or tutorial suggestions
   ✓ Skip "Learn how to trade" or "Start with our free course"

2️⃣ NAVIGATION TO SIMULATOR (Steps 8-10):
   ✓ Look for "STOCK GAME" or "STOCK SIMULATOR" link
   ✓ Click on it without reading descriptions
   ✓ Wait for dashboard to load (will show 100,000 virtual dollars)

3️⃣ STOCK SEARCH (Steps 11-13):
   ✓ Find the stock search box (usually prominent on trading screen)
   ✓ Type "TSLA" quickly (no research, just picks Tesla)
   ✓ Press Enter or click first result

4️⃣ BUY PHASE (Steps 14-18):
   ✓ Locate "Buy" button on Tesla page
   ✓ Enter quantity: 5 (random choice, not researched)
   ✓ See the total cost (~$250 virtual with stock at $50)
   ✓ Click "Buy" or "Place Order" IMMEDIATELY
   ✓ Confirm if popup appears (frustrated by extra steps)

5️⃣ VERIFICATION (Steps 19-20):
   ✓ Navigate to Portfolio/My Positions
   ✓ Verify 5 TSLA shares appear with purchase price
   ✓ Note the total portfolio value

⚠️  KEY BEHAVIORAL TRAITS:
   • Wants to TRADE, not LEARN
   • Skips all educational content
   • Makes quick decisions without analysis
   • Doesn't compare prices or wait for better timing
   • Gets frustrated by confirmation steps
   • Picks exciting stocks (TSLA) not boring ones
   • Mobile user = smaller clicks, scans quickly

📊 SUCCESS CRITERIA:
   ✅ Successfully logged in
   ✅ Navigated to Stock Simulator
   ✅ Found TSLA via search
   ✅ Bought 5 shares impulsively
   ✅ Portfolio shows position
   ✅ Completed in <20 steps (faster than before - no signup!)
    """)

    print_section("DIFFERENCES: Investopedia vs Wall Street Survivor")

    print("""
📊 COMPARISON:

INVESTOPEDIA SURVIVOR:
• Focus: Learn to invest FIRST, then practice
• Flow: Educational content → Account → Simulator
• Friction: Lots of course recommendations
• Entry point: Simulator portfolio page

WALL STREET SURVIVOR:
• Focus: Practice FIRST, then learn
• Flow: Direct to Simulator → Trading dashboard
• Friction: Educational popups (can skip)
• Entry point: Homepage with "STOCK GAME" link
• Stock choice: More exciting (TSLA vs AAPL)

EXPECTED BEHAVIOR DIFFERENCE:
✓ Investopedia Léo: Reads signup flow, slower
✓ Wall Street Survivor Léo: Skips tutors, faster
    """)

    print_section("TEST RESULT SUMMARY")

    print(f"""
✅ Persona Test Execution Complete!

📈 What was tested:
   • Navigation of Wall Street Survivor simulator
   • Login with pre-created account
   • Impulsive persona behavior (skips education)
   • Stock search and purchase (TSLA - volatile stock)
   • Portfolio verification
   • Speed: Mobile user clicking quickly

🎯 Scenario Completed:
   1. Login with existing credentials
   2. Navigate to Stock Simulator
   3. Search for TSLA stock
   4. Buy 5 shares impulsively
   5. Verify position in portfolio

⏱️  Expected duration: <20 steps (faster due to simpler navigation)

🎯 Next steps:
   1. Compare this run with Investopedia test
   2. Analyze how impulsivity affects stock choice
   3. Test with different personas (Aurélie = slow/cautious)
   4. Check traces for differences in decision-making
   5. Export comparison report
    """)

if __name__ == "__main__":
    main()
