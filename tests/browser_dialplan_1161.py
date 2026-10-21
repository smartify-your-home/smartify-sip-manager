from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    pg = b.new_context(bypass_csp=True, viewport={'width': 1330, 'height': 1000}).new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8102/'); pg.wait_for_selector('.pb-group')
    pg.evaluate("showPanel('route')"); pg.wait_for_timeout(2500)
    print(pg.inner_text('#groupsExisting')[:900])
    print('scroll els', pg.evaluate("[...document.querySelectorAll('#groupsExisting, #groupsExisting *')].filter(e=>{const c=getComputedStyle(e);return /(auto|scroll)/.test(c.overflowY)&&e.scrollHeight>e.clientHeight}).length"))
    pg.locator('#groupsExisting').screenshot(path='1161.png')
    print('ERRORS', errs); b.close()
