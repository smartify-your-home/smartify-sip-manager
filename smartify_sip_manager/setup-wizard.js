/* Smartify SIP Manager – direct model editor wizard.
 * Uses the existing /api/anlage model, optimistic hash locking, server validation.
 * Never applies Asterisk configuration or stores passwords. */
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ref=t=>t.nummer||(t.typ==='extern_ziel'&&t.sip_adresse?'sip:'+t.sip_adresse.replace(/^sip:/i,''):'')||t.endpoint||'';
 const sections={ha:'Home Assistant & System',participant:'SIP-Teilnehmer',cloud:'Cloud-Konto / externes SIP-Ziel',group:'Rufgruppe'};
 const style=document.createElement('style');
 style.textContent=`#setupWizard{width:min(760px,calc(100vw - 24px));max-width:760px;max-height:92vh;overflow:auto;padding:22px;border:1px solid var(--border,#888);border-radius:16px;background:var(--card-background-color,#fff);color:inherit;box-shadow:0 18px 60px #0006}#setupWizard::backdrop{background:#0009}#setupWizard .wiz-head,#setupWizard .wiz-actions{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}#setupWizard .wiz-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}#setupWizard label{display:flex;flex-direction:column;gap:5px;margin:9px 0;font-size:.95em}#setupWizard input:not([type=checkbox]),#setupWizard select{width:100%;box-sizing:border-box;padding:8px;min-width:0}#setupWizard .wiz-check{display:flex;flex-direction:row;align-items:center}#setupWizard .wiz-check input{width:auto}#setupWizard .wiz-choice{display:block;width:100%;text-align:left;margin:8px 0;padding:12px}#setupWizard .wiz-note{background:rgba(128,128,128,.1);border-radius:8px;padding:12px;line-height:1.5}#setupWizard .wiz-error{color:#d44;font-weight:600;white-space:pre-wrap}#setupWizard .wiz-ok{color:#178b78}#setupWizard .wiz-progress{display:flex;gap:5px;margin:12px 0}#setupWizard .wiz-progress span{height:5px;background:#8885;flex:1;border-radius:5px}#setupWizard .wiz-progress .active{background:#178b78}#setupWizard .wiz-members{border:1px solid #8885;border-radius:8px;padding:8px;max-height:190px;overflow:auto}#setupWizard .wiz-members label{display:flex;flex-direction:row;align-items:center;margin:5px 0}#setupWizard .wiz-actions{margin-top:18px}`;
 document.head.appendChild(style);
 const dialog=document.createElement('dialog');dialog.id='setupWizard';dialog.setAttribute('aria-label','Einrichtungsassistent');document.body.appendChild(dialog);
 const button=document.createElement('button');button.type='button';button.id='openSetupWizard';button.textContent='✨ Einrichtungsassistent';
 document.querySelector('.quick-actions')?.prepend(button);
 let kind='',step=0,model=null,hash=null,selected='',draft=null,original=null,saved=false,busy=false;
 const count=()=>kind==='ha'?2:3;
 const label=(name,key,value,opts={})=>'<label>'+esc(name)+(opts.select?'<select data-field="'+esc(key)+'">'+opts.select.map(([v,t])=>'<option value="'+esc(v)+'" '+(String(value??'')===String(v)?'selected':'')+'>'+esc(t)+'</option>').join('')+'</select>':'<input data-field="'+esc(key)+'" '+(opts.type?'type="'+opts.type+'" ':'')+'value="'+esc(value??'')+'" '+(opts.placeholder?'placeholder="'+esc(opts.placeholder)+'" ':'')+'/>')+'</label>';
 const check=(name,key,val)=>'<label class="wiz-check"><input type="checkbox" data-field="'+esc(key)+'" '+(val?'checked':'')+'/> '+esc(name)+'</label>';
 const options=(arr,empty='Neu anlegen')=>'<option value="">'+esc(empty)+'</option>'+arr.map(x=>'<option value="'+esc(x.value)+'" '+(x.value===selected?'selected':'')+'>'+esc(x.text)+'</option>').join('');
 const participants=()=>model.teilnehmer.filter(t=>t.typ!=='kamera'&&(kind==='cloud'?t.typ==='extern_ziel':kind==='participant'?t.typ!=='extern_ziel':true));
 const groups=()=>model.wege;
 const getItems=()=>kind==='group'?groups():participants();
 function selectDraft(){
  original=getItems().find(x=>(kind==='group'?x.nummer:ref(x))===selected)||null;
  draft=original?structuredClone(original):kind==='group'?{nummer:'',name:'',von:[],ziele:[],klingelzeit:20,kontexte:[],ersetzen:false,mitglieder_rufen:false}:{nummer:'',name:'',typ:kind==='cloud'?'extern_ziel':'sip_telefon',ha_benutzer:'',endpoint:'',sip_adresse:'',eingang:'',stream:'',video_codecs:'auto',qualify_frequency:'',browser_mod_entity:'',realm:'',anruf_ziele:null,angerufen_von:null,darf_anrufen:[],quell_ips:[],faehigkeiten:{kamerabild:false,video_im_anruf:false,ios:false,tuer_oeffnen:false}};
  saved=false;
 }
 function fieldValue(el){return el.type==='checkbox'?el.checked:el.value.trim();}
 function collect(){
  if(!draft)return;
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
   (kind==='participant'?label('Gerätetyp','typ',draft.typ,{select:[['sip_telefon','SIP-Telefon'],['ha_geraet','HA-Gerät / SIP Core'],['tuerstation','Türstation']]}):'')+
   (kind==='cloud'?label('SIP-Adresse','sip_adresse',draft.sip_adresse,{placeholder:'name@sip.linphone.org'}):label('HA-Benutzer (HA-Gerät)','ha_benutzer',draft.ha_benutzer))+'</div>';
  if(step===1)return '<div class="wiz-grid">'+label('Ausgehender Anschluss / Endpoint','endpoint',draft.endpoint,{placeholder:kind==='cloud'?'linphone-cloud':'optional'})+
   (kind==='cloud'?label('Eingehender Anschluss','eingang',draft.eingang,{placeholder:'linphone-in'}):label('Stream / Browser-ID','stream',draft.stream))+
   label('Video-Codecs','video_codecs',draft.video_codecs||'auto',{select:[['auto','Automatisch'],['vp8','Nur VP8'],['h264','Nur H.264'],['vp9','Nur VP9'],['vp8,h264','VP8 + H.264'],['none','Kein Video']]})+
   label('OPTIONS / qualify_frequency (Sekunden)','qualify_frequency',draft.qualify_frequency??'',{placeholder:'leer = bestehend'})+
   label('Browser-Mod-Status (zentral)','browser_mod_entity',draft.browser_mod_entity)+
   (kind==='cloud'?label('Quell-IPs (kommagetrennt)','quell_ips',(draft.quell_ips||[]).join(', ')):label('Realm / Domain','realm',draft.realm))+'</div>'+check('SIP-Video aktivieren','fae.video_im_anruf',draft.faehigkeiten?.video_im_anruf)+check('Kamerabild im HA-Popup','fae.kamerabild',draft.faehigkeiten?.kamerabild)+check('iOS-Gerät','fae.ios',draft.faehigkeiten?.ios)+check('Türöffner anzeigen','fae.tuer_oeffnen',draft.faehigkeiten?.tuer_oeffnen);
  return '<div class="wiz-grid">'+label('Darf anrufen (Nummern, leer = uneingeschränkt bei lokalen Teilnehmern)',''+(kind==='cloud'?'darf_anrufen':'anruf_ziele'),(kind==='cloud'?draft.darf_anrufen:draft.anruf_ziele)?.join(', ')||'')+label('Darf angerufen werden von (Nummern)','angerufen_von',draft.angerufen_von?.join(', ')||'')+'</div><p class="wiz-note">Leer bedeutet bei lokalen Anrufrechten keine Einschränkung. Bei Cloud-Konten werden die ausgehenden Freigaben explizit als Nummernliste gespeichert. Änderungen sind erst nach „Erzeugen & Übernehmen“ in Asterisk aktiv.</p>';
 }
 function render(message='',error=false){
  const header='<div class="wiz-head"><h2>Einrichtungsassistent</h2><button type="button" data-action="close" aria-label="Schließen">✕</button></div>';
  if(!kind){dialog.innerHTML=header+'<p>Was möchtest du direkt einrichten oder bearbeiten?</p>'+Object.entries(sections).map(([k,v])=>'<button type="button" class="wiz-choice" data-kind="'+k+'">'+esc(v)+'</button>').join('')+'<p class="wiz-note">Bestehende Einträge werden gezielt geändert. Speichern übernimmt nur das Anlagenmodell, nicht die laufende Asterisk-Konfiguration.</p>';return;}
  const select=kind==='ha'?'':step===0?'<label>Vorhandenen Eintrag bearbeiten oder neu anlegen<select id="wizSelect">'+options(getItems().map(t=>({value:kind==='group'?t.nummer:ref(t),text:((t.nummer||'')+' '+t.name).trim()})))+'</select></label>':'';
  const steps=count();
  dialog.innerHTML=header+'<h3>'+esc(sections[kind])+'</h3><p>Schritt '+(step+1)+' von '+steps+'</p><div class="wiz-progress">'+Array.from({length:steps},(_,i)=>'<span class="'+(i<=step?'active':'')+'"></span>').join('')+'</div>'+select+form()+
   '<p id="wizMessage" class="'+(error?'wiz-error':'wiz-ok')+'" role="status">'+esc(message)+'</p>'+
   '<div class="wiz-actions"><button type="button" data-action="home">Bereiche</button><div><button type="button" data-action="back" '+(step===0?'disabled':'')+'>Zurück</button> <button type="button" class="primary" data-action="next">'+(step===steps-1?'Validieren & speichern':'Weiter')+'</button></div></div>'+
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
 async function open(){try{await load();kind='';step=0;selected='';draft=null;render();if(!dialog.open)dialog.showModal();}catch(e){alert('Assistent konnte nicht starten: '+e.message);}}
 button.addEventListener('click',open);
 dialog.addEventListener('change',e=>{if(e.target.id==='wizSelect'){selected=e.target.value;selectDraft();render();}});
 dialog.addEventListener('click',async e=>{
  const b=e.target.closest('button');if(!b||busy)return;
  if(b.dataset.action==='close'){dialog.close();return;}
  if(b.dataset.kind){kind=b.dataset.kind;step=0;selected='';if(kind==='ha'){draft=structuredClone(model.anlage);original=null;}else selectDraft();render();return;}
  if(b.dataset.action==='home'){collect();kind='';step=0;render();return;}
  if(b.dataset.action==='back'){collect();step=Math.max(0,step-1);render();return;}
  if(b.dataset.action==='next'){collect();if(step<count()-1){step++;render();return;}
   busy=true;b.disabled=true;try{await save();}catch(err){render(err.message,true);}finally{busy=false;} }
 });
})();
