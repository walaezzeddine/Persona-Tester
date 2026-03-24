# Persona Tester 🎭

**Outil de simulation comportementale IA** — PFE ENSI / TALAN Tunisie (Fév–Juin 2026)

---

## Table des matières

- [Description](#-description)
- [Architecture MCP](#-architecture-mcp)
- [Pipeline d'exécution](#-pipeline-dexécution)
- [Boucle ReAct MCP en détail](#-boucle-react-mcp-en-détail)
- [Stratégies par persona](#-stratégies-par-persona)
- [Structure des fichiers](#-structure-des-fichiers)
- [Personas](#-personas)
- [Scénarios](#-scénarios)
- [Configuration](#-configuration)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Rapports](#-rapports)
- [LLM Providers supportés](#-llm-providers-supportés)
- [Outils MCP disponibles](#-outils-mcp-disponibles)
- [Limitations & Roadmap](#-limitations--roadmap)

---

## 📋 Description

Persona Tester simule des **utilisateurs virtuels** avec des comportements différents qui naviguent
sur un vrai site web en production. Un LLM incarne chaque persona et **prend toutes les décisions
de navigation en temps réel** via le protocole MCP (Model Context Protocol).

L'outil implémente le paradigme **ReAct** (Yao et al., ICLR 2023) où :
- le LLM **observe** un snapshot de la page (arbre d'accessibilité)
- **raisonne** selon le profil comportemental de la persona
- **agit** directement sur le browser via les outils MCP Playwright

**Stack technique :** Python 3 · Playwright MCP · LangChain · Groq / GitHub Models / OpenAI / Ollama

**Site cible de test :** [automationexercise.com](https://automationexercise.com)

---

## 🏗️ Architecture MCP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PERSONA TESTER — MCP ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   test_mcp.py                                                               │
│       │                                                                     │
│       ▼                                                                     │
│   PersonaAgent.run_with_mcp()                                               │
│       │                                                                     │
│       ├── 1. Charge persona + scénario → construit system prompt            │
│       │                                                                     │
│       ├── 2. Connexion stdio → @playwright/mcp (serveur MCP)                │
│       │         ↕  stdio (JSON-RPC)                                         │
│       │   Playwright MCP Server (Node.js) ←→ Chromium                       │
│       │                                                                     │
│       └── 3. BOUCLE ReAct (max 20 steps)                                    │
│                                                                             │
│             ┌──────────────────────────────────────────────────┐            │
│             │  LLM (Groq / GitHub / OpenAI / Ollama)           │            │
│             │                                                  │            │
│             │  THOUGHT: je vois Blue Top Rs.500, je clique...  │            │
│             │  ACTION: browser_click                           │            │
│             │  ACTION_INPUT: {"ref": "e116"}                   │            │
│             └──────────────────┬───────────────────────────────┘            │
│                                │ appel outil MCP                            │
│                                ▼                                            │
│             ┌──────────────────────────────────────────────────┐            │
│             │  Playwright MCP Server                           │            │
│             │  exécute : browser_click(ref=e116)               │            │
│             │  retourne : OBSERVATION (nouveau snapshot)        │            │
│             └──────────────────┬───────────────────────────────┘            │
│                                │ résultat compressé                         │
│                                ▼                                            │
│                         Prochain THOUGHT...                                 │
│                                                                             │
│             Jusqu'à : DONE / max_steps atteint                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rôle de chaque composant

| Composant | Rôle |
|-----------|------|
| `test_mcp.py` | Point d'entrée — charge config, persona, lance la session |
| `PersonaAgent` | Construit le system prompt persona + orchestre la boucle ReAct |
| `@playwright/mcp` | Serveur MCP Node.js — expose les outils browser au LLM |
| **LLM** | Lit le snapshot, raisonne selon la persona, choisit l'action suivante |
| `_compress_snapshot()` | Réduit le snapshot Playwright en table de produits lisible par le LLM |
| `reports/` | Rapport JSON complet généré après chaque session |

---

## 🔄 Pipeline d'exécution

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       PIPELINE D'EXÉCUTION                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1          PHASE 2              PHASE 3                           │
│  INPUTS    ──▶    PERSONA     ──▶      BOUCLE ReAct MCP                  │
│                                                                          │
│  config.yaml      personas/*.json      LLM décide chaque action          │
│  scenarios/*.yaml  system prompt       MCP exécute dans le browser       │
│  .env (API keys)   stratégie persona   snapshot → observation → thought  │
│                                        → jusqu'à DONE / max_steps        │
│                                                                          │
│                                        ▼                                 │
│                                        reports/*.json                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Phase 1 — INPUTS

| Source | Rôle |
|--------|------|
| `config/config.yaml` | Paramètres LLM, browser, navigation |
| `scenarios/*.yaml` | Objectif, critères succès/abandon |
| `.env` | Clés API (`GROQ_API_KEY`, etc.) |

### Phase 2 — PERSONA → System Prompt

Les attributs de la persona sont traduits en **stratégie de navigation** injectée dans le system prompt du LLM :

| Attribut | `acheteur_impatient` | `acheteur_prudent` |
|----------|---------------------|-------------------|
| `vitesse_navigation` | `rapide` → pas de scroll, 1er écran seulement | `lente` → scroll complet obligatoire |
| `sensibilite_prix` | `faible` → prend le 1er produit visible | `haute` → compare TOUS les prix |
| `tolerance_erreurs` | `haute` → ignore les erreurs | `faible` → retry soigneusement |
| `patience_attente_sec` | `5s` → abandonne vite | `20s` → attend le chargement |
| `device` | `mobile` | `desktop` |

### Phase 3 — BOUCLE ReAct MCP

À chaque step, le LLM reçoit le snapshot compressé de la page et produit :

```
THOUGHT: <raisonnement persona>
ACTION: <nom_outil_mcp>
ACTION_INPUT: {"param": "valeur"}
```

Python extrait l'action, appelle l'outil MCP, reçoit l'observation, et renvoie au LLM.

---

## 🔍 Boucle ReAct MCP en détail

```
Step 1 ──▶ THOUGHT: Navigate to /products
           ACTION: browser_navigate
           ACTION_INPUT: {"url": "https://automationexercise.com/products"}
           OBSERVATION: PRODUCTS:
                        - Blue Top | Rs. 500 | View ref=e116
                        - Men Tshirt | Rs. 400 | View ref=e130
                        - ...

Step 2 ──▶ THOUGHT: Men Tshirt at Rs. 400 is cheapest. Clicking View Product.
           ACTION: browser_click
           ACTION_INPUT: {"ref": "e130"}
           OBSERVATION: Product detail page loaded.

Step 3 ──▶ THOUGHT: I see Add to Cart button ref=e50.
           ACTION: browser_click
           ACTION_INPUT: {"ref": "e50"}
           OBSERVATION: Product added to cart.

Step 4 ──▶ THOUGHT: Task complete.
           DONE
```

Le snapshot brut Playwright (arbre d'accessibilité) est **compressé** par `_compress_snapshot()` avant d'être envoyé au LLM. Cela réduit ~15 000 caractères en une table de produits de ~500 caractères.

---

## 🧠 Stratégies par persona

### `acheteur_impatient` (vitesse=rapide)

- Navigue sur **mobile**, pas de patience
- **Interdit de scroller** — n'agit que sur le 1er écran visible
- Prend le produit le moins cher **parmi ceux visibles immédiatement**
- Ignore les erreurs (tolérance haute) et passe au produit suivant
- Se termine dès que le produit est ajouté au panier (`DONE` immédiat)

### `acheteur_prudent` (vitesse=lente)

- Navigue sur **desktop**, patient et méthodique
- **Scroll obligatoire** : `browser_evaluate → browser_snapshot` en boucle jusqu'au bas de page
- Accumule la liste de **tous les produits** et leurs prix sur tous les snapshots
- Compare **uniquement après avoir atteint le bas** de la page
- Choisit le produit avec le **prix absolu le plus bas**
- Retry soigneux en cas d'erreur (tolérance faible)

---

## 🗂️ Structure des fichiers

```
part1 pfe/
├── app.py                      # Mode ReAct manuel (sans MCP)
├── test_mcp.py                 # Point d'entrée — mode MCP (LLM aux commandes)
├── requirements.txt            # Dépendances Python
│
├── config/
│   └── config.yaml             # Configuration globale (LLM, browser, navigation)
│
├── personas/
│   ├── acheteur_impatient.json # Persona rapide, mobile, peu sensible au prix
│   └── acheteur_prudent.json   # Persona lente, desktop, très sensible au prix
│
├── scenarios/
│   ├── achat_vetement.yaml     # Scénario achat de vêtement
│   ├── comparaison_produits.yaml
│   └── trouver_moins_cher.yaml
│
├── src/
│   ├── config_loader.py        # Chargement YAML / JSON
│   ├── prompt_builder.py       # Génération du system prompt persona
│   ├── agent.py                # PersonaAgent — boucle ReAct MCP + _compress_snapshot
│   ├── dom_extractor.py        # Extraction DOM (mode ReAct manuel)
│   └── parser.py               # Parsing réponses LLM (mode ReAct manuel)
│
├── reports/                    # Rapports JSON générés automatiquement
└── dom_output/                 # Dumps DOM pour debug (mode ReAct manuel)
```

---

## 👤 Personas

### `acheteur_impatient`

```json
{
  "id": "acheteur_impatient",
  "objectif": "Trouver et acheter l'article le moins cher disponible",
  "vitesse_navigation": "rapide",
  "sensibilite_prix": "faible",
  "tolerance_erreurs": "haute",
  "patience_attente_sec": 5,
  "device": "mobile",
  "heure_connexion": "23:00"
}
```

### `acheteur_prudent`

```json
{
  "id": "acheteur_prudent",
  "objectif": "Trouver un produit de bonne qualité au meilleur prix",
  "vitesse_navigation": "lente",
  "sensibilite_prix": "haute",
  "tolerance_erreurs": "faible",
  "patience_attente_sec": 20,
  "device": "desktop",
  "heure_connexion": "21:00"
}
```

---

## 📄 Scénarios

Chaque fichier `scenarios/*.yaml` définit :

- **`funnel_steps`** : étapes attendues (homepage → products → detail → cart)
- **`success_criteria`** : conditions de `DONE`
- **`abandon_criteria`** : conditions d'arrêt anticipé
- **`constraints`** : budget max, devise

---

## ⚙️ Configuration

`config/config.yaml` :

```yaml
llm:
  provider: "groq"                   # groq | github | openai | ollama
  model: "llama-3.1-8b-instant"
  temperature: 0.7
  max_tokens: 1024

navigation:
  max_steps: 20                      # Maximum d'étapes par session ReAct
  action_delay: 2                    # Délai entre actions (secondes)
  page_content_limit: 1500

browser:
  headless: false                    # true = browser invisible
  viewport:
    width: 1280
    height: 800

logging:
  verbosity: "normal"
  opentelemetry_enabled: false
  screenshots_enabled: false
```

Variables d'environnement (`.env`) :

```env
GROQ_API_KEY=...
GITHUB_TOKEN=...
OPENAI_API_KEY=...
TARGET_URL=https://automationexercise.com
```

---

## 🛠️ Installation

```bash
# 1. Créer et activer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Installer les navigateurs Playwright
playwright install chromium

# 4. Installer le serveur MCP Playwright (Node.js requis)
npm install -g @playwright/mcp

# 5. Créer le fichier .env et remplir avec vos clés API
```

---

## 🚀 Utilisation

```bash
# Un seul persona (défaut : acheteur_impatient)
python test_mcp.py

# Persona spécifique
python test_mcp.py acheteur_prudent

# Les deux personas en comparaison côte-à-côte
python test_mcp.py both
```

### Exemple de sortie

```
════════════════════════════════════════════════════════════
           MCP INTEGRATION TEST
════════════════════════════════════════════════════════════

[1] Loading configuration...
  ✓ LLM: groq/llama-3.1-8b-instant
  ✓ Headless: False

[2] Running persona: acheteur_impatient...
  ✓ Persona     : acheteur_impatient
  ✓ Objectif    : Trouver et acheter l'article le moins cher
  ✓ Vitesse     : rapide
  ✓ Prix sens.  : faible
  ✓ Tolérance   : haute
  ✓ Patience    : 5s
  ✓ Device      : mobile

════════════════════════════════════════════════════════════
🚀 MCP ReAct SESSION STARTING
════════════════════════════════════════════════════════════
📍 Target URL: https://automationexercise.com
👤 Persona: acheteur_impatient
🎯 Scenario: Find the cheapest t-shirt and add it to cart

🔌 Connecting to Playwright MCP Server...
✓ Connected! 24 tools available

─── Step 1/20 ────────────────────────────────────────────
THOUGHT: I need to navigate to the products page.
ACTION: browser_navigate
ACTION_INPUT: {"url": "https://automationexercise.com/products"}
OBSERVATION: PRODUCTS:
  - Blue Top | Rs. 500 | View ref=e116
  - Men Tshirt | Rs. 400 | View ref=e130

─── Step 2/20 ────────────────────────────────────────────
THOUGHT: Men Tshirt at Rs. 400 is the cheapest. Clicking View Product.
ACTION: browser_click
ACTION_INPUT: {"ref": "e130"}

...

  Status   : completed
  Steps    : 5
  Duration : 38.2s
  Report   : reports/mcp_test_acheteur_impatient_20260312_121054.json

════════════════════════════════════════════════════════════
  ✅ MCP TEST PASSED
════════════════════════════════════════════════════════════
```

---

## 📊 Rapports

Chaque session génère automatiquement un fichier JSON dans `reports/` :

```
reports/mcp_test_acheteur_impatient_20260312_121054.json
```

Structure :

```json
{
  "test_type": "MCP Integration Test",
  "timestamp": "2026-03-12T12:10:54",
  "persona": {
    "id": "acheteur_impatient",
    "vitesse_navigation": "rapide",
    "sensibilite_prix": "faible",
    "tolerance_erreurs": "haute",
    "patience_attente_sec": 5,
    "device": "mobile"
  },
  "scenario": { "name": "...", "objectif": "..." },
  "target_url": "https://automationexercise.com",
  "config": { "llm_provider": "groq", "llm_model": "llama-3.1-8b-instant", "headless": false },
  "result": {
    "status": "completed",
    "steps": 5,
    "duration_sec": 38.2,
    "response": "Task completed successfully.",
    "steps_detail": [
      {
        "step": 1,
        "thought": "Navigate to products page.",
        "action": "browser_navigate",
        "input": {"url": "https://automationexercise.com/products"},
        "result_preview": "PRODUCTS: - Blue Top | Rs. 500 ..."
      }
    ]
  }
}
```

**Statuts possibles :** `completed` · `max_steps_reached` · `error`

---

## 🤖 LLM Providers supportés

| Provider | Variable `.env` | `provider` dans config |
|----------|-----------------|------------------------|
| **Groq** (défaut) | `GROQ_API_KEY` | `groq` |
| **GitHub Models** | `GITHUB_TOKEN` | `github` |
| **OpenAI** | `OPENAI_API_KEY` | `openai` |
| **Ollama** (local) | *(aucune)* | `ollama` |

---

## 🛠️ Outils MCP disponibles

Le LLM dispose des outils Playwright suivants pour naviguer :

| Outil MCP | Description |
|-----------|-------------|
| `browser_navigate` | Naviguer vers une URL |
| `browser_snapshot` | Capturer l'arbre d'accessibilité de la page courante |
| `browser_click` | Cliquer sur un élément par son `ref` |
| `browser_type` | Saisir du texte dans un champ |
| `browser_press_key` | Appuyer sur une touche clavier |
| `browser_evaluate` | Exécuter du JavaScript (scroll uniquement) |
| `browser_select_option` | Sélectionner une option dans un `<select>` |
| `browser_wait_for` | Attendre N millisecondes |

---

## ⚠️ Limitations & Roadmap

**Limitations actuelles :**

- Exécution séquentielle uniquement (pas de multi-personas en parallèle)
- OpenTelemetry non activé
- Pas de screenshots automatiques
- Pas de conteneurisation

**Prochaines étapes :**

- [ ] OpenTelemetry pour les traces distribuées
- [ ] Multi-personas en parallèle
- [ ] Screenshots automatiques à chaque step MCP
- [ ] Conteneurisation Docker
- [ ] Interface web de visualisation des rapports
- [ ] Métriques et dashboards comparatifs

---

## 🔬 Références

- ReAct: Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Playwright MCP Server](https://github.com/microsoft/playwright-mcp)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Playwright Python](https://playwright.dev/python/)

---

**Auteur** : PFE ENSI / TALAN Tunisie  
**Période** : Février – Juin 2026
