from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8092'
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('dialog', lambda d: d.accept())
    pg.goto(B + '/'); pg.wait_for_selector('.pb-group')
    pg.click('[data-tab="anlage"]'); pg.wait_for_function("document.getElementById('anState').textContent.includes('Modell')")
    pg.click('#anVorschlag'); pg.wait_for_selector('#anRows tr[data-i="2"]'); pg.wait_for_timeout(800)
    pg.select_option('#anAddTyp', 'neu:extern_ziel'); pg.wait_for_timeout(300)
    r = pg.locator('#anRows tr[data-i]').last
    for k in ('endpoint', 'eingang'):
        sel = r.locator(f'select[data-k="{k}"]')
        print(k, '=', sel.input_value(), '|', sel.evaluate("s=>[...s.querySelectorAll('optgroup')].map(g=>g.label+': '+[...g.children].map(o=>o.textContent).join(', ')).join(' / ')"))
    r.locator('select[data-k="endpoint"]').select_option('linphone-in')
    r.locator('[data-k="sip_adresse"]').fill('x@sip.linphone.org'); r.locator('[data-k="name"]').fill('Test')
    pg.click('#anSave'); pg.wait_for_timeout(1200)
    pg.click('[data-tab="anlage"]'); pg.wait_for_timeout(600)
    r = pg.locator('#anRows tr[data-i]').last
    r.locator('.an-ziel').screenshot(path='1132_ziel.png')
    pg.click('[data-tab="start"]'); pg.wait_for_timeout(1500)
    t = pg.inner_text('#pbRows'); j = t.find('eher ein'); print(t[max(0,j-60):j+250])
    print('ERRORS', errs); b.close()
