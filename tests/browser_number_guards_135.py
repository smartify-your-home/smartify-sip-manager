"""Browser regression: an occupied extension must not be creatable via either form."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'smartify_sip_manager'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1360,'height':950})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('dialog',lambda d:d.accept())
    html=(ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
    page.set_content(html)
    page.add_style_tag(path=str(ROOT/'app.css'))
    page.evaluate('''() => {
      window.calls=[];
      window.fetch=async (url, opts) => {
        const path=String(url).replace(/^api\\//,'');
        if(opts?.method === 'POST') {
          const body=JSON.parse(opts.body || '{}'); window.calls.push({path,body});
          return {ok:true,status:200,json:async()=>({saved:true,note:'OK',hash:'next'})};
        }
        const vals={
          'health':{asterisk_directory:true,custom_directory:true},
          'status':{container:'addon_test',custom:'test',files:['pjsip_custom.conf','extensions.conf'],asterisk_config_found:true,version:'1.3.5'},
          'endpoints':{endpoints:[{extension:'107',display_name:'Beate',files:['custom/pjsip_custom.conf'],status:'Nicht geprüft',editable:'custom'}],warnings:[]},
          'number-plan':{used:{'107':['Asterisk-Nebenstelle'],'600':['Rufgruppe (default)']},endpoints:[{extension:'107',display_name:'Beate',files:['custom/pjsip_custom.conf']}],dialplan:[{number:'600',kind:'Rufgruppe',context:'default',source:'custom/extensions.conf',targets:[],steps:[]}],warnings:[]},
          'structured/pjsip':{source:'custom',hash:'pjsiphash',cloud_endpoints:[],rows:[{number:'107',name:'Beate',max_contacts:'1',remove_existing:'yes',remove_unavailable:'no',context:'default',codecs:'alaw,ulaw',username:'107',editable:true,settings:{}}]},
          'file/pjsip_custom.conf':{source:'custom',hash:'pjsiphash',content:'[107]\\ntype=aor\\n'},
          'file/extensions.conf':{source:'custom',hash:'ehash',content:'[default]\\n'},
          'hints':{hints:{}},'discovery':{files:[]},
        };
        return {ok:true,status:200,json:async()=>vals[path]||{}};
      };
    }''')
    page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
    page.add_script_tag(path=str(ROOT/'app.js'))
    page.locator('#pjsipDetails > summary').click()
    page.wait_for_selector('[data-save-pjsip="107"]')
    page.locator('#epExt').fill('107')
    assert page.locator('#makeEndpoint').is_disabled(), 'Existing number must disable builder'
    assert page.locator('#epDirectSave').is_disabled(), 'Existing number must disable direct-save'
    assert page.locator('#epEditExisting').is_visible(), 'Existing number should reveal edit action'
    page.locator('#epEditExisting').click()
    assert page.locator('[data-extension="107"] [data-col="name"]').evaluate('(el)=>document.activeElement===el')
    page.locator('#pjsipTableNew').click()
    page.locator('[data-new-pjsip] [data-col="number"]').fill('107')
    assert page.locator('[data-add-pjsip]').is_disabled(), 'Existing number must disable new-row save'
    assert 'belegt' in page.locator('[data-new-status]').inner_text().lower()
    page.locator('[data-new-pjsip] [data-col="number"]').fill('108')
    assert page.locator('[data-add-pjsip]').is_enabled(), 'Free number can be created'
    page.locator('[data-cancel-pjsip]').click()
    page.locator('[data-delete-pjsip="107"]').click()
    page.wait_for_function("window.calls.some(c=>c.path==='structured/pjsip/save' && c.body.operation==='delete')")
    delete=page.evaluate("window.calls.find(c=>c.body.operation==='delete')")
    assert delete['body']['number']=='107'
    assert not errors,errors
    print('Chromium UI: occupied form+table numbers blocked, existing edit/delete actions – PASS')
    browser.close()
