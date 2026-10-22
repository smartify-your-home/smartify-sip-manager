const $=id=>document.getElementById(id);let loadedHash=null,loadedName=null,loadedSource=null,asteriskContainer='addon_<asterisk-slug>';
const msg=t=>{const b=$('feedback');b.textContent=t;b.style.display='block';setTimeout(()=>b.style.display='none',5000)};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Theme belongs exclusively to this manager, never modify the HA theme/SIP Core.
(function initManagerTheme(){
 const select=$('managerTheme');
 let saved='light';
 try {saved=localStorage.getItem('smartify-manager-theme')||'light'} catch(_e) {}
 if(!['light','dark'].includes(saved)) saved='light';
 const apply=theme=>{document.documentElement.dataset.managerTheme=theme;select.value=theme};
 apply(saved);
 select.addEventListener('change',()=>{
   apply(select.value);
   try {localStorage.setItem('smartify-manager-theme',select.value)} catch(_e) {}
 });
})();

// Three primary work areas. Deep links from existing tools still open the correct area.
const PANEL_AREA={start:'start',anlage:'start',rufgruppen:'start',verbindungen:'start',erzeugen:'start',endpoint:'asterisk',inbound:'asterisk',live:'asterisk',pjsip:'asterisk',draft:'sipcore',callercams:'sipcore',presets:'sipcore',entity:'sipcore',device:'sipcore',sip:'sipcore',route:'groups',overview:'tools',checks:'tools',guide:'tools',help:'tools',audit:'tools',backup:'tools'};
const AREA_START={start:'start',asterisk:'endpoint',sipcore:'draft',groups:'route',tools:'overview'};

// Global top-bar controls use the same validated backend operations as the editor.
let globalActionBusy=false;
async function globalAction(task) {
 const apply=$('globalApply'),reload=$('globalReload'),save=$('globalSave'),status=$('globalActionStatus');
 if(globalActionBusy)return;
 globalActionBusy=true;apply.disabled=true;reload.disabled=true;save.disabled=true;
 try{
  if(task==='save'){
   if(!['anlage','rufgruppen'].some(id=>document.getElementById(id)?.classList.contains('active'))) {
    throw new Error('Der globale Speichern-Button gilt für Anlage, Teilnehmer und Rufgruppen. In anderen Bereichen den dortigen Speichern-Button verwenden.');
   }
   if(typeof window.smartifyQuickSave!=='function') throw new Error('Anlagenverwaltung nicht geladen.');
   status.textContent='Speichere Teilnehmer und Rufgruppen …';
   status.textContent=await window.smartifyQuickSave();
  } else if(task==='apply'){
   if(typeof window.smartifyQuickApply!=='function')throw new Error('Anlagenverwaltung noch nicht geladen.');
   status.textContent='Prüfe und übernehme Asterisk-Konfiguration …';
   status.textContent=await window.smartifyQuickApply();
  } else {
   if(!confirm('Asterisk PJSIP und Dialplan neu laden? Laufende Gespräche sollen dabei möglichst bestehen bleiben.')){status.textContent='Reload abgebrochen.';return}
   status.textContent='Lade PJSIP neu …';
   await post('api/ami/command',{command:'pjsip reload',confirm:true});
   status.textContent='Lade Dialplan neu …';
   await post('api/ami/command',{command:'dialplan reload',confirm:true});
   status.textContent='PJSIP und Dialplan neu geladen.';
  }
 }catch(e){status.textContent='Fehler: '+e.message;msg(e.message)}
 finally{globalActionBusy=false;apply.disabled=false;reload.disabled=false;save.disabled=false}
}
$('globalSave').onclick=()=>globalAction('save');
$('globalApply').onclick=()=>globalAction('apply');
$('globalReload').onclick=()=>globalAction('reload');

function showPanel(id){
 const area=PANEL_AREA[id]||'tools';
 document.querySelectorAll('[data-area]').forEach(b=>b.classList.toggle('active',b.dataset.area===area));
 document.querySelectorAll('[data-subarea]').forEach(x=>x.classList.toggle('active',x.dataset.subarea===area));
 document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===id));
 document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===id));
 if(id==='start')window.smartifyPruefbericht?.();
 if(id==='anlage')window.smartifyAnlage?.();
 if(id==='erzeugen')window.smartifyErzeugen?.();
 if(id==='verbindungen')window.smartifyVerbindungen?.();
 if(id==='rufgruppen')window.smartifyRufgruppen?.();
 if(id==='endpoint')refreshEndpoints();
 if(id==='inbound')loadInbound();
 if(id==='route')refreshNumberPlan();
 if(id==='draft')refreshSipWorkspace();
}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>showPanel(b.dataset.tab));
document.querySelectorAll('[data-area]').forEach(b=>b.onclick=()=>showPanel(AREA_START[b.dataset.area]));

async function request(path,opts){let r;try{r=await fetch(path,opts)}catch(e){throw Error('Manager nicht erreichbar ('+e.message+')')}let d;try{d=await r.json()}catch(e){throw Error('Ungültige Server-Antwort (HTTP '+r.status+') bei '+path)}if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
// Fehler in der Oberfläche sichtbar machen, statt dass Knöpfe still nicht reagieren.
function showFatal(text){let b=document.getElementById('fatalBar');if(!b){b=document.createElement('div');b.id='fatalBar';b.className='fatal';document.body.prepend(b)}b.textContent='⚠ Fehler in der Oberfläche: '+text+' – bitte diese Meldung weitergeben.'}
window.addEventListener('error',e=>showFatal((e.message||'Unbekannt')+(e.filename?' ('+e.filename.split('/').pop()+':'+e.lineno+')':'')));
window.addEventListener('unhandledrejection',e=>showFatal(String(e.reason&&e.reason.message||e.reason)));
async function status(){try{const check=await request('api/health');$('startupCheck').textContent=(check.asterisk_directory?'✓ Asterisk-Konfigurationsordner gefunden · '+(check.custom_directory?'Custom-Verzeichnis vorhanden':'Custom-Verzeichnis noch nicht vorhanden')+' · Keine automatischen Reloads': '⚠ '+check.hint)+' · HA-API-Token: '+(check.homeassistant_api_token_present?'im Prozess vorhanden':'FEHLT – Add-on-Image neu bauen');const d=await request('api/status');applyVersions(d);asteriskContainer=d.container||asteriskContainer;fillHelpCommands();renderGuide();$('health').textContent=d.asterisk_config_found?'● Asterisk-Konfiguration gefunden':'⚠ Asterisk-Pfad nicht gefunden';$('path').textContent=d.custom;const sel=$('filename');const prev=sel.value;sel.replaceChildren(...d.files.map(n=>{const o=document.createElement('option');o.textContent=n;return o}));if(d.files.includes(prev))sel.value=prev;$('known').textContent='Teilnehmer im Bereich Live / Diagnose oder in Asterisk-Dateien prüfen. Keine voreingestellten Rufnummern werden als Live-Daten ausgegeben.'}catch(e){msg('Verbindung zum Manager fehlgeschlagen: '+e.message)}}
// One inventory instead of two competing "Nummernbelegung" and "Endpoints" tables.
async function refreshEndpoints(){
 await refreshNumberPlan();
}
function renderUnifiedInventory(){
 const root=$('unifiedInventory');if(!root||!numberPlan)return;
 const plan=numberPlan, rows=pjsipTableState?.rows||[];
 const all=new Set([...Object.keys(plan.used||{}),...(plan.endpoints||[]).filter(e=>validExt(e.extension)).map(e=>e.extension)]);
 const nums=[...all].sort((a,b)=>Number(a)-Number(b));
 if(!nums.length){root.textContent='Keine Nummern in den aktuell lesbaren Dateien gefunden. Das ist keine Bestätigung freier Nummern.';return;}
 const tr=nums.map(n=>{
  const eps=(plan.endpoints||[]).filter(e=>e.extension===n);
  const paths=rows.filter(r=>r.number===n);
  const dial=(plan.dialplan||[]).filter(r=>r.number===n);
  const sip=(plan.sip_core_numbers||[]).filter(u=>u.number===n);
  const refs=(plan.dialplan||[]).filter(r=>(r.targets||[]).includes(n)).map(r=>r.number+'@'+r.context);
  const types=(plan.used?.[n]||[]).join(' · ') || 'Asterisk-Endpoint';
  const name=[...eps.map(e=>e.display_name),...sip.map(u=>u.name)].filter(Boolean).join(' · ')||'–';
  const src=[...new Set([...eps.flatMap(e=>e.files||[]),...dial.map(d=>d.source),...paths.map(r=>'custom/'+r.file)])].join(', ')||'–';
  const detail=dial.map(d=>d.kind+' '+d.context+': '+(d.targets?.join(', ')||d.summary||d.steps?.join(' → ')||'Dialplan')).join(' | ') || eps.map(e=>e.context||'').filter(Boolean).join(', ') || '–';
  let action='';
  if(paths.some(r=>r.editable)){
   action='<button type="button" data-inv-edit="'+esc(n)+'">Bearbeiten</button> <button type="button" class="danger-button" data-inv-delete="'+esc(n)+'">Löschen …</button>'+((refs.length||sip.length)?'<small class="inventory-warning">Löschen erst nach Entfernen der Verweise: '+esc([...refs.map(x=>'Rufziel '+x),...sip.map(x=>'SIP Core')].join(', '))+'</small>':'');
  }else if(paths.length){
   action='<button type="button" data-inv-info="'+esc(n)+'">Warum gesperrt?</button>';
  }else if(dial.length){
   action='<button type="button" data-inv-route="'+esc(n)+'">Rufziel öffnen</button>';
  }else if(eps.length){
   action='<small>Nur lesen – keine vollständige editierbare Custom-Definition</small>';
  }else if(sip.length){
   action='<button type="button" data-inv-sip="'+esc(n)+'">SIP Core öffnen</button>';
  }
  return '<tr><td class="id-col">'+esc(n)+'</td><td>'+esc(types)+'</td><td>'+esc(name)+'</td><td class="inv-detail">'+esc(detail)+'</td><td class="inv-source">'+esc(src)+'</td><td>'+action+'</td></tr>';
 }).join('');
 root.innerHTML='<table class="edit-table inventory-table"><thead><tr><th>Nummer</th><th>Belegung / Typ</th><th>Name</th><th>Kontext / Ziel</th><th>Quelle</th><th>Aktionen</th></tr></thead><tbody>'+tr+'</tbody></table>';
 root.querySelectorAll('[data-inv-edit]').forEach(b=>b.onclick=()=>focusExistingEndpoint(b.dataset.invEdit));
 root.querySelectorAll('[data-inv-delete]').forEach(b=>b.onclick=()=>deletePjsipTableRow(b.dataset.invDelete));
 root.querySelectorAll('[data-inv-info]').forEach(b=>b.onclick=()=>{
  const n=b.dataset.invInfo;const reasons=rows.filter(r=>r.number===n).map(r=>'custom/'+r.file+': '+(r.reason||'Nur Rohdatei-Editor')).join(' | ');
  msg('Nebenstelle '+n+' nicht automatisch änderbar: '+reasons);
 });
 root.querySelectorAll('[data-inv-route]').forEach(b=>b.onclick=()=>{
  showPanel('route');$('groupsExisting').scrollIntoView({block:'start',behavior:'smooth'});
  msg('Rufziel '+b.dataset.invRoute+' im Rufgruppen-Bereich bearbeiten.');
 });
 root.querySelectorAll('[data-inv-sip]').forEach(b=>b.onclick=()=>showPanel('draft'));
}

function focusExistingEndpoint(n){
 const item=numberPlan?.endpoints?.find(e=>e.extension===n);
 const route=numberPlan?.dialplan?.find(r=>r.number===n);
 if(!item&&route){
  showPanel('route');$('groupsExisting').scrollIntoView({block:'start',behavior:'smooth'});
  msg('Nummer '+n+' ist ein Rufziel/Rufgruppe – bitte dort bearbeiten.');return;
 }
 const details=$('pjsipDetails');if(details)details.open=true;
 const tr=Array.from(document.querySelectorAll('#pjsipTable tr[data-extension]')).find(x=>x.dataset.extension===n);
 if(!tr){
  msg('Nummer '+n+' ist belegt, aber nicht in der bearbeitbaren Custom-Tabelle. '+(item?'Quelle: '+item.files.join(', '):'Quelle über Nummernbelegung prüfen')+'. Nicht als neu anlegen.');return;
 }
 tr.scrollIntoView({block:'center',behavior:'smooth'});
 tr.classList.add('highlight-existing');setTimeout(()=>tr.classList.remove('highlight-existing'),2500);
 tr.querySelector('[data-col="name"]')?.focus();
 msg('Vorhandene Nebenstelle '+n+' bearbeiten oder über „Löschen“ entfernen.');
}
$('endpointRefresh').onclick=async()=>{await refreshEndpoints();await refreshPjsipTable();};
async function loadFile(){const name=$('filename').value;try{const d=await request('api/file/'+name);loadedName=name;loadedSource=d.source;loadedHash=d.source==='default (nur lesen)'?null:d.hash;$('editor').value=d.content;$('fileSource').textContent=d.source==='custom'?'Aktive Custom-Datei – Änderungen werden vor dem Speichern automatisch gesichert.':d.source==='missing'?'Neue leere Datei – wird erst bei Speichern angelegt.':'Dies ist eine STANDARD-REFERENZDATEI. Speichern ist aus Sicherheitsgründen deaktiviert; bearbeite nur eine bewusste Custom-Kopie.';$('reloadHint').textContent=(await request('api/hints')).hints[name]||'Nach Speichern Ladeverfahren prüfen.';msg(name+' geladen · '+d.source)}catch(e){msg(e.message)}}
$('loadFile').onclick=loadFile;$('filename').onchange=loadFile;
$('createCustom').onclick=async()=>{const name=$('filename').value;if(loadedName!==name||loadedSource!=='missing'){msg('Zuerst die fehlende Datei laden. Existierende Standarddateien ausdrücklich kopieren.');return}if(!confirm('Leere Custom-Datei '+name+' anlegen? Sie wird NICHT automatisch in Asterisk eingebunden.'))return;try{const d=await request('api/create-custom/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});msg(d.note);await loadFile()}catch(e){msg('NICHT angelegt: '+e.message)}};
$('copyDefault').onclick=async()=>{const name=$('filename').value;if(loadedName!==name||loadedSource!=='default (nur lesen)'){msg('Zuerst eine Default-Datei im Editor laden');return}const h=await request('api/file/'+name);if(!confirm('Standarddatei '+name+' VOLLSTÄNDIG nach custom kopieren? Das kann das Verhalten des Add-ons verändern. Wirksamkeit erst nach Include/Override-Prüfung.'))return;try{const d=await request('api/copy-default/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hash:h.hash})});msg(d.note);await loadFile()}catch(e){msg('NICHT kopiert: '+e.message)}};
$('saveFile').onclick=async()=>{if(loadedName!==$('filename').value||loadedHash===null){msg('Speichern nicht möglich: zunächst passende Custom-Datei laden.');return}const lint=await lintEditor();if(lint&&lint.errors&&!confirm(lint.errors+' Fehler gefunden (siehe Prüfergebnis). Trotzdem speichern?'))return;if(!confirm('Custom-Datei '+loadedName+' sichern und ersetzen? KEIN automatischer Reload.'))return;try{const d=await request('api/file/'+loadedName,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:$('editor').value,hash:loadedHash})});loadedHash=d.hash;$('reloadHint').textContent=d.hint;msg(d.note)}catch(e){msg('NICHT gespeichert: '+e.message)}};
$('copyFile').onclick=()=>copy($('editor').value);
async function copy(text){try{await navigator.clipboard.writeText(text);msg('In Zwischenablage kopiert')}catch(e){msg('Kopieren blockiert – Text bitte markieren')}}
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>copy($(b.dataset.copy).value));
function value(id){return $(id).value.trim()}
function validExt(n){return /^\d{2,6}$/.test(n)}
$('makeRoute').onclick=async()=>{
 const n=value('groupNum'),ctx=value('groupContext'),dest=value('groupTargets').split(',').map(x=>x.trim()).filter(Boolean),extURI=value('cloudURI'),ep=value('cloudEp'),seconds=Number(value('timeout'));
 const description=value('groupDesc')||'Smartify Rufgruppe '+n;
 if(!validExt(n)||/[\r\n();]/.test(description)||description.length>120||!/^[A-Za-z0-9_-]{1,64}$/.test(ctx)||!dest.every(validExt)||new Set(dest).size!==dest.length||!Number.isInteger(seconds)||seconds<5||seconds>120||(extURI&&(!/^[\w-]+$/.test(ep)||!/^sip:[a-zA-Z0-9_.+%-]+@[a-zA-Z0-9.-]+$/.test(extURI)))){
  msg('Ungültige Gruppennummer, doppelte Ziele, Zeit oder SIP-URI');return;
 }
 const plan=await getFreshNumberPlan();if(!plan)return;
 if(plan.used[n]){msg('Gruppennummer '+n+' ist bereits belegt: '+plan.used[n].join(', '));$('routeOut').value='';return;}
 const present=new Set(plan.endpoints.map(x=>x.extension));
 const missing=dest.filter(x=>!present.has(x));
 if(missing.length){msg('Nur existierende Asterisk-Nebenstellen als Ziele: '+missing.join(', '));return;}
 if(!dest.length&&!extURI){msg('Mindestens ein vorhandenes lokales Ziel oder externes Ziel angeben');return;}
 const parts=dest.map(x=>'${PJSIP_DIAL_CONTACTS('+x+')}');if(extURI)parts.push('PJSIP/'+ep+'/'+extURI);
 $('routeOut').value='; Im BESTEHENDEN ['+ctx+']-Kontext ergänzen (nicht doppelt!)\nexten => '+n+',1,NoOp('+description+')\n same => n,Dial('+parts.join('&')+','+seconds+')\n same => n,Hangup()';
 msg('Dialplan vorbereitet; nicht gespeichert. Vor Reload den wirksamen Kontext prüfen.');
};
function yq(s){return JSON.stringify(String(s))}
$('makeSip').onclick=()=>{const users=value('userList').split('\n').map(s=>s.trim()).filter(Boolean).map(line=>line.split(',').map(s=>s.trim()));if(users.some(u=>u.length!==3||!validExt(u[0])||!u[1]||!u[2])){msg('Teilnehmerformat: Nummer,HA-Benutzer,Anzeigename');return}const stream=value('sipStream'),door=value('sipDoor'),light=value('sipLight');if(!/^[\w-]+$/.test(stream)||[door,light].some(x=>x&&!/^[a-z_]+\.[a-zA-Z0-9_]+$/.test(x))){msg('Stream oder Entität ungültig');return}const lines=['auto_answer: false','incomingRingtoneUrl: '+yq(value('sipRing')),'popup_override_component: smartify-doorstation-popup','popup_config:','  auto_open: true','  large: true','  hide_header_button: true','  smartify:','    stream: '+yq(stream),'    theme: '+value('sipTheme'),'    door_confirm: true','    camera_mode: always','    mode: mse','    camera_ui: true'];if(door)lines.push('    door_entity: '+yq(door),'    door_service: turn_on');if(light)lines.push('    light_entity: '+yq(light),'    light_service: toggle');lines.push(...cameraLines(4));lines.push('users:');for(const [num,ha,name] of users)lines.push('  - extension: '+yq(num),'    ha_username: '+yq(ha),'    display_name: '+yq(name),'    password: "HIER_BESTEHENDES_PASSWORT_EINSETZEN"');$('sipOut').value=lines.join('\n')+'\n';msg('YAML erzeugt – vor Übernahme Passwörter und vorhandene Optionen ergänzen')};
status();loadFile();

const scenarioHelp={"new": [["Vorbereitung", "Asterisk-Container läuft, UDP-Transport prüfen: pjsip show transports; bestehende 106-Einträge ausschließen."], ["Sicherung", "pjsip_custom.conf im Dateieditor laden. Backup erstellen oder bestehende Datei vollständig kopieren."], ["Nebenstelle erzeugen", "Unter „Nebenstellen“ Nummer, Caller-ID und Passwort eingeben. Das erzeugte Snippet kontrollieren."], ["Speichern", "Snippet bewusst in pjsip_custom.conf einfügen und die komplette Datei speichern."], ["Laden", "Über HAOS-Hostkonsole: docker exec addon_3e533915_asterisk asterisk -rx \"pjsip reload\""], ["Prüfen", "pjsip show endpoint 106 und pjsip show aor 106; danach Linphone mit eigener Nummer registrieren."], ["Anruf testen", "Zuerst ausgehend zur 104, dann eingehend von 104 auf 106. Gegensprechen prüfen."]], "group": [["Ziele festlegen", "iPad 104 ist SIP Core; iPhone Linphone-Cloud über linphone-cloud. Beide einzeln testen."], ["Dialplan sichern", "extensions.conf sichern und vorhandenen [default]-Kontext prüfen."], ["600 generieren", "Im Reiter Rufgruppen die Ziele 104 + externe SIP-URI eintragen."], ["Regel einfügen", "Nur eine 600-Regel innerhalb des wirksamen [default]-Kontextes ergänzen."], ["Reload", "dialplan reload über HAOS-Konsole, kein Add-on-Neustart."], ["Prüfen", "dialplan show 600@default; 600 vom iPad/HA oder einem anderen Teilnehmer wählen."], ["Türstation umstellen", "Erst nach erfolgreichem Test die Akuvox-Taste auf Rufziel 600 konfigurieren."]], "cloud": [["Cloud-Konto", "Linphone-Konto bei sip.linphone.org anmelden, iPhone-Push erlauben."], ["Direktes Ziel", "Ausgehenden PJSIP-Endpoint linphone-cloud konfigurieren; UDP-Transport und Netzroute prüfen."], ["Testnummer", "906 so einrichten, dass sie sip:DEINNAME@sip.linphone.org anwählt."], ["Test", "906 anrufen, iPhone sperren, Push prüfen und Audio in beide Richtungen testen."], ["Produktivbetrieb", "Erst danach 106 oder die Gruppe 600 gezielt mit dem funktionierenden Cloud-Ziel verbinden."]], "popup": [["SIP Core sichern", "Aktuelle Integrations-YAML kopieren, einschließlich aller Passwörter (nicht in den Manager einfügen)."], ["Geräte festlegen", "Unter Entitäten die Tür/Licht-IDs suchen und go2rtc-Streamnamen prüfen."], ["Konfiguration", "Im SIP-Core-Reiter Stream, Entitäten, Theme und Tonadresse eintragen; YAML erzeugen."], ["Vergleichen", "Generierte YAML mit der vorhandenen Konfiguration vergleichen; fehlende Optionen und Passwörter bewahren."], ["Übernehmen", "Über die SIP-Core-Integration in Home Assistant ändern, nicht die versteckten .storage-Dateien."], ["Test", "Anruf, Mikrofonschaltung, Türbestätigung und Wiedergabe am iPad UND iPhone testen."]], "repair": [["Nicht überstürzt neu starten", "Bei Problemen erst Asterisk-Logs kontrollieren und Backups behalten."], ["Status prüfen", "AMI-Liveanzeige und die Asterisk-Kontakte prüfen. Registriert heißt noch nicht klingelt."], ["Konfiguration prüfen", "PJSIP- und Dialplan-Syntax sowie doppelten Endpoint-Namen prüfen."], ["Gezielt laden", "Nach kleinen PJSIP-Änderungen pjsip reload; nach Dialplan-Änderungen dialplan reload."], ["Wenn Supervisor blockiert", "Keine wiederholten Installations-/Deinstallationsversuche. Über Proxmox den Containerstatus und die Logs prüfen."], ["Rückgängig machen", "Zuletzt gespeichertes Backup wiederherstellen und kontrolliert nur betroffene Konfiguration neu laden."]]};
function renderGuide(){const steps=scenarioHelp[value('scenario')]||[];$('guideSteps').innerHTML=steps.map(([title,body],i)=>`<div class="guide-step"><b>Schritt ${i+1}: ${esc(title)}</b><span>${esc(body.replaceAll('addon_3e533915_asterisk',asteriskContainer))}</span></div>`).join('')}
$('scenario').onchange=renderGuide;renderGuide();
document.querySelectorAll('#endpoint [data-copy]').forEach(b=>b.onclick=()=>copy($(b.dataset.copy).value));
// Jede Änderung verwirft den bisherigen PJSIP-Vorschlag, damit keine veralteten Parameter gespeichert werden.
let endpointGeneration=0;
function invalidateEndpointPreview(){
 endpointGeneration++;
 $('epOut').value='';
 $('epWarnings').hidden=true;
 $('epPreviewStatus').textContent='Einstellungen geändert – Vorschau neu erzeugen.';
}
function endpointValues(){
 return {
  extension:value('epExt'), displayName:value('epName'), password:$('epPassword').value,
  authUsername:value('epAuthUsername'), context:value('epContext'), transport:value('epTransport'),
  maxContacts:value('epMaxContacts'), removeExisting:value('epRemoveExisting'), removeUnavailable:value('epRemoveUnavailable'),
  qualifyFrequency:value('epQualify'), minimumExpiration:value('epMinExp'), defaultExpiration:value('epDefExp'),maximumExpiration:value('epMaxExp'),
  codecs:Array.from(document.querySelectorAll('#epForm input[name="epCodec"]:checked')).map(x=>x.value),
  dtmfMode:value('epDtmf'), directMedia:value('epDirectMedia'),forceRport:value('epForceRport'),
  rewriteContact:value('epRewriteContact'),rtpSymmetric:value('epRtpSymmetric'),iceSupport:value('epIceSupport')
 };
}
$('epForm').addEventListener('input',()=>{invalidateEndpointPreview();updateSlotStatuses();});
$('epForm').addEventListener('change',()=>{invalidateEndpointPreview();updateSlotStatuses();});
$('epEditExisting').onclick=()=>focusExistingEndpoint(value('epExt'));
$('epPresetSingle').onclick=()=>{
 $('epMaxContacts').value='1'; $('epRemoveExisting').value='yes';$('epRemoveUnavailable').value='no';invalidateEndpointPreview();
};
$('epPresetMultiple').onclick=()=>{
 $('epMaxContacts').value='3'; $('epRemoveExisting').value='no';$('epRemoveUnavailable').value='yes';invalidateEndpointPreview();
};
$('epPresetLinphone').onclick=()=>{
 $('epMaxContacts').value='1';$('epRemoveExisting').value='yes';$('epRemoveUnavailable').value='no';
 $('epDirectMedia').value='no';$('epRewriteContact').value='yes';$('epRtpSymmetric').value='yes';$('epForceRport').value='yes';$('epDtmf').value='rfc4733';
 invalidateEndpointPreview();msg('Linphone-Voreinstellung geladen. SIP-Server, Login und Passwort werden in Linphone selbst eingerichtet.');
};
$('makeEndpoint').onclick=async()=>{
 let output;
 try{output=SmartifyPjsip.build(endpointValues());}
 catch(e){invalidateEndpointPreview();$('epPreviewStatus').textContent=e.message;msg(e.message);return;}
 const revision=endpointGeneration;
 const ready=await getFreshNumberPlan();if(!ready||revision!==endpointGeneration)return;
 if(ready.used[output.extension]){
  invalidateEndpointPreview();$('epPreviewStatus').textContent='Nummer '+output.extension+' ist bereits belegt.';
  msg('Nummer '+output.extension+' ist belegt: '+ready.used[output.extension].join(', '));return;
 }
 $('epOut').value=output.snippet;
 $('epPreviewStatus').textContent='PJSIP-Vorschau für '+output.extension+' erstellt, noch NICHT gespeichert.';
 $('epWarnings').hidden=output.notices.length===0;
 $('epWarnings').replaceChildren(...output.notices.map(t=>{const p=document.createElement('p');p.textContent='⚠ '+t;return p;}));
 msg('Konfiguration erzeugt. AOR, Auth und Endpoint prüfen.');
};
$('refreshLive').onclick=async()=>{const box=$('liveResults');box.textContent='Frage Asterisk ab …';try{const d=await request('api/live');if(!d.available){box.textContent='✗ '+d.message;return}box.innerHTML='<b>'+esc(d.message)+'</b>'+ (d.endpoints||[]).map(x=>`<p><code>${esc(x.ObjectName||'-')}</code> · ${esc(x.DeviceState||'-')} · ${esc(x.ActiveChannels||'0')} Kanäle</p>`).join('');}catch(e){box.textContent='✗ '+e.message}};
$('discover').onclick=async()=>{try{const d=await request('api/discovery');$('discoveryResults').innerHTML=d.files.map(f=>`<p><b>${esc(f.file)}</b> (${esc(f.source)})<br><span class="muted">${esc(f.entries.join(', ')||'Keine Treffer in lesbarer Datei')}</span></p>`).join('')}catch(e){msg(e.message)}};
let allEntities=[];
function showEntities(){const q=value('entitySearch').toLowerCase();let results=allEntities.filter(x=>(x.entity_id+' '+x.name).toLowerCase().includes(q)).slice(0,100);$('entityResults').innerHTML=results.map(e=>`<div class="entity-row"><div><b>${esc(e.name||e.entity_id)}</b><br><small>${esc(e.entity_id)}</small></div><button data-entity="${esc(e.entity_id)}">Kopieren</button></div>`).join('')||'<p class="hint">Keine passenden Entitäten.</p>';document.querySelectorAll('[data-entity]').forEach(b=>b.onclick=()=>copy(b.dataset.entity))}
$('entitySearch').oninput=showEntities;
$('loadEntities').onclick=async()=>{try{const d=await request('api/entities');if(!d.available){msg(d.message);return}allEntities=d.entities;showEntities();msg(allEntities.length+' Entitäten geladen')}catch(e){msg(e.message)}};

let draftHash=null;
$('draftLoad').onclick=async()=>{try{let d=await request('api/sip-core-draft');draftHash=d.hash;$('draftEditor').value=d.content;$('draftResult').textContent=d.hint;msg('SIP-Core-Entwurf geladen')}catch(e){msg(e.message)}};
$('draftSave').onclick=async()=>{if(draftHash===null){msg('Bitte zuerst Entwurf laden');return}if(!confirm('SIP-Core-Entwurf sicher im Manager speichern? Aktive SIP-Core-Konfiguration wird NICHT verändert.'))return;try{const d=await request('api/sip-core-draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:$('draftEditor').value,hash:draftHash})});draftHash=d.hash;$('draftResult').textContent=d.hint;msg('Entwurf gespeichert und bei Bedarf gesichert')}catch(e){msg(e.message)}};
$('draftCopy').onclick=()=>copy($('draftEditor').value);
$('logRefresh').onclick=async()=>{try{let d=await request('api/changes');$('auditText').value=d.logs.join('');msg('Protokoll aktualisiert')}catch(e){msg(e.message)}};

// Vorlagen: no active SIP-Core write API; no passwords or config mutation.
function pyaml(v){return JSON.stringify(String(v));}
function presetBuild(silent){
 const kind=value('presetKind'),mode=value('presetMode'),stream=value('presetStream').trim(),door=value('presetDoor').trim(),light=value('presetLight').trim();
 const go=$('go2rtcOut'), status=$('videoStatus');go.value='';
 if(!stream){status.textContent='go2rtc-Streamnamen eingeben, um eine Vorlage zu erzeugen.';$('presetOut').value='';if(silent!==true)msg('Bitte zuerst einen Streamnamen eingeben');return;}
 if(!/^[a-zA-Z0-9_-]+$/.test(stream)){msg('Ungültiger Streamname');return;}
 if([door,light].some(x=>x&&!/^[a-z_]+\.[a-zA-Z0-9_]+$/.test(x))){msg('Entitäts-ID ungültig');return;}
 if(kind==='original'||kind==='simple'){
   if(mode==='rtsp') {msg('RTSP/go2rtc-Vorlage erfordert die Smartify-Card; wähle Smartify als Popup');status.textContent='Nicht unterstützt: direktes RTSP im Standard-Popup.';return;}
   $('presetOut').value='popup_override_component: null\npopup_config:\n  auto_open: true\n  large: '+(kind==='original'?'true':'false')+'\n';
   status.textContent='Standard-Popup: Die tatsächlich unterstützte Kameraeinbindung hängt von SIP Core ab. Kein MSE-/WebRTC-Video aus der Smartify-Karte.';
   msg('Original-Popup: Override im SIP-Core-Einstellungsdialog deaktivieren');return;
 }
 let realMode=mode==='rtsp'?value('presetRtspPlayback'):mode;
 if(mode==='rtsp'){
   const uri=value('presetRtsp').trim();
   if(!/^rtsps?:\/\/[^\s]+$/i.test(uri)){msg('Für RTSP ist eine vollständige rtsp://- oder rtsps://-URL notwendig');return;}
   if(/[\r\n]/.test(uri)){msg('RTSP-URL enthält unzulässige Zeichen');return;}
   // URLs with credentials should not be included in a downloadable Manager draft or audit log.
   const safeUri=uri.replace(/^(rtsps?:\/\/)[^/@]+@/i,'$1BENUTZER:PASSWORT@');
   go.value='streams:\n  '+stream+': '+pyaml(safeUri)+'\n';
   status.textContent='RTSP ist die Quelle, '+stream+' der go2rtc-Stream. Wiedergabe im Popup: '+realMode.toUpperCase()+'. Achtung: go2rtc-Definition getrennt eintragen, echte Zugangsdaten dort ergänzen. SIP-Audio bleibt unabhängig.';
 }else{
   status.textContent='Der Stream '+stream+' muss bereits in go2rtc existieren. '+realMode.toUpperCase()+' ist der Wiedergabemodus der Smartify-Karte, nicht das Quellprotokoll.';
 }
 const lines=['popup_override_component: smartify-doorstation-popup','popup_config:','  auto_open: true','  large: true','  hide_header_button: true','  smartify:', '    stream: '+pyaml(stream), '    mode: '+realMode,'    media: video,audio','    camera_ui: true','    camera_mode: '+value('presetCamera'),'    theme: '+value('presetTheme'),'    door_confirm: true'];
 if(door)lines.push('    door_entity: '+pyaml(door),'    door_service: turn_on');
 if(light)lines.push('    light_entity: '+pyaml(light),'    light_service: toggle');
 lines.push(...cameraLines(4));lines.push('incomingRingtoneUrl: '+pyaml(value('presetRing')));
 $('presetOut').value=lines.join('\n')+'\n';
 msg(mode==='rtsp'?'Zwei getrennte Vorschauen erzeugt: go2rtc und SIP Core – vor Aktivierung prüfen':'Smartify-Popup-Vorlage erstellt');
}
$('presetBuild').onclick=()=>presetBuild(false);
$('presetToDraft').onclick=()=>{const v=$('presetOut').value;if(!v){msg('Bitte zuerst eine Vorlage erzeugen');return;}mergeIntoDraft(v,'Vorlage');};
function routeParts(){const targets=value('groupTargets').split(',').map(x=>x.trim()).filter(validExt);return{targets:targets.length?targets:['104'],uri:value('cloudURI')||'sip:benutzer@sip.linphone.org',ep:value('cloudEp')||'linphone-cloud',group:validExt(value('groupNum'))?value('groupNum'):'600'}}
if($('presetGroup'))$('presetGroup').onclick=()=>{const r=routeParts();$('presetDial').value='; Rufgruppe '+r.group+': lokale Nebenstellen und externes Ziel gleichzeitig (Werte aus „Rufgruppen“)\nexten => '+r.group+',1,NoOp(Rufgruppe '+r.group+')\n same => n,Dial('+r.targets.map(t=>'${PJSIP_DIAL_CONTACTS('+t+')}').join('&')+'&PJSIP/'+r.ep+'/'+r.uri+',30)\n same => n,Hangup()\n';};
if($('presetCloud'))$('presetCloud').onclick=()=>{const r=routeParts();$('presetDial').value='; Testnummer 906: nur externes Ziel (Werte aus „Rufgruppen“)\nexten => 906,1,NoOp(Test externes Ziel)\n same => n,Dial(PJSIP/'+r.ep+'/'+r.uri+',30)\n same => n,Hangup()\n';};
// SIP-Anrufer → go2rtc Kamera. Dauerhafte Manager-Konfiguration, kein aktiver SIP-Core-Schreibzugriff.
const callerCameras=new Map(); let cameraMappingHash=null, cameraMappingSaved=false;
function isEntity(e){return !e||/^[a-z_]+\.[A-Za-z0-9_]+$/.test(e)}
function mappingEntries(){return [...callerCameras].sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true}));}
function cameraLines(indent){
 const space=' '.repeat(indent), o=[];
 if(!callerCameras.size)return [space+'camera_by_caller: {}'];
 o.push(space+'camera_by_caller:');
 for(const [num,v] of mappingEntries()){
   o.push(space+'  '+pyaml(num)+':',space+'    label: '+pyaml(v.label),space+'    stream: '+pyaml(v.stream),space+'    mode: '+v.mode,space+'    camera_mode: '+v.camera_mode);
   if(v.bell)o.push(space+'    bell_entity: '+pyaml(v.bell));
   if(v.door)o.push(space+'    door_entity: '+pyaml(v.door),space+'    door_service: turn_on',space+'    door_confirm: true');
   if(v.light)o.push(space+'    light_entity: '+pyaml(v.light),space+'    light_service: toggle');
 }
 return o;
}
function cameraYaml(){
 const stream=value('presetStream');
 const o=['# Nur Smartify-spezifischen Abschnitt in die bestehende SIP-Core-Konfiguration übernehmen',
   '# Bestehende users, Passwörter, popup_config.buttons und extensions erhalten!',
   'popup_override_component: smartify-doorstation-popup','popup_config:',
   '  smartify:',
   ...(stream?['    stream: '+pyaml(stream)+'   # Standard, falls kein Anrufer passt']:[]),'    mode: mse','    camera_mode: always',
   ...cameraLines(4)];
 return o.join('\n')+'\n';
}
function cameraCardYaml(){
 const stream=value('presetStream')||mappingEntries()[0]?.[1]?.stream||'';
 const first=mappingEntries()[0]?.[0] || '200';
 return ['type: custom:smartify-doorstation-card','title: Smartify Türstationen',
   'follow_sip_core: true','station_extension: '+pyaml(first),
   ...(stream?['stream: '+pyaml(stream)]:[]),'mode: mse',
   'camera_mode: always','show_sip: true','show_status: true',
   '# Die Kamera- und Aktionszuordnung kommt automatisch aus SIP Core:',
   '# popup_config.smartify.camera_by_caller',''].join('\n');
}
function camChanged(){cameraMappingSaved=false;$('camSavedState').textContent='● Ungespeicherte Änderungen – bitte „dauerhaft speichern“ klicken.';}
function camRefresh(){
 const rows=$('camRows');rows.replaceChildren();
 for(const [num,v] of mappingEntries()){
   const b=document.createElement('button');b.type='button';b.textContent=num+' · '+v.label+' → '+v.stream+' ('+v.mode.toUpperCase()+')';
   b.style.cssText='display:block;width:100%;margin:5px 0;text-align:left';b.onclick=()=>{
     $('camCaller').value=num;$('camLabel').value=v.label;$('camStream').value=v.stream;$('camStreamPreview').replaceChildren();
     $('camMode').value=v.mode;$('camCameraMode').value=v.camera_mode||'always';
     $('camDoor').value=v.door||'';$('camLight').value=v.light||'';$('camBell').value=v.bell||'';entityInfoAll();
     $('camCaller').scrollIntoView({behavior:'smooth',block:'center'});$('camCaller').focus({preventScroll:true});
   };rows.appendChild(b);
 }
 if(!callerCameras.size)rows.textContent='Noch keine Station zugeordnet.';
 $('camYaml').value=cameraYaml();$('camCardYaml').value=cameraCardYaml();
}
async function camLoad(){
 try{
   const data=await request('api/camera-mapping');
   cameraMappingHash=data.hash;cameraMappingSaved=true;
   callerCameras.clear();
   for(const [number,v] of Object.entries(data.mapping||{}))callerCameras.set(number,v);
   camRefresh();
   $('camSavedState').textContent=data.saved?'✓ '+callerCameras.size+' Zuordnung(en) aus Manager geladen. SIP Core separat aktivieren.':'Noch kein Mapping gespeichert. Zum Start eine Station hinzufügen.';
 }catch(e){msg('Kamera-Zuordnungen konnten nicht geladen werden: '+e.message);}
}
$('camLoad').onclick=camLoad;
$('camSave').onclick=async()=>{
 if(cameraMappingHash===null){msg('Bitte Zuordnungen zuerst laden');return;}
 if(!confirm('Kamera-Zuordnungen dauerhaft im Manager speichern? Die aktive SIP-Core-Konfiguration bleibt unverändert.'))return;
 try{
   const mapping=Object.fromEntries(callerCameras);
   const data=await request('api/camera-mapping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mapping,hash:cameraMappingHash})});
   cameraMappingHash=data.hash;cameraMappingSaved=true;
   $('camSavedState').textContent='✓ '+data.count+' Zuordnung(en) dauerhaft gespeichert. Jetzt Popup-YAML in SIP Core übernehmen.';
   msg('Kamerazuordnungen im Manager gespeichert. SIP Core noch unverändert.');
 }catch(e){msg('Nicht gespeichert: '+e.message);}
};
$('camAdd').onclick=()=>{
 const id=value('camCaller'),label=value('camLabel'),stream=value('camStream'),mode=value('camMode'),camera_mode=value('camCameraMode'),door=value('camDoor'),light=value('camLight'),bell=value('camBell');
 if(!/^\d{1,8}$/.test(id)||!/^[A-Za-z0-9_-]{1,64}$/.test(stream)||!isEntity(door)||!isEntity(light)||!isEntity(bell)||label.length>80){msg('Nummer, Streamname oder Entitäts-ID ungültig');return;}
 callerCameras.set(id,{label,stream,mode,camera_mode,door,light,bell});camRefresh();camChanged();
};
$('camRemove').onclick=()=>{const id=value('camCaller');if(!callerCameras.has(id))return;if(!confirm('Kamerazuordnung für '+id+' entfernen?'))return;callerCameras.delete(id);camRefresh();camChanged();};
$('camToDraft').onclick=()=>mergeIntoDraft($('camYaml').value,'Kamera-Zuordnung');
camRefresh();camLoad();presetBuild(true);

// Versionen: einzige Quelle ist das Add-on (config.yaml + FRONTEND_VERSIONS in app.py).
function applyVersions(d){
 if(d.version)$('appVersion').textContent='v'+d.version;
 const fe=d.frontend||{};
 document.querySelectorAll('[data-version]').forEach(el=>{const v=fe[el.dataset.version];if(v)el.textContent=v;});
 if(fe.popup)$('presetKindSmartify').textContent='Smartify Doorstation v'+fe.popup+' (Kamera, Mikrofon, Tür & Licht)';
}

// Entitätsvorschläge: Domains und Schlüsselwörter je Feldtyp; Kontext (Bezeichnung/Stream) hebt passende Entitäten nach oben.
const ENTITY_ROLES={
 bell:{domains:['binary_sensor','event','sensor'],words:['klingel','doorbell','bell','ringing','taste','button_press'],avoid:['fenster','window','temperatur','battery','batterie'],classes:['occupancy','sound','vibration','doorbell']},
 door:{domains:['switch','lock','button','input_button','script','input_boolean','cover'],words:['haustur','haustuer','tuer','door','offner','oeffner','opener','gate','garagentor','relais','relay','schloss','lock'],avoid:['licht','light','lampe','steckdose','plug'],classes:['door','gate','garage']},
 light:{domains:['light','switch'],words:['licht','light','lampe','leuchte','eingang','aussen','vordach','porch'],avoid:['haustur','haustuer','tuer','door','offner','oeffner','schloss','lock'],classes:[]}
};
let entityIndex=null, entityIndexPromise=null;
function ensureEntityIndex(){
 if(entityIndex)return Promise.resolve(entityIndex);
 if(!entityIndexPromise)entityIndexPromise=request('api/entities').then(d=>{entityIndex=d.available?d.entities:[];if(!d.available)console.info('Entitätsvorschläge nicht verfügbar:',d.message);if(!allEntities.length)allEntities=entityIndex;return entityIndex}).catch(()=>{entityIndexPromise=null;return []});
 return entityIndexPromise;
}
function normText(t){return String(t||'').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'')}
function contextTokens(ctx){
 const src=ctx==='cam'?[value('camLabel'),value('camStream')]:ctx==='sip'?[value('sipStream')]:[value('presetStream')];
 return [...new Set(src.join(' ').split(/[^a-z0-9äöüß]+/i).map(normText).filter(t=>t.length>=3))];
}
function scoreEntity(e,role,tokens){
 const r=ENTITY_ROLES[role],dom=e.entity_id.split('.')[0],hay=normText(e.entity_id+' '+e.name);
 let s=10-r.domains.indexOf(dom);
 for(const w of r.words)if(hay.includes(normText(w)))s+=6;
 for(const w of r.avoid)if(hay.includes(normText(w)))s-=12;
 if(e.device_class&&r.classes.includes(e.device_class))s+=5;
 for(const t of tokens)if(hay.includes(t))s+=8;
 if(e.state==='unavailable')s-=4;
 return s;
}
function fillDatalist(role,ctx){
 const dl=$({bell:'dlBell',door:'dlDoor',light:'dlLight'}[role]);if(!dl||!entityIndex)return;
 const r=ENTITY_ROLES[role],tokens=contextTokens(ctx);
 const list=entityIndex.filter(e=>r.domains.includes(e.entity_id.split('.')[0]))
  .map(e=>[scoreEntity(e,role,tokens),e]).sort((a,b)=>b[0]-a[0]||a[1].entity_id.localeCompare(b[1].entity_id)).slice(0,250);
 dl.replaceChildren(...list.map(([,e])=>{const o=document.createElement('option');o.value=e.entity_id;o.label=(e.name||e.entity_id)+(e.state==='unavailable'?' (nicht verfügbar)':'');return o}));
}
function entityInfo(input){
 let info=input.nextElementSibling;
 if(!info||!info.classList.contains('ent-info')){info=document.createElement('small');info.className='ent-info';input.after(info)}
 const v=input.value.trim(),role=input.dataset.entityRole;
 if(!v){info.className='ent-info';info.textContent=entityIndex&&entityIndex.length?'Tippen oder Feld anklicken für Vorschläge':'';return}
 if(!/^[a-z_]+\.[A-Za-z0-9_]+$/.test(v)){info.className='ent-info bad';info.textContent='✗ Keine gültige Entitäts-ID (Format domain.objekt_id)';return}
 if(!entityIndex){info.className='ent-info';info.textContent='';return}
 const hit=entityIndex.find(e=>e.entity_id===v);
 if(!hit){info.className='ent-info warn';info.textContent='⚠ In Home Assistant nicht gefunden – Schreibweise prüfen';return}
 const okDomain=ENTITY_ROLES[role].domains.includes(v.split('.')[0]);
 info.className='ent-info '+(okDomain&&hit.state!=='unavailable'?'ok':'warn');
 info.textContent=(okDomain?'✓ ':'⚠ Ungewöhnliche Domain für dieses Feld · ')+(hit.name||v)+(hit.state?' · Zustand: '+hit.state:'');
}
function entityInfoAll(){document.querySelectorAll('[data-entity-role]').forEach(entityInfo)}
function resolveFriendlyName(input){
 // Wer den Anzeigenamen statt der ID eintippt oder auswählt, bekommt automatisch die Entitäts-ID.
 const v=input.value.trim();if(!v||!entityIndex||/^[a-z_]+\.[A-Za-z0-9_]+$/.test(v))return;
 const role=ENTITY_ROLES[input.dataset.entityRole],q=normText(v);
 const hits=entityIndex.filter(e=>role.domains.includes(e.entity_id.split('.')[0])&&normText(e.name)===q);
 if(hits.length===1)input.value=hits[0].entity_id;
}
document.querySelectorAll('[data-entity-role]').forEach(input=>{
 const prepare=()=>ensureEntityIndex().then(()=>{fillDatalist(input.dataset.entityRole,input.dataset.entityContext);entityInfo(input)});
 input.addEventListener('focus',prepare);
 input.addEventListener('input',()=>entityInfo(input));
 input.addEventListener('change',()=>{resolveFriendlyName(input);entityInfo(input)});
});
ensureEntityIndex().then(entityInfoAll);

// ---------------------------------------------------------------- Ab 1.2.0
const post=(path,body)=>request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const ICON={error:'✗',warn:'⚠',info:'ℹ',ok:'✓'};
function renderIssues(box,issues,withLine){
 box.replaceChildren(...issues.map(i=>{const d=document.createElement('div');d.className='issue '+i.level;d.textContent=(ICON[i.level]||'•')+' '+(withLine&&i.line?'Zeile '+i.line+': ':'')+i.message;return d}));
}
function fillHelpCommands(){
 const c=asteriskContainer;
 $('helpCmds').value=['pjsip show transports','pjsip reload','dialplan reload','dialplan show 600@default','pjsip show contacts'].map(x=>`docker exec ${c} asterisk -rx "${x}"`).join('\n');
}
fillHelpCommands();

// Asterisk-Dateien prüfen
async function lintEditor(){
 const box=$('lintResult');
 try{const d=await post('api/lint',{name:$('filename').value,content:$('editor').value});
  if(!d.issues.length){box.className='note';box.textContent='✓ Keine Auffälligkeiten gefunden.';return d}
  box.className='note caution';renderIssues(box,d.issues,true);return d}
 catch(e){box.textContent='Prüfung nicht möglich: '+e.message;return null}
}
$('lintFile').onclick=lintEditor;
$('fixHash').onclick=()=>{
 const ed=$('editor');let n=0;
 ed.value=ed.value.split('\n').map(l=>{if(/^\s*#(?!\s*(include|tryinclude|exec)\b)/i.test(l)){n++;return l.replace('#',';')}return l}).join('\n');
 msg(n?n+' Kommentarzeile(n) auf „;“ umgestellt – noch nicht gespeichert':'Keine „#“-Kommentare gefunden');lintEditor();
};

// go2rtc-Streams: Vorschläge und Test
let streamsLoaded=false;
async function loadStreams(){
 streamsLoaded=true;
 try{const d=await request('api/go2rtc/streams');
  $('dlStream').replaceChildren(...(d.streams||[]).map(n=>{const o=document.createElement('option');o.value=n;return o}));
  if(!d.available)console.info('go2rtc:',d.message);}catch(e){streamsLoaded=false}
}
['camStream','sipStream','presetStream'].forEach(id=>$(id).addEventListener('focus',()=>{if(!streamsLoaded)loadStreams()}));
let previewUrl=null;
$('camStreamTest').onclick=async()=>{
 const name=value('camStream'),box=$('camStreamPreview');
 if(!/^[A-Za-z0-9_-]{1,64}$/.test(name)){msg('Gültigen Streamnamen eingeben');return}
 box.textContent='Hole Bild von „'+name+'“ …';
 try{const r=await fetch('api/go2rtc/frame?src='+encodeURIComponent(name)+'&t='+Date.now());
  if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.error||'Kein Bild')}
  if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=URL.createObjectURL(await r.blob());
  const img=document.createElement('img');img.src=previewUrl;img.alt='Standbild '+name;
  const ok=document.createElement('div');ok.className='issue ok';ok.textContent='✓ Stream liefert Bild';box.replaceChildren(img,ok);
 }catch(e){const d=document.createElement('div');d.className='issue error';d.textContent='✗ '+e.message;box.replaceChildren(d)}
};

// AMI-Befehle
async function runAmi(command,isReload){
 if(isReload&&!confirm(command+' jetzt ausführen? Laufende Gespräche bleiben normalerweise bestehen.'))return;
 $('amiOut').value='Führe „'+command+'“ aus …';
 try{const d=await post('api/ami/command',{command,confirm:isReload===true});$('amiOut').value='> '+d.command+'\n\n'+d.output}
 catch(e){$('amiOut').value='Fehler: '+e.message}
}
document.querySelectorAll('[data-ami]').forEach(b=>b.onclick=()=>runAmi(b.dataset.ami,/reload$/.test(b.dataset.ami)));
$('amiEndpoint').onclick=()=>{const a=value('amiArg');if(!/^[A-Za-z0-9_.+-]{1,60}$/.test(a)){msg('Nebenstelle eingeben, z. B. 104');return}runAmi('pjsip show endpoint '+a,false)};
$('amiDialplan').onclick=()=>{const a=value('amiArg');if(!/^[A-Za-z0-9_.+-]{0,40}@?[A-Za-z0-9_-]{1,40}$/.test(a)){msg('Kontext eingeben, z. B. 600@default');return}runAmi('dialplan show '+a,false)};

// SIP Core: aktive Konfiguration, Prüfung, Unterschiede, Übernahme, Zusammenführen
let activeHash=null,diffedContent=null;
async function loadActive(){const d=await request('api/sip-core/active');activeHash=d.hash;return d}
$('draftFromActive').onclick=async()=>{
 const ed=$('draftEditor');if(ed.value.trim()&&!confirm('Editor-Inhalt durch die aktive SIP-Core-Konfiguration ersetzen? Ungespeicherte Änderungen gehen verloren.'))return;
 try{const d=await loadActive();ed.value=d.content;if(draftHash===null){draftHash=(await request('api/sip-core-draft')).hash}msg('Aktive SIP-Core-Konfiguration geladen – noch nicht als Entwurf gespeichert')}catch(e){msg('Nicht geladen: '+e.message)}
};
$('draftCheck').onclick=async()=>{try{const d=await post('api/check/users',{content:$('draftEditor').value});renderIssues($('draftCheckResult'),d.issues)}catch(e){renderIssues($('draftCheckResult'),[{level:'error',message:e.message}])}};
$('draftDiff').onclick=async()=>{
 const out=$('draftDiffOut');out.hidden=false;out.textContent='Vergleiche …';
 try{const d=await post('api/sip-core/diff',{content:$('draftEditor').value});activeHash=d.active_hash;diffedContent=$('draftEditor').value;
  out.textContent=(d.warnings.length?d.warnings.map(w=>'⚠ '+w).join('\n')+'\n\n':'')+(d.changed?(d.diff||'(nur Reihenfolge/Formatierung unterschiedlich)'):'Keine Unterschiede zur aktiven Konfiguration.');}
 catch(e){out.textContent='Fehler: '+e.message}
};
$('draftApply').onclick=async()=>{
 const content=$('draftEditor').value;
 if(diffedContent!==content||!activeHash){msg('Bitte zuerst „Unterschiede zu SIP Core“ für den aktuellen Inhalt ansehen');return}
 if(!confirm('Diesen Entwurf jetzt in die SIP-Core-Integration übernehmen?\n\nDie aktive Konfiguration wird vorher gesichert. Danach alle Geräte neu laden.'))return;
 try{const d=await post('api/sip-core/apply',{content,active_hash:activeHash,confirm:true});msg(d.note);$('draftResult').textContent=d.note+' Backup: '+d.backup;diffedContent=null;activeHash=null}
 catch(e){msg('Nicht übernommen: '+e.message);$('draftResult').textContent='Nicht übernommen: '+e.message}
};
async function mergeIntoDraft(snippet,label){
 const ed=$('draftEditor');let base=ed.value;
 try{
  if(!base.trim()){
   const saved=await request('api/sip-core-draft');draftHash=saved.hash;base=saved.content;
   if(!base.trim()){try{base=(await loadActive()).content}catch(e){if(!confirm('Aktive SIP-Core-Konfiguration nicht erreichbar ('+e.message+'). Nur den Baustein als Entwurf verwenden?'))return}}
  }
  const d=await post('api/sip-core/merge',{base,snippet});
  ed.value=d.content;
  const out=$('draftDiffOut');out.hidden=false;
  out.textContent=label+' zusammengeführt – noch NICHT gespeichert.'+(d.protected_skipped.length?'\nNicht übernommen (geschützt): '+d.protected_skipped.join(', '):'')+(d.note?'\n'+d.note:'')+'\n\n'+(d.diff||'Keine Änderung.');
  document.querySelector('[data-tab="draft"]').click();msg(label+' in den Entwurf eingefügt – prüfen, speichern, übernehmen');
 }catch(e){msg('Zusammenführen nicht möglich: '+e.message)}
}

// Prüfungen
$('checkUsers').onclick=async()=>{const box=$('checkUsersResult');box.textContent='Prüfe …';try{const d=await request('api/check/users');renderIssues(box,d.issues);const head=document.createElement('p');head.className='hint';head.textContent='Quelle: '+d.source+' · '+d.users+' Teilnehmer · '+d.endpoints+' Asterisk-Nebenstellen · '+d.persons+' HA-Personen';box.prepend(head)}catch(e){renderIssues(box,[{level:'error',message:e.message}])}};
$('checkFiles').onclick=async()=>{
 const box=$('checkFilesResult');box.textContent='Prüfe …';
 try{const st=await request('api/status');const out=[];
  for(const name of st.files){const f=await request('api/file/'+name);if(f.source!=='custom')continue;
   const d=await post('api/lint',{name,content:f.content});
   const first=d.issues.find(i=>i.level==='error')||d.issues.find(i=>i.level==='warn');
   out.push({level:d.errors?'error':d.warnings?'warn':'ok',message:name+': '+(first?d.errors+' Fehler, '+d.warnings+' Hinweise – z. B. Zeile '+first.line+': '+first.message:'keine Auffälligkeiten')});}
  renderIssues(box,out.length?out:[{level:'info',message:'Keine Custom-Dateien vorhanden.'}]);
 }catch(e){renderIssues(box,[{level:'error',message:e.message}])}
};

// Teilnehmer aus SIP Core in den Generator
$('usersFromCore').onclick=async()=>{try{const d=await loadActive();$('userList').value=d.users.map(u=>[u.extension,u.ha_username,u.display_name||u.ha_username].join(',')).join('\n');msg(d.users.length+' Teilnehmer übernommen (ohne Passwörter)')}catch(e){msg('Nicht verfügbar: '+e.message)}};

// Export / Import
$('exportBtn').onclick=async()=>{try{const d=await request('api/export');const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='smartify-export-'+d.created.slice(0,16).replace(/[:T]/g,'-')+'.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000);msg('Export erstellt. Falls kein Download startet: „Als Text anzeigen“.')}catch(e){msg(e.message)}};
$('exportShow').onclick=async()=>{try{const d=await request('api/export');const t=$('exportOut');t.hidden=false;t.value=JSON.stringify(d,null,2)}catch(e){msg(e.message)}};
$('importFile').onchange=()=>{const f=$('importFile').files[0];if(!f)return;if(f.size>2_000_000){msg('Datei zu groß');return}const r=new FileReader();r.onload=()=>{$('importText').value=r.result};r.readAsText(f)};
$('importBtn').onclick=async()=>{
 let data;try{data=JSON.parse($('importText').value)}catch(e){msg('Kein gültiges JSON');return}
 if(!confirm('Kamera-Zuordnungen und SIP-Core-Entwurf dieser Installation durch den Import ersetzen? Der bisherige Stand wird gesichert.'))return;
 try{const d=await post('api/import',{data,confirm:true});msg(d.note);await camLoad();$('draftLoad').click()}catch(e){msg('Import fehlgeschlagen: '+e.message)}
};

$('amiDiagnose').onclick=async()=>{const box=$('liveResults');box.textContent='Prüfe AMI Schritt für Schritt …';try{const d=await request('api/ami/diagnose');renderIssues(box,d.steps)}catch(e){box.textContent='✗ '+e.message}};


// --- Version 1.3.0: Nummernbelegung und aktive Konfiguration ---
let numberPlan=null, currentSipUsers=[], sipWorkspaceLoaded=false;
function slotStatus(id, num){
 const el=$(id);if(!el)return;
 if(!num){el.className='slot-info';el.textContent='Nummer eingeben';return;}
 if(!validExt(num)){el.className='slot-info busy';el.textContent='Nur 2–6 Ziffern zulässig';return;}
 if(!numberPlan){el.className='slot-info caution';el.textContent='Belegung noch nicht eingelesen';return;}
 const usages=numberPlan.used[num];
 el.className='slot-info '+(usages?'busy':'caution');
 el.textContent=usages?'✗ Belegt: '+usages.join(' · '):'In gelesenen Dateien nicht gefunden – Laufzeitprüfung weiterhin nötig';
}
function updateSlotStatuses(){
 const n=value('epExt');slotStatus('epAvailability',n);slotStatus('groupAvailability',value('groupNum'));
 const occupied=Boolean(numberPlan?.used?.[n]);
 const valid=validExt(n)&&Boolean(numberPlan);
 for(const id of ['makeEndpoint','epToFile','epDirectSave'])$(id).disabled=!valid||occupied;
 const edit=$('epEditExisting');if(edit){
  edit.hidden=!occupied;edit.disabled=!occupied;
  edit.textContent=numberPlan?.endpoints?.some(e=>e.extension===n)?'Vorhandene Nebenstelle bearbeiten':numberPlan?.dialplan?.some(e=>e.number===n)?'Rufziel/Rufgruppe anzeigen':'Belegte Nummer prüfen';
 }
 if(occupied){
  $('epOut').value='';
  $('epPreviewStatus').textContent='Nebenstelle '+n+' existiert bereits – bitte den vorhandenen Eintrag bearbeiten oder löschen, keine Neuanlage.';
 }
 updateNewRowAvailability();
}
function updateNewRowAvailability(){
 const tr=document.querySelector('#pjsipTable tr[data-new-pjsip]');if(!tr)return;
 const n=cellValue(tr,'number');
 const busy=Boolean(numberPlan?.used?.[n])||Boolean(pjsipTableState?.rows?.some(r=>r.number===n));
 const ok=validExt(n)&&Boolean(numberPlan)&&!busy;
 const btn=tr.querySelector('[data-add-pjsip]');if(btn)btn.disabled=!ok;
 const note=tr.querySelector('[data-new-status]');
 if(note){note.textContent=!n?'Neue Nummer eingeben':!validExt(n)?'Ungültige Nummer':!numberPlan?'Belegung nicht verfügbar':busy?'✗ Bereits belegt – vorhandenen Eintrag bearbeiten':'In eingelesenen Dateien nicht belegt';note.className=busy?'slot-info busy':'slot-info caution';}
 const jump=tr.querySelector('[data-new-edit]');if(jump)jump.hidden=!busy;
}

function numberTable(items,columns){
 if(!items.length)return '<p class="hint">Keine Einträge in den lesbaren Dateien erkannt.</p>';
 return '<table><thead><tr>'+columns.map(c=>'<th>'+esc(c[0])+'</th>').join('')+'</tr></thead><tbody>'+items.map(item=>'<tr>'+columns.map(c=>'<td>'+esc(String(c[1](item)??'–'))+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
}
async function getFreshNumberPlan(){
 try{const d=await request('api/number-plan');numberPlan=d;updateSlotStatuses();return d;}
 catch(e){numberPlan=null;updateSlotStatuses();msg('Belegung nicht prüfbar: '+e.message);return null;}
}
async function refreshNumberPlan(){
 const plan=await getFreshNumberPlan();if(!plan){$('groupsExisting').textContent='Nummernbelegung derzeit nicht verfügbar';return;}
 const busy=Object.keys(plan.used||{}).length;
 $('numberState').textContent=busy+' Nummern in lesbarer Konfiguration gefunden · '+(plan.warnings?.length?'⚠ '+plan.warnings.join(' · ')+' · ':'')+'Nicht gefunden heißt nicht sicher frei.';
 renderUnifiedInventory();
 renderDialplanRows(plan.dialplan);
 const others=plan.dialplan.filter(x=>x.kind!=='Rufgruppe');
 $('groupsOther').textContent=others.length+' weitere numerische Dialplan-Ziele erkannt. Diese Nummern können ebenfalls nicht bedenkenlos wiederverwendet werden.';
 const options=$('dlEndpoints');options.replaceChildren(...plan.endpoints.filter(e=>validExt(e.extension)).map(e=>{const o=document.createElement('option');o.value=e.extension;o.label=e.display_name||e.extension;return o}));
 renderTargetChoices(plan.endpoints);
}
function renderTargetChoices(endpoints){
 let target=$('targetChoices');if(!target){target=document.createElement('div');target.id='targetChoices';target.className='toolbar';$('targetsState').after(target)}
 target.replaceChildren();
 for(const ep of endpoints.filter(e=>validExt(e.extension))){
  const btn=document.createElement('button');btn.type='button';btn.textContent=ep.extension+(ep.display_name?' · '+ep.display_name:'');btn.title='Als Rufgruppen-Ziel hinzufügen/entfernen';
  btn.onclick=()=>{const values=value('groupTargets').split(',').map(x=>x.trim()).filter(Boolean);const i=values.indexOf(ep.extension);if(i>=0)values.splice(i,1);else values.push(ep.extension);$('groupTargets').value=values.join(',');renderTargetChoices(endpoints)};
  btn.classList.toggle('active',value('groupTargets').split(',').map(x=>x.trim()).includes(ep.extension));target.append(btn);
 }
}
$('groupTargets').addEventListener('input',()=>{if(numberPlan)renderTargetChoices(numberPlan.endpoints)});
$('epExt').addEventListener('input',updateSlotStatuses);
$('groupNum').addEventListener('input',updateSlotStatuses);
$('groupsRefresh').onclick=refreshNumberPlan;
$('groupsOpenFile').onclick=()=>{$('filename').value='extensions.conf';showPanel('pjsip');loadFile()};

let autoSecretState=null;
$('autoSecretPreview').onclick=async()=>{
 const status=$('autoSecretStatus');autoSecretState=null;$('autoSecretApply').disabled=true;$('autoSecretUsers').replaceChildren();status.textContent='Prüfe Asterisk und SIP Core …';
 try{const d=await request('api/sip-core/auto-secret');autoSecretState=d;
 status.textContent='Auto Add Extensions: '+(d.auto_add_enabled?'aktiv':'inaktiv')+' · Auto Add Secret: '+(d.secret_present?'vorhanden':'nicht gesetzt')+' · '+d.count_changed+' Passwörter abweichend. Das Geheimnis bleibt verborgen.';
 $('autoSecretUsers').textContent=(d.users||[]).map(u=>u.extension+' '+(u.display_name||'')+' – '+(u.change?'wird überschrieben':'bereits gleich')).join(' | ');
 $('autoSecretApply').disabled=!(d.auto_add_enabled&&d.secret_present&&d.count_changed>0);
 }catch(e){status.textContent='Prüfung fehlgeschlagen: '+e.message;}
};
$('autoSecretApply').onclick=async()=>{
 if(!autoSecretState||!autoSecretState.secret_present||!autoSecretState.auto_add_enabled)return;
 const n=autoSecretState.count_changed;
 if(!confirm('Achtung: '+n+' bestehende SIP-Core-Passwörter durch Asterisk Auto Add Secret ersetzen? Manuelle Asterisk-Nebenstellen können danach ihre Registrierung verlieren. Vorher wird eine Sicherung erstellt.'))return;
 const phrase=prompt('Zur Bestätigung exakt ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN eingeben:');
 if(phrase!=='ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN')return;
 $('autoSecretApply').disabled=true;
 try{const d=await post('api/sip-core/auto-secret/apply',{active_hash:autoSecretState.active_hash,confirm:phrase});
 $('autoSecretStatus').textContent='Synchronisierung: '+d.changed+' geändert · Prüfung: '+(d.verified?'OK':'nicht eindeutig')+' · Backup: '+(d.backup||'nicht benötigt')+'. '+d.note;
 autoSecretState=null;await refreshSipWorkspace();}catch(e){$('autoSecretStatus').textContent='Synchronisierung fehlgeschlagen: '+e.message;}
};
async function refreshSipWorkspace(){
 const out=$('sipActiveStatus'),sel=$('sipUserPick');out.textContent='Lese Asterisk-Nebenstellen und SIP-Core-Konfiguration …';
 try{
  const ep=await request('api/endpoints');
  const list=ep.endpoints.filter(e=>validExt(e.extension));
  const prior=sel.value;
  sel.replaceChildren();const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Nebenstelle auswählen';sel.append(placeholder);
  for(const e of list){const opt=document.createElement('option');opt.value=e.extension;opt.textContent=e.extension+' · '+(e.display_name||'Asterisk-Endpoint');sel.append(opt)}
  if(list.some(e=>e.extension===prior))sel.value=prior;
  let core;
  try{core=await loadActive()}catch(e){currentSipUsers=[];out.textContent='Asterisk: '+list.length+' erkannte Nebenstellen. Aktives SIP Core nicht erreichbar: '+e.message;return}
  currentSipUsers=core.users||[];
  out.textContent='Aktives SIP Core gelesen · '+currentSipUsers.length+' Teilnehmer · '+list.length+' aus Asterisk-Konfigurationsdateien erkannte Nebenstellen. Popup/Video-Einstellungen sind im YAML-Editor unten verfügbar.';
  const set=new Set(list.map(e=>e.extension));
  $('sipCurrentUsers').innerHTML=numberTable(currentSipUsers,[['Nr.',x=>x.extension],['Name',x=>x.display_name||'–'],['HA-Benutzer',x=>x.ha_username||'–'],['Asterisk',x=>set.has(x.extension)?'Erkannt':'⚠ Nicht erkannt']]);
  if(!$('draftEditor').value.trim()){
   $('draftEditor').value=core.content;
   if(draftHash===null){draftHash=(await request('api/sip-core-draft')).hash}
  }
  sipWorkspaceLoaded=true;
 }catch(e){out.textContent='Fehler beim Einlesen: '+e.message}
}
$('sipRefresh').onclick=refreshSipWorkspace;
$('sipUserPick').addEventListener('change',()=>{
 const u=currentSipUsers.find(x=>x.extension===value('sipUserPick'));
 $('sipHaUser').value=u?.ha_username||'';$('sipDisplay').value=u?.display_name||'';$('sipUserPassword').value='';
 $('sipUserMessage').textContent=u?'Bereits in SIP Core vorhanden – Änderungen erhalten das Passwort.':'In Asterisk vorhanden, in SIP Core noch nicht eingetragen.';
});
$('sipAddUser').onclick=async()=>{
 const num=value('sipUserPick');if(!num){msg('Zuerst eine vorhandene Asterisk-Nebenstelle auswählen');return}
 let base=$('draftEditor').value;
 if(!base.trim()){try{base=(await loadActive()).content}catch(e){msg('Keinen SIP-Core-Entwurf geladen: '+e.message);return}}
 try{
  const d=await post('api/sip-core/stage-user',{content:base,extension:num,ha_username:value('sipHaUser'),display_name:value('sipDisplay'),password:$('sipUserPassword').value});
  $('draftEditor').value=d.content;$('sipUserPassword').value='';diffedContent=null;activeHash=null;
  $('sipUserMessage').textContent=d.message+' · Vor Übernahme den Unterschiedsvergleich durchführen.';
  msg(d.message);
 }catch(e){$('sipUserMessage').textContent='Nicht übernommen: '+e.message;msg('Nicht übernommen: '+e.message)}
};
$('sipEditYaml').onclick=()=>$('sipYamlWorkspace').scrollIntoView({behavior:'smooth',block:'start'});
// Initial load for the first work area; no asynchronous changes to Asterisk.
refreshNumberPlan().then(refreshEndpoints);

// Non-destructive staging in the existing file editor: never write or reload automatically.
async function prepareInAsteriskFile(kind){
 const ep=kind==='endpoint',target=ep?'pjsip_custom.conf':value('groupSaveFile');
 const snippet=$(ep?'epOut':'routeOut').value.trim(),n=value(ep?'epExt':'groupNum');
 const initialGeneration=endpointGeneration;
 if(!snippet){msg('Zuerst eine gültige Konfigurationsvorschau erzeugen');return}
 const plan=await getFreshNumberPlan();if(!plan || (ep && initialGeneration!==endpointGeneration))return;
 if(plan.used[n]){msg('Nummer '+n+' ist inzwischen belegt – keine Übernahme');return;}
 if(ep ? !snippet.includes('['+n+']') : !snippet.includes('exten => '+n+',1,')){msg('Vorschau passt nicht zur eingegebenen Nummer. Bitte neu generieren.');return;}
 if(loadedName!==target&&$('editor').value.trim()&&loadedSource==='custom'&&!confirm('Vorhandene, möglicherweise noch nicht gespeicherte Editor-Inhalte werden beim Dateiwechsel verworfen. Fortfahren?'))return;
 if(loadedName!==target){$('filename').value=target;showPanel('pjsip');await loadFile();}
 else showPanel('pjsip');
 if(ep && initialGeneration!==endpointGeneration){msg('Einstellungen während der Übernahme geändert – Vorschau neu erzeugen.');return;}
 if(loadedName!==target||loadedSource!=='custom'){
  msg(target+' ist keine bearbeitbare Custom-Datei. Zuerst prüfen/anlegen, welche Datei Asterisk wirklich einliest. Nichts geändert.');
  return;
 }
 const original=$('editor').value;
 if(ep){
  if(new RegExp('^\\['+n+'\\]','m').test(original)){
   msg('Dieser Abschnitt ist in '+target+' schon definiert');return;
  }
  $('editor').value=original.trimEnd()+'\n\n'+snippet+'\n';
 }else{
  const context=value('groupContext');
  const match=new RegExp('^[ \t]*\\['+context+'\\][ \t]*(?:;[^\n]*)?$','im').exec(original);
  if(!match){msg('Kein vorhandener ['+context+']-Kontext in der Custom-Datei. Bitte den wirksamen Dialplan prüfen; kein zusätzlicher Kontext automatisch erzeugt.');return;}
  const after=match.index+match[0].length;
  const next=/^\s*\[[^\]\r\n]+\]/m.exec(original.slice(after));
  const pos=next?after+next.index:original.length;
  $('editor').value=original.slice(0,pos).trimEnd()+'\n'+snippet+'\n\n'+original.slice(pos).trimStart();
 }
 msg('Vorschlag im Datei-Editor eingefügt – noch NICHT gespeichert. Prüfen, dann mit Backup sichern und gezielt reloaden.');
}
$('epToFile').onclick=()=>prepareInAsteriskFile('endpoint');
$('groupToFile').onclick=()=>prepareInAsteriskFile('group');


// v1.3.3 · Structured AOR/Endpoint, outbound Cloud and SIP-dialplan tables.
let pjsipTableState=null;
function cellValue(tr,key){return tr.querySelector('[data-col="'+key+'"]')?.value?.trim()||''}
function fieldText(name,val,extra=''){
 return '<input '+extra+' data-col="'+name+'" value="'+esc(val??'')+'" autocomplete="off">';
}
function fieldChoice(name,value,options){
 return '<select data-col="'+name+'">'+options.map(opt=>'<option value="'+esc(opt)+'"'+(opt===value?' selected':'')+'>'+esc(opt)+'</option>').join('')+'</select>';
}
function advancedPjsipFields(st={}){
 const val=(key,defaultValue)=>st[key]??defaultValue;
 const text=(label,key,fallback,extra='')=>'<label>'+label+fieldText(key,val(key,fallback),extra)+'</label>';
 const yesno=(label,key,fallback)=>'<label>'+label+fieldChoice(key,val(key,fallback),['yes','no'])+'</label>';
 return '<details class="advanced-cell"><summary>11 Parameter</summary><div class="advanced-cell-grid">'+
  text('qualify_frequency','qualify_frequency','0','type="number" min="0" max="3600"')+
  text('minimum_expiration','minimum_expiration','60','type="number" min="1" max="86400"')+
  text('default_expiration','default_expiration','3600','type="number" min="1" max="86400"')+
  text('maximum_expiration','maximum_expiration','7200','type="number" min="1" max="86400"')+
  text('transport','transport','')+
  '<label>dtmf_mode'+fieldChoice('dtmf_mode',val('dtmf_mode','rfc4733'),['rfc4733','inband','info','auto','auto_info'])+'</label>'+
  yesno('direct_media','direct_media','no')+yesno('force_rport','force_rport','yes')+
  yesno('rewrite_contact','rewrite_contact','yes')+yesno('rtp_symmetric','rtp_symmetric','yes')+
  yesno('ice_support','ice_support','no')+'</div></details>';
}

function cloudSettingsFromRow(tr){
 const settings={transport:cellValue(tr,'transport'),allow:cellValue(tr,'allow')};
 for(const key of ['direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support']){
  const v=cellValue(tr,key);if(v)settings[key]=v;
 }
 return settings;
}
function cloudBoolean(key,val){
 return '<select data-col="'+key+'"><option value=""'+(!val?' selected':'')+'>nicht gesetzt</option>'+['yes','no'].map(x=>'<option value="'+x+'"'+(x===val?' selected':'')+'>'+x+'</option>').join('')+'</select>';
}
function renderCloudTable(data){
 const root=$('cloudTable');if(!root)return;
 const rows=data.cloud_endpoints||[];
 const cols=['Endpoint','Transport','Codecs','direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support','Aktion'];
 const bool=(key,val)=>cloudBoolean(key,val);
 root.innerHTML='<div class="edit-scroll dp-rows"><table class="edit-table"><thead><tr>'+cols.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>{
  const a=r.settings||{};
  return '<tr data-cloud="'+esc(r.name)+'"><td class="id-col">'+esc(r.name)+'</td><td>'+fieldText('transport',a.transport||'')+'</td><td>'+fieldText('allow',a.allow||'alaw,ulaw')+'</td>'+['direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support'].map(k=>'<td>'+bool(k,a[k])+'</td>').join('')+
  '<td>'+(r.editable?'<button type="button" data-cloud-save="'+esc(r.name)+'">Speichern</button>':'<small>'+esc(r.reason)+'</small>')+'</td></tr>';
 }).join('')+'</tbody></table></div>';
 root.querySelectorAll('[data-cloud-save]').forEach(btn=>btn.onclick=()=>saveCloudRow(btn.dataset.cloudSave,btn.closest('tr'),'edit'));
}
async function saveCloudRow(name,tr,operation){
 const settings=cloudSettingsFromRow(tr);
 if(!confirm('Ausgehenden SIP-Endpoint '+name+' in pjsip_custom.conf speichern? Backup, kein automatischer Reload.'))return;
 try{
  const d=await post('api/structured/cloud/save',{name,operation,settings,hash:pjsipTableState.hash});
  msg(d.note);await Promise.all([refreshPjsipTable(),refreshEndpoints()]);
 }catch(e){msg('Endpoint nicht gespeichert: '+e.message)}
}
$('cloudTableNew').onclick=()=>{
 if(pjsipTableState?.source!=='custom'){msg('pjsip_custom.conf zuerst als Custom-Datei anlegen.');return;}
 const tbody=$('cloudTable').querySelector('tbody');if(!tbody)return;
 if(tbody.querySelector('[data-new-cloud]')){tbody.querySelector('[data-col="name"]').focus();return;}
 const tr=document.createElement('tr');tr.dataset.newCloud='1';
 tr.innerHTML='<td>'+fieldText('name','','placeholder="linphone-cloud"')+'</td><td>'+fieldText('transport','transport-udp')+'</td><td>'+fieldText('allow','alaw,ulaw')+'</td>'+['direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support'].map(k=>'<td>'+fieldChoice(k,['direct_media','ice_support'].includes(k)?'no':'yes',['yes','no'])+'</td>').join('')+
 '<td><button data-add-cloud>Speichern</button><button data-cancel-cloud>Abbrechen</button></td>';
 tr.querySelector('[data-add-cloud]').onclick=()=>saveCloudRow(cellValue(tr,'name'),tr,'add');
 tr.querySelector('[data-cancel-cloud]').onclick=()=>tr.remove();
 tbody.prepend(tr);tr.querySelector('[data-col="name"]').focus();
};

async function refreshPjsipTable(){
 const root=$('pjsipTable');root.textContent='Lade PJSIP-Einstellungen …';
 try{
  const data=await request('api/structured/pjsip');pjsipTableState=data;
  if(data.source!=='custom'){
   if($('cloudTable'))$('cloudTable').textContent='custom/pjsip_custom.conf nicht vorhanden.';
   if(!data.rows?.length){root.textContent='Keine editierbaren Custom-PJSIP-Dateien gefunden. Vorhandene Nummern bleiben in der gemeinsamen Übersicht sichtbar. Die Default-Dateien sind schreibgeschützt.';renderUnifiedInventory();return;}
  }
  const rows=data.rows||[];
  const head=['Nr. / Datei','Name / Caller-ID','max_contacts','remove_existing','remove_unavailable','Kontext','Codecs','SIP-Anmeldename','Neues Passwort (optional)','Weitere AOR/Endpoint-Werte','Aktion'];
  root.innerHTML='<div class="edit-scroll dp-rows"><table class="edit-table"><thead><tr>'+head.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>{
   const row='<tr data-extension="'+esc(r.number)+'"><td class="id-col">'+esc(r.number)+'<small class="source-label">'+esc(r.file)+'</small></td>'+
     '<td class="name-col">'+fieldText('name',r.name)+'</td>'+
     '<td>'+fieldText('max_contacts',r.max_contacts,'type="number" min="1" max="100"')+'</td>'+
     '<td>'+fieldChoice('remove_existing',r.remove_existing,['yes','no'])+'</td>'+
     '<td>'+fieldChoice('remove_unavailable',r.remove_unavailable,['yes','no'])+'</td>'+
     '<td>'+fieldText('context',r.context)+'</td>'+
     '<td class="code-col">'+fieldText('codecs',r.codecs)+'</td>'+
     '<td>'+fieldText('username',r.username)+'</td>'+
     '<td class="pw-col"><input data-col="password" type="password" autocomplete="new-password" placeholder="unverändert"></td>'+
     '<td>'+advancedPjsipFields(r.settings)+'</td>'+
     '<td>'+(r.editable?'<button type="button" data-save-pjsip="'+esc(r.number)+'">Änderungen speichern</button> <button class="danger-button" type="button" data-delete-pjsip="'+esc(r.number)+'">Löschen …</button>':'<small>'+esc(r.reason)+'</small>')+'</td></tr>';
   return row;
  }).join('')+'</tbody></table></div>';
  root.querySelectorAll('[data-save-pjsip]').forEach(b=>b.onclick=()=>savePjsipTableRow(b.dataset.savePjsip,b.closest('tr')));
  root.querySelectorAll('[data-delete-pjsip]').forEach(b=>b.onclick=()=>deletePjsipTableRow(b.dataset.deletePjsip));
  renderCloudTable(data);
  renderUnifiedInventory();
  if(!rows.length)root.insertAdjacentHTML('beforeend','<p class="hint">Keine direkt bearbeitbaren Nebenstellen in custom/pjsip_custom.conf. Die vorhandenen Asterisk-Definitionen stehen in der Übersicht darüber.</p>');
 }catch(e){root.textContent='PJSIP-Tabelle nicht geladen: '+e.message;}
}
function buildTablePjsip(r,tr){
 const st=r.settings||{};
 const codecs=cellValue(tr,'codecs').split(',').map(x=>x.trim()).filter(Boolean);
 return SmartifyPjsip.build({
  extension:r.number,displayName:cellValue(tr,'name'),authUsername:cellValue(tr,'username'),
  context:cellValue(tr,'context'),password:tr.querySelector('[data-col="password"]').value,
  allowEmptyPassword:true,transport:cellValue(tr,'transport'),
  maxContacts:cellValue(tr,'max_contacts'),removeExisting:cellValue(tr,'remove_existing'),
  removeUnavailable:cellValue(tr,'remove_unavailable'),
  qualifyFrequency:cellValue(tr,'qualify_frequency'),minimumExpiration:cellValue(tr,'minimum_expiration'),
  defaultExpiration:cellValue(tr,'default_expiration'), maximumExpiration:cellValue(tr,'maximum_expiration'),
  codecs,dtmfMode:cellValue(tr,'dtmf_mode'),directMedia:cellValue(tr,'direct_media'),
  forceRport:cellValue(tr,'force_rport'),rewriteContact:cellValue(tr,'rewrite_contact'),
  rtpSymmetric:cellValue(tr,'rtp_symmetric'),iceSupport:cellValue(tr,'ice_support')
 });
}
async function savePjsipTableRow(n,tr){
 const row=pjsipTableState?.rows.find(r=>r.number===n);
 if(!row||!row.editable)return;
 let output;try{output=buildTablePjsip(row,tr);}catch(e){msg(e.message);return;}
 if(!confirm('Nebenstelle '+n+' in custom/'+row.file+' direkt speichern? Backup wird erstellt; bestehende Passwörter bleiben bei leerem Passwortfeld erhalten. Noch kein Reload.'))return;
 try{
  const data=await post('api/structured/pjsip/save',{operation:'edit',number:n,file:row.file,snippet:output.snippet,hash:row.hash});
  msg(data.note);await Promise.all([refreshPjsipTable(),refreshNumberPlan(),refreshEndpoints()]);
 }catch(e){msg('Nicht gespeichert: '+e.message)}
}
async function deletePjsipTableRow(n){
 const row=pjsipTableState?.rows.find(x=>x.number===n);
 if(!row?.editable){msg(row?.reason||'Diese Definition ist nur über den Datei-Editor bearbeitbar.');return;}
 // Refresh the references immediately before displaying any destructive confirmation.
 const plan=await getFreshNumberPlan();if(!plan)return;
 const deps=[...(plan.dialplan||[]).filter(r=>(r.targets||[]).includes(n))
   .map(r=>'Rufziel '+r.number+'@'+r.context+' ('+r.source+')'),
   ...(plan.sip_core_numbers||[]).filter(u=>u.number===n).map(u=>'SIP Core: '+(u.name||n))];
 if(deps.length){msg('Löschen derzeit gesperrt: '+n+' wird noch verwendet in '+deps.join(' · ')+'. Erst diese Verweise entfernen.');return;}
 if(!confirm('Nebenstelle '+n+' aus custom/'+row.file+' entfernen? Datei-Backup wird erstellt. Noch kein Reload.'))return;
 if(!confirm('Wirklich Nebenstelle '+n+' LÖSCHEN? Nur die Custom-Konfiguration wird geändert, kein Asterisk-Reload.'))return;
 try{
  const d=await post('api/structured/pjsip/save',{operation:'delete',number:n,file:row.file,hash:row.hash});
  msg(d.note);await Promise.all([refreshPjsipTable(),refreshNumberPlan(),refreshEndpoints()]);
 }catch(e){msg('Nicht gelöscht: '+e.message);}
}
async function saveNewPjsipDirect(){
 let output;try{output=SmartifyPjsip.build(endpointValues());}catch(e){msg(e.message);return;}
 const plan=await getFreshNumberPlan();if(!plan)return;
 if(plan.used[output.extension]){msg('Nummer '+output.extension+' ist bereits belegt – bitte vorhandene Nebenstelle bearbeiten.');return;}
 if(!confirm('Nebenstelle '+output.extension+' wirklich in custom/pjsip_custom.conf speichern? Vorher Nummernbelegung prüfen. Datei-Backup, aber KEIN automatischer Reload.'))return;
 try{
  const file=await request('api/file/pjsip_custom.conf');
  if(file.source==='default (nur lesen)'){msg('Default-Datei wird nicht überschrieben. Bitte die Custom-Datei anlegen.');return}
  const data=await post('api/structured/pjsip/save',{operation:'add',number:output.extension,snippet:output.snippet,hash:file.hash});
  $('epPassword').value='';invalidateEndpointPreview();msg(data.note);
  await Promise.all([refreshPjsipTable(),refreshNumberPlan(),refreshEndpoints()]);
 }catch(e){msg('Nicht gespeichert: '+e.message)}
}
$('epDirectSave').onclick=saveNewPjsipDirect;
$('pjsipTableRefresh').onclick=refreshPjsipTable;
$('pjsipTableNew').onclick=()=>{$('pjsipDetails').open=true;appendPjsipRow();};
$('reloadPjsip').onclick=()=>{if(confirm('Asterisk pjsip reload ausführen? Registrierte Telefone können betroffen sein.'))runAmi('pjsip reload',true)};
$('reloadDialplan').onclick=()=>{if(confirm('Asterisk dialplan reload ausführen? Bestehende Anrufe und Routing prüfen.'))runAmi('dialplan reload',true)};
const previousRefreshEndpoints=refreshEndpoints;
refreshEndpoints=async()=>{await previousRefreshEndpoints();await refreshPjsipTable()};

function renderDialplanRows(allRows){
 const root=$('groupsExisting');
 if(!allRows?.length){root.textContent='Keine Dialplan-Einträge in den gelesenen Dateien gefunden.';return;}
 // Vom Manager verwaltete Einträge stehen je Kontext einmal im Dialplan (z. B. 600 in default und linphone-in) – hier als EINE Zeile
 const managed=r=>(r.steps||[]).some(x=>/^NoOp\(Smartify:/i.test(x));
 const rows=[];const seen={};
 for(const r of allRows){
  const key=r.number+'|'+r.source;
  if(managed(r)&&seen[key]){if(!seen[key].contexts.includes(r.context))seen[key].contexts.push(r.context);continue;}
  const c={...r,contexts:[r.context],managed:managed(r)};rows.push(c);if(c.managed)seen[key]=c;
 }
 const headings=['Nr.','Typ','Kontext','NoOp / Beschreibung','Lokale SIP-Ziele','Externer Endpoint','SIP-Adresse','Rufdauer','Abschluss','Quelle','Aktion'];
 root.innerHTML='<div class="edit-scroll dp-rows"><table class="edit-table"><thead><tr>'+headings.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map((r,i)=>{
  const o=r.route_options,ext=o?.external_targets?.[0]||null;
  const simple=!!(o && r.source.startsWith('custom/') && !r.managed);
  const summary=(r.steps||[]).map(x=>esc(x)).join(' → ');
  const desc=o?.description??(r.steps||[]).find(x=>/^NoOp\(/i.test(x))??'';
  const cells=simple?[
   fieldText('description',desc),fieldText('targets',(o.targets||[]).join(','),'placeholder="104,106"'),
   fieldText('cloud_ep',ext?.endpoint||'','placeholder="linphone-cloud"'),
   fieldText('cloud_uri',ext?.uri||'','placeholder="sip:benutzer@sip.linphone.org"'),
   fieldText('timeout',o.timeout,'type="number" min="5" max="120"'),'<code>Hangup()</code>'
  ]:[esc(desc),esc((o?.targets||r.targets||[]).join(',')||'–'),esc(ext?.endpoint||'–'),esc(ext?.uri||'–'),esc(o?.timeout??'–'),esc((r.steps||[]).at(-1)||'–')];
  return '<tr data-route="'+i+'"><td class="id-col">'+esc(r.number)+'</td><td>'+esc(r.managed?'Smartify (verwaltet)':r.kind)+'</td><td>'+esc(r.contexts.join(', '))+'</td>'+
   cells.map(x=>'<td>'+x+'</td>').join('')+'<td>'+esc(r.source)+':'+esc(r.line)+'</td><td>'+
   (r.managed?'<button data-goto-rg="1">Im Rufgruppen-Manager</button>':simple?'<button data-save-route="'+i+'">Speichern</button>':'<button data-open-route="'+i+'">Datei öffnen</button>')+
   '<details><summary>Original</summary><div class="route-steps">'+summary+'</div></details></td></tr>';
 }).join('')+'</tbody></table></div>';
 root.querySelectorAll('[data-save-route]').forEach(btn=>btn.onclick=()=>saveRouteRow(rows[Number(btn.dataset.saveRoute)],btn.closest('tr')));
 root.querySelectorAll('[data-open-route]').forEach(btn=>btn.onclick=()=>openRouteFile(rows[Number(btn.dataset.openRoute)]));
 root.querySelectorAll('[data-goto-rg]').forEach(btn=>btn.onclick=()=>showPanel('rufgruppen'));
}
async function openRouteFile(row){
 const name=row.source.split('/').pop();$('filename').value=name;showPanel('pjsip');await loadFile();
 msg('Datei '+row.source+' geöffnet, Zeile '+row.line+'. Default-Dateien sind schreibgeschützt.');
}
async function saveRouteRow(row,tr){
 const targets=cellValue(tr,'targets').split(',').map(x=>x.trim()).filter(Boolean);
 const timeout=Number(cellValue(tr,'timeout'));
 const cloudEp=cellValue(tr,'cloud_ep'),cloudUri=cellValue(tr,'cloud_uri');
 const external=cloudEp||cloudUri?{endpoint:cloudEp,uri:cloudUri}:null;
 const description=cellValue(tr,'description');
 if(!targets.every(validExt)||new Set(targets).size!==targets.length||(!targets.length&&!external)||!Number.isInteger(timeout)||timeout<5||timeout>120){
  msg('Ungültige lokale/externe SIP-Ziele oder Rufdauer');return;
 }
 const name=row.source.split('/').pop();
 if(!confirm('Dialplan-Ziel '+row.number+' in custom/'+name+' speichern? Backup wird erstellt; noch kein Dialplan-Reload.'))return;
 try{
  const file=await request('api/file/'+name);
  const d=await post('api/structured/group/save',{operation:'edit',number:row.number,context:row.context,file:name,targets,timeout,description,external,hash:file.hash});
  msg(d.note);await refreshNumberPlan();
 }catch(e){msg('Nicht gespeichert: '+e.message)}
}
$('groupDirectSave').onclick=async()=>{
 const n=value('groupNum'),context=value('groupContext'),target=value('groupSaveFile');
 const targets=value('groupTargets').split(',').map(s=>s.trim()).filter(Boolean);
 const timeout=Number(value('timeout'));
 const uri=value('cloudURI'),ep=value('cloudEp');
 if(!validExt(n)||!targets.every(validExt)||!Number.isInteger(timeout)||timeout<5||timeout>120){msg('Gruppenwerte überprüfen');return}
 const external=uri?{uri,endpoint:ep}:null;
 const description=value('groupDesc')||'Smartify Rufgruppe '+n;
 if(!confirm('Rufgruppe '+n+' in custom/'+target+' speichern? Backup und Konfliktprüfung, KEIN automatischer Reload.'))return;
 try{
  const file=await request('api/file/'+target);
  if(file.source!=='custom'){msg('Custom-Datei fehlt oder ist nur Default-Referenz. Bitte zunächst Custom-Datei mit dem richtigen Kontext anlegen.');return}
  const d=await post('api/structured/group/save',{operation:'add',number:n,context,file:target,targets,timeout,external,description,hash:file.hash});
  msg(d.note);await refreshNumberPlan();
 }catch(e){msg('Rufgruppe nicht gespeichert: '+e.message)}
};
$('groupPreset').onchange=()=>{
 if(value('groupPreset')==='linphone'){
  $('cloudEp').value='linphone-cloud';$('cloudURI').focus();
  msg('Linphone-Cloud: gültige SIP-URI eingeben. Der externe PJSIP-Endpoint muss in Asterisk bereits konfiguriert sein.');
 }else{ $('cloudURI').value='';$('cloudEp').value=''; }
};
// Initial render cannot rely on the earlier promise's captured refresh callback.
refreshPjsipTable();

function appendPjsipRow(){
 if(!pjsipTableState || pjsipTableState.source!=='custom'){
  msg('custom/pjsip_custom.conf zuerst anlegen und sicherstellen, dass Asterisk sie einliest.');return;
 }
 const tbody=$('pjsipTable').querySelector('tbody');
 if(!tbody)return;
 if(tbody.querySelector('[data-new-pjsip]')){tbody.querySelector('[data-col="number"]').focus();return}
 const tr=document.createElement('tr');tr.dataset.newPjsip='1';
 tr.innerHTML='<td>'+fieldText('number','','inputmode="numeric" maxlength="6" placeholder="107"')+
  '<select data-col="profile"><option value="standard">Standard</option><option value="linphone">Linphone</option><option value="multi">Mehrere Geräte</option></select></td>'+
  '<td>'+fieldText('name','','placeholder="Beate Linphone"')+'</td>'+
  '<td>'+fieldText('max_contacts','1','type="number" min="1" max="100"')+'</td>'+
  '<td>'+fieldChoice('remove_existing','yes',['yes','no'])+'</td>'+
  '<td>'+fieldChoice('remove_unavailable','no',['yes','no'])+'</td>'+
  '<td>'+fieldText('context','default')+'</td>'+
  '<td>'+fieldText('codecs','alaw,ulaw')+'</td>'+
  '<td>'+fieldText('username','','placeholder="Nummer"')+'</td>'+
  '<td><input type="password" data-col="password" autocomplete="new-password" placeholder="SIP-Passwort"></td>'+
  '<td>'+advancedPjsipFields({transport:'transport-udp',qualify_frequency:'30'})+'</td>'+
  '<td><button type="button" data-add-pjsip disabled>Neue Nebenstelle speichern</button> <button type="button" data-new-edit hidden>Vorhandene bearbeiten</button><small data-new-status class="slot-info">Neue Nummer eingeben</small><button type="button" data-cancel-pjsip>Abbrechen</button></td>';
 tr.querySelector('[data-col="profile"]').onchange=()=>{
  const profile=cellValue(tr,'profile');
  tr.querySelector('[data-col="max_contacts"]').value=profile==='multi'?'3':'1';
  tr.querySelector('[data-col="remove_existing"]').value=profile==='multi'?'no':'yes';
  tr.querySelector('[data-col="remove_unavailable"]').value=profile==='multi'?'yes':'no';
  if(profile==='linphone')msg('Linphone: SIP-Konto mit gewöhnlichen PJSIP/NAT-Werten. Zugangsdaten in der Linphone-App eintragen.');
 };
 tr.querySelector('[data-col="number"]').addEventListener('input',updateNewRowAvailability);
 tr.querySelector('[data-new-edit]').onclick=()=>focusExistingEndpoint(cellValue(tr,'number'));
 tr.querySelector('[data-add-pjsip]').onclick=async()=>{
  const n=cellValue(tr,'number');
  const fresh=await getFreshNumberPlan();if(!fresh)return;
  if(fresh.used[n]){msg('Nummer '+n+' bereits vergeben – nicht als neu speichern.');return;}
  const input={extension:n,displayName:cellValue(tr,'name'),authUsername:cellValue(tr,'username')||n,
   password:tr.querySelector('[data-col="password"]').value, context:cellValue(tr,'context'),
   maxContacts:cellValue(tr,'max_contacts'),removeExisting:cellValue(tr,'remove_existing'),
   removeUnavailable:cellValue(tr,'remove_unavailable'),codecs:cellValue(tr,'codecs').split(',').map(x=>x.trim()).filter(Boolean),
   transport:cellValue(tr,'transport'),qualifyFrequency:cellValue(tr,'qualify_frequency'),
   minimumExpiration:cellValue(tr,'minimum_expiration'),defaultExpiration:cellValue(tr,'default_expiration'),
   maximumExpiration:cellValue(tr,'maximum_expiration'),dtmfMode:cellValue(tr,'dtmf_mode'),
   directMedia:cellValue(tr,'direct_media'),forceRport:cellValue(tr,'force_rport'),
   rewriteContact:cellValue(tr,'rewrite_contact'),rtpSymmetric:cellValue(tr,'rtp_symmetric'),
   iceSupport:cellValue(tr,'ice_support')};
  let output;try{output=SmartifyPjsip.build(input);}catch(e){msg(e.message);return;}
  if(!confirm('Neue Nebenstelle '+n+' mit Backup in pjsip_custom.conf schreiben? Noch kein Reload.'))return;
  try{
   const data=await post('api/structured/pjsip/save',{operation:'add',number:n,snippet:output.snippet,hash:pjsipTableState.hash});
   msg(data.note);await Promise.all([refreshPjsipTable(),refreshEndpoints(),refreshNumberPlan()]);
  }catch(e){msg('Nicht gespeichert: '+e.message)}
 };
 tr.querySelector('[data-cancel-pjsip]').onclick=()=>tr.remove();
 tbody.prepend(tr);updateNewRowAvailability();tr.querySelector('[data-col="number"]').focus();
}


// v1.3.7: authenticated-by-source-IP external calls, scoped to selected Asterisk extensions.
let inboundState=null;
function inboundIPs(){return value('inIPs').split(/[\n,;]+/).map(x=>x.trim()).filter(Boolean)}
function inboundTargets(){return Array.from(document.querySelectorAll('#inTargets input:checked')).map(e=>e.value)}
function inSelectTargets(values){document.querySelectorAll('#inTargets input').forEach(c=>c.checked=values.includes(c.value))}
function inFiles(list){
 const sel=$('inPFile');const prev=sel.value;
 const items=[...new Set(['pjsip_custom.conf',...list.filter(x=>(x.startsWith('pjsip')||x==='custom.conf')&&x.endsWith('.conf'))])];
 sel.replaceChildren(...items.map(x=>{const o=document.createElement('option');o.value=x;o.textContent=x;return o}));
 if(items.includes(prev))sel.value=prev;
}
async function loadInbound(){
 try{
  const [d,status]=await Promise.all([request('api/inbound'),request('api/status')]);
  inboundState=d;inFiles(status.files||[]);
  const root=$('inRows');root.replaceChildren();
  for(const p of d.profiles){
   const tr=document.createElement('tr');
   const cell=(text)=>{const td=document.createElement('td');td.textContent=text;tr.append(td);return td};
   cell(p.name);cell(p.ips.join(', '));cell(p.targets.join(', '));
   cell(p.pjsip_file+' / '+p.extensions_file);
   const td=document.createElement('td');const btn=document.createElement('button');btn.textContent=p.readonly?'Nur lesen':'Bearbeiten';btn.disabled=p.readonly;
   btn.onclick=()=>{
    $('inName').value=p.name;$('inIPs').value=p.ips.join('\n');inSelectTargets(p.targets);
    $('inPFile').value=p.pjsip_file.replace(/^custom\//,'');$('inEFile').value=p.extensions_file.replace(/^custom\//,'');
    msg('Eingang '+p.name+' geladen. Änderungen zuerst in der Vorschau prüfen.');
   };td.append(btn);tr.append(td);root.append(tr);
  }
  if(!d.profiles.length){const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=5;td.textContent='Noch keine zugehörigen Endpoint/Identify/Dialplan-Konfigurationen erkannt';tr.append(td);root.append(tr)}
  const targets=$('inTargets');const wanted=inboundTargets();targets.replaceChildren();
  for(const n of d.available_extensions){
   const label=document.createElement('label');const inp=document.createElement('input');inp.type='checkbox';inp.value=n;inp.checked=wanted.includes(n);
   label.append(inp,document.createTextNode(' '+n));targets.append(label);
  }
  const matching=d.profiles.find(x=>x.name===$('inName').value&&!x.readonly);
  if(matching){$('inIPs').value=matching.ips.join('\n');inSelectTargets(matching.targets);
   $('inPFile').value=matching.pjsip_file.replace(/^custom\//,'');
   $('inEFile').value=matching.extensions_file.replace(/^custom\//,'');}
  $('inStatus').textContent=d.profiles.length+' vorhandene Eingänge, '+d.available_extensions.length+' auswählbare Nebenstellen';
 }catch(e){$('inStatus').textContent='Einlesen fehlgeschlagen: '+e.message;msg(e.message)}
}
function inForm(hashes){return {name:value('inName').trim(),ips:inboundIPs(),targets:inboundTargets(),
 timeout:Number(value('inSeconds')),pjsip_file:value('inPFile'),extensions_file:value('inEFile'),hashes};}
async function inData(){
 const [p,e]=await Promise.all([request('api/file/'+value('inPFile')),request('api/file/'+value('inEFile'))]);
 if(p.source!=='custom'||e.source!=='custom')throw Error('Zuerst die beiden existierenden Custom-Dateien wählen/anlegen. Standarddateien werden nicht verändert.');
 return inForm({pjsip:p.hash,extensions:e.hash});
}
$('inPreview').onclick=async()=>{
 try{const body=await inData();const response=await post('api/inbound/preview',body);
 $('inPreviewP').value=response.pjsip;$('inPreviewE').value=response.extensions;
 msg('Beide Konfigurationen geprüft, noch nichts gespeichert.');
 }catch(e){msg('Vorschau fehlgeschlagen: '+e.message)}
};
$('inSave').onclick=async()=>{
 try{const body=await inData();await post('api/inbound/preview',body);
 if(!confirm('Eingang '+body.name+' für '+body.ips.join(', ')+' freigeben? Erlaubte Ziele: '+body.targets.join(', ')+'\n\nBEIDE Custom-Dateien mit Backups speichern? Kein Reload.'))return;
 body.confirm=true;const response=await post('api/inbound/save',body);
 msg(response.note);await Promise.all([loadInbound(),refreshNumberPlan()]);
 }catch(e){msg('Eingang konnte nicht gespeichert werden: '+e.message)}
};
$('inRefresh').onclick=loadInbound;
