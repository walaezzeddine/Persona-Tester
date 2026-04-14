import sqlite3
import json
import os

conn = sqlite3.connect('database/persona_automation.db')
cursor = conn.cursor()

# 1. Insert test websites
print('📥 Insertion des websites...')
websites = [
    ('parabank', 'https://parabank.parasoft.com', 'parabank.parasoft.com', 'banking', 'Demo banking app'),
    ('booking-com', 'https://www.booking.com', 'booking.com', 'travel', 'Hotel booking platform'),
]
for w in websites:
    cursor.execute('INSERT OR IGNORE INTO websites VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)', w)
print('   ✓ 2 websites ajoutés')

# 2. Import existing personas from JSON files
print('\n📥 Import des personas existants...')
persona_dir = 'generated_personas'
imported = 0

for filename in os.listdir(persona_dir):
    if filename.endswith('.json') and not filename.startswith('website_') and not filename.startswith('personas_'):
        filepath = os.path.join(persona_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        persona_id = filename.replace('.json', '')
        website_url = data.get('website_url', '')
        
        # Determine website_id
        if 'parabank' in website_url.lower():
            website_id = 'parabank'
        elif 'booking' in website_url.lower():
            website_id = 'booking-com'
        else:
            website_id = 'parabank'
        
        cursor.execute('''
            INSERT OR IGNORE INTO personas 
            (id, website_id, nom, type_persona, device, vitesse, patience_sec, objectif, json_file_path, generated_by_llm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            persona_id,
            website_id,
            data.get('nom', 'Unknown'),
            data.get('style_navigation', 'unknown'),
            data.get('device', 'desktop'),
            data.get('vitesse_navigation', 'moyenne'),
            int(data.get('patience_attente_sec', 30)),
            data.get('objectif', ''),
            filepath
        ))
        imported += 1
        print(f'   ✓ {persona_id}')

conn.commit()

# 3. Show results
print(f'\n✅ {imported} personas importés!')
print('\n' + '='*50)
print('📊 CONTENU DE LA BASE DE DONNÉES')
print('='*50)

cursor.execute('SELECT COUNT(*) FROM websites')
print(f'\n🌐 Websites: {cursor.fetchone()[0]}')
cursor.execute('SELECT id, domain, type FROM websites')
for row in cursor.fetchall():
    print(f'   - {row[0]}: {row[1]} ({row[2]})')

cursor.execute('SELECT COUNT(*) FROM personas')
print(f'\n👤 Personas: {cursor.fetchone()[0]}')
cursor.execute('SELECT id, nom, website_id, device, vitesse FROM personas')
for row in cursor.fetchall():
    print(f'   - {row[0]}: {row[1]} | {row[2]} | {row[3]}/{row[4]}')

conn.close()
print('\n✅ Test terminé!')
