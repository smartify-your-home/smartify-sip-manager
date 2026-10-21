"""End-to-end browser interaction for SIP routes 109 / 600 and cloud endpoint editor."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'smartify_sip_manager'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1400,'height':1100})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('dialog',lambda d:d.accept())
    html=(ROOT/'index.html').read_text().replace('<script defer="" src="pjsip-builder.js"></script><script defer="" src="app.js"></script>','')
    page.set_content(html)
    page.add_style_tag(path=str(ROOT/'app.css'))
    page.evaluate('''() => {
      window.calls=[];
      window.fetch=async function(url,opts){
        let path=String(url).replace(/^api\\//,'');
        if(opts?.method==='POST'){
          window.calls.push({path,body:JSON.parse(opts.body||'{}')});
          return {ok:true,status:200,json:async()=>({saved:true,note:'Gespeichert',hash:'newhash'})};
        }
        const vals={
          'health':{asterisk_directory:true,custom_directory:true},
          'status':{container:'addon_test',custom:'test',files:['pjsip_custom.conf','extensions.conf'],asterisk_config_found:true,version:'1.3.3'},
          'endpoints':{endpoints:[{extension:'104',display_name:'iPad',files:['default/pjsip_default.conf'],status:'Unknown'},
            {extension:'106',display_name:'Raphael',files:['custom/pjsip_custom.conf'],status:'Unknown'},
            {extension:'linphone-cloud',display_name:'',files:['custom/pjsip_custom.conf'],status:'Unknown'}],warnings:[]},
          'number-plan':{used:{'104':['Asterisk'],'106':['Asterisk'],'109':['Dialplan'],'600':['Rufgruppe']},
            endpoints:[{extension:'104',display_name:'iPad'},{extension:'106',display_name:'Raphael'},{extension:'linphone-cloud',display_name:''}],warnings:[],dialplan:[
              {number:'109',kind:'Dialplan-Ziel',context:'default',source:'custom/extensions.conf',line:9,targets:[],editable:true,
               route_options:{targets:[],external_targets:[{endpoint:'linphone-cloud',uri:'sip:test-benutzer-v@sip.linphone.org'}],timeout:30,description:'Linphone Push 106'},
               steps:['NoOp(Linphone Push 106)','Dial(PJSIP/linphone-cloud/sip:test-benutzer-v@sip.linphone.org,30)','Hangup()']},
              {number:'600',kind:'Rufgruppe',context:'default',source:'custom/extensions.conf',line:15,targets:['104'],editable:true,
               route_options:{targets:['104'],external_targets:[{endpoint:'linphone-cloud',uri:'sip:beispielkonto@sip.linphone.org'}],timeout:30,description:'Akuvox Klingel iPad + iPhone'},
               steps:['NoOp(Akuvox Klingel iPad + iPhone)','Dial(${PJSIP_DIAL_CONTACTS(104)}&PJSIP/linphone-cloud/sip:beispielkonto@sip.linphone.org,30)','Hangup()']}
            ]},
          'structured/pjsip':{source:'custom',hash:'phash',cloud_endpoints:[{name:'linphone-cloud',editable:true,settings:{transport:'transport-udp',allow:'alaw,ulaw',direct_media:'no',force_rport:'yes',rtp_symmetric:'yes'}}],rows:[
            {number:'106',name:'Raphael',max_contacts:'1',remove_existing:'yes',remove_unavailable:'no',context:'default',codecs:'alaw,ulaw',username:'106',editable:true,settings:{transport:'transport-udp',qualify_frequency:'30',direct_media:'no',rtp_symmetric:'yes',force_rport:'yes',rewrite_contact:'yes'}}]},
          'file/pjsip_custom.conf':{source:'custom',hash:'phash',content:'[106]\\ntype=aor\\n'},
          'file/extensions.conf':{source:'custom',hash:'ehash',content:'[default]\\n'},
          'hints':{hints:{'extensions.conf':'dialplan reload','pjsip_custom.conf':'pjsip reload'}},
          'discovery':{files:[]}
        };
        return {ok:true,status:200,json:async()=> vals[path]||{}};
      };
    }''')
    page.add_script_tag(path=str(ROOT/'pjsip-builder.js'))
    page.add_script_tag(path=str(ROOT/'app.js'))
    page.locator('[data-area="groups"]').click()
    page.wait_for_selector('[data-save-route="0"]')
    assert page.locator('[data-route="0"] [data-col="cloud_ep"]').input_value()=='linphone-cloud'
    assert page.locator('[data-route="1"] [data-col="targets"]').input_value()=='104'
    page.locator('[data-route="0"] [data-col="cloud_uri"]').fill('sip:new@sip.linphone.org')
    page.locator('[data-route="0"] [data-col="description"]').fill('Linphone Push New')
    page.locator('[data-save-route="0"]').click()
    page.wait_for_function('window.calls.some(c=>c.path==="structured/group/save")')
    out=page.evaluate('window.calls.find(c=>c.path==="structured/group/save").body')
    assert out['number']=='109' and out['external']['uri']=='sip:new@sip.linphone.org' and out['description']=='Linphone Push New',out
    page.locator('[data-area="asterisk"]').click()
    page.locator('#pjsipDetails > summary').click()
    page.wait_for_selector('[data-cloud="linphone-cloud"]')
    page.locator('#cloudTableNew').click()
    page.locator('[data-new-cloud] [data-col="name"]').fill('test-cloud')
    page.locator('[data-new-cloud] [data-col="transport"]').fill('transport-udp')
    page.locator('[data-add-cloud]').click()
    page.wait_for_function('window.calls.some(c=>c.path==="structured/cloud/save" && c.body.operation==="add")')
    assert page.evaluate('window.calls.find(c=>c.path==="structured/cloud/save").body.name')=='test-cloud'
    page.locator('[data-extension="106"] .advanced-cell summary').click()
    assert page.locator('[data-extension="106"] [data-col="qualify_frequency"]').input_value()=='30'
    assert not errors,errors
    print('Chromium: 109+600 cells, Cloud create, AOR detailed fields – PASS')
    browser.close()
