#!/usr/bin/env python3
"""Prüft vor einem Release, ob alle Versionsangaben zusammenpassen. Aufruf: python3 check-versions.py"""
import re, sys
from pathlib import Path

root = Path(__file__).resolve().parent
addon = root / 'smartify_sip_manager'
errors = []

version = re.search(r'^version:\s*["\']?([0-9][0-9A-Za-z.+-]*)', (addon / 'config.yaml').read_text(encoding='utf-8'), re.M).group(1)
changelog = (addon / 'CHANGELOG.md').read_text(encoding='utf-8')
first = re.search(r'^## (\S+)', changelog, re.M).group(1)
if first != version:
    errors.append(f'CHANGELOG beginnt mit {first}, config.yaml hat {version}')

app = (addon / 'app.py').read_text(encoding='utf-8')
fe = dict(re.findall(r"'(popup|card)':\s*'([0-9.]+)'", re.search(r'FRONTEND_VERSIONS\s*=\s*\{[^}]*\}', app).group(0)))
headers = {
    'popup': re.search(r'Popup v([0-9.]+)', (root / 'frontend/smartify-doorstation-popup.js').read_text(encoding='utf-8')).group(1),
    'card': re.search(r'Doorstation v([0-9.]+)', (root / 'frontend/smartify-doorstation-card.js').read_text(encoding='utf-8')).group(1),
}
for key, ver in headers.items():
    if fe.get(key) != ver:
        errors.append(f'FRONTEND_VERSIONS[{key}]={fe.get(key)}, Dateikopf hat {ver}')

docs = [addon / 'README.md', addon / 'index.html', root / 'INSTALLATION-KAMERA-MAPPING.md']
for doc in docs:
    text = doc.read_text(encoding='utf-8')
    for name, key in (('popup', 'popup'), ('card', 'card')):
        for found in re.findall(rf'smartify-doorstation-{name}\.js\?v=(?:<span[^>]*>)?([0-9.]+)', text):
            if found != headers[key]:
                errors.append(f'{doc.name}: ?v={found} für {name}, erwartet {headers[key]}')
    if re.search(r'/config/www/smartify-doorstation-[a-z]+\.js\?v=', text):
        errors.append(f'{doc.name}: Ressourcenpfad muss /local/ statt /config/www/ sein')

print(f'Add-on {version} · Popup {headers["popup"]} · Card {headers["card"]}')
if errors:
    print('\n'.join('FEHLER: ' + e for e in errors)); sys.exit(1)
print('Alle Versionsangaben stimmen überein.')
