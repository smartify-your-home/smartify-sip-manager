/* Smartify SIP Manager – guided setup and editing. Existing editors remain the source of truth.
 * Never writes SIP secrets or Asterisk files by itself. */
(() => {
 'use strict';
 const tasks = {
  ha: {title:'Home Assistant & System', steps:[
   ['Systemstatus prüfen','overview','Home Assistant, Asterisk und AMI prüfen.'],
   ['Anlage & Netzwerk','anlageSetup','Home-Assistant-Benutzer, Anlage und Netzwerkzuordnung konfigurieren.'],
   ['SIP Core','draft','SIP-Core-Verbindung und zugehörige Einstellungen prüfen.'],
   ['Live-Status','live','AMI-Verbindung und aktuelle Erreichbarkeit prüfen.']]},
  participant: {title:'Teilnehmer einrichten / bearbeiten', steps:[
   ['Teilnehmer wählen oder anlegen','anlage','Teilnehmerzeile wählen oder neue Zeile hinzufügen. Vorhandene Werte bleiben erhalten.'],
   ['Asterisk-Nebenstelle','endpoint','PJSIP-Zugang, Passwort, Transport, OPTIONS und Codecs konfigurieren.'],
   ['SIP Core','draft','Browser- und SIP-Core-Einstellungen bei Bedarf ergänzen.'],
   ['Anrufberechtigungen','anlage','Darf anrufen / darf angerufen werden von und Browser-Mod-Entität prüfen.'],
   ['Speichern und übernehmen','erzeugen','Vorschau kontrollieren, Backup erstellen und Änderungen übernehmen.']]},
  cloud: {title:'Cloud- / externe SIP-Konten', steps:[
   ['Externen Teilnehmer konfigurieren','anlage','Teilnehmertyp „Externes SIP-Ziel“ und SIP-Adresse angeben.'],
   ['Cloud-Registrierung / Eingänge','inbound','Eingehende Cloud-Verbindung und Registrierung prüfen.'],
   ['PJSIP-Endpoint','endpoint','Ausgehenden Endpoint, Zugangsdaten und Codecs kontrollieren.'],
   ['Wahlregeln und Rechte','route','Routing und Anrufberechtigungen prüfen.'],
   ['Speichern und testen','live','Änderungen übernehmen und Registrierung / Testanruf prüfen.']]},
  group: {title:'Rufgruppe einrichten / bearbeiten', steps:[
   ['Gruppe auswählen oder erstellen','rufgruppen','Vorhandene Rufgruppe wählen oder neue Gruppe erstellen.'],
   ['Mitglieder und Reihenfolge','rufgruppen','Interne und externe Ziele hinzufügen und Anrufverhalten konfigurieren.'],
   ['Berechtigungen und Verbindungen','verbindungen','Anrufrechte und Verbindungsübersicht prüfen.'],
   ['Dialplan prüfen','route','Vorhandene Wahlregeln auf Konflikte prüfen.'],
   ['Speichern und übernehmen','erzeugen','Vorschau, Backup, Speichern und Asterisk-Reload.']]}
 };
 const css=document.createElement('style');
 css.textContent=`#setupWizard{width:min(480px,calc(100vw - 20px));max-height:90vh;border:1px solid var(--border,#aaa);border-radius:14px;padding:20px;color:inherit;background:var(--card-background-color,#fff);box-shadow:0 10px 50px #0005}#setupWizard::backdrop{background:#0008}#setupWizard .wiz-top{display:flex;justify-content:space-between;align-items:center;gap:12px}#setupWizard .wiz-steps{display:flex;gap:5px;margin:12px 0}#setupWizard .wiz-steps span{height:5px;flex:1;background:#aaa7;border-radius:4px}#setupWizard .wiz-steps span.done{background:#178b78}#setupWizard .wiz-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;margin-top:20px}#setupWizard button{cursor:pointer}#setupWizard .wiz-choice{display:block;width:100%;text-align:left;margin:7px 0;padding:12px;border-radius:8px}#setupWizard .wiz-note{padding:10px;border-radius:8px;background:rgba(120,120,120,.10);line-height:1.5}#setupWizard .wiz-target{font-weight:600}#setupWizard .wiz-sub{font-size:.9em;opacity:.8}`;
 document.head.appendChild(css);
 const dialog=document.createElement('dialog');dialog.id='setupWizard';dialog.setAttribute('aria-label','Smartify Einrichtungsassistent');document.body.appendChild(dialog);
 const launch=document.createElement('button');launch.type='button';launch.id='openSetupWizard';launch.textContent='✨ Einrichtungsassistent';launch.title='Teilnehmer, Gruppen, Cloud-Konten und Home Assistant geführt einrichten oder bearbeiten';
 const actions=document.querySelector('.quick-actions');if(actions)actions.prepend(launch);
 let type=null,step=0;
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','"':'&quot;',"'":'&#39;'}[c]));
 function render(){
  if(!type){
   dialog.innerHTML='<div class="wiz-top"><h2>Einrichtungsassistent</h2><button type="button" data-wiz="close" aria-label="Schließen">✕</button></div><p>Was möchtest du einrichten oder bearbeiten?</p>'+Object.entries(tasks).map(([k,v])=>'<button type="button" class="wiz-choice" data-kind="'+k+'">'+escape(v.title)+'</button>').join('')+'<p class="wiz-sub">Bestehende Konfigurationen werden in den vorhandenen Editoren bearbeitet; der Assistent selbst speichert nichts automatisch.</p>';
  }else{
   const task=tasks[type],s=task.steps[step];
   dialog.innerHTML='<div class="wiz-top"><h2>'+escape(task.title)+'</h2><button type="button" data-wiz="close" aria-label="Schließen">✕</button></div>'+
    '<p class="wiz-sub">Schritt '+(step+1)+' von '+task.steps.length+'</p><div class="wiz-steps">'+task.steps.map((_,i)=>'<span class="'+(i<=step?'done':'')+'"></span>').join('')+'</div>'+
    '<h3>'+escape(s[0])+'</h3><p class="wiz-note">'+escape(s[2])+'</p>'+
    '<p>Öffne den passenden Editor. Der Assistent bleibt für die nächsten Schritte verfügbar.</p>'+
    '<button type="button" class="primary" data-wiz="open">Editor „'+escape(s[0])+'“ öffnen</button>'+
    '<div class="wiz-actions"><button type="button" data-wiz="home">Bereiche</button><button type="button" data-wiz="back" '+(step===0?'disabled':'')+'>Zurück</button><button type="button" class="primary" data-wiz="next">'+(step===task.steps.length-1?'Fertig':'Weiter')+'</button></div>'+
    '<p class="wiz-sub">Änderungen nur im jeweiligen Editor speichern. Vor Asterisk-Übernahme Vorschau und Backup prüfen.</p>';
  }
 }
 function open(){type=null;step=0;render();if(!dialog.open)dialog.showModal();}
 launch.addEventListener('click',open);
 dialog.addEventListener('click',event=>{
  const btn=event.target.closest('button');if(!btn)return;
  const kind=btn.dataset.kind,action=btn.dataset.wiz;
  if(kind&&tasks[kind]){type=kind;step=0;render();return;}
  if(action==='close'){dialog.close();return;}
  if(action==='home'){type=null;step=0;render();return;}
  if(action==='back'){step=Math.max(0,step-1);render();return;}
  if(action==='next'){if(step===tasks[type].steps.length-1){dialog.close();return;}step++;render();return;}
  if(action==='open'){
   const target=tasks[type].steps[step][1];
   const nav=document.querySelector('[data-tab="'+target+'"]');
   if(nav){dialog.close();nav.click();}
   else {const note=dialog.querySelector('.wiz-note');if(note)note.textContent='Editor nicht gefunden. Bitte die App neu laden.';}
  }
 });
})();
