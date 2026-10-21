"""Real Chromium smoke test with stubbed HA/Asterisk APIs. Run manually."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1] / 'smartify_sip_manager'
with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1330,'height':940})
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        def stub_payload(path):
            responses={
                'health':{'asterisk_directory':True,'custom_directory':True,'hint':''},
                'status':{'container':'addon_test_asterisk','custom':'/addon_configs/test/asterisk/custom','files':['pjsip_custom.conf','extensions.conf'],'asterisk_config_found':True, 'version':'1.3.3'},
                'endpoints':{'endpoints':[{'extension':'100','display_name':'iPad','files':['default/pjsip_default.conf'],'status':'Offline'}],'warnings':[]},
                'number-plan':{'used':{'100':['Asterisk-Nebenstelle'],'600':['Rufgruppe']},'endpoints':[{'extension':'100','display_name':'iPad'}],'dialplan':[],'warnings':[], 'complete':False},
            }
            return responses.get(path,{'error':'Stub nicht definiert: '+path})
        data={p:stub_payload(p) for p in ['health','status','endpoints','number-plan']}
        page.set_content((ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>', ''))
        page.add_style_tag(path=str(ROOT/'app.css'))
        page.evaluate('(data) => { window.fetch = async (url) => ({ok:true,status:200,json:async () => data[String(url).replace(/^api\//,"")] || {}}) }', data)
        page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
        page.add_script_tag(path=str(ROOT/'app.js'))
        page.locator('#epExt').fill('107')
        page.locator('#epName').fill('Beate Linphone')
        page.locator('#epPassword').fill('test1234test1234')
        page.locator('#epMaxContacts').fill('4')
        page.locator('#epRemoveExisting').select_option('no')
        page.locator('#epRemoveUnavailable').select_option('yes')
        page.locator('#makeEndpoint').click()
        page.wait_for_function('document.querySelector("#epOut").value.includes("max_contacts=4")',timeout=5000)
        output=page.locator('#epOut').input_value()
        assert 'remove_existing=no' in output and 'remove_unavailable=yes' in output and 'callerid="Beate Linphone" <107>' in output
        page.locator('#epMaxContacts').fill('2')
        assert page.locator('#epOut').input_value()==''
        page.locator('#makeEndpoint').click()
        page.wait_for_function('document.querySelector("#epOut").value.includes("max_contacts=2")',timeout=5000)
        page.locator('#epExt').fill('100')
        assert page.locator('#makeEndpoint').is_disabled()
        assert page.locator('#epOut').input_value()==''
        # advanced fields behave and cannot fall back to old fixed values
        page.locator('#epExt').fill('109')
        page.locator('.ep-extra summary').click()
        page.locator('#epQualify').fill('30')
        page.locator('#epDtmf').select_option('info')
        page.locator('input[name="epCodec"][value="g722"]').check()
        page.locator('#makeEndpoint').click()
        page.wait_for_function('document.querySelector("#epOut").value.includes("qualify_frequency=30")',timeout=5000)
        output=page.locator('#epOut').input_value()
        assert 'allow=alaw,ulaw,g722' in output and 'dtmf_mode=info' in output
        assert not errors,errors
        print('Chromium: UI (107/109), Belegung, AOR-Einstellungen, erweiterte Optionen, Vorschau-Ungültigkeit – OK')
        browser.close()
