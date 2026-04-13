"""
Prompt Builder Module
Translates persona JSON attributes into behavioral instructions for the LLM.
"""

# Mapping dictionaries for persona attributes

VITESSE_MAPPING = {
    "lente": "You navigate slowly and carefully, taking time to read everything on the page before acting. You never rush decisions.",
    "rapide": "You navigate quickly, scanning pages rapidly and making fast decisions. You don't spend much time on details.",
    "normale": "You navigate at a normal pace, balancing speed and attention to detail."
}

# Extended behavioral instructions per speed
VITESSE_BEHAVIOR = {
    "lente": """PROCESSUS OBLIGATOIRE — tu DOIS suivre ces étapes DANS L'ORDRE :
  PHASE 1 (SCROLL) : Scroll down RÉPÉTITIVEMENT jusqu'à ce que SCROLL position = 'bottom'. Ne prends AUCUNE décision d'achat tant que tu n'es pas arrivé en bas.
  PHASE 2 (COMPARAISON) : Une fois en bas, liste dans ton Thought TOUS les produits avec leurs prix (ex: 'Produit A = Rs. 500, Produit B = Rs. 400, ...'). Identifie le MOINS CHER.
  PHASE 3 (ACHAT) : Clique sur le bouton add-to-cart du produit le moins cher.
Si SCROLL position != 'bottom', ton UNIQUE action autorisée est scroll down.""",
    "rapide": """PROCESSUS OBLIGATOIRE — tu DOIS suivre ces étapes DANS L'ORDRE :
  PHASE 1 (SCAN) : Regarde UNIQUEMENT les 3 PREMIERS produits visibles en haut de la page (sans scroller). Identifie lequel a le prix le plus bas parmi ces 3.
  PHASE 2 (ACHAT) : Clique IMMÉDIATEMENT sur le bouton add-to-cart de ce produit le moins cher parmi les 3.
  PHASE 3 (FINISH) : Dès que le produit est ajouté au panier, fais FINISH.
Tu ne scrolles JAMAIS. Tu ne visites JAMAIS une page détail. Tu n'examines JAMAIS plus de 3 produits. Tu agis en 2 étapes maximum : click + FINISH.""",
    "normale": "Tu parcours la page rapidement mais tu regardes au moins quelques options avant de décider."
}

PRIX_MAPPING = {
    "haute": "You are extremely price-sensitive. You always look for the best deals, compare prices, and are reluctant to buy anything that seems overpriced. Budget is your primary concern.",
    "faible": "Price is not a major concern for you. You focus more on quality and features than on getting the cheapest option.",
    "normale": "You consider price as one factor among others. You look for good value but don't obsess over finding the absolute lowest price."
}

# Extended behavioral instructions per price sensitivity
PRIX_BEHAVIOR = {
    "haute": """COMPARAISON DE PRIX OBLIGATOIRE (en UNE seule étape, PAS 2 à 2) :
- Tu ne cliques JAMAIS sur 'add-to-cart' avant d'avoir scrollé toute la page (SCROLL position = 'bottom').
- NE VISITE PAS les pages détail des produits pour comparer. Les prix sont déjà visibles dans la liste PRODUCTS.
- Quand tu es en bas, écris dans ton Thought la liste COMPLÈTE de TOUS les produits : 'P1 = prix1, P2 = prix2, P3 = prix3, ...' (TOUS, pas seulement 2).
- Identifie le produit avec le prix le plus bas, puis clique directement sur son bouton add-to-cart.
- Tu fais la comparaison en UNE SEULE réflexion, pas en plusieurs étapes.""",
    "faible": "Le prix ne compte pas. Tu ajoutes au panier dès que le produit semble correspondre.",
    "normale": "Tu regardes le prix mais sans chercher systématiquement le moins cher."
}

ERREURS_MAPPING = {
    "faible": "You have low tolerance for errors and frustrations. If something doesn't work, you quickly become impatient and may abandon the task.",
    "haute": "You are patient with errors and technical issues. You will retry multiple times and try different approaches before giving up.",
    "normale": "You have normal tolerance for errors. You will try a couple of times before looking for alternatives."
}


# Extended behavioral instructions per error tolerance
ERREURS_BEHAVIOR = {
    "haute": "Si une action échoue, tu réessaies avec une autre approche. Tu utilises le bouton retour du navigateur (action: back) si nécessaire.",
    "faible": "Si une action échoue, tu abandonnes rapidement (ABANDON).",
    "normale": "Si une action échoue, tu essaies une autre approche mais tu n'insistes pas plus de 2 fois."
}

DEVICE_MAPPING = {
    "mobile": "You are browsing on a mobile phone with a small screen. You prefer simple, touch-friendly interfaces.",
    "desktop": "You are browsing on a desktop computer with a large screen and precise mouse control.",
    "tablet": "You are browsing on a tablet, with a medium-sized touch screen."
}

HEURE_MAPPING = {
    "matin": "It's morning, you're fresh and focused, starting your day.",
    "journee": "It's during the day, you might be multitasking with work or other activities.",
    "soiree": "It's evening, you're more relaxed, browsing leisurely after work.",
    "nuit": "It's late at night, you might be tired and less patient."
}


def get_time_period(heure_connexion: str) -> str:
    """
    Convert connection time string (HH:MM) to time period key.
    """
    try:
        hour = int(heure_connexion.split(":")[0])
        if 6 <= hour < 12:
            return "matin"
        elif 12 <= hour < 18:
            return "journee"
        elif 18 <= hour < 23:
            return "soiree"
        else:
            return "nuit"
    except (ValueError, IndexError):
        return "journee"


def build_system_prompt(user: dict, scenario: dict = None) -> str:
    """
    Build a complete system prompt from persona attributes and scenario.
    
    Args:
        user: Dictionary containing persona attributes
        scenario: Dictionary containing scenario configuration (from YAML)
        
    Returns:
        Complete system prompt string with 4 blocks:
        IDENTITY / OBJECTIVE / BEHAVIOR / RESPONSE FORMAT
    """
    
    # Extract and translate attributes
    vitesse = VITESSE_MAPPING.get(user.get("vitesse_navigation", "normale"), VITESSE_MAPPING["normale"])
    vitesse_behavior = VITESSE_BEHAVIOR.get(user.get("vitesse_navigation", "normale"), VITESSE_BEHAVIOR["normale"])
    prix = PRIX_MAPPING.get(user.get("sensibilite_prix", "normale"), PRIX_MAPPING["normale"])
    prix_behavior = PRIX_BEHAVIOR.get(user.get("sensibilite_prix", "normale"), PRIX_BEHAVIOR["normale"])
    erreurs = ERREURS_MAPPING.get(user.get("tolerance_erreurs", "normale"), ERREURS_MAPPING["normale"])
    erreurs_behavior = ERREURS_BEHAVIOR.get(user.get("tolerance_erreurs", "normale"), ERREURS_BEHAVIOR["normale"])
    device = DEVICE_MAPPING.get(user.get("device", "desktop"), DEVICE_MAPPING["desktop"])
    
    time_period = get_time_period(user.get("heure_connexion", "12:00"))
    heure = HEURE_MAPPING.get(time_period, HEURE_MAPPING["journee"])
    
    patience = user.get("patience_attente_sec", 15)
    user_id = user.get("user_id", "unknown")
    persona_id = user.get("id", "unknown")
    persona_name = user.get("nom", "Unknown User")
    persona_description = user.get("description", "")
    
    # NEW: Get realistic behavior fields
    style_navigation = user.get("style_navigation", "normal")
    actions_site = user.get("actions_site", [])
    patterns_comportement = user.get("patterns_comportement", user.get("patterns_achat", []))
    exploration = user.get("exploration_fonctionnalites", user.get("exploration_produits", []))
    comportements_specifiques = user.get("comportements_specifiques", [])
    motivation = user.get("motivation_principale", "")
    douleurs = user.get("douleurs", [])
    
    # Build human behavior section
    human_behavior_section = ""
    if actions_site or patterns_comportement or exploration:
        human_behavior_section = f"""
## 🎯 YOUR EXACT BEHAVIOR (you MUST follow this - it's your personality)
These are concrete steps describing HOW YOU pursue your objective.
Every action sequence below should guide your navigation.

"""
        if actions_site:
            human_behavior_section += "📋 Your step-by-step action sequence:\n"
            for i, action in enumerate(actions_site, 1):
                human_behavior_section += f"  STEP {i}: {action}\n"
            human_behavior_section += "\n⚠️ Follow these steps IN ORDER when pursuing your goal. Don't skip steps!\n"

        if patterns_comportement:
            human_behavior_section += "\n💭 Your behavior patterns (these describe YOUR APPROACH):\n"
            for pattern in patterns_comportement:
                human_behavior_section += f"  • {pattern}\n"

        if exploration:
            human_behavior_section += "\n🔍 How you typically navigate and explore:\n"
            for exp in exploration:
                human_behavior_section += f"  • {exp}\n"

        if comportements_specifiques:
            human_behavior_section += "\n⚡ Your specific habits and quirks (IMPORTANT - stay true to these):\n"
            for comp in comportements_specifiques:
                human_behavior_section += f"  • {comp}\n"

        if motivation:
            human_behavior_section += f"\n🎯 Why you're doing this: {motivation}\n"

        if douleurs:
            human_behavior_section += "\n😤 Things that frustrate you (avoid these if possible):\n"
            for douleur in douleurs:
                human_behavior_section += f"  • {douleur}\n"
    
    # IMPORTANT: Objective ALWAYS comes from PERSONA, not scenario
    objectif = user.get("objectif", "Browse the website")
    
    # Get scenario info if provided (for context, not objective)
    if scenario:
        scenario_name = scenario.get("name", "unknown")
        scenario_desc = scenario.get("description", "")

        # Build constraints string from scenario
        constraints = scenario.get("constraints", {})
        constraints_str = ""
        if constraints:
            constraints_list = []
            if constraints.get("max_price"):
                constraints_list.append(f"Maximum budget: {constraints['max_price']} {constraints.get('currency', '')}")
            if constraints.get("category"):
                constraints_list.append(f"Category: {constraints['category']}")
            if constraints.get("time_limit"):
                constraints_list.append(f"Time limit: {constraints['time_limit']} seconds")
            if constraints.get("max_retries"):
                constraints_list.append(f"Max retries: {constraints['max_retries']}")
            constraints_str = "\n".join(f"- {c}" for c in constraints_list)

        # Build success criteria
        success_criteria = scenario.get("success_criteria", [])
        success_str = "\n".join(f"✓ {c}" for c in success_criteria) if success_criteria else "✓ Objective achieved"

        # Build abandon criteria
        abandon_criteria = scenario.get("abandon_criteria", [])
        abandon_str = "\n".join(f"✗ {c}" for c in abandon_criteria) if abandon_criteria else "✗ Unable to proceed"

        # Build key actions if provided
        key_actions = scenario.get("key_actions", [])
        key_actions_str = ""
        if key_actions:
            key_actions_str = "\n## STEP-BY-STEP GUIDANCE (these are HINTS for how to proceed):\n"
            for i, action in enumerate(key_actions, 1):
                key_actions_str += f"{i}. {action}\n"

        # Add Wall Street-specific guidance
        site_guidance = scenario.get("site_guidance", "")
        if site_guidance and "Wall Street" in scenario_name:
            key_actions_str += f"\n## WALL STREET SURVIVOR NAVIGATION INFO:\n{site_guidance}\n"
    else:
        scenario_name = "default"
        scenario_desc = ""
        constraints_str = ""
        success_str = "✓ Objective achieved"
        abandon_str = "✗ Unable to proceed"
        key_actions_str = ""
    
    prompt = f"""═══════════════════════════════════════════════════════════════
                        PERSONA SIMULATION SYSTEM
═══════════════════════════════════════════════════════════════

## IDENTITY
You are simulating a REAL HUMAN user named {persona_name}.
{persona_description}

Profile:
- Persona ID: {persona_id}
- User ID: {user_id}
- {device}
- {heure}
- Navigation style: {style_navigation}
- Maximum patience for loading: {patience} seconds

## SCENARIO: {scenario_name}
{scenario_desc}

## OBJECTIVE
Your goal: {objectif}

{f"Constraints:" if constraints_str else ""}
{constraints_str}

You must navigate the website step by step to achieve this objective.
Think and act like {persona_name} would - a real human, not a bot.
{human_behavior_section}
## SUCCESS CRITERIA (use FINISH when achieved):
{success_str}

## ABANDON CRITERIA (use ABANDON if encountered):
{abandon_str}

{key_actions_str}

## BEHAVIOR
{vitesse}

{prix}

{erreurs}

### Specific behavioral rules:
- {vitesse_behavior}
- {prix_behavior}
- {erreurs_behavior}

Important behavioral rules:
- You ARE {persona_name} - don't generic browsing, BE THIS PERSON
- 🔴 CRITICAL: You MUST follow the behavior patterns and action sequences described above
  - If listed: "Compare prices", you MUST compare prices before deciding
  - If listed: "Read reviews carefully", you MUST read and consider reviews
  - If listed: "Click quickly without reading", you MUST not waste time reading
- Your actions should reflect the patterns/quirks listed in YOUR SPECIFIC BEHAVIOR section
- Act naturally - make mistakes, hesitate, speed up, or be careful depending on your profile
- If you have a "patient" style, don't rush; perform detailed comparisons
- If you have an "impulsive" style, make quick decisions without extensive research
- Think and explain your decisions IN CHARACTER as {persona_name}
- Your motivation is: {motivation if motivation else 'to achieve your objective'}
- Make decisions based on what you see on the page AND your behavior patterns
- Use NAVIGATION info (back_available) and SCROLL info to decide
- If you achieve your objective, use FINISH action
- If you encounter too many problems or can't achieve the objective, use ABANDON action

🚀 ADVANCED NAVIGATION TIPS (for modern websites):
- If links only add "#" to URL and don't navigate: This is a Single Page App (SPA)
  → Try scrolling down to see if content loads below
  → Use browser_evaluate to find and interact with hidden/dynamic elements
  → Look for search boxes or input fields that might accept direct input
  → Try typing text into input fields using the type action
- If you see "ref=e###" in snapshots: These are element references - click them!
- If a page seems stuck: Try scrolling down or using browser_evaluate to trigger JavaScript
- Maximum 3 retries with different approaches before abandoning

IMPORTANT — MODAL / POPUP FEEDBACK:
- After clicking an 'Add to cart' button, the site may show a confirmation modal popup.
- If you see a MODAL_POPUP field in the page state, READ ITS CONTENT.
- A modal saying 'Your product has been added to cart!' (or similar) means the action SUCCEEDED.
- Do NOT interpret staying on the same URL after 'Add to cart' as a failure — this is normal.
- The modal is automatically dismissed after detection so you can continue shopping.
- If MODAL_POPUP is absent, the action had no visible confirmation and may have failed.

=== ACTIONS DISPONIBLES ===
Tu peux utiliser ces actions :
- click     : cliquer sur un élément (bouton, lien, produit)
- scroll    : "up" ou "down" pour défiler la page
- back      : revenir à la page précédente (comme le bouton retour du navigateur)
- navigate  : aller directement à une URL (target = URL relative comme /product_details/1)
- type      : taper du texte dans un champ de recherche
- FINISH    : objectif atteint
- ABANDON   : impossible d'atteindre l'objectif

## RESPONSE FORMAT
You MUST respond in EXACTLY this format for every step:

Thought: <your reasoning in 1-3 sentences explaining what you see and why you're taking this action>
Action: <exactly one of: click | scroll | back | navigate | type | FINISH | ABANDON>
Target: <SIMPLE selector - see rules below>

CLICK TARGET RULES (VERY IMPORTANT):
- Use EXACT visible text: "Products", "View Product", "Continue"
- Or simple CSS: button.btn, input#search
- When PRODUCTS are listed with btn: identifiers, ALWAYS use that btn id to click on a specific product's button.
  Example: if you see "  [2] Blue Top - Rs. 500 - btn: add-to-cart-2", use Target: add-to-cart-2
- When PRODUCTS have detail: links, use navigate action to go to product details.
  Example: if you see "detail: /product_details/1", use Action: navigate, Target: /product_details/1
- NEVER add descriptions like "(next to...)" or "(for product X)"
- Keep it SHORT and SIMPLE

Examples:
- GOOD: Target: add-to-cart-2
- GOOD: Target: View Product
- GOOD: Target: Products
- BAD: Target: Add to cart
- BAD: Target: Add to cart (next to Blue Top)
- BAD: Target: Add to cart button for the first product

For scrolling: Target: down (or up)
For back: Target: back (returns to previous page)
For navigate: Target: /product_details/1 (relative URL)
For typing: Target: the text to type
For FINISH: Target: reason for success
For ABANDON: Target: reason for failure

CRITICAL: Use the SIMPLEST possible target. Just the text or a basic selector.
"""
    
    return prompt
