from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8106'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="2"]'); pg.wait_for_timeout(800)
    pg.select_option('#anAddTyp', 'neu:sip_telefon'); pg.wait_for_timeout(300)
    r = pg.locator('#anRows tr', has=pg.locator('select[data-k="gleiches_geraet"]')).last
    pg.fill('#anTsIp','100.64.10.10'); pg.fill('#anLan','192.168.2.65')
    r.locator('select[data-k="gleiches_geraet"]').select_option('906')
    pg.wait_for_timeout(200); render=pg.evaluate("document.querySelector('#anRows tr:last-child [data-k=realm]')?.placeholder"); print('placeholder', render)
    pg.click('#anSave'); pg.wait_for_timeout(1200); print(pg.inner_text('#anState'))
    m = pg.evaluate("fetch('api/anlage').then(r=>r.json())")
    print([(t['nummer'], t['realm'], t['gleiches_geraet']) for t in m['model']['teilnehmer'] if t['typ']=='sip_telefon'])
    print('after save', pg.evaluate("[...document.querySelectorAll('#anRows [data-k=realm]')].map(x=>x.placeholder)"), m['model']['anlage'].get('tailscale_ip'))
    print('ERRORS', errs); b.close()
