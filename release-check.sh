#!/bin/sh
# Vor jedem Release ausführen: ./release-check.sh
set -e
cd "$(dirname "$0")"
python3 check-versions.py
python3 -m py_compile smartify_sip_manager/app.py
python3 -m unittest discover -s tests
if command -v node >/dev/null 2>&1; then
  for f in smartify_sip_manager/pjsip-builder.js smartify_sip_manager/app.js smartify_sip_manager/anlage-ui.js frontend/smartify-doorstation-popup.js frontend/smartify-doorstation-card.js; do node --check "$f"; done
  node --test tests/test_pjsip_builder.js
  echo "JavaScript-Syntax und Generator-Tests OK"
else
  echo "Hinweis: node nicht gefunden – JavaScript-Syntax nicht geprüft"
fi
echo "Release-Prüfung bestanden."
