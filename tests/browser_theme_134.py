"""Manager themes and password acceptance in Chromium; no HA runtime required."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1] / 'smartify_sip_manager'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1250,'height':900})
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 html=(root/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
 page.set_content(html)
 page.add_style_tag(path=str(root/'app.css'))
 page.evaluate('''() => {window.fetch=async(url)=>({ok:true,status:200,json:async()=>String(url).endsWith('number-plan')?{used:{},endpoints:[],dialplan:[],warnings:[]}:{} })}''')
 page.add_script_tag(path=str(root/'pjsip-builder.js'))
 page.add_script_tag(path=str(root/'app.js'))
 page.wait_for_selector('#managerTheme')
 assert page.locator('#managerTheme').input_value()=='light'
 light=page.evaluate("""() => ({bg:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,font:getComputedStyle(document.body).fontFamily})""")
 assert light['bg']=='rgb(233, 236, 239)' and light['text']=='rgb(23, 27, 32)',light
 assert 'Calibri' in light['font'], light
 page.locator('#managerTheme').select_option('dark')
 dark=page.evaluate("""() => ({bg:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,font:getComputedStyle(document.body).fontFamily})""")
 assert dark['bg']=='rgb(16, 24, 33)' and dark['text']=='rgb(237, 243, 248)',dark
 assert 'Calibri' in dark['font']
 page.locator('#managerTheme').select_option('light')
 page.locator('#epExt').fill('117')
 page.locator('#epName').fill('Kurzes Passwort')
 page.locator('#epPassword').fill('1234')
 page.locator('#makeEndpoint').click()
 page.wait_for_function('document.querySelector("#epOut").value.includes("password=1234")',timeout=5000)
 assert not errors,errors
 print('Chromium: Hell/Dunkel Calibri, Lesbarkeit, 4-stelliges Passwort in PJSIP-Vorschau – OK')
 browser.close()
