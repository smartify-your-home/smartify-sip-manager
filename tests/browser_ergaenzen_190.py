# Manuell: Testserver (Port 8095) mit extensions_custom.conf starten, dann dieses Skript.
import json, urllib.request
from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8095'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.wait_for_function("document.querySelectorAll('#anAddTyp option').length > 5")
    pg.select_option('#anAddTyp', 'sip:ipad')
    pg.locator('#anRows tr[data-i="0"] [data-k="name"]').fill('Mein iPad (umbenannt)')
    pg.click('#anSave'); pg.wait_for_function("document.getElementById('anState').textContent==='Gespeichert'")
    pg.click('#anVorschlag'); pg.wait_for_function("document.getElementById('feedback').textContent.includes('ergänzt')")
    print(pg.inner_text('#feedback')); print(pg.inner_text('#anHints'))
    rows = pg.locator('#anRows tr[data-i]')
    print([(rows.nth(i).locator('[data-k=\"nummer\"]').input_value(), rows.nth(i).locator('[data-k=\"name\"]').input_value(), rows.nth(i).locator('[data-k=\"typ\"]').input_value()) for i in range(rows.count())])
    pg.click('#anVorschlag'); pg.wait_for_timeout(1500); print(pg.inner_text('#feedback'))
    print('ERRORS', errs); b.close()
