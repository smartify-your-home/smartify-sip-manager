# Manuell: Testserver (Port 8087) mit Dialplan-Muster _1XX starten, dann dieses Skript.
from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8087'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="3"]'); pg.wait_for_timeout(800)
    pg.select_option('#anAddTyp', 'neu:extern_ziel')
    r = pg.locator('#anRows tr[data-i]').last
    r.locator('[data-k="sip_adresse"]').fill('test-benutzer-a@sip.linphone.org'); r.locator('[data-k="sip_adresse"]').dispatch_event('change')
    pg.locator('#anRows tr[data-i]').last.locator('[data-k="name"]').fill('Amelie Handy')
    door = pg.locator('#anRows tr', has=pg.locator('input[data-k="nummer"][value="110"]'))
    door.locator('[data-k="stream"]').fill('cam_pt2'); door.locator('[data-f="kamerabild"]').check()
    pg.click('#anWegAdd'); w = pg.locator('#anWege tr[data-w="0"]')
    w.locator('[data-pick="von"] summary').click(); w.locator('[data-pick="von"] label', has_text='110').locator('input').check()
    w.locator('[data-pick="ziele"] summary').click(); w.locator('[data-pick="ziele"] label', has_text='104').locator('input').check()
    w.locator('[data-pick="ziele"] label', has_text='Test Linphone').locator('input').check()
    pg.mouse.click(5, 5)
    pg.click("#anSave"); pg.wait_for_timeout(1500); print("STATE:", pg.inner_text("#anState"))
    pg.click('[data-tab="verbindungen"]'); pg.wait_for_selector('#vbSvg .vb-node')
    print('SUM:', pg.inner_text('#vbSum'))
    pg.locator('.vb-wrap').screenshot(path='195_graph.png')
    pg.locator('#vbSvg .vb-node[data-id="tn:906"]').click(); pg.wait_for_timeout(300)
    pg.locator('.vb-wrap').screenshot(path='195_sel.png')
    print(pg.inner_text('#vbDetail'))
    print('ERRORS', errs); b.close()
