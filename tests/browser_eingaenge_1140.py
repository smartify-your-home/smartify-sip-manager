from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8097'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="2"]'); pg.wait_for_timeout(800)
    # Linphone-Teilnehmer mit Eingang linphone-in
    r = pg.locator('#anRows tr', has=pg.locator('input[data-k="nummer"][value="906"]'))
    print('906 eingang:', r.locator('select[data-k="eingang"]').input_value(), '| darf:', r.locator('.an-darf input:checked').evaluate_all("l=>l.map(x=>x.value)"))
    print(pg.inner_text('#anEingaenge'))
    pg.locator('#anEingaenge [data-eg="ips"]').first.fill('100.64.10.20, 100.64.1.2'); pg.locator('#anEingaenge [data-eg="ips"]').first.dispatch_event('change')
    pg.locator('#anEingaenge').screenshot(path='1140_eg.png')
    pg.click('#anSave'); pg.wait_for_timeout(1200); print('STATE', pg.inner_text('#anState'))
    m = pg.evaluate("fetch('api/anlage').then(r=>r.json())"); print('MODEL eingaenge', m['model']['eingaenge'])
    pg.click('[data-tab="erzeugen"]'); pg.wait_for_selector('.erz-ziel'); pg.wait_for_timeout(500)
    for z in pg.locator('.erz-ziel').all()[:2]:
        print('---', z.locator('.erz-head').inner_text()); print('\n'.join(z.locator('.erz-akt li').all_inner_texts()))
        if z.locator('details summary').count(): z.locator('details summary').click(); print(z.locator('pre.diff').inner_text()[-1500:])
    print('ERRORS', errs); b.close()
