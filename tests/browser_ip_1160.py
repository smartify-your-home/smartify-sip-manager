from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8101'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="2"]'); pg.wait_for_timeout(800)
    r = pg.locator('#anRows tr', has=pg.locator('input[data-k="nummer"][value="906"]'))
    ip = r.locator('input[data-k="quell_ips"]'); ip.fill('100.64.10.20'); ip.dispatch_event('change'); pg.wait_for_timeout(300)
    print(pg.inner_text('#anEingaenge'))
    r.locator('.an-ziel').screenshot(path='1160_ziel.png'); pg.locator('#anEingaenge').screenshot(path='1160_eg.png')
    pg.click('#anSave'); pg.wait_for_timeout(1200); print('STATE', pg.inner_text('#anState'))
    m = pg.evaluate("fetch('api/anlage').then(r=>r.json())")
    print([ (t['name'], t['quell_ips']) for t in m['model']['teilnehmer'] if t['typ']=='extern_ziel'])
    pg.click('[data-tab="erzeugen"]'); pg.wait_for_selector('.erz-ziel'); pg.wait_for_timeout(500)
    for z in pg.locator('.erz-ziel').all()[:2]:
        print('---'); print('\n'.join(z.locator('.erz-akt li').all_inner_texts()))
    print('ERRORS', errs); b.close()
