# Manuell: Testserver aus tests/browser_erzeugen_150_server.py mit simulierten Entitäten starten, dann dieses Skript.
import json, urllib.request
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto('http://127.0.0.1:8099/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.wait_for_function("document.querySelectorAll('#anAddTyp option').length > 5")
    print('Menü leer:', pg.locator('#anAddTyp').inner_text().replace('\n', ' | '))
    pg.click('#anErkennen'); pg.wait_for_timeout(500)
    print('Netz:', pg.input_value('#anLan'), pg.input_value('#anTs'), pg.input_value('#anHttps'))
    # SIP-Core-Benutzer direkt aus Menü
    pg.select_option('#anAddTyp', 'sip:ipad')
    pg.select_option('#anAddTyp', 'neu:tuerstation')
    pg.select_option('#anAddTyp', 'ext:linphone-cloud')
    pg.select_option('#anAddTyp', 'neu:sip_telefon')
    rows = pg.locator('#anRows tr[data-i]')
    for i in range(rows.count()):
        r = rows.nth(i)
        print(' ', r.locator('[data-k="nummer"]').input_value(), '|', r.locator('[data-k="name"]').input_value(), '|', r.locator('[data-k="typ"]').input_value())
    door = pg.locator('#anRows tr[data-i="1"]')
    door.locator('[data-k="tuer_entity"]').fill('switch.flur_kg_sa1_a8_haustuer')
    door.locator('[data-k="klingel_entity"]').fill('binary_sensor.akuvox_klingel')
    door.locator('[data-k="stream"]').fill('cam_pt2')
    print('Menü danach:', pg.locator('#anAddTyp').inner_text().replace('\n', ' | '))
    pg.click('#anWegAdd'); w = pg.locator('#anWege tr[data-w="0"]')
    w.locator('[data-pick="von"] summary').click(); w.locator('[data-pick="von"] label', has_text='100').locator('input').check()
    w.locator('[data-pick="ziele"] summary').click(); w.locator('[data-pick="ziele"] label', has_text='104').locator('input').check()
    w.locator('[data-k="klingelzeit"]').select_option('30')
    pg.mouse.click(5, 5)
    pg.click('#anSave'); pg.wait_for_function("document.getElementById('anState').textContent==='Gespeichert'")
    m = json.load(urllib.request.urlopen('http://127.0.0.1:8099/api/anlage'))['model']
    print('Teilnehmer:', [(t['nummer'], t['name'], t['typ'], t['ha_benutzer'] or t['endpoint'], t['tuer_entity'], t['klingel_entity']) for t in m['teilnehmer']])
    print('Wege:', m['wege'])
    pg.screenshot(path='16_anlage.png', full_page=True)
    print('ERRORS', errs); b.close()
