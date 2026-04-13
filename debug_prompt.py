#!/usr/bin/env python3
"""
Debug script to check what system prompt is generated
"""

from pathlib import Path
from src.config_loader import Config, load_scenario
from src.prompt_builder import build_system_prompt

# Load scenario
scenario_path = Path("scenarios/wallstreet_improved.yaml")
scenario = load_scenario(str(scenario_path))

# Create test persona
test_persona = {
    "id": "test_wallstreet_001",
    "nom": "Test Investor",
    "description": "A test persona analyzing stocks",
    "objectif": "Analyze Apple (AAPL) stock and decide whether to buy or sell",
    "device": "desktop",
    "heure_connexion": "12:00",
    "vitesse_navigation": "normale",
    "sensibilite_prix": "haute",
    "tolerance_erreurs": "haute",
}

# Build system prompt
system_prompt = build_system_prompt(test_persona, scenario)

# Print key sections
print("="*80)
print("SYSTEM PROMPT - KEY SECTIONS")
print("="*80)

# Extract objectif section
lines = system_prompt.split("\n")
for i, line in enumerate(lines):
    if "OBJECTIVE" in line or "SCENARIO" in line or "STEP-BY-STEP" in line or "KEY ACTIONS" in line.upper():
        # Print this line and next 10 lines
        for j in range(i, min(i+15, len(lines))):
            print(lines[j])
        print("\n" + "-"*80 + "\n")
