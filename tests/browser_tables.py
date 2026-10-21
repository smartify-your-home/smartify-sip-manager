"""UI smoke with mocked REST responses for new structured tables."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'smartify_sip_manager'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1360,'height':1000})
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('dialog',lambda d:d.accept())
 html=(ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
 page.set_content(html)
 page.add_style_tag(path=str(ROOT/'app.css'))
 stub='''window.calls=[];window.fetch=async function(url,opts){
 const path=String(url).replace(/^api\\//, '');
 if(opts?.method==='POST'){
   window.calls.push({path,body:JSON.parse(opts.body||'{}')});
   return {ok:true,status:200,json:async()=>({saved:true,note:'Gespeichert',hash:'new_hash'})};
 }
 const vals={
  'health':{asterisk_directory:true,custom_directory:true},
  'status':{container:'addon_test',custom:'test',files:['pjsip_custom.conf','extensions.conf'],'asterisk_config_found':true,version:'1.3.3'},
  'endpoints':{endpoints:[{extension:'100',display_name:'iPad',files:['default/pjsip_default.conf'],status:'Unknown'},{extension:'107',display_name:'Linphone',files:['custom/pjsip_custom.conf'],status:'Unknown'}],warnings:[]},
  'number-plan':{used:{'100':['Asterisk'],'107':['Asterisk'],'444':['Dialplan'],'600':['Rufgruppe']},endpoints:[{extension:'100',display_name:'iPad'},{extension:'107',display_name:'Linphone'}],warnings:[],dialplan:[
  {number:'444',kind:'Dialplan-Ziel',context:'default',source:'custom/extensions.conf',line:9,targets:[],editable:false,steps:['Playback(hello-world)','Hangup()']},
  {number:'600',kind:'Rufgruppe',context:'default',source:'custom/extensions.conf',line:26,targets:['100'],editable:true,route_options:{targets:['100'],external_targets:[],description:'Smartify Rufgruppe 600',timeout:30,hangup:true},steps:['NoOp(Smartify Rufgruppe 600)','Dial(${PJSIP_DIAL_CONTACTS(100)},30)','Hangup()']}
  ]},
  'structured/pjsip':{source:'custom',hash:'pjsiphash',cloud_endpoints:[{name:'linphone-cloud',editable:true,settings:{transport:'transport-udp',allow:'alaw,ulaw'}}],rows:[{number:'107',name:'Beate Linphone',max_contacts:'1',remove_existing:'yes',remove_unavailable:'no',context:'default',codecs:'alaw,ulaw',username:'107',editable:true,settings:{}}]},
  'file/pjsip_custom.conf':{source:'custom',hash:'phash',content:'[107]\\ntype=aor\\n'},
  'file/extensions.conf':{source:'custom',hash:'ehash',content:'[default]\\n'},
  'hints':{hints:{'extensions.conf':'dialplan reload','pjsip_custom.conf':'pjsip reload'}},
  'discovery':{files:[]}
 };
 return {ok:true,status:200,json:async()=> vals[path]||{}};
 }'''
 page.evaluate(stub)
 page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
 page.add_script_tag(path=str(ROOT/'app.js'))
 page.locator('#pjsipDetails > summary').click()
 page.wait_for_selector('[data-save-pjsip="107"]', timeout=3000)
 page.locator('[data-extension="107"] [data-col="max_contacts"]').fill('3')
 page.locator('[data-save-pjsip="107"]').click()
 page.wait_for_function('window.calls.some(c=>c.path==="structured/pjsip/save")')
 c=page.evaluate('window.calls.find(c=>c.path==="structured/pjsip/save")')
 assert c['body']['operation']=='edit' and 'max_contacts=3' in c['body']['snippet']
 assert 'password=\n' in c['body']['snippet']
 # Test advanced editable AOR values from the existing row.
 page.locator('[data-extension="107"] .advanced-cell summary').click()
 page.locator('[data-extension="107"] [data-col="qualify_frequency"]').fill('30')
 page.locator('[data-save-pjsip="107"]').click()
 page.wait_for_function('window.calls.filter(c=>c.path==="structured/pjsip/save").length>=2')
 assert 'qualify_frequency=30' in page.evaluate('window.calls.filter(c=>c.path==="structured/pjsip/save")[1].body.snippet')
 # Cloud endpoint edit.
 page.locator('[data-cloud="linphone-cloud"] [data-col="allow"]').fill('alaw,ulaw,g722')
 page.locator('[data-cloud-save="linphone-cloud"]').click()
 page.wait_for_function('window.calls.some(c=>c.path==="structured/cloud/save")')
 assert page.evaluate('window.calls.find(c=>c.path==="structured/cloud/save").body.settings.allow')=='alaw,ulaw,g722'
 # Create a new PJSIP entry entirely through a table row.
 page.locator('#pjsipTableNew').click()
 page.locator('[data-new-pjsip] [data-col="number"]').fill('108')
 page.locator('[data-new-pjsip] [data-col="name"]').fill('Test Linphone')
 page.locator('[data-new-pjsip] [data-col="profile"]').select_option('linphone')
 page.locator('[data-new-pjsip] [data-col="password"]').fill('short')
 page.locator('[data-add-pjsip]').click()
 page.wait_for_function('window.calls.some(c=>c.path==="structured/pjsip/save" && c.body.operation==="add")')
 assert 'password=short' in page.evaluate('window.calls.find(c=>c.path==="structured/pjsip/save" && c.body.operation==="add").body.snippet')
 # Show full actions instead of former 'siehe Datei'.
 page.locator('[data-area="groups"]').click()
 page.wait_for_selector('[data-save-route="1"]')
 assert 'Playback(hello-world)' in page.locator('#groupsExisting').text_content()
 assert 'siehe Datei' not in page.locator('#groupsExisting').inner_text()
 page.locator('[data-route="1"] [data-col="timeout"]').fill('45')
 page.locator('[data-save-route="1"]').click()
 page.wait_for_function('window.calls.some(c=>c.path==="structured/group/save")')
 c=page.evaluate('window.calls.find(c=>c.path==="structured/group/save")')
 assert c['body']['timeout']==45 and c['body']['targets']==['100']
 # Short passwords are allowed in new endpoint builder.
 page.locator('[data-area="asterisk"]').click()
 page.locator('#epExt').fill('108')
 page.locator('#epName').fill('Another')
 page.locator('#epPassword').fill('abc123')
 page.locator('#makeEndpoint').click()
 page.wait_for_function('document.querySelector("#epOut").value.includes("password=abc123")')
 assert not errors,errors
 print('Chromium UI: structured PJSIP changes, dialplan details and group save, short passwords – PASS')
 browser.close()
