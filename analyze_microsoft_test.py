#!/usr/bin/env python3
"""Analyze Microsoft test results to see what actions were actually taken"""
import json
import sys

def analyze_results(results_file):
    print("=" * 80)
    print(f"ANALYSE DU TEST: {results_file}")
    print("=" * 80)

    with open(results_file, 'r') as f:
        data = json.load(f)

    result = data['result']
    steps_detail = result.get('steps_detail', [])

    print(f"\n📊 RÉSUMÉ GÉNÉRAL:")
    print(f"   Scénario: {data['scenario']}")
    print(f"   Persona: {data['persona']}")
    print(f"   Status: {result['status']}")
    print(f"   Étapes: {result['steps']}/{result.get('status_detail', 'unknown')}")

    # Statistiques des actions
    actions = {}
    rejections = []

    for i, step in enumerate(steps_detail):
        action = step.get('action', 'unknown')
        actions[action] = actions.get(action, 0) + 1

        if 'rejected_reason' in step:
            rejections.append((i+1, action, step['rejected_reason']))

    print(f"\n🔧 ACTIONS EFFECTUÉES:")
    for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
        print(f"   {action}: {count}x")

    # Rejets d'actions
    if rejections:
        print(f"\n⛔ ACTIONS REJETÉES ({len(rejections)} rejets):")
        for step_num, action, reason in rejections:
            print(f"   Étape {step_num}: {action}")
            print(f"      → {reason}")

    # Progression du test
    print(f"\n📍 PROGRESSION DU TEST:")
    key_milestones = [
        ('browser_navigate', 'Navigation'),
        ('browser_click', 'Clic sur éléments'),
        ('browser_type', 'Saisie de texte'),
        ('browser_snapshot', 'Snapshots'),
        ('browser_evaluate', 'Évaluation JS'),
    ]

    for action, label in key_milestones:
        count = actions.get(action, 0)
        if count > 0:
            print(f"   ✓ {label}: {count}x")

    # Pages visitées
    print(f"\n🌐 PAGES VISITÉES:")
    pages_visited = set()
    for step in steps_detail:
        if step.get('result_preview'):
            # Extraire l'URL
            if 'Page URL:' in step['result_preview']:
                url_line = [l for l in step['result_preview'].split('\n') if 'Page URL:' in l]
                if url_line:
                    url = url_line[0].replace('Page URL:', '').strip()
                    pages_visited.add(url)

    for i, page in enumerate(sorted(pages_visited), 1):
        print(f"   {i}. {page}")

    # Scénario demandé vs complété
    print(f"\n✅ SCÉNARIO DEMANDÉ:")
    success_criteria = [
        "Navigated to Microsoft company profile",
        "Reviewed at least 4 data sources: News, Ratings, Price History, Financial Statements",
        "Made a clear BUY/NO BUY decision based on analysis",
        "Decision is documented with reasoning"
    ]

    for i, criterion in enumerate(success_criteria, 1):
        print(f"   [{i}] {criterion}")

    # Tentative de trouver si le scénario a été complété
    final_thought = steps_detail[-1].get('thought', '')
    print(f"\n💭 DERNIÈRE PENSÉE DE L'AGENT:")
    print(f"   {final_thought[:500]}...")

    # Verdict
    print(f"\n🎯 ANALYSE:")
    if result['status'] == 'max_steps_reached':
        print(f"   ❌ Scénario NON complété (max steps atteint)")
        print(f"   → L'agent a épuisé les {result['steps']} étapes autorisées")
    elif result['status'] == 'success':
        print(f"   ✅ Scénario complété avec succès")
    else:
        print(f"   ⚠️  Status: {result['status']}")

    # Problèmes identifiés
    print(f"\n⚠️ PROBLÈMES IDENTIFIÉS:")
    if rejections:
        print(f"   • {len(rejections)} tentatives de navigation rejetées")
        print(f"   → Le LLM essaie de contourner les restrictions d'URL")

    if len(pages_visited) < 5:
        print(f"   • Peu de pages visitées ({len(pages_visited)} pages)")
        print(f"   → Difficultés à naviguer sur le site")

    # Chercher si Microsoft a été recherché/trouvé
    msft_found = False
    for step in steps_detail:
        if 'MSFT' in str(step) or 'Microsoft' in str(step):
            msft_found = True
            break

    if not msft_found:
        print(f"   • Microsoft (MSFT) n'a pas été trouvé/recherché")
        print(f"   → Scénario principal non atteint")
    else:
        print(f"   • Microsoft (MSFT) a été recherché")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    results_file = sys.argv[1] if len(sys.argv) > 1 else "test_microsoft_analyst_results.json"
    analyze_results(results_file)
