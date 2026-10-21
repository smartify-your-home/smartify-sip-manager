# Manuell: Testserver (Port 8090, Dialplan mit Rufgruppe 600) starten, dann dieses Skript.
from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8090'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="2"]'); pg.wait_for_timeout(800)
    print('HINTS', pg.inner_text('#anHints'))
    print('WEGE rows', pg.locator('#anWege tr[data-w]').count())
    pg.click("#anSave"); pg.wait_for_timeout(1200); print("STATE:", pg.inner_text("#anState"))
    pg.click('[data-tab="rufgruppen"]'); pg.wait_for_selector('#rgPal .rg-chip')
    print('PAL', pg.locator('#rgPal .rg-chip').all_inner_texts())
    print('GROUP0', pg.locator('.rg-group[data-w="0"]').inner_text())
    # drag 110 -> von of group 0
    pg.drag_and_drop('#rgPal .rg-chip[data-ref="110"]', '.rg-group[data-w="0"] .rg-zone[data-zone="von"]')
    # tap mode: 105 -> ziele
    pg.click('#rgPal .rg-chip[data-ref="105"]'); pg.click('.rg-group[data-w="0"] .rg-zone[data-zone="ziele"] .rg-zl')
    # drag 104 -> new group
    pg.drag_and_drop('#rgPal .rg-chip[data-ref="104"]', '.rg-new .rg-zone')
    # tuerstation to ziele must be refused
    pg.drag_and_drop('#rgPal .rg-chip[data-ref="110"]', '.rg-group[data-w="1"] .rg-zone[data-zone="ziele"]')
    print('MSG', pg.evaluate("document.getElementById('msg')?.textContent || ''"))
    pg.wait_for_timeout(300)
    print('LINES', pg.locator('#rgLines path').count())
    pg.locator('#rgBoard').screenshot(path='198_board.png')
    pg.click('#rgSave'); pg.wait_for_timeout(1200); print('RGSTATE', pg.inner_text('#rgState'))
    m = pg.evaluate("fetch('api/anlage').then(r=>r.json())")
    for w in m['model']['wege']: print(w)
    pg.click('[data-tab="erzeugen"]'); pg.wait_for_timeout(2500)
    print('ERZ', pg.inner_text('#erzeugen')[:1500])
    pg.set_viewport_size({'width': 420, 'height': 900}); pg.click('[data-tab="rufgruppen"]'); pg.wait_for_timeout(400)
    pg.screenshot(path='198_mobile.png', full_page=False)
    print('ERRORS', errs); b.close()
