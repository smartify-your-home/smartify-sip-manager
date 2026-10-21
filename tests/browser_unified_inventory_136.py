"""Chromium test: exactly one main overview and explain why deletion is blocked."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'smartify_sip_manager'
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1460,'height':900})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
  page.set_content(html)
  page.add_style_tag(path=str(ROOT/'app.css'))
  page.evaluate('''() => {
    window.calls=[];
    window.fetch=async (url, opts) => {
      const path=String(url).replace(/^api\\//,'');
      if(opts?.method==='POST') {window.calls.push(path);return {ok:true,status:200,json:async()=>({saved:true,note:'OK'})};}
      const ep={extension:'106',display_name:'Raphael',context:'default',files:['custom/pjsip_devices.conf'],editable:'custom',status:'Nicht geprüft'};
      const row={number:'106',file:'pjsip_devices.conf',hash:'hash',name:'Raphael',max_contacts:'1',remove_existing:'yes',remove_unavailable:'no',context:'default',codecs:'alaw,ulaw',username:'106',editable:true,settings:{}};
      const group={number:'600',kind:'Rufgruppe',context:'default',source:'custom/extensions.conf',targets:['106'],steps:['NoOp(Klingel)','Dial(${PJSIP_DIAL_CONTACTS(106)},30)'],route_options:null};
      const vals={
        'health':{asterisk_directory:true,custom_directory:true},
        'status':{version:'1.3.6',files:['pjsip_custom.conf','pjsip_devices.conf'],asterisk_config_found:true},
        'number-plan':{used:{'106':['Asterisk-Nebenstelle'],'600':['Rufgruppe (default)']},endpoints:[ep],dialplan:[group],sip_core_numbers:[],warnings:[]},
        'structured/pjsip':{source:'missing',hash:'empty',rows:[row],cloud_endpoints:[]},
        'endpoints':{endpoints:[ep],warnings:[]},
        'file/pjsip_custom.conf':{source:'missing',hash:'empty',content:''},
        'hints':{hints:{}},'discovery':{files:[]}
      };
      return {ok:true,status:200,json:async()=>vals[path]||{}};
    }
  }''')
  page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
  page.add_script_tag(path=str(ROOT/'app.js'))
  page.wait_for_selector('[data-inv-delete="106"]')
  assert page.locator('#numberSummary').count()==0
  assert page.locator('#endpointResults').count()==0
  assert page.locator('#unifiedInventory tbody tr').count()==2
  assert 'Rufgruppe' in page.locator('#unifiedInventory').inner_text()
  assert 'custom/pjsip_devices.conf' in page.locator('#unifiedInventory').inner_text()
  assert not page.locator('#pjsipDetails').evaluate('(el)=>el.open')
  page.locator('[data-inv-edit="106"]').click()
  assert page.locator('#pjsipDetails').evaluate('(el)=>el.open')
  page.locator('[data-inv-delete="106"]').click()
  page.wait_for_function("document.querySelector('#feedback').textContent.includes('Rufziel 600@default')")
  assert not page.evaluate('window.calls.length')
  assert not errors,errors
  print('Chromium: gemeinsame Nummerntabelle, Custom-Quelldatei, Bearbeiten und Löschblocker – PASS')
  browser.close()
