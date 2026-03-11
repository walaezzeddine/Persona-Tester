# Persona Tester 🎭

**Outil de simulation comportementale IA** - PFE ENSI / TALAN Tunisie (Fév–Juin 2026)

## 📋 Description

Persona Tester simule des utilisateurs virtuels avec des comportements différents qui naviguent sur un vrai site web en production. Un LLM (GPT-4o) incarne chaque persona et prend les décisions de navigation en temps réel basées sur le contenu de la page.

---

## 🔄 Pipeline de Fonctionnement

Le pipeline se déroule en **3 phases successives** :

```
┌─────────────────────────────────────────────────────────────────┐
│                     PERSONA TESTER PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   PHASE 1    │   │   PHASE 2    │   │   PHASE 3    │        │
│  │   INPUTS     │──▶│   PERSONA    │──▶│  REACT LOOP  │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│                                                                 │
│  • URL cible        • Profil JSON      • OBSERVE (DOM)         │
│  • Scénario YAML    • Comportement     • REASON (LLM)          │
│  • Config globale   • System prompt    • ACT (Playwright)      │
│                                        • TRACE (logs)          │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1 : INPUTS

| Entrée | Description | Fichier |
|--------|-------------|---------|
| **URL cible** | Le vrai site en production à tester | `.env` |
| **Scénario** | Objectif du test, critères de succès/abandon | `scenarios/*.yaml` |
| **Configuration** | Paramètres LLM, timeouts, verbosité | `config/config.yaml` |

### Phase 2 : PERSONA

Chaque persona est un profil comportemental défini en JSON :

```json
{
  "vitesse_navigation": "lente",      // Comment il navigue
  "sensibilite_prix": "haute",        // Sensibilité au budget
  "tolerance_erreurs": "faible",      // Patience face aux erreurs
  "device": "desktop",                // Type d'appareil
  "heure_connexion": "21:00"          // Contexte temporel
}
```

Ces attributs sont **traduits en instructions comportementales** et injectés dans le system prompt du LLM.

### Phase 3 : BOUCLE ReAct

Inspirée du paradigme ReAct (Yao et al., ICLR 2023) :

```
┌─────────────────────────────────────────────────────────────┐
│                    BOUCLE REACT                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. OBSERVE    →  Extraire le DOM structuré de la page    │
│       ↓            (boutons, liens, inputs, produits)      │
│                                                             │
│   2. REASON     →  LLM analyse avec le profil persona      │
│       ↓            "Je vois un bouton Products, je clique" │
│                                                             │
│   3. ACT        →  Playwright exécute l'action             │
│       ↓            click / scroll / type                   │
│                                                             │
│   4. TRACE      →  Logger l'action et son résultat         │
│       ↓            (OpenTelemetry prévu)                   │
│                                                             │
│   REPEAT        →  Jusqu'à FINISH / ABANDON / max steps    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture du Projet

```
part1 pfe/
├── .env                              # Variables d'environnement
├── requirements.txt                  # Dépendances Python
├── main.py                           # Point d'entrée - Pipeline complet
│
├── config/
│   └── config.yaml                   # Configuration globale
│
├── scenarios/
│   └── achat_smartphone.yaml         # Scénario de test
│
├── personas/
│   └── acheteur_prudent.json         # Profil comportemental
│
└── src/
    ├── __init__.py
    ├── config_loader.py              # Chargement config/scénario/persona
    ├── prompt_builder.py             # Génération du system prompt
    ├── parser.py                     # Parsing des réponses LLM
    ├── dom_extractor.py              # Extraction structurée du DOM
    └── agent.py                      # Agent LLM (PersonaAgent)
```

---

## 📁 Fichiers en Détail

### `config/config.yaml`

Configuration centrale du système :

```yaml
llm:
  provider: "github"          # github | openai | ollama
  model: "gpt-4o"
  temperature: 0.2

navigation:
  max_steps: 15               # Maximum d'étapes par session
  action_delay: 2             # Délai entre actions (sec)
  page_content_limit: 1500    # Limite de caractères pour le LLM

browser:
  headless: false             # true = invisible
  viewport: {width: 1280, height: 800}
```

### `scenarios/achat_smartphone.yaml`

Définit l'objectif et les critères :

```yaml
name: "achat_smartphone"
objective: "Trouver un produit intéressant et l'ajouter au panier"

success_criteria:
  - "Produit ajouté au panier"

abandon_criteria:
  - "Erreur 404 ou 500"
  - "Prix hors budget"

constraints:
  max_price: 500
  currency: "TND"
```

### `personas/acheteur_prudent.json`

Profil comportemental complet :

```json
{
  "id": "acheteur_prudent",
  "vitesse_navigation": "lente",
  "sensibilite_prix": "haute",
  "tolerance_erreurs": "faible",
  "patience_attente_sec": 20,
  "device": "desktop",
  "heure_connexion": "21:00",
  "objectif": "Trouver un smartphone sous 500 TND"
}
```

### `src/prompt_builder.py`

Traduit les attributs JSON en instructions via des dictionnaires de mapping :

| Attribut | Valeurs | Comportement généré |
|----------|---------|---------------------|
| `vitesse_navigation` | lente/rapide/normale | Rythme de navigation |
| `sensibilite_prix` | haute/faible/normale | Attention au budget |
| `tolerance_erreurs` | faible/haute/normale | Patience face aux bugs |
| `device` | mobile/desktop/tablet | Contexte d'utilisation |
| `heure_connexion` | HH:MM → période | Contexte temporel |

### `src/dom_extractor.py`

Extraction structurée du DOM (pas juste inner_text) :

- **Clickables** : Boutons et liens visibles
- **Inputs** : Champs de formulaire
- **Products** : Informations produits (nom, prix)
- **Errors** : Messages d'erreur détectés

### `src/agent.py`

Classe `PersonaAgent` :

```python
agent = PersonaAgent(
    user=persona,       # Profil JSON
    scenario=scenario,  # Scénario YAML
    config=config       # Configuration
)

decision = agent.decide(page_content, page_url, step)
# → {"thought": "...", "action": "click", "target": "Products"}
```

---

## 🛠️ Installation

```bash
# 1. Cloner et accéder au projet
cd "c:\Users\Lenovo\part1 pfe"

# 2. Installer les dépendances
pip install playwright langchain langchain-openai langchain-core python-dotenv openai pyyaml

# 3. Installer Chromium
python -m playwright install chromium
```

---

## ⚙️ Configuration

### Fichier `.env`

```env
# Token GitHub pour GitHub Models (gratuit)
GITHUB_TOKEN=github_pat_VOTRE_TOKEN

# URL du site à tester
TARGET_URL=https://automationexercise.com/
```

### Obtenir un token GitHub Models

1. https://github.com/settings/tokens
2. "Generate new token (classic)"
3. Cocher les permissions nécessaires
4. Copier dans `.env`

---

## 🚀 Utilisation

```bash
python main.py
```

### Sortie attendue :

```
════════════════════════════════════════════════════════════
           PERSONA TESTER - Navigation Session
════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────
  PHASE 1: INPUTS
  Chargement de la configuration, scénario et URL cible
────────────────────────────────────────────────────────────
  ✓ Config loaded: github/gpt-4o
  ✓ Scenario loaded: achat_smartphone
    Objective: Trouver un produit intéressant et l'ajouter au panier
  ✓ Target URL: https://automationexercise.com/

────────────────────────────────────────────────────────────
  PHASE 2: PERSONA
  Génération du profil comportemental
────────────────────────────────────────────────────────────
  ✓ Persona loaded: acheteur_prudent
    - Vitesse: lente
    - Sensibilité prix: haute
    - Tolérance erreurs: faible
    - Device: desktop
  ✓ Agent initialized with gpt-4o

────────────────────────────────────────────────────────────
  PHASE 3: REACT LOOP
  Boucle Observe → Reason → Act → Trace
────────────────────────────────────────────────────────────

  🚀 Opening browser: https://automationexercise.com/

──────────────────── Step 1/15 ────────────────────
💭 Thought : Je vois un lien Products, je vais cliquer dessus
🎯 Action  : click
📍 Target  : Products
  ✓ Action executed

──────────────────── Step 2/15 ────────────────────
💭 Thought : Je suis sur la page produits, je vais chercher
🎯 Action  : type
📍 Target  : smartphone
  ✓ Action executed
...

════════════════════════════════════════════════════════════
                    SESSION SUMMARY
════════════════════════════════════════════════════════════
✅ Status  : SUCCESS (FINISH)
📝 Reason  : Produit ajouté au panier
📊 Steps   : 8
⏱️  Duration: 45.2s
🌐 URL     : https://automationexercise.com/view_cart
════════════════════════════════════════════════════════════
```

---

## 🧠 Choix Techniques

| Choix | Raison |
|-------|--------|
| **GitHub Models** | Gratuit, accès GPT-4o sans carte bancaire |
| **Playwright** | Navigation web robuste, support async |
| **LangChain** | Abstraction LLM, gestion historique |
| **YAML configs** | Lisible, facile à modifier |
| **DOM structuré** | Meilleure compréhension pour le LLM |

---

## 📝 Actions Supportées

| Action | Description | Target |
|--------|-------------|--------|
| `click` | Cliquer sur un élément | Sélecteur CSS ou texte |
| `scroll` | Défiler la page | `up` ou `down` |
| `type` | Saisir du texte | Texte à taper |
| `FINISH` | Objectif atteint | Raison du succès |
| `ABANDON` | Abandon | Raison de l'échec |

---

## ⚠️ Limitations Actuelles

- Pas de multi-personas en parallèle (prévu)
- Pas d'OpenTelemetry (prévu)
- Limite tokens GitHub Models (8000)
- Pas de Docker/Kubernetes

---

## 🔜 Prochaines Étapes

- [ ] OpenTelemetry pour les traces
- [ ] Multi-personas en parallèle
- [ ] Screenshots automatiques
- [ ] Conteneurisation Docker
- [ ] Interface web de visualisation
- [ ] Métriques et dashboards

---

**Auteur** : PFE ENSI / TALAN Tunisie  
**Date** : Février - Juin 2026
