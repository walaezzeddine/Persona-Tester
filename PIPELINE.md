# Persona Tester — Architecture & Pipeline Technique

## Vue d'ensemble

Persona Tester est un outil de simulation comportementale qui utilise un **agent LLM** (GPT-4o-mini) pour incarner des personas virtuelles et naviguer sur un site web réel. Chaque persona a un comportement différent (vitesse, sensibilité prix, tolérance erreurs) mais le même objectif, permettant de comparer leurs parcours.

**Stack technique :** Python 3 · Playwright (navigation browser) · LangChain (interface LLM) · GitHub Models API

---

## Pipeline d'exécution

```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         PERSONA TESTER PIPELINE                         │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │   PHASE 1: INPUTS          PHASE 2: PERSONAS         PHASE 3: REACT    │
    │  ┌──────────────┐        ┌──────────────────┐      ┌────────────────┐   │
    │  │ config.yaml  │───────▶│ Chargement JSON  │─────▶│  Boucle ReAct  │   │
    │  │ scenario.yaml│        │ personas/*.json   │      │  par persona   │   │
    │  │ .env (URL)   │        │ build_system_     │      │                │   │
    │  └──────────────┘        │ prompt()          │      │ OBSERVE (DOM)  │   │
    │                          └──────────────────┘      │ REASON  (LLM)  │   │
    │                                                     │ ACT (Playwright)│   │
    │                                                     │ TRACE  (logs)  │   │
    │                                                     └───────┬────────┘   │
    │                                                             │            │
    │                                                    ┌────────▼────────┐   │
    │                                                    │ Rapport JSON    │   │
    │                                                    │ reports/*.json  │   │
    │                                                    └─────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────┘
```

### Phase 1 — INPUTS
Chargement des 3 sources de configuration :
- **`config/config.yaml`** → paramètres LLM, navigation, browser
- **`scenarios/trouver_moins_cher.yaml`** → objectif du test, critères succès/abandon
- **`.env`** → `TARGET_URL` et `GITHUB_TOKEN`

### Phase 2 — PERSONAS
Auto-découverte de tous les fichiers `personas/*.json`. Pour chaque persona, `build_system_prompt()` génère un system prompt complet avec les instructions comportementales.

### Phase 3 — REACT LOOP
Pour chaque persona, dans son propre navigateur :
1. **OBSERVE** — Extraction DOM structurée (`dom_extractor`)
2. **REASON** — L'agent LLM décide la prochaine action
3. **ACT** — Playwright exécute l'action dans le browser
4. **TRACE** — Logging détaillé + sauvegarde JSON

---

## Structure des fichiers

```
part1 pfe/
├── main.py                    # Point d'entrée — pipeline principal
├── config/
│   └── config.yaml            # Configuration globale
├── personas/
│   ├── acheteur_prudent.json  # Persona lente, prix sensible
│   └── acheteur_impatient.json# Persona rapide, prix insensible
├── scenarios/
│   └── trouver_moins_cher.yaml# Scénario de test
├── src/
│   ├── __init__.py
│   ├── config_loader.py       # Chargement YAML/JSON
│   ├── prompt_builder.py      # Génération du system prompt
│   ├── agent.py               # Agent LLM (appels API + historique)
│   ├── dom_extractor.py       # Extraction DOM pour le LLM
│   └── parser.py              # Parsing des réponses LLM
├── reports/                   # Rapports JSON générés
├── dom_output/                # Dumps DOM pour debug
├── .env                       # Variables d'environnement
├── requirements.txt           # Dépendances Python
├── README.md                  # README original
└── PIPELINE.md                # Ce fichier
```

---

## Détail de chaque fichier

---

### `main.py` — Point d'entrée & boucle ReAct

**Rôle :** Orchestre tout le pipeline. Charge la config, découvre les personas, lance une session browser par persona, exécute la boucle ReAct, et produit le rapport final de comparaison.

#### Fonctions clés

| Fonction | Description |
|----------|-------------|
| `main()` | Fonction principale async. Charge config + scénario + personas, puis lance `run_persona_session()` pour chaque persona séquentiellement. Affiche la comparaison finale. |
| `run_persona_session()` | Ouvre un navigateur Playwright, initialise l'agent LLM, et exécute la boucle ReAct (max 15 steps). À chaque step : close_popups → extract DOM → agent.decide() → execute_action(). Sauvegarde le rapport JSON à la fin. |
| `execute_action()` | Traduit la décision de l'agent en action Playwright concrète : `click`, `scroll`, `type`, `back`, `navigate`, `FINISH`, `ABANDON`. Gère aussi l'auto-correction (click sur URL → navigate) et la détection/dismissal du modal panier. |
| `close_popups()` | Supprime les popups publicitaires, bannières cookies et overlays Google sans affecter le modal de confirmation panier (`#cartModal`). |
| `_dismiss_cart_modal()` | Détecte et ferme le modal Bootstrap de confirmation "produit ajouté au panier" en cliquant "Continue Shopping". Stocke le feedback dans `page._cart_feedback` pour que l'agent le voie au step suivant. |

#### Classe `SessionTracker`
Collecte toutes les données d'une session (steps, durée, tokens, résultat). Méthode `save_json()` pour exporter en `reports/session_*.json`.

#### Boucle ReAct (dans `run_persona_session`)
```
Pour chaque step (1 à max_steps) :
    1. close_popups(page)
    2. Restaurer pending_modal_feedback si présent
    3. OBSERVE : extract_page_content(page) → format_for_llm()
    4. REASON  : agent.decide(page_content, url, step)
    5. Si action terminale (FINISH/ABANDON) → stop
    6. ACT     : execute_action(page, action, target)
    7. Capturer modal feedback pour le step suivant
    8. TRACE   : print_detailed_step_log() + tracker.add_step()
    9. sleep(action_delay)
```

---

### `src/config_loader.py` — Chargement de la configuration

**Rôle :** Lit `config.yaml`, les scénarios YAML et les personas JSON. Fournit des propriétés typées pour chaque paramètre.

#### Fonctions clés

| Fonction / Propriété | Description |
|----------------------|-------------|
| `Config.__init__()` | Charge le fichier `config/config.yaml` via PyYAML. |
| `Config.llm_provider` | Retourne le provider LLM (`"github"`, `"openai"`, `"ollama"`). |
| `Config.llm_model` | Retourne le nom du modèle (ex: `"openai/gpt-4o-mini"`). |
| `Config.max_steps` | Nombre maximum d'étapes par session (défaut: 15). |
| `Config.action_delay` | Délai en secondes entre chaque action (défaut: 7). |
| `Config.headless` | Mode headless du browser (`false` = visible). |
| `Config.viewport` | Taille de la fenêtre `{width: 1280, height: 800}`. |
| `load_scenario(path)` | Charge un fichier scénario YAML et retourne un `dict`. |
| `load_persona(path)` | Charge un fichier persona JSON et retourne un `dict`. |

---

### `src/prompt_builder.py` — Construction du system prompt

**Rôle :** Traduit les attributs JSON d'une persona en instructions comportementales textuelles pour le LLM. C'est le cœur de la différenciation comportementale entre personas.

#### Architecture à 3 couches

```
Persona JSON               Dictionnaires de mapping           System Prompt
─────────────              ───────────────────────            ─────────────
vitesse: "lente"    ───▶   VITESSE_MAPPING["lente"]    ───▶  "You navigate slowly..."
                           VITESSE_BEHAVIOR["lente"]   ───▶  "PHASE 1: SCROLL..."
sensibilite: "haute" ──▶   PRIX_MAPPING["haute"]       ───▶  "You are price-sensitive..."
                           PRIX_BEHAVIOR["haute"]      ───▶  "COMPARAISON OBLIGATOIRE..."
```

#### Dictionnaires de comportement

| Dictionnaire | Rôle | Clés |
|-------------|------|------|
| `VITESSE_MAPPING` | Description générale du style de navigation | `lente`, `rapide`, `normale` |
| `VITESSE_BEHAVIOR` | Instructions concrètes (scroll obligatoire, etc.) | `lente` → 3 phases obligatoires, `rapide` → premier produit direct |
| `PRIX_MAPPING` | Description de la sensibilité au prix | `haute`, `faible`, `normale` |
| `PRIX_BEHAVIOR` | Règles de comparaison des prix | `haute` → comparaison de TOUS les produits en une fois, `faible` → achat immédiat |
| `ERREURS_MAPPING` | Tolérance aux erreurs | `faible`, `haute`, `normale` |
| `ERREURS_BEHAVIOR` | Réaction aux échecs | `faible` → ABANDON rapide, `haute` → retry |
| `DEVICE_MAPPING` | Type d'appareil simulé | `mobile`, `desktop`, `tablet` |
| `HEURE_MAPPING` | Période de la journée | `matin`, `journee`, `soiree`, `nuit` |

#### Fonctions clés

| Fonction | Description |
|----------|-------------|
| `build_system_prompt(user, scenario)` | Fonction principale. Assemble le system prompt complet avec : IDENTITY, OBJECTIVE, BEHAVIOR, RESPONSE FORMAT, ACTIONS DISPONIBLES. Injecte les instructions comportementales spécifiques à la persona. |
| `get_time_period(heure)` | Convertit `"10:00"` → `"matin"`, `"23:00"` → `"nuit"`, etc. |

#### Structure du system prompt généré

```
PERSONA SIMULATION SYSTEM
├── IDENTITY        → ID, device, heure, patience
├── SCENARIO        → nom, description, contraintes
├── OBJECTIVE       → objectif de la persona (ex: "trouver l'article le moins cher")
├── SUCCESS/ABANDON → critères de fin
├── BEHAVIOR        → mappings + behavioral rules spécifiques
├── ACTIONS         → click, scroll, back, navigate, type, FINISH, ABANDON
└── RESPONSE FORMAT → Thought / Action / Target (format strict)
```

---

### `src/agent.py` — Agent LLM

**Rôle :** Gère la communication avec le LLM (GPT-4o-mini via GitHub Models). Maintient un historique de conversation pour la continuité entre les steps.

#### Classe `PersonaAgent`

| Méthode | Description |
|---------|-------------|
| `__init__(user, scenario, config)` | Initialise l'agent : construit le system prompt via `build_system_prompt()`, configure le LLM via LangChain `ChatOpenAI`. |
| `_init_llm()` | Configure le client LLM selon le provider (GitHub Models, OpenAI direct, Ollama local). |
| `decide(page_content, page_url, step)` | Méthode principale. Envoie le system prompt + historique + état de page au LLM, parse la réponse avec `parse_response()`, retourne `{thought, action, target}`. Inclut un retry avec backoff exponentiel pour les rate limits (429). |
| `_build_user_message()` | Formate l'état de page en message "STEP N — Current State" pour le LLM. |
| `_trim_history()` | Garde seulement les 6 derniers échanges (12 messages) pour ne pas dépasser la fenêtre de contexte. |

#### Flux d'un appel `decide()`

```
1. Construire user_message avec le contenu de page actuel
2. Assembler : [SystemMessage, ...historique, HumanMessage]
3. Appeler llm.invoke(messages)
4. Parser la réponse → {thought, action, target}
5. Ajouter à l'historique (Human + AI)
6. Trim historique à 6 échanges max
7. Retourner le résultat parsé
```

---

### `src/dom_extractor.py` — Extraction DOM structurée

**Rôle :** Extrait le contenu pertinent d'une page web via Playwright et le formate pour le LLM. C'est les "yeux" de l'agent.

#### Fonctions d'extraction

| Fonction | Ce qu'elle extrait |
|----------|-------------------|
| `extract_page_content(page)` | Fonction principale. Orchestre toutes les sous-extractions et retourne un `dict` complet. |
| `_extract_clickables(page)` | Boutons et liens visibles (max 20). Retourne `[{type, text, href}]`. |
| `_extract_inputs(page)` | Champs de formulaire visibles : `[{type, name, placeholder}]`. |
| `_extract_products(page)` | **Fonction critique.** Extrait les produits visibles : nom, prix, bouton add-to-cart (avec injection `data-btn-id`), lien détail. |
| `_extract_scroll_position(page)` | Position de scroll : `"top"` (< 15%), `"middle"`, `"bottom"` (> 85%). Calculée via `scrollTop / (scrollHeight - clientHeight)`. |
| `_extract_nav_state(page)` | Disponibilité navigation arrière/avant : `{back_available, forward_available}`. |
| `_extract_modal(page)` | Détecte les modals visibles (ex: confirmation panier). Vérifie aussi `page._cart_feedback` (feedback stocké après dismissal). |
| `_extract_category(page)` | Catégorie courante via breadcrumb ou sidebar active. |
| `_extract_errors(page)` | Messages d'erreur visibles (`.error`, `[role="alert"]`, etc.). |
| `_extract_text_content(page)` | Contenu texte principal de la page (max 1500 chars). |
| `format_for_llm(extracted)` | **Formateur final.** Convertit le dict extrait en texte structuré pour le LLM. |

#### Format de sortie de `format_for_llm()`

```
URL: https://automationexercise.com/products
Page Title: All Products

NAVIGATION: back_available=True | forward_available=False
SCROLL: position=middle
CURRENT_CATEGORY: Men > Tshirts

CLICKABLES: Products | Cart | Login | ...
INPUTS: search (placeholder: Search Products)
PRODUCTS:
  [1] Blue Top - Rs. 500 - btn: add-to-cart-1
       → To see details: Action=navigate Target=/product_details/1
  [2] Men Tshirt - Rs. 400 - btn: add-to-cart-2
       → To see details: Action=navigate Target=/product_details/2
ERRORS: aucune
```

#### Mécanisme `data-btn-id`
`_extract_products()` injecte un attribut `data-btn-id="add-to-cart-N"` sur chaque bouton "Add to cart" trouvé. Cela permet au LLM de cibler un bouton spécifique via `Target: add-to-cart-2`, qui est résolu par `parser.resolve_target()` en sélecteur CSS `[data-btn-id="add-to-cart-2"]`.

---

### `src/parser.py` — Parsing des réponses LLM

**Rôle :** Parse les réponses textuelles du LLM au format `Thought / Action / Target`. Inclut des fallbacks robustes pour les réponses mal formatées.

#### Fonctions clés

| Fonction | Description |
|----------|-------------|
| `parse_response(text)` | Fonction principale. Extrait `thought`, `action`, `target` via regex. Si le format `Action:` n'est pas trouvé, tombe en fallback prose. Ne retourne **jamais** un dict vide (défaut: `scroll down`). |
| `_parse_prose_response(text, result)` | Fallback pour les réponses en prose libre. Détecte "I will click on X", "scrolling down", "task completed", etc. via des patterns regex. |
| `resolve_target(target)` | Convertit `"add-to-cart-2"` en sélecteur CSS `'[data-btn-id="add-to-cart-2"]'`. Laisse les autres targets inchangés. |
| `is_terminal_action(action)` | Retourne `True` si l'action est `FINISH` ou `ABANDON`. |

#### Stratégie de parsing (dans `parse_response`)

```
1. Chercher "Action: <mot>" via regex
   → Si trouvé : extraire Thought et Target normalement
   → Si pas trouvé :
      2. Essayer _parse_prose_response() (patterns NL)
      3. Sinon retourner {action: "scroll", target: "down"} par défaut
```

---

## Fichiers de données

### `personas/*.json` — Profils comportementaux

Chaque persona est un fichier JSON avec ces attributs :

| Attribut | Valeurs possibles | Effet sur le comportement |
|----------|-------------------|--------------------------|
| `id` | Identifiant unique | Nom dans les logs et rapports |
| `user_id` | ID utilisateur | Utilisé pour les noms de fichiers de rapport |
| `objectif` | Texte libre | Objectif injecté dans le system prompt |
| `vitesse_navigation` | `lente`, `rapide`, `normale` | Scroll obligatoire vs achat immédiat |
| `sensibilite_prix` | `haute`, `faible`, `normale` | Comparaison de tous les prix vs indifférence |
| `tolerance_erreurs` | `faible`, `haute`, `normale` | ABANDON rapide vs retry patient |
| `device` | `desktop`, `mobile`, `tablet` | Contexte device dans le prompt |
| `heure_connexion` | `"HH:MM"` | Contexte temporel (matin/soir/nuit) |
| `patience_attente_sec` | Entier (secondes) | Patience déclarée dans le prompt |

**Exemple — acheteur_prudent :**
```json
{
  "vitesse_navigation": "lente",       → scroll toute la page avant de décider
  "sensibilite_prix": "haute",         → compare TOUS les prix, achète le moins cher
  "tolerance_erreurs": "faible"         → abandonne vite si erreur
}
```

**Exemple — acheteur_impatient :**
```json
{
  "vitesse_navigation": "rapide",      → clique sur le premier produit direct
  "sensibilite_prix": "faible",        → ne compare pas les prix
  "tolerance_erreurs": "haute"          → réessaie en cas d'erreur
}
```

### `scenarios/*.yaml` — Scénarios de test

Définit le contexte du test (pas l'objectif, qui vient de la persona) :
- `name` — nom du scénario
- `description` — description courte
- `success_criteria` — conditions pour FINISH
- `abandon_criteria` — conditions pour ABANDON
- `constraints` — catégorie, budget max, etc.

### `config/config.yaml` — Configuration globale

| Section | Paramètres principaux |
|---------|----------------------|
| `llm` | `provider`, `model` (gpt-4o-mini), `temperature` (0.2), `max_tokens` (500) |
| `navigation` | `max_steps` (15), `action_delay` (7s), `action_timeout` (5000ms) |
| `browser` | `headless` (false), `viewport` (1280×800), `user_agent` |
| `logging` | `verbosity`, `screenshots_enabled` |

### `reports/*.json` — Rapports de session

Chaque session génère un fichier JSON avec :
```json
{
  "persona_id": "acheteur_prudent",
  "user_id": "user_prudent_001",
  "result": "FINISH",
  "total_steps": 8,
  "duration_sec": 85.2,
  "final_url": "https://automationexercise.com/products",
  "steps": [
    {"step": 1, "thought": "...", "action": "click", "target": "Products", "success": true},
    {"step": 2, "thought": "...", "action": "scroll", "target": "down", "success": true},
    ...
  ]
}
```

---

## Diagramme de séquence d'un step

```
    main.py                  dom_extractor.py          agent.py              parser.py
       │                          │                       │                      │
       │  close_popups(page)      │                       │                      │
       │─────────────────────────▶│                       │                      │
       │                          │                       │                      │
       │  extract_page_content()  │                       │                      │
       │─────────────────────────▶│                       │                      │
       │  {products, scroll, ...} │                       │                      │
       │◀─────────────────────────│                       │                      │
       │                          │                       │                      │
       │  format_for_llm()        │                       │                      │
       │─────────────────────────▶│                       │                      │
       │  "PRODUCTS: [1]..."      │                       │                      │
       │◀─────────────────────────│                       │                      │
       │                                                  │                      │
       │  agent.decide(content, url, step)                │                      │
       │─────────────────────────────────────────────────▶│                      │
       │                                                  │  llm.invoke()        │
       │                                                  │─────▶ GPT-4o-mini   │
       │                                                  │◀───── response       │
       │                                                  │                      │
       │                                                  │  parse_response()    │
       │                                                  │─────────────────────▶│
       │                                                  │  {thought,action,    │
       │                                                  │   target}            │
       │                                                  │◀─────────────────────│
       │  {thought, action, target}                       │                      │
       │◀─────────────────────────────────────────────────│                      │
       │                                                                         │
       │  execute_action(page, action, target)                                   │
       │  ─────▶ Playwright click/scroll/navigate/...                            │
       │                                                                         │
       │  tracker.add_step(...)                                                  │
       │  sleep(action_delay)                                                    │
```

---

## Comparaison comportementale attendue

| Aspect | Acheteur Prudent | Acheteur Impatient |
|--------|------------------|--------------------|
| **Navigation** | Scroll toute la page (top → bottom) avant de décider | Clique sur le premier produit visible |
| **Comparaison** | Liste TOUS les prix, identifie le moins cher | Aucune comparaison |
| **Achat** | Add-to-cart du produit le moins cher uniquement | Add-to-cart du premier match |
| **Erreurs** | Abandonne vite (ABANDON) | Réessaie (retry, back, autre approche) |
| **Steps estimés** | 6-10 (scroll × N + compare + buy) | 2-4 (click + buy) |
| **Device** | Desktop (1280×800) | Mobile |
| **Heure** | 10:00 (matin, concentré) | 23:00 (nuit, fatigué) |
