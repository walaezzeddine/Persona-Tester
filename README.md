# Persona Automation - Architecture Physique et Logique

Ce projet automatise des tests UX en simulant des utilisateurs synthétiques (personas) sur des sites web réels.

Objectif principal:
- analyser un site,
- générer des personas réalistes et cohérents,
- générer un scénario de navigation par persona,
- exécuter ce scénario dans un navigateur via Playwright/MCP,
- stocker les traces d'exécution pour analyse.

## 1) Architecture Physique

### 1.1 Vue d'ensemble des couches

- Couche présentation: `frontend/web` (React + TypeScript)
- Couche API: `Backend/src/api/routes.py` (FastAPI)
- Couche intelligence métier/LLM: `Backend/src/agents` et `Backend/src/tools`
- Couche persistance: `Backend/database` (SQLite)
- Couche exécution navigateur: agent Playwright MCP custom (`mcp-server/playwright-custom`)

### 1.2 Arborescence utile (simplifiée)

```text
Persona-Tester/
├── Backend/
│   ├── src/
│   │   ├── main.py                       # Entrée backend
│   │   ├── api/routes.py                 # Endpoints FastAPI
│   │   ├── agents/
│   │   │   ├── persona_generator.py      # Génération personas
│   │   │   ├── persona_action_planner.py # Plan d'actions persona (review)
│   │   │   └── persona_agent.py          # Exécution runtime (ReAct + MCP)
│   │   ├── tools/
│   │   │   ├── website_analyzer.py       # Analyse du site
│   │   │   ├── scenario_generator.py     # Génération de scénario
│   │   │   └── dom_extractor.py          # Résumé DOM pour LLM
│   │   ├── prompts/builder.py            # Construction du prompt système
│   │   └── models/db_manager.py          # Accès DB
│   ├── database/
│   │   ├── persona_automation.db         # SQLite
│   │   └── schema.sql
│   └── .env
├── frontend/
│   └── web/src/
│       ├── App.tsx                       # Dashboard principal
│       ├── ScriptModal.tsx               # Vue scénario/script
│       └── PlaywrightHistory.tsx         # Historique exécutions
└── mcp-server/playwright-custom/agent.py # Agent Playwright MCP custom
```

### 1.3 Déploiement local

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5000`
- Modèle LLM local (par défaut): Ollama sur `http://localhost:11434/v1`
- DB: SQLite locale dans `Backend/database`

## 2) Architecture Logique

### 2.1 Pipeline global (end-to-end)

1. L'utilisateur configure un test via le frontend.
2. L'API backend enregistre le site cible.
3. `WebsiteAnalyzer` produit une analyse structurée + `llm_context`.
4. `PersonaGenerator` crée N personas à objectif partagé.
5. Les personas sont persistés en base (JSON + métadonnées).
6. `ScenarioGenerator` (ou `PersonaActionPlanner`) produit les actions/scénarios.
7. Le frontend peut afficher/éditer les actions.
8. `PersonaAgent` exécute le scénario via les outils Playwright MCP.
9. Les logs/steps/screenshots/statuts sont stockés et exposés par API.

### 2.2 Flux de données

- Entrée: URL + configuration test + objectif
- Analyse: JSON d'analyse du site (`website_analyses.raw_json`)
- Génération: JSON persona (`personas.persona_json`)
- Scénarisation: JSON scénario (`playwright_test_executions.generated_script`)
- Exécution: logs d'étapes + erreurs + capture + durée

### 2.3 Comportement runtime

- Le runtime suit un pattern ReAct: Observation -> Raisonnement -> Action.
- Le scénario guide le comportement, mais l'état réel de page reste la vérité opérationnelle.
- Le `dom_extractor` compresse le DOM en éléments actionnables (liens, boutons, inputs, modal/popup).
- `persona_agent.py` applique des règles générales + règles spécifiques par site quand nécessaire.

## 3) Composants et responsabilités

### Frontend (React)

- `App.tsx`
	- orchestre génération personas, génération scénario, lancement exécution,
	- appelle les endpoints backend,
	- affiche les erreurs métier (ex: persona introuvable).

- `ScriptModal.tsx`
	- visualise script/scénario,
	- permet édition avant exécution.

- `PlaywrightHistory.tsx`
	- affiche l'historique des exécutions et statuts.

### API FastAPI

- `Backend/src/api/routes.py`
	- expose endpoints `generate`, `run-script`, `executions`, `stats`, etc.,
	- coordonne analyse -> génération -> exécution,
	- gère les erreurs de cohérence (persona absente, exécution verrouillée, etc.).

### Intelligence de génération

- `website_analyzer.py`
	- transforme le crawl/snapshot en profil fonctionnel de site,
	- produit un `llm_context` orienté génération de personas.

- `persona_generator.py`
	- génère des personas diversifiés mais alignés sur le même objectif,
	- injecte device, vitesse, style, patience, sensibilité prix, douleurs, actions_site,
	- normalise et valide les champs.

- `scenario_generator.py`
	- produit un scénario de test structuré: `key_actions`, `success_criteria`, `description`.

- `persona_action_planner.py`
	- produit un plan d'actions pondéré par traits persona,
	- utile pour revue humaine avant exécution.

### Runtime d'exécution

- `persona_agent.py`
	- exécute le scénario dans le navigateur via MCP,
	- applique stratégies d'interaction visibles,
	- gère retries, erreurs, blocages UI (modals/overlays), et contrôle de progression.

- `dom_extractor.py`
	- extrait un état de page compact et actionnable pour le LLM,
	- expose signaux utiles: clickables, inputs, produits, popups.

### Persistance

- `models/db_manager.py` + `database/schema.sql`
	- stockage central des websites, analyses, personas, sessions de génération,
		exécutions Playwright, logs de steps.

## 4) Pourquoi ce choix d'architecture

### Séparation des responsabilités

- Frontend: UX, orchestration visuelle, contrôle utilisateur.
- Backend API: coordination des workflows, sécurité métier, cohérence de données.
- Agents/Tools: logique IA spécialisée et réutilisable.
- DB: traçabilité complète et auditabilité des runs.

Ce découpage réduit le couplage et permet de faire évoluer chaque couche séparément.

### Pipeline orienté données

Le projet conserve chaque artefact intermédiaire (analyse, persona, scénario, logs).
Avantages:
- debug plus rapide,
- reproductibilité,
- comparaison de stratégies de génération,
- amélioration incrémentale des prompts/règles runtime.

### Architecture hybride "LLM + garde-fous"

- LLM pour générer et raisonner.
- Règles runtime déterministes pour fiabiliser l'exécution (formats d'actions, anti-loop, popup handling).

Ce compromis donne plus de robustesse qu'une approche purement générative.

### Provider-agnostic

Support de plusieurs providers (Ollama/OpenAI/Google/GitHub) dans les composants de génération.
Cela évite le verrouillage fournisseur et facilite les tests de modèles.

## 5) Endpoints clés

- `POST /api/test-config`: analyse + génération personas
- `POST /api/playwright/generate`: génération de scénario pour une persona
- `POST /api/playwright/run-script`: exécution scenario par `execution_id`
- `GET /api/playwright/executions`: historique d'exécution
- `GET /api/personas`, `GET /api/websites`, `GET /api/stats`

## 6) Démarrage recommandé

### Prérequis

- Python 3.10+
- Node.js 18+
- Ollama local actif (ou autre provider configuré)

### Backend

```bash
cd Backend
python src/main.py
```

### Frontend

```bash
cd frontend/web
npm install
npm run dev
```

## 7) Résumé exécutif

Le projet suit une architecture en couches claire (UI -> API -> génération IA -> exécution browser -> persistance), avec un pipeline explicite et traçable.

Le choix majeur est de combiner:
- génération intelligente contextuelle (analyse + personas + scénarios),
- exécution déterministe instrumentée,
- stockage complet des artefacts,

afin d'obtenir un système robuste, auditable, et itératif pour les tests UX pilotés par personas.
