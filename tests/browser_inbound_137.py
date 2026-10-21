"""Browser test of the configurable, constrained Linphone inbound form."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'smartify_sip_manager'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    html=(ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
    page.set_content(html)
    page.add_style_tag(path=str(ROOT/'app.css'))
    page.evaluate('''() => {
      window.saved=[];window.confirm=()=>true;
      window.fetch=async (url,opts)=>{
        const key=String(url).replace(/^\\/?api\\//,'');
        let body=opts?.method==='POST'?JSON.parse(opts.body):null;
        if(body) window.saved.push({key,body});
        const vals={
         'status':{version:'1.3.7',files:['pjsip_custom.conf','extensions.conf'],asterisk_config_found:true},
         'health':{asterisk_directory:true,custom_directory:true},
         'inbound':{profiles:[{name:'linphone-in',ips:['100.64.10.20/32'],targets:['104'],pjsip_file:'custom/pjsip_custom.conf',extensions_file:'custom/extensions.conf',readonly:false}],available_extensions:['100','104','106']},
         'file/pjsip_custom.conf':{source:'custom',hash:'P',content:''},
         'file/extensions.conf':{source:'custom',hash:'E',content:''},
         'inbound/preview':{pjsip:'[linphone-in-identify]\\nmatch=100.64.10.20/32',extensions:'[linphone-in]\\nexten => 104,1,NoOp()'},
         'inbound/save':{saved:true,note:'Saved'},
         'number-plan':{used:{},endpoints:[],dialplan:[],sip_core_numbers:[],warnings:[]},
         'structured/pjsip':{source:'custom',hash:'P',rows:[],cloud_endpoints:[]},
         'endpoints':{endpoints:[],warnings:[]}
        };
        return {ok:true,status:200,json:async()=>vals[key]||{}};
      }
    }''')
    page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
    page.add_script_tag(path=str(ROOT/'app.js'))
    page.locator('[data-tab="inbound"]').click()
    page.wait_for_function("document.querySelector('#inRows').textContent.includes('linphone-in')")
    assert page.locator('#inTargets input').count()==3
    assert page.locator('#inTargets input[value="104"]').is_checked()
    page.locator('#inTargets input[value="100"]').check()
    page.locator('#inIPs').fill('100.64.10.20/32\n100.64.10.21/32')
    page.locator('#inPreview').click()
    page.wait_for_function("document.querySelector('#inPreviewP').value.includes('match=100.126')")
    page.locator('#inSave').click()
    page.wait_for_function("window.saved.some(x=>x.key==='inbound/save')")
    saved=page.evaluate("window.saved.find(x=>x.key==='inbound/save').body")
    assert saved['targets']==['100','104'],saved
    assert saved['ips']==['100.64.10.20/32','100.64.10.21/32'],saved
    assert saved['hashes']=={'pjsip':'P','extensions':'E'},saved
    assert not errors,errors
    print('Chromium: Linphone-Eingang, mehrere Quell-IPs, Mehrfachauswahl und Speichern – PASS')
    browser.close()
