/* Smartify SIP Manager – direct model editor wizard.
 * Uses the existing /api/anlage model, optimistic hash locking, server validation.
 * Never applies Asterisk configuration or stores passwords. */
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ref=t=>t.nummer||(t.typ==='extern_ziel'&&t.sip_adresse?'sip:'+t.sip_adresse.replace(/^sip:/i,''):'')||t.endpoint||'';
 const sections={ha:'Home Assistant & System',participant:'SIP-Teilnehmer',cloud:'Cloud-Konto / externes SIP-Ziel',group:'Rufgruppe',password:'Passwörter verwalten'};
 const style=document.createElement('style');
 style.textContent=`#setupWizard{width:min(760px,calc(100vw - 24px));max-width:760px;max-height:92vh;overflow:auto;padding:22px;border:1px solid var(--border,#888);border-radius:16px;background:var(--card-background-color,#fff);color:inherit;box-shadow:0 18px 60px #0006}#setupWizard::backdrop{background:#0009}#setupWizard .wiz-head,#setupWizard .wiz-actions{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}#setupWizard .wiz-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}#setupWizard label{display:flex;flex-direction:column;gap:5px;margin:9px 0;font-size:.95em}#setupWizard input:not([type=checkbox]),#setupWizard select{width:100%;box-sizing:border-box;padding:8px;min-width:0}#setupWizard .wiz-check{display:flex;flex-direction:row;align-items:center}#setupWizard .wiz-check input{width:auto}#setupWizard .wiz-choice{display:block;width:100%;text-align:left;margin:8px 0;padding:12px}#setupWizard .wiz-note{background:rgba(128,128,128,.1);border-radius:8px;padding:12px;line-height:1.5}#setupWizard .wiz-error{color:#d44;font-weight:600;white-space:pre-wrap}#setupWizard .wiz-ok{color:#178b78}#setupWizard .wiz-progress{display:flex;gap:5px;margin:12px 0}#setupWizard .wiz-progress span{height:5px;background:#8885;flex:1;border-radius:5px}#setupWizard .wiz-progress .active{background:#178b78}#setupWizard .wiz-members{border:1px solid #8885;border-radius:8px;padding:8px;max-height:190px;overflow:auto}#setupWizard .wiz-members label{display:flex;flex-direction:row;align-items:center;margin:5px 0}#setupWizard .wiz-actions{margin-top:18px}`;
 style.textContent+=' #setupWizard .wiz-autolist{position:relative;z-index:5;border:1px solid var(--border,#888);border-radius:8px;max-height:220px;overflow-y:auto;background:var(--card-background-color,#fff);box-shadow:0 8px 16px #0003}#setupWizard .wiz-autolist[hidden]{display:none}#setupWizard .wiz-auto-option{display:block;width:100%;text-align:left;padding:9px;border:0;background:transparent;color:inherit;cursor:pointer}#setupWizard .wiz-auto-option[aria-selected=true],#setupWizard .wiz-auto-option:hover{background:rgba(100,130,150,.2)}#setupWizard .wiz-auto-option small{opacity:.7}';
 style.textContent+=' #setupWizard.wiz-ring-mode #erzeugen{display:block!important;width:100%;margin:0;padding:0}#setupWizard.wiz-ring-mode #erzZiele{max-width:100%;overflow-x:auto}';
 style.textContent+=' #setupWizard.wiz-ring-mode{width:calc(100vw - 22px);max-width:1180px;padding:12px}#setupWizard.wiz-ring-mode #rufgruppen{display:block!important;width:100%;margin:0;padding:0}#setupWizard.wiz-ring-mode #rufgruppen .card{max-width:none}#setupWizard.wiz-ring-mode .rg-board{max-width:100%;overflow-x:auto}';
 style.textContent+=` #setupWizard{color-scheme:light dark;background:var(--card,#f5f6f7);color:var(--txt,#171b20);border-color:var(--line,#c3cbd2)}#setupWizard :is(input,select,textarea,button){color:var(--txt,#171b20);background:var(--control,#f5f6f7);border:1px solid var(--line,#c3cbd2)}#setupWizard :is(input,select,textarea){background:var(--control,#fff)}#setupWizard :is(input,select,textarea)::placeholder{color:var(--muted,#5b6470);opacity:1}#setupWizard button.primary{color:#fff;background:var(--accent,#006d68)}#setupWizard .wiz-choice:hover,#setupWizard .wiz-members label:hover{background:color-mix(in srgb,var(--accent,#006d68) 10%,transparent)}#setupWizard .wiz-note{background:color-mix(in srgb,var(--card,#f5f6f7) 84%,var(--txt,#171b20) 8%);color:inherit}#setupWizard .wiz-members,#setupWizard .wiz-autolist{background:var(--card,#f5f6f7);border-color:var(--line,#c3cbd2)}#setupWizard .wiz-error{color:var(--error-color,#c63737)}#setupWizard .wiz-ok{color:var(--success-color,#178b78)}#setupWizard .wiz-progress .active{background:var(--accent,#006d68)}#setupWizard :is(button,input,select,textarea):focus-visible{outline:2px solid var(--accent,#006d68);outline-offset:2px}#setupWizard input:disabled{opacity:.5} :root[data-manager-theme=dark] #setupWizard{color-scheme:dark} :root[data-manager-theme=dark] #setupWizard .wiz-note{background:color-mix(in srgb,var(--card,#202833) 80%,white 6%)} :root[data-manager-theme=dark] #setupWizard .wiz-error{color:#ff8e8e} :root[data-manager-theme=dark] #setupWizard .wiz-ok{color:#75d4b8}`;
 document.head.appendChild(style);
 const dialog=document.createElement('dialog');dialog.id='setupWizard';dialog.setAttribute('aria-label','Einrichtungsassistent');document.body.appendChild(dialog);
 // Reuse the *actual* graphical Rufgruppen manager node and event handlers.
 // It is moved into the modal, then restored, never cloned or rebuilt.
 const applyPanel=$('erzeugen');
 const applyHome=applyPanel?.parentNode||null;
 const applyNext=applyPanel?.nextSibling||null;
 let applyEmbedded=false;
 function restoreApplyPanel(){
  if(!applyEmbedded||!applyPanel||!applyHome)return;
  if(applyNext&&applyNext.parentNode===applyHome)applyHome.insertBefore(applyPanel,applyNext);
  else applyHome.appendChild(applyPanel);
  applyPanel.classList.remove('active');
  applyEmbedded=false;
 }
  const ringPanel=$('rufgruppen');
 const ringHome=ringPanel?.parentNode||null;
 const ringNext=ringPanel?.nextSibling||null;
 let ringEmbedded=false;
 function restoreRingPanel(){
  restoreApplyPanel();
  if(!ringEmbedded||!ringPanel||!ringHome)return;
  if(ringNext&&ringNext.parentNode===ringHome)ringHome.insertBefore(ringPanel,ringNext);
  else ringHome.appendChild(ringPanel);
  ringPanel.classList.remove('active');
  dialog.classList.remove('wiz-ring-mode');
  ringEmbedded=false;
 }
 async function showRingPanel(){
  if(!ringPanel||!ringHome){dialog.innerHTML='<p role="alert">Grafischer Rufgruppen-Manager nicht verfügbar.</p>';return;}
  dialog.innerHTML='<div class="wiz-head"><h2>Rufgruppen grafisch einrichten</h2><button type="button" data-action="home">Bereiche</button><button type="button" data-action="close" aria-label="Schließen">✕</button></div><p class="wiz-note">Teilnehmer ziehen oder antippen. Nach dem Speichern kannst du hier direkt die Konfiguration erzeugen, die Vorschau prüfen und die Änderungen übernehmen.</p>';
  dialog.appendChild(ringPanel);
  const tools=document.createElement('div');
  tools.className='wiz-actions';
  tools.innerHTML='<button type="button" class="primary" data-action="ring-preview">Erzeugen &amp; Übernehmen …</button><span id="wizRingApplyStatus" role="status"></span>';
  dialog.appendChild(tools);
  ringPanel.classList.add('active');
  dialog.classList.add('wiz-ring-mode');
  ringEmbedded=true;
  try{await window.smartifyRufgruppen?.();}catch(e){const p=document.createElement('p');p.className='wiz-error';p.textContent='Rufgruppen konnten nicht geladen werden: '+e.message;dialog.insertBefore(p,ringPanel);}
  requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')));
 }
 async function showWizardApply(){
  if(!applyPanel||!applyHome)throw Error('Original-Vorschau und Übernahme nicht verfügbar.');
  // Preserve form data and reject invalid or stale models before opening a preview.
  collect();
  const invalid=valid();if(invalid)throw Error(invalid);
  await save();
  if(!saved)throw Error('Speichern wurde nicht bestätigt. Vorschau abgebrochen.');
  // The shared manager reloads after the model-updated event. Its preview always
  // reads the saved model from the API and requires independent confirmation.
  const toolbar=document.createElement('div');
  toolbar.className='wiz-actions';
  toolbar.innerHTML='<b>Vorschau und Übernahme</b><span role="status">Wähle nur die benötigten Konfigurationsziele. Übernahme erst nach Bestätigung.</span>';
  dialog.appendChild(toolbar);
  if(!applyEmbedded){dialog.appendChild(applyPanel);applyPanel.classList.add('active');applyEmbedded=true;}
  const previewButton=applyPanel.querySelector('#erzVorschau');
  if(!previewButton)throw Error('Original-Vorschau nicht verfügbar.');
  previewButton.click();
  applyPanel.scrollIntoView({block:'nearest'});
 }
 async function showRingApply(){
  if(!applyPanel||!applyHome)throw Error('Original-Vorschau und Übernahme nicht verfügbar.');
  const status=dialog.querySelector('#wizRingApplyStatus');
  if(status)status.textContent='Speichere und berechne Vorschau …';
  // Same save and generation routines as the main manager. Never apply silently.
  await window.smartifyQuickSave();
  if(!applyEmbedded){
   dialog.appendChild(applyPanel);
   applyPanel.classList.add('active');
   applyEmbedded=true;
  }
  const previewButton=applyPanel.querySelector('#erzVorschau');
  if(!previewButton)throw Error('Vorschau-Schaltfläche nicht gefunden.');
  previewButton.click();
  if(status)status.textContent='Bitte Vorschau und Ziele prüfen. Übernehmen erfordert eine eigene Bestätigung.';
  applyPanel.scrollIntoView({block:'nearest',behavior:'smooth'});
 }
  dialog.addEventListener('close',restoreRingPanel);
 const button=$('openSetupWizard');
 if(!button) return;
 let kind='',step=0,model=null,hash=null,selected='',draft=null,original=null,saved=false,busy=false,cloudPreset='linphone';
 const count=()=>kind==='ha'?2:3;

 let passwordTargets=[],passwordHash='',passwordInfo='',passwordBusy=false;
 async function loadPasswords(){
  const response=await fetch('api/wizard/password-targets',{credentials:'same-origin',cache:'no-store'});
  const data=await response.json();
  if(!response.ok||data.error)throw Error(data.error||'Passwortverwaltung nicht erreichbar');
  passwordTargets=data.targets||[];passwordHash=data.sip_core_hash||'';
 }
 function passwordForm(){
  const sip=passwordTargets.filter(x=>x.kind==='sip_core');
  const pjsip=passwordTargets.filter(x=>x.kind==='pjsip');
  const oneGroup=(type,list)=>{
   const files=type==='sip_core'?['sip_core']:[...new Set(list.map(t=>t.file))];
   return files.map(file=>{
    const rows=list.filter(t=>type==='sip_core'||t.file===file);
    const caption=type==='sip_core'?'SIP Core (auch manuell eingetragene Benutzer)':'Asterisk PJSIP · '+file;
    return '<section class="wiz-note"><h4>'+esc(caption)+'</h4>'+
     '<p>'+(type==='sip_core'?'Alle in der aktiven SIP-Core-Konfiguration vorhandenen Nebenstellen sind auswählbar – auch wenn Benutzer und Passwort manuell in YAML eingetragen wurden. ':'')+'Bestehende Passwörter werden niemals angezeigt. Nur markierte und bearbeitbare Teilnehmer ändern.</p>'+
     '<label class="wiz-check"><input type="checkbox" data-action="password-all" data-kind="'+esc(type)+'" data-file="'+esc(file)+'"/> Alle bearbeitbaren auswählen</label>'+
     rows.map(x=>'<label class="wiz-check"><input type="checkbox" data-pw-target="'+esc(type)+'" data-pw-file="'+esc(file)+'" value="'+esc(x.number)+'" '+(!x.editable?'disabled ':'')+'/> '+esc(x.number+' · '+x.name)+(x.configured?' · Passwort vorhanden':' · Passwort fehlt')+(x.imported_auth?' · Auth importiert (erweiterte Konfiguration bleibt erhalten)':'')+(x.editable?'':' · nicht bearbeitbar: '+esc(x.reason||'Mehrdeutige Konfiguration'))+'</label>').join('')+
     '<button type="button" class="primary" data-action="password-apply" data-kind="'+esc(type)+'" data-file="'+esc(file)+'">Für markierte Teilnehmer setzen</button></section>';
   }).join('');
  };
  return '<div class="wiz-head"><h2>Passwörter verwalten</h2><button type="button" data-action="close">✕</button></div>'+
   '<p>Individuell: einen Teilnehmer markieren. Gemeinsames Passwort: mehrere Teilnehmer markieren. Cloud-Konten werden beim externen Anbieter verwaltet und sind ausgeschlossen.</p>'+
   '<div class="wiz-grid"><label>Neues SIP-Passwort (12–128 Zeichen)<input id="wizPassword" type="password" autocomplete="new-password" spellcheck="false"/></label><div><button type="button" data-action="password-generate">Sicheres Passwort erzeugen</button><label class="wiz-check"><input type="checkbox" data-action="password-show"/> Anzeigen</label></div></div>'+
   '<p class="wiz-note">Änderungen erfolgen pro SIP Core bzw. PJSIP-Datei getrennt mit Sicherheitsprüfung und Backup. PJSIP benötigt anschließend einen bewussten Reload. Telefon-Apps müssen das neue Passwort erhalten.</p>'+
   oneGroup('sip_core',sip)+oneGroup('pjsip',pjsip)+
   '<p class="'+(passwordInfo.startsWith('Fehler')?'wiz-error':'wiz-ok')+'" role="status">'+esc(passwordInfo)+'</p>'+
   '<div class="wiz-actions"><button type="button" data-action="home">Zurück zur Übersicht</button></div>';
 }
 async function changePasswords(button){
  if(passwordBusy)return;
  const password=dialog.querySelector('#wizPassword')?.value||'';
  const type=button.dataset.kind,file=button.dataset.file;
  const selected=[...dialog.querySelectorAll('input[data-pw-target]:checked')].filter(el=>el.dataset.pwTarget===type&&el.dataset.pwFile===file).map(el=>el.value);
  if(!selected.length){passwordInfo='Fehler: Bitte Teilnehmer auswählen.';dialog.querySelector('[role=status]').textContent=passwordInfo;return;}
  if(password.length<12||password.length>128||/[\s;#]/.test(password)){passwordInfo='Fehler: Das Passwort braucht 12–128 Zeichen ohne Leerzeichen, # oder Semikolon.';dialog.querySelector('[role=status]').textContent=passwordInfo;return;}
  if(!confirm('Passwörter für '+selected.join(', ')+' ('+type+(file==='sip_core'?'':' / '+file)+') ändern? Die bisherigen Passwörter werden ungültig.'))return;
  passwordBusy=true;button.disabled=true;
  try{
   const body={kind:type,numbers:selected,password,confirm:'PASSWOERTER AENDERN',active_hash:passwordHash};
   if(type==='pjsip'){
    const row=passwordTargets.find(t=>t.kind===type&&t.file===file);
    body.file=file;body.file_hash=row?.file_hash;
   }
   const response=await fetch('api/wizard/password-rotate',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   const data=await response.json();
   if(!response.ok||data.error)throw Error(data.error||'Änderung fehlgeschlagen');
   passwordInfo=data.message||'Passwort geändert.';
   dialog.querySelector('#wizPassword').value='';
   await loadPasswords();
   dialog.innerHTML=passwordForm();
  }catch(err){
   passwordInfo='Fehler: '+err.message;
   const status=dialog.querySelector('[role=status]');if(status)status.textContent=passwordInfo;
  }finally{passwordBusy=false;button.disabled=false;}
 }

 let haChoices={ha_users:[],entities:{},streams:[]},haEntities=[];
 const entityTypes={
  browser_mod_entity:['sensor','binary_sensor'],
  tuer_entity:['lock','switch','button','input_button','script','cover'],
  licht_entity:['light','switch'],
  klingel_entity:['binary_sensor','event','input_boolean','sensor'],
  ring_player:['media_player']
 };
 const datalistId=key=>'wiz-list-'+key;
 function suggested(key){
  if(key==='ha_benutzer')return (haChoices.ha_users||[]).map(x=>({value:x.value,label:x.label||x.value}));
  if(key==='stream')return haChoices.streams||[];
  const map={tuer_entity:'tuer',licht_entity:'licht',klingel_entity:'klingel'};
  if(map[key])return haChoices.entities?.[map[key]]||[];
  return haEntities.filter(e=>{
   const domain=e.entity_id?.split('.')[0];
   if(!(entityTypes[key]||[]).includes(domain))return false;
   return key!=='browser_mod_entity'||(/browser|visibility|sichtbar|presence|anwesenheit/i.test(e.entity_id+' '+(e.name||'')));
  }).map(e=>({value:e.entity_id,label:e.name||e.entity_id}));
 }
 function suggestionLists(){
  return [...Object.keys(entityTypes),'ha_benutzer','stream'].map(key=>
   '<datalist id="'+datalistId(key)+'">'+suggested(key).map(x=>'<option value="'+esc(x.value)+'" label="'+esc(x.label||x.value)+'"></option>').join('')+'</datalist>'
  ).join('');
 }
 async function fetchSuggestions(){
  const requests=await Promise.allSettled([
   fetch('api/anlage/auswahl',{credentials:'same-origin',cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HA Auswahl HTTP '+r.status);return r.json();}),
   fetch('api/entities',{credentials:'same-origin',cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HA Entitäten HTTP '+r.status);return r.json();})
  ]);
  haChoices=requests[0].status==='fulfilled'?requests[0].value:{ha_users:[],entities:{},streams:[]};
  haEntities=requests[1].status==='fulfilled'&&requests[1].value.available?requests[1].value.entities||[]:[];
 }

 const normalizeSearch=v=>String(v??'').toLocaleLowerCase('de').normalize('NFKD').replace(/[\u0300-\u036f]/g,'');
 const maxSuggestions=12;
 function showMatches(input){
  const key=input.dataset.field;
  if(!key||!['ha_benutzer','stream',...Object.keys(entityTypes)].includes(key))return;
  const list=input.parentElement.querySelector('.wiz-autolist');
  if(!list)return;
  const query=normalizeSearch(input.value.trim());
  const matches=suggested(key).filter(x=>!query||normalizeSearch(x.value+' '+(x.label||'')).includes(query)).slice(0,maxSuggestions);
  list.innerHTML=matches.map((x,i)=>'<button type="button" role="option" aria-selected="'+(i===0)+'" class="wiz-auto-option" data-value="'+esc(x.value)+'">'+esc(x.value)+(x.label&&x.label!==x.value?'<small> · '+esc(x.label)+'</small>':'')+'</button>').join('');
  list.hidden=!matches.length;
  input.setAttribute('aria-expanded',String(!!matches.length));
 }
 function hideMatches(input){
  const list=input?.parentElement?.querySelector('.wiz-autolist');
  if(list)list.hidden=true;
  if(input)input.setAttribute('aria-expanded','false');
 }
 const label=(name,key,value,opts={})=>'<label>'+esc(name)+(opts.select?'<select data-field="'+esc(key)+'">'+opts.select.map(([v,t])=>'<option value="'+esc(v)+'" '+(String(value??'')===String(v)?'selected':'')+'>'+esc(t)+'</option>').join('')+'</select>':'<input data-field="'+esc(key)+'" '+(suggested(key).length?'autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" ':'')+(opts.type?'type="'+opts.type+'" ':'')+'value="'+esc(value??'')+'" '+(opts.placeholder?'placeholder="'+esc(opts.placeholder)+'" ':'')+'/>'+(suggested(key).length?'<div class="wiz-autolist" role="listbox" hidden></div>':''))+'</label>';
 const check=(name,key,val)=>'<label class="wiz-check"><input type="checkbox" data-field="'+esc(key)+'" '+(val?'checked':'')+'/> '+esc(name)+'</label>';
 const options=(arr,empty='Neu anlegen')=>'<option value="">'+esc(empty)+'</option>'+arr.map(x=>'<option value="'+esc(x.value)+'" '+(x.value===selected?'selected':'')+'>'+esc(x.text)+'</option>').join('');
 const participants=()=>model.teilnehmer.filter(t=>t.typ!=='kamera'&&(kind==='cloud'?t.typ==='extern_ziel':kind==='participant'?t.typ!=='extern_ziel':true));
 const groups=()=>model.wege;
 const getItems=()=>kind==='group'?groups():participants();
 function selectDraft(){
  original=getItems().find(x=>(kind==='group'?x.nummer:ref(x))===selected)||null;
  draft=original?structuredClone(original):kind==='group'?{nummer:'',name:'',von:[],ziele:[],klingelzeit:20,kontexte:[],ersetzen:false,mitglieder_rufen:false}:{nummer:'',name:'',typ:kind==='cloud'?'extern_ziel':'sip_telefon',ha_benutzer:'',endpoint:kind==='cloud'?'linphone-cloud':'',sip_adresse:'',eingang:kind==='cloud'?'linphone-in':'',stream:'',video_codecs:'auto',qualify_frequency:'30',browser_mod_entity:'',realm:'',anruf_ziele:null,angerufen_von:null,darf_anrufen:[],quell_ips:[],faehigkeiten:{kamerabild:false,video_im_anruf:false,ios:false,tuer_oeffnen:false}};
  cloudPreset=kind==='cloud'&&original&&!/^([a-z0-9_.-]+)@sip\.linphone\.org$/i.test(String(original.sip_adresse||'').replace(/^sip:/i,''))?'custom':'linphone';
  saved=false;
 }
 function fieldValue(el){return el.type==='checkbox'?el.checked:el.value.trim();}
 function collect(){
  if(!draft)return;
  if(kind==='cloud'&&step===0&&cloudPreset==='linphone'){
   const username=dialog.querySelector('#wizLinphoneUsername')?.value.trim();
   if(username!==undefined){draft.sip_adresse=username?username+'@sip.linphone.org':'';if(!draft.name)draft.name=username;}
  }
  dialog.querySelectorAll('[data-field]').forEach(el=>{const k=el.dataset.field,v=fieldValue(el);if(k.startsWith('fae.')){draft.faehigkeiten=draft.faehigkeiten||{};draft.faehigkeiten[k.slice(4)]=v;}else if(k==='quell_ips')draft[k]=v.split(/[\s,;]+/).filter(Boolean);else if(k==='klingelzeit')draft[k]=Number(v);else if(k==='anruf_ziele'||k==='angerufen_von')draft[k]=v? v.split(/[\s,;]+/).filter(Boolean):null;else if(k==='darf_anrufen')draft[k]=v?v.split(/[\s,;]+/).filter(Boolean):[];else draft[k]=v;});
  if(kind==='group'){for(const zone of ['von','ziele'])draft[zone]=[...dialog.querySelectorAll('[data-member="'+zone+'"]:checked')].map(e=>e.value);}
 }
 function members(zone,values){return '<div class="wiz-members">'+model.teilnehmer.filter(t=>t.typ!=='kamera'&&ref(t)).map(t=>'<label><input type="checkbox" data-member="'+zone+'" value="'+esc(ref(t))+'" '+((values||[]).includes(ref(t))?'checked':'')+'/> '+esc((t.nummer?t.nummer+' · ':'')+t.name)+'</label>').join('')+'</div>';}
 function form(){
  if(kind==='ha')return '<div class="wiz-grid">'+(step===0?
   label('Anlagenname','name',draft.name)+label('Kunde','kunde',draft.kunde)+label('Nummern von','nummer_von',draft.nummer_von)+label('Nummern bis','nummer_bis',draft.nummer_bis):
   label('LAN-IP','lan_ip',draft.lan_ip)+label('Tailscale-IP','tailscale_ip',draft.tailscale_ip)+label('Tailscale-Name','tailscale_name',draft.tailscale_name)+label('go2rtc HTTPS URL','go2rtc_https_url',draft.go2rtc_https_url))+'</div>';
  if(kind==='group')return step===0?'<div class="wiz-grid">'+label('Rufnummer','nummer',draft.nummer)+label('Name','name',draft.name)+label('Klingelzeit (5–300 s)','klingelzeit',draft.klingelzeit,{type:'number'})+'</div>'+check('Vorhandene Rufgruppe bei Übernahme ersetzen','ersetzen',draft.ersetzen)+check('Mitglieder dürfen Gruppe anrufen','mitglieder_rufen',draft.mitglieder_rufen):step===1?'<div class="wiz-grid"><section><b>Darf die Gruppe anrufen</b>'+members('von',draft.von)+'</section><section><b>Klingelt bei</b>'+members('ziele',draft.ziele)+'</section></div>':'<p class="wiz-note">Speichern legt die Rufgruppe im Anlagenmodell ab. Für die aktive Telefonanlage anschließend „Erzeugen & Übernehmen“ mit Vorschau und Backup verwenden.</p>';
  if(step===0)return '<div class="wiz-grid">'+label('Nummer (2–8 Ziffern, bei Cloud optional)','nummer',draft.nummer)+label('Name','name',draft.name)+
   (kind==='participant'?label('Teilnehmertyp','typ',draft.typ,{select:[['sip_telefon','SIP-Telefon (Asterisk)'],['ha_geraet','HA-Benutzer (SIP Core)'],['tuerstation','Türstation (SIP)']]}):'')+
   (kind==='cloud'?'<label>Anbieter<select id="wizCloudProvider"><option value="linphone" '+(cloudPreset==='linphone'?'selected':'')+'>Linphone (sip.linphone.org)</option><option value="custom" '+(cloudPreset==='custom'?'selected':'')+'>Anderer SIP-Anbieter / manuell</option></select></label>'+
    (cloudPreset==='linphone'?'<label>Linphone-Benutzername<input id="wizLinphoneUsername" autocomplete="username" value="'+esc(String(draft.sip_adresse||'').replace(/^sip:/i,'').replace(/@sip\.linphone\.org$/i,''))+'" placeholder="benutzername" /></label><p class="wiz-note">SIP-Adresse: <strong id="wizLinphoneAddress">'+esc(draft.sip_adresse||'benutzername@sip.linphone.org')+'</strong>. Ausgehender Endpoint <code>linphone-cloud</code>, Eingang <code>linphone-in</code>. Bestehende Konten werden nicht überschrieben. Die Vorlage erstellt kein Linphone-Konto und meldet es nicht automatisch an.</p>':label('SIP-Adresse','sip_adresse',draft.sip_adresse,{placeholder:'name@anbieter.example'})):label('HA-Benutzer (SIP Core)','ha_benutzer',draft.ha_benutzer))+'</div>';
  if(step===1){
   const type=draft.typ;
   const cloud=kind==='cloud', ha=type==='ha_geraet', door=type==='tuerstation';
   const video=label('Video-Codecs','video_codecs',draft.video_codecs||'auto',{select:[['auto','Automatisch'],['vp8','Nur VP8'],['h264','Nur H.264'],['vp9','Nur VP9'],['vp8,h264','VP8 + H.264'],['none','Kein Video']]});
   const checks=check('Videoanruf erlauben','fae.video_im_anruf',draft.faehigkeiten?.video_im_anruf);
   // Cloud identities are remote SIP destinations, not local HA devices.
   // Their browser visibility, media playback, local OPTIONS/AOR and camera controls
   // are configured (if needed) on the actual receiving participant.
   if(cloud)return '<div class="wiz-grid">'+
    label('Ausgehender SIP-Anschluss','endpoint',draft.endpoint,{placeholder:'linphone-cloud'})+
    label('Eingehender SIP-Anschluss','eingang',draft.eingang,{placeholder:'linphone-in'})+
    video+label('Zugelassene Quell-IPs / Netze (optional)','quell_ips',(draft.quell_ips||[]).join(', '),{placeholder:'100.64.1.2/32'})+
    '</div>'+checks+'<p class="wiz-note">Cloud-Konten sind externe Anrufziele. Browser Mod, Klingeltonausgabe, Türöffner, lokale SIP-OPTIONS-Prüfung und HA-Stream werden deshalb hier nicht benötigt. Quell-IPs betreffen den eingehenden Anschluss, nicht deinen Linphone-Benutzernamen.</p>';
   const local=label('OPTIONS – Erreichbarkeitsprüfung (s) · 0 s = deaktiviert','qualify_frequency',draft.qualify_frequency??'30',{placeholder:'Standard: 30 s'});
   const browser=ha?label('Browser-Mod-Status (zentral, optional)','browser_mod_entity',draft.browser_mod_entity):'';
   const doorEntities=door?(label('Türöffner-Entität','tuer_entity',draft.tuer_entity)+label('Licht-Entität','licht_entity',draft.licht_entity)+label('Klingel-Entität','klingel_entity',draft.klingel_entity)):'';
   const ring=ha?(label('Klingelton-Ausgabe','ring_output',draft.ring_output||'standard',{select:[['standard','Standard'],['media_player','HA-Mediaplayer']]})+
    ((draft.ring_output==='media_player')?label('Klingelton-Mediaplayer','ring_player',draft.ring_player):'')):'';
   return '<div class="wiz-grid">'+
    (ha?label('go2rtc-Stream / Gerätekennung (optional)','stream',draft.stream):label('SIP-Endpoint','endpoint',draft.endpoint,{placeholder:'Nebenstellennummer'}))+
    local+video+(door?label('Kamerastream (go2rtc)','stream',draft.stream):'')+browser+doorEntities+ring+
    (door?label('Realm / Domain (optional)','realm',draft.realm):'')+'</div>'+
    checks+(ha?check('Kamerabild im HA-Popup','fae.kamerabild',draft.faehigkeiten?.kamerabild)+check('iOS-Gerät','fae.ios',draft.faehigkeiten?.ios)+check('Türöffner anzeigen','fae.tuer_oeffnen',draft.faehigkeiten?.tuer_oeffnen):
    door?check('Kamerabild anbieten','fae.kamerabild',draft.faehigkeiten?.kamerabild):'')+aaForm();
  }
  return '<div class="wiz-grid">'+label('Darf anrufen (Nummern, leer = uneingeschränkt bei lokalen Teilnehmern)',''+(kind==='cloud'?'darf_anrufen':'anruf_ziele'),(kind==='cloud'?draft.darf_anrufen:draft.anruf_ziele)?.join(', ')||'')+label('Darf angerufen werden von (Nummern)','angerufen_von',draft.angerufen_von?.join(', ')||'')+'</div><p class="wiz-note">Leer bedeutet bei lokalen Anrufrechten keine Einschränkung. Bei Cloud-Konten werden die ausgehenden Freigaben explizit als Nummernliste gespeichert. Änderungen sind erst nach „Erzeugen & Übernehmen“ in Asterisk aktiv.</p>';
 }

 let aaActive=null,aaDraft=null,aaChanged=false,aaError='';
 async function loadWizardAutoAnswer(){
  const r=await fetch('api/sip-core/active',{credentials:'same-origin',cache:'no-store'});
  const d=await r.json();if(!r.ok||d.error)throw Error(d.error||'SIP Core nicht erreichbar');
  aaActive=d;aaDraft=null;aaChanged=false;aaError='';
 }
 function aaForm(){
  if(kind!=='participant'||draft?.typ!=='ha_geraet')return '';
  const number=String(draft.nummer||'');
  const users=aaActive?.users||[];
  const configured=users.some(u=>String(u.extension)===number);
  const selected=(aaActive?.auto_answer_by_extension||{})[number]||[];
  const checked=aaDraft?aaDraft.enabled:!!selected.length;
  const allowed=aaDraft?aaDraft.allowed:selected;
  return '<section class="wiz-note"><b>Auto Answer – SIP Core</b>'+
   '<p>Nur für SIP-Core-Geräte mit Smartify-Popup. Die Regel gilt für die angerufene Nebenstelle '+esc(number||'–')+'. Globale automatische Annahme wird deaktiviert.</p>'+
   (!configured?'<p class="wiz-error">Nebenstelle noch nicht in SIP Core vorhanden. Zuerst SIP-Core-Teilnehmer anlegen und dann hier erneut laden.</p>':
    '<label class="wiz-check"><input type="checkbox" id="wizAaEnabled" '+(checked?'checked':'')+'/> Auto Answer aktivieren</label>'+
    '<div class="wiz-members">'+users.filter(u=>String(u.extension)!==number).map(u=>'<label><input type="checkbox" data-aa-caller="'+esc(u.extension)+'" '+(allowed.map(String).includes(String(u.extension))?'checked':'')+' '+(!checked?'disabled':'')+'/> '+esc(u.extension+' · '+(u.display_name||u.ha_username||''))+'</label>').join('')+'</div>'+
    '<button type="button" data-action="aa-preview">Änderung prüfen</button>'+
    (aaChanged?'<button type="button" data-action="aa-apply" class="primary">Geprüfte Regel in SIP Core übernehmen</button>':''))+
   '<p role="status">'+esc(aaError)+'</p></section>';
 }
 async function aaPreview(){
  collect();
  const number=String(draft.nummer||'');
  const enabled=!!dialog.querySelector('#wizAaEnabled')?.checked;
  const allowed=[...dialog.querySelectorAll('[data-aa-caller]:checked')].map(x=>x.dataset.aaCaller);
  const r=await fetch('api/sip-core/auto-answer/stage',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:aaActive.content,extension:number,enabled,allowed})});
  const d=await r.json();if(!r.ok||d.error)throw Error(d.error||'Auto Answer konnte nicht geprüft werden');
  aaDraft={content:d.content,enabled,allowed:d.allowed};aaChanged=true;
  const diffResponse=await fetch('api/sip-core/diff',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:d.content})});
  const diff=await diffResponse.json();if(!diffResponse.ok||diff.error)throw Error(diff.error||'Vergleich fehlgeschlagen');
  aaDraft.hash=diff.active_hash;
  aaError='Prüfung abgeschlossen. '+(diff.changed?'SIP-Core-Regel kann übernommen werden.':'Keine Änderung notwendig.')+' '+(diff.warnings||[]).join('; ');
  render();
 }
 async function aaApply(){
  if(!aaDraft?.hash)throw Error('Zuerst Änderung prüfen.');
  if(!confirm('Auto Answer für Nebenstelle '+draft.nummer+' in SIP Core aktiv übernehmen? Bestehende Konfiguration wird gesichert.'))return;
  const r=await fetch('api/sip-core/apply',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:aaDraft.content,active_hash:aaDraft.hash,confirm:true})});
  const d=await r.json();if(!r.ok||d.error)throw Error(d.error||'Übernahme fehlgeschlagen');
  await loadWizardAutoAnswer();aaError='Auto Answer in SIP Core übernommen.';render();
 }
 function advancedTools(){
  if(kind==='ha')return [['anlageSetup','Anlage und Netzwerk']];
  if(kind==='group')return [['rufgruppen','Rufgruppen-Manager'],['verbindungen','Anrufrechte'],['erzeugen','Vorschau, Backup und Übernahme'],['live','Live-Status']];
  return [
   ['endpoint','PJSIP / AOR / Auth / Audio- und Video-Codecs'],
   ...(draft?.typ==='ha_geraet'?[['draft','SIP-Core-Benutzer, Passwort und Auto Answer']]:[]),
   ...(kind==='cloud'?[['inbound','Cloud-Konten und SIP-Eingänge']]:[]),
   ...(draft?.typ==='tuerstation'?[['device','Türstation und Video'],['callercams','Kameras pro Anrufer']]:[]),
   ['verbindungen','Anrufrechte'],['live','SIP-Status prüfen'],
   ['erzeugen','Vorschau, Backup und Übernahme']
  ];
 }
 function toolButtons(){
  return '<section class="wiz-note"><b>Weiterführende Einrichtung</b><p>Die folgenden Funktionen nutzen die bestehenden geprüften Manager-Editoren. Änderungen dort müssen separat geprüft und übernommen werden.</p><div class="wiz-grid">'+advancedTools().map(([id,name])=>'<button type="button" data-editor="'+esc(id)+'">'+esc(name)+'</button>').join('')+'</div></section>';
 }
 function render(message='',error=false){
  if(kind==='password'){dialog.innerHTML=passwordForm();return;}
  const header='<div class="wiz-head"><h2>Einrichtungsassistent</h2><button type="button" data-action="close" aria-label="Schließen">✕</button></div>';
  if(!kind){dialog.innerHTML=header+'<p>Was möchtest du direkt einrichten oder bearbeiten?</p>'+Object.entries(sections).map(([k,v])=>'<button type="button" class="wiz-choice" data-kind="'+k+'">'+esc(v)+'</button>').join('')+'<p class="wiz-note">Bestehende Einträge werden gezielt geändert. Speichern übernimmt nur das Anlagenmodell, nicht die laufende Asterisk-Konfiguration.</p>';return;}
  const select=kind==='ha'?'':step===0?'<label>Vorhandenen Eintrag bearbeiten oder neu anlegen<select id="wizSelect">'+options(getItems().map(t=>({value:kind==='group'?t.nummer:ref(t),text:((t.nummer||'')+' '+t.name).trim()+' · '+(kind==='group'?'Rufgruppe':({ha_geraet:'HA-User',sip_telefon:'SIP',tuerstation:'SIP-Türstation',extern_ziel:'Cloud'}[t.typ]||'Sonstige'))})))+'</select></label>':'';
  const steps=count();
  dialog.innerHTML=header+suggestionLists()+'<h3>'+esc(sections[kind])+'</h3><p>Schritt '+(step+1)+' von '+steps+'</p><div class="wiz-progress">'+Array.from({length:steps},(_,i)=>'<span class="'+(i<=step?'active':'')+'"></span>').join('')+'</div>'+select+form()+
   '<p id="wizMessage" class="'+(error?'wiz-error':'wiz-ok')+'" role="status">'+esc(message)+'</p>'+
   '<div class="wiz-actions"><button type="button" data-action="home">Bereiche</button><div><button type="button" data-action="back" '+(step===0?'disabled':'')+'>Zurück</button> <button type="button" class="primary" data-action="next">'+(step===steps-1?'Validieren & speichern':'Weiter')+'</button> '+(step===steps-1?'<button type="button" data-action="wizard-apply">Erzeugen &amp; Übernehmen …</button>':'')+'</div></div>'+
   toolButtons()+
   '<p class="wiz-note">Kein automatischer Asterisk-Reload. Nach dem Speichern Vorschau, Backup und Übernahme separat prüfen. Bestehende SIP-Zugangsdaten bleiben unberührt.</p>';
  if(step===0&&kind!=='ha')$('wizSelect').value=selected;
 }
 function valid(){
  if(kind==='ha')return '';
  if(!draft.name?.trim())return 'Bitte einen Namen angeben.';
  if(draft.nummer&&!/^\d{2,8}$/.test(draft.nummer))return 'Nummer: 2–8 Ziffern erforderlich.';
  if(kind==='group'){if(!draft.nummer)return 'Die Rufgruppe benötigt eine Rufnummer.';if(!Number.isInteger(draft.klingelzeit)||draft.klingelzeit<5||draft.klingelzeit>300)return 'Klingelzeit muss 5–300 Sekunden betragen.';if(!draft.ziele.length)return 'Mindestens ein Klingelziel wählen.';}
  else{
   if(kind==='participant'&&!/^\d{2,8}$/.test(draft.nummer))return 'Teilnehmernummer: 2–8 Ziffern erforderlich.';
   if(kind==='cloud'&&cloudPreset==='linphone'&&!/^[a-z0-9_.-]+@sip\.linphone\.org$/.test(draft.sip_adresse||''))return 'Linphone-Benutzername: nur Kleinbuchstaben, Zahlen, Punkt, _ oder - verwenden.';
   if(kind==='cloud'&&!/^[A-Za-z0-9_.+!~*()%-]{1,64}@[A-Za-z0-9.-]{1,253}(:\d{1,5})?$/.test((draft.sip_adresse||'').replace(/^sip:/i,'')))return 'Gültige Cloud-SIP-Adresse angeben (name@server).';
   if(kind==='cloud'&&!draft.endpoint)return 'Für Cloud-Konten einen ausgehenden Anschluss wählen.';
   if(draft.qualify_frequency!==''&&draft.qualify_frequency!=null&&(!/^\d+$/.test(String(draft.qualify_frequency))||Number(draft.qualify_frequency)>3600))return 'OPTIONS muss leer oder 0–3600 Sekunden sein.';
   if(draft.faehigkeiten?.kamerabild&&!draft.stream)return 'Für Kamerabild einen Streamnamen angeben.';
  }
  const numbers=new Set([...model.teilnehmer.filter(t=>t!==original).map(t=>t.nummer),...model.wege.filter(w=>w!==original).map(w=>w.nummer)].filter(Boolean));
  if(draft.nummer&&numbers.has(draft.nummer))return 'Diese Nummer ist bereits vergeben.';
  return '';
 }
 async function load(){
  const response=await fetch('api/anlage',{credentials:'same-origin',cache:'no-store'});const data=await response.json();
  if(!response.ok||data.error)throw Error(data.error||'Laden fehlgeschlagen');
  model=data.model;hash=data.hash;
 }
 async function save(){
  const error=valid();if(error){render(error,true);return;}
  // Recheck the hash; never silently overwrite another editor's changes.
  const current=await fetch('api/anlage',{credentials:'same-origin',cache:'no-store'});const data=await current.json();
  if(!current.ok||data.error)throw Error(data.error||'Konfiguration konnte nicht geprüft werden');
  if(data.hash!==hash)throw Error('Die Konfiguration wurde zwischenzeitlich geändert. Assistent schließen und neu öffnen; nichts wurde überschrieben.');
  const copy=structuredClone(model);
  if(kind==='ha')copy.anlage=structuredClone(draft);
  else{
   const list=kind==='group'?copy.wege:copy.teilnehmer;
   const index=original?(kind==='group'?model.wege:model.teilnehmer).indexOf(original):-1;
   if(index>=0)list[index]=structuredClone(draft);else list.push(structuredClone(draft));
   // Preserve references when a previously numbered entry is renamed.
   if(original&&kind!=='group'&&ref(original)!==ref(draft)){
    for(const g of copy.wege)for(const z of ['von','ziele'])g[z]=(g[z]||[]).map(r=>r===ref(original)?ref(draft):r);
    for(const t of copy.teilnehmer)for(const k of ['anruf_ziele','angerufen_von','darf_anrufen'])if(Array.isArray(t[k]))t[k]=t[k].map(r=>r===original.nummer?draft.nummer:r);
   }
  }
  const response=await fetch('api/anlage',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:copy,hash})});
  const result=await response.json();if(!response.ok||result.error)throw Error(result.error||'Speichern fehlgeschlagen');
  model=result.model;hash=result.hash;saved=true;
  if(kind!=='ha'){selected=kind==='group'?draft.nummer:ref(draft);selectDraft();}
  window.dispatchEvent(new CustomEvent('smartify-model-updated',{detail:{source:'setup-wizard'}}));
  // Other editor's in-memory state must be reloaded rather than silently overwritten.
  render('Gespeichert. Bitte vorhandene Editoren vor weiteren Änderungen neu laden. Für Asterisk: „Erzeugen & Übernehmen“ verwenden.');
 }
 async function open(){
  // Show the dialog before loading: a slow/failed HA Ingress request must never look like an inert button.
  kind='';step=0;selected='';draft=null;
  dialog.innerHTML='<div class="wiz-head"><h2>Einrichtungsassistent</h2><button type="button" data-action="close">✕</button></div><p role="status">Anlagenmodell wird geladen …</p>';
  try {
   if(!dialog.open) dialog.showModal();
  } catch(e) {
   dialog.setAttribute('open','');
  }
  try {await load();await fetchSuggestions();render();}
  catch(e) {dialog.innerHTML='<div class="wiz-head"><h2>Einrichtungsassistent</h2><button type="button" data-action="close">✕</button></div><p class="wiz-error" role="alert">Konfiguration konnte nicht geladen werden: '+esc(e.message)+'</p><button type="button" data-action="retry">Erneut versuchen</button>';}
 }
 button.addEventListener('click',open);
 dialog.addEventListener('input',e=>{
  if(e.target.id==='wizLinphoneUsername'){
   const value=e.target.value.trim();draft.sip_adresse=value?value+'@sip.linphone.org':'';
   const preview=dialog.querySelector('#wizLinphoneAddress');if(preview)preview.textContent=draft.sip_adresse||'benutzername@sip.linphone.org';
   return;
  }
  if(e.target.matches('input[data-field]'))showMatches(e.target);
 });
 dialog.addEventListener('focusin',e=>{if(e.target.matches('input[data-field]'))showMatches(e.target);});
 dialog.addEventListener('keydown',e=>{
  const input=e.target.closest('input[data-field]');
  if(!input)return;
  const list=input.parentElement.querySelector('.wiz-autolist');
  if(!list||list.hidden)return;
  const opts=[...list.querySelectorAll('.wiz-auto-option')];
  if(e.key==='Escape'){hideMatches(input);e.preventDefault();return;}
  if(!['ArrowDown','ArrowUp','Enter'].includes(e.key)||!opts.length)return;
  const active=opts.findIndex(x=>x.getAttribute('aria-selected')==='true');
  if(e.key==='Enter'){e.preventDefault();(opts[Math.max(0,active)]).click();return;}
  e.preventDefault();
  const next=(active+(e.key==='ArrowDown'?1:-1)+opts.length)%opts.length;
  opts.forEach((x,i)=>x.setAttribute('aria-selected',String(i===next)));
  opts[next].scrollIntoView({block:'nearest'});
 });
 dialog.addEventListener('pointerdown',e=>{
  const choice=e.target.closest('.wiz-auto-option');
  if(!choice)return;
  e.preventDefault();
  const input=choice.parentElement.parentElement.querySelector('input[data-field]');
  if(input){input.value=choice.dataset.value;input.focus();hideMatches(input);input.dispatchEvent(new Event('change',{bubbles:true}));}
 });
 dialog.addEventListener('click',e=>{
  if(e.target.closest('.wiz-auto-option,.wiz-autolist'))return;
  if(!e.target.matches('input[data-field]'))dialog.querySelectorAll('.wiz-autolist').forEach(x=>x.hidden=true);
 });
 dialog.addEventListener('change',e=>{
  if(e.target.id==='wizAaEnabled'){dialog.querySelectorAll('[data-aa-caller]').forEach(x=>x.disabled=!e.target.checked);aaChanged=false;}
  if(e.target.matches('[data-aa-caller]'))aaChanged=false;
  if(e.target.dataset.action==='password-show'){const pw=dialog.querySelector('#wizPassword');if(pw)pw.type=e.target.checked?'text':'password';}
  if(e.target.dataset.action==='password-all'){dialog.querySelectorAll('input[data-pw-target]').forEach(input=>{if(input.dataset.pwTarget===e.target.dataset.kind&&input.dataset.pwFile===e.target.dataset.file&&!input.disabled)input.checked=e.target.checked;});}
 });
 dialog.addEventListener('change',e=>{
  if(e.target.id==='wizCloudProvider'){
   collect();cloudPreset=e.target.value;
   if(cloudPreset==='linphone'){
    if(!/@sip\.linphone\.org$/i.test(draft.sip_adresse||''))draft.sip_adresse='';
    if(!original){draft.endpoint=draft.endpoint||'linphone-cloud';draft.eingang=draft.eingang||'linphone-in';}
   }
   render();return;
  }
 });
 dialog.addEventListener('change',e=>{if(e.target.id==='wizSelect'){selected=e.target.value;selectDraft();render();}});
 dialog.addEventListener('click',async e=>{
  const b=e.target.closest('button');if(!b||busy)return;
  if(b.dataset.editor){
   const target=b.dataset.editor;
   if(!['anlageSetup','endpoint','draft','inbound','rufgruppen','verbindungen','erzeugen','live','device','callercams'].includes(target))return;
   if(!saved&&kind&&draft&&!confirm('Nicht gespeicherte Eingaben können beim Wechsel verloren gehen. Trotzdem den Editor öffnen?'))return;
   dialog.close();
   const tab=document.querySelector('[data-tab="'+target+'"]');
   if(tab)tab.click();else alert('Editor nicht verfügbar: '+target);
   return;
  }
  if(b.dataset.action==='close'){dialog.close();return;}
  if(b.dataset.action==='retry'){open();return;}
  if(b.dataset.kind&&!b.dataset.action){kind=b.dataset.kind;step=0;selected='';if(kind==='group'){await showRingPanel();return;}if(kind==='password'){passwordInfo='';try{await loadPasswords();}catch(e){passwordInfo='Fehler: '+e.message;}render();return;}if(kind==='ha'){draft=structuredClone(model.anlage);original=null;}else selectDraft();render();return;}
  if(b.dataset.action==='home'){restoreApplyPanel();if(kind==='group')restoreRingPanel();else if(kind!=='password')collect();kind='';step=0;render();return;}
  if(b.dataset.action==='password-generate'){const alphabet='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!$%&*+-_=?.';const bytes=new Uint32Array(24);crypto.getRandomValues(bytes);const pass=[...bytes].map(v=>alphabet[v%alphabet.length]).join('');const el=dialog.querySelector('#wizPassword');if(el){el.value=pass;el.type='text';}return;}
  if(b.dataset.action==='password-apply'){await changePasswords(b);return;}
  if(b.dataset.action==='wizard-apply'){b.disabled=true;try{await showWizardApply();}catch(err){restoreApplyPanel();render(err.message,true);}finally{b.disabled=false;}return;}
  if(b.dataset.action==='ring-preview'){b.disabled=true;try{await showRingApply();}catch(err){const status=dialog.querySelector('#wizRingApplyStatus');if(status)status.textContent='Fehler: '+err.message;}finally{b.disabled=false;}return;}
  if(b.dataset.action==='aa-preview'||b.dataset.action==='aa-apply'){try{if(b.dataset.action==='aa-preview')await aaPreview();else await aaApply();}catch(err){aaError='Fehler: '+err.message;render();}return;}
  if(b.dataset.action==='back'){restoreApplyPanel();collect();step=Math.max(0,step-1);render();return;}
  if(b.dataset.action==='next'){collect();if(step<count()-1){step++;if(kind==='participant'&&draft?.typ==='ha_geraet'&&step===1){try{await loadWizardAutoAnswer();}catch(err){aaActive=null;aaError='SIP Core: '+err.message;}}render();return;}
   busy=true;b.disabled=true;try{await save();}catch(err){render(err.message,true);}finally{busy=false;} }
 });
})();
