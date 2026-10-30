/* Smartify SIP Calling Card v1.0 - read-only HA/Asterisk overview.
 * Data: sensor.smartify_sip_teilnehmer (published by SIP Manager every 10 s).
 * Browser Mod visibility entities are optional and user-configurable.
 */
class SmartifySipCallingCard extends HTMLElement {
  setConfig(config) {
    this.config = {title: "Smartify SIP · Calling", entity: "sensor.smartify_sip_teilnehmer",
      browser_mod: {}, stale_seconds: 35, ...config};
    if (!this.config.entity || typeof this.config.browser_mod !== "object" || Array.isArray(this.config.browser_mod))
      throw new Error("entity und browser_mod müssen korrekt konfiguriert sein");
    if (!this.shadowRoot) this.attachShadow({mode:"open"});
    this._selectionKey = "smartify-sip-calling:" + (this.config.selection_id || this.config.title);
    try { this._selected = JSON.parse(localStorage.getItem(this._selectionKey) || "null"); }
    catch (_) { this._selected = null; }
    if (!Array.isArray(this._selected)) this._selected = null;
    this._prefsKey = this._selectionKey + ":prefs";
    try { this._prefs = JSON.parse(localStorage.getItem(this._prefsKey) || "{}"); } catch (_) { this._prefs = {}; }
    this._prefs = this._prefs && typeof this._prefs === "object" ? this._prefs : {};
    this._editMode = false;
    this._fontSize = Math.max(11,Math.min(24,Number(this._prefs._fontSize)||14));
    this._phoneSize = Math.max(24,Math.min(50,Number(this._prefs._phoneSize)||42));
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    if (this.config && this.isConnected) {
      this.render();
      this.shadowRoot?.querySelectorAll(".call-host > *").forEach(card => { card.hass = hass; });
    }
  }
  connectedCallback() { if (this.config) this.render(); this._ticker = setInterval(() => this.render(), 5000); }
  disconnectedCallback() { clearInterval(this._ticker); }
  getCardSize() { return 5; }
  static getStubConfig() { return {title:"Smartify SIP · Calling", browser_mod:{"104":"sensor.ipadvisu_browser_visibility"}}; }
  render() {
    const h = this._hass, c = this.config;
    if (!c || !this.shadowRoot || this._dragging) return;
    const s = h?.states?.[c.entity];
    const attrs = s?.attributes || {};
    const age = attrs.updated ? (Date.now() - Date.parse(attrs.updated))/1000 : Infinity;
    const fresh = s && s.state !== "unavailable" && s.state !== "unknown" && age >= 0 && age <= Number(c.stale_seconds);
    const rows = fresh && Array.isArray(attrs.participants) ? attrs.participants : [];
    const selected = this._selected;
    const caller = String(this._prefs._callerExtension || c.caller_extension || "").trim();
    const rules = attrs.call_rules || {};
    const access = (target) => {
      if (!caller || !rules[caller] || !rules[target]) return {allowed:null,reason:"Eigene Nebenstelle wählen oder Regeln noch nicht geladen"};
      if(caller===target)return {allowed:false,reason:"Eigene Nebenstelle"};
      const outgoing=rules[caller].can_call;
      const incoming=rules[target].called_by;
      if(Array.isArray(outgoing) && !outgoing.includes(target))return {allowed:false,reason:"Im SIP Manager: darf nicht angerufen werden (Anrufziele des Anrufers)"};
      if(Array.isArray(incoming) && !incoming.includes(caller))return {allowed:false,reason:"Im SIP Manager: Angerufen von schließt diese Nebenstelle aus"};
      return {allowed:true,reason:"Anruf laut SIP-Manager-Regeln erlaubt"};
    };
    const displayed = (selected === null ? rows : selected.map(id => rows.find(p => p.extension === id)).filter(Boolean)).filter(p => !caller || p.extension !== caller);
    const reachable = displayed.filter(p=>p.reachable).length;
    const unavailable = displayed.filter(p=>!p.reachable && p.status!=="unknown").length;
    const unchecked = displayed.filter(p=>!p.reachable && p.status==="unknown").length;
    const esc = (v) => String(v ?? "").replace(/[&<>"']/g, ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    const state = (p) => p.reachable ? ["ok","Erreichbar"] : p.status==="unknown" ? ["warn","?"] : p.registered ? ["bad","Nicht erreichbar"] : ["bad","Nicht registriert"];
    const browser = (id) => {
      const eid = attrs.browser_mod_entities?.[id] || c.browser_mod?.[id];
      if (!eid) return null;
      const raw = h?.states?.[eid]?.state;
      if (!raw || ["unknown","unavailable"].includes(raw)) return ["bad","BM n.ok"];
      if (["visible","on"].includes(raw.toLowerCase())) return null;
      if (["hidden","off"].includes(raw.toLowerCase())) return ["bad","BM n.ok"];
      return ["bad","BM n.ok"];
    };
    const own = caller ? rows.find(p => p.extension === caller) : null;
    const ownStatus = !caller ? ["warn","Eigene Nr. wählen","?"] :
      !fresh || !own ? ["warn","Eigene Nebenstelle nicht geprüft","?"] :
      own.reachable ? ["ok","Eigene Nebenstelle erreichbar","●"] :
      own.status === "unreachable" || own.status === "unregistered" ? ["bad","Eigene Nebenstelle nicht erreichbar","●"] :
      ["warn","Eigene Nebenstelle ungeprüft","?"];
    const line = (text, css) => `<span class="flag ${css}">${esc(text)}</span>`;
    const participant = p => {
      const [cls, desc]=state(p);
      const b=browser(p.extension);
      const permission=access(p.extension);
      return `<div class="person" data-id="${esc(p.extension)}">${this._editMode ? '<span class="grab" title="Zum Sortieren ziehen" aria-label="Teilnehmer verschieben">⠿</span>' : ""}<span class="avatar">☎</span><div class="info">
        <strong>${esc(this._prefs?.[p.extension]?.name || (c.names || {})[p.extension] || p.name || p.extension)}</strong>
        <small>Nr. ${esc(p.extension)}${p.contacts ? ` · ${p.contacts} Kontakt(e)` : ""}</small>
        </div><div class="flags">${desc==="?" ? `<span class="status-question" title="SIP-Erreichbarkeit ungeprüft">?</span>` : line(desc,cls)}${b ? line(b[1],b[0]) : ""}</div>
        ${!this._editMode ? (permission.allowed===false ? `<span class="blocked" title="${esc(permission.reason)}" aria-label="Anruf gesperrt">⛔</span>` : `<div class="call-host" data-call="${esc(p.extension)}" title="${esc(permission.reason)}"></div>`) : ""}
        ${this._editMode ? `<div class="actions"><button data-edit="${esc(p.extension)}" title="Karteneintrag bearbeiten">✎</button><button data-delete="${esc(p.extension)}" title="Aus Karte entfernen">✕</button></div>` : ""}</div>`;
    };
    const browserOnly = Object.entries({...c.browser_mod,...(attrs.browser_mod_entities||{})}).filter(([id])=>id!==caller && (selected===null || selected.includes(id)) && !displayed.some(p=>p.extension===id))
      .map(([id])=>{const b=browser(id);return `<div class="person"><span class="avatar">▣</span><div class="info"><strong>${esc((c.names||{})[id] || id)}</strong><small>Browser Mod · keine SIP-Kontaktzuordnung</small></div><div class="flags">${b ? line(b[1],b[0]) : ""}</div></div>`;}).join("");
    const choices = rows.filter(p=>p.extension!==caller && (selected===null || !selected.includes(p.extension)))
      .map(p=>`<option value="${esc(p.extension)}">${esc(p.name || p.extension)} (${esc(p.extension)})</option>`).join("");
    const removeButtons = "";
    const picker = `<div class="picker"><select id="add-participant" aria-label="Teilnehmer auswählen"><option value="">Teilnehmer auswählen …</option>${choices}</select>
      <button id="add-btn" title="Ausgewählten Teilnehmer hinzufügen">+ Hinzufügen</button>
      <button id="all-btn" title="Alle Teilnehmer anzeigen">Alle</button></div>
      ${selected===null ? '<small class="help">Alle erkannten SIP-Teilnehmer werden angezeigt. Mit „Hinzufügen“ auf eine eigene Auswahl umstellen.</small>' :
        '<div class="chosen">'+removeButtons+'</div>'}`;
    const html = `<style>
      :host{display:block;color:var(--primary-text-color)}
      ha-card{padding:12px;overflow:hidden}
      .head{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px;gap:7px}
      .head h3{font-size:${Math.min(18,this._fontSize+1)}px;margin:0;font-weight:600;min-width:0;line-height:1.2}
      .head-actions{display:flex;align-items:center;gap:6px;flex-shrink:0}
      .own-status{display:grid;place-items:center;border:0;background:transparent;border-radius:0;width:28px;height:28px;padding:0;font-size:21px;line-height:1;cursor:pointer}
      .own-status.ok{color:var(--success-color,#43a047)}.own-status.bad{color:var(--error-color,#dc4747)}.own-status.warn{color:var(--warning-color,#ef9800)}
      #edit-toggle{background:var(--secondary-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:9px;min-width:35px;min-height:35px;cursor:pointer;font-size:19px}
      .summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-bottom:6px}
      .stat{background:var(--secondary-background-color);border-radius:8px;text-align:center;padding:3px 3px;line-height:1.05}
      .num{font-size:17px;line-height:1.05;font-weight:650;display:block;font-variant-numeric:tabular-nums}
      .stat small{display:block;font-size:10px!important;line-height:1.1;margin-top:1px}
      .stat small,.info small,.foot{color:var(--secondary-text-color);font-size:${Math.max(10,Math.min(12,this._fontSize-3))}px;line-height:1.25}
      .person{display:flex;align-items:center;gap:6px;touch-action:pan-y;border-top:1px solid var(--divider-color);padding:5px 0;min-height:${Math.max(44,this._phoneSize+10)}px;height:auto;box-sizing:border-box;position:relative}
      .grab{cursor:grab;touch-action:none;user-select:none;padding:9px 4px;color:var(--secondary-text-color);font-size:22px}
      .person.dragged{opacity:.5}
      .person.target{outline:2px dashed var(--primary-color);border-radius:8px}
      .actions{display:flex;gap:3px}
      .actions button{border:0;background:transparent;color:var(--secondary-text-color);font-size:17px;cursor:pointer;padding:5px}
      .person .info,.person .flags{min-height:0}
      .avatar{display:grid;place-items:center;border-radius:12px;background:var(--secondary-background-color);width:30px;height:30px;flex-shrink:0}
      .info{min-width:0;flex:1 1 auto;display:flex;flex-direction:column;gap:1px}
      .info strong{font-size:${this._fontSize}px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.2}
      .flags{display:flex;flex:0 0 auto;flex-direction:column;align-items:flex-end;gap:3px}
      .flag{font-size:11px;border-radius:7px;padding:2px 4px;white-space:nowrap;background:var(--secondary-background-color)}
      .status-question{font-size:19px;color:var(--warning-color,#ef9800);font-weight:700;min-width:14px;text-align:center}
      .ok{color:var(--success-color,#43a047)}
      .warn{color:var(--warning-color,#ef9800)}
      .bad{color:var(--error-color,#dc4747)}
      .foot{margin-top:10px}
      .empty{padding:15px 2px;color:var(--secondary-text-color)}
      .picker{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:9px}
      .picker select{min-width:130px;flex:1;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:7px}
      .picker button,.remove{color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:7px;cursor:pointer}
      .chosen{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:9px}
      .remove{font-size:11px;padding:4px 7px}
      .blocked{width:${this._phoneSize}px;flex:0 0 ${this._phoneSize}px;display:grid;place-items:center;font-size:${Math.min(this._phoneSize,32)}px;line-height:1}
      .call-host{width:${this._phoneSize}px;height:${this._phoneSize}px;flex:0 0 ${this._phoneSize}px;position:relative;overflow:visible;align-self:center;min-height:0}
      /* Keep SIP Core's native layout intact: scale its 90px card instead of clipping/reflowing it. */
      .call-host>custom-sip-call-button,.call-host>*{position:absolute!important;left:50%!important;top:50%!important;width:90px!important;height:90px!important;min-width:90px!important;min-height:90px!important;max-width:90px!important;max-height:none!important;transform:translate(-50%,-50%) scale(${(this._phoneSize/90).toFixed(4)})!important;transform-origin:center center!important;--ha-card-border-width:0px;--ha-card-box-shadow:none}
      .font-setting{display:flex;align-items:center;gap:10px;margin:8px 0 12px;font-size:13px}
      .font-setting input{flex:1;min-width:70px}
      .help{display:block;color:var(--secondary-text-color);font-size:11px;margin-bottom:10px}
    </style><ha-card>
    <div class="head"><h3>☎ ${esc(c.title)}</h3><div class="head-actions">${fresh ? "" : line("Daten veraltet","bad")}<button class="own-status ${ownStatus[0]}" id="own-status" title="${esc(ownStatus[1]+(caller ? ` (${caller})` : ""))}" aria-label="${esc(ownStatus[1])}">${ownStatus[2]}</button><button id="edit-toggle" title="${this._editMode ? "Bearbeitung beenden" : "Teilnehmer bearbeiten"}" aria-label="${this._editMode ? "Bearbeitung beenden" : "Bearbeitungsmodus einschalten"}" aria-pressed="${this._editMode}">${this._editMode ? "✓" : "⚙"}</button></div></div>
    <div class="summary"><div class="stat"><span class="num ok">${fresh?reachable:"–"}</span><small>Erreichbar</small></div>
    <div class="stat"><span class="num bad">${fresh?unavailable:"–"}</span><small>Offline</small></div>
    <div class="stat"><span class="num">${fresh?displayed.length:"–"}</span><small>Gesamt${fresh&&unchecked ? ` · ${unchecked} ?` : ""}</small></div></div>
    ${this._editMode ? `<label class="font-setting">Eigene Nebenstelle <select id="caller-extension"><option value="">– Bitte wählen –</option>${rows.map(p=>`<option value="${esc(p.extension)}" ${caller===p.extension?'selected':''}>${esc(p.name||p.extension)} (${esc(p.extension)})</option>`).join("")}</select></label><label class="font-setting">Schriftgröße <input id="font-size" type="range" min="11" max="24" step="1" value="${this._fontSize}"><span>${this._fontSize} px</span></label><label class="font-setting">Hörergröße <input id="phone-size" type="range" min="24" max="50" step="2" value="${this._phoneSize}"><span>${this._phoneSize} px</span></label>` + picker : ""}
    ${fresh ? (displayed.map(participant).join("")+browserOnly || '<div class="empty">Keine PJSIP-Endpunkte gefunden.</div>') :
      '<div class="empty">Keine aktuellen Asterisk-Daten. Prüfe AMI und Smartify SIP Manager.</div>'}
    <div class="foot">Asterisk alle 10 s · Browser Mod aus HA · letzte AMI-Meldung: ${attrs.updated ? esc(new Date(attrs.updated).toLocaleTimeString()) : "–"}<br>
    SIP erreichbar bedeutet nicht automatisch, dass iOS im Hintergrund hörbar klingelt.</div>
    </ha-card>`;
    if (html !== this._lastHtml) {
      const oldPicker = this.shadowRoot.querySelector("#add-participant");
      const oldChoice = oldPicker?.value;
      this.shadowRoot.innerHTML = html;
      if (oldChoice && this.shadowRoot.querySelector(`#add-participant option[value="${CSS.escape(oldChoice)}"]`))
        this.shadowRoot.querySelector("#add-participant").value = oldChoice;
      this._lastHtml = html;
      this.shadowRoot.querySelector("#caller-extension")?.addEventListener("change",ev=>{
        this._prefs._callerExtension=ev.target.value;
        try{localStorage.setItem(this._prefsKey,JSON.stringify(this._prefs));}catch(_){}
        this._lastHtml=null;this.render();
      });
      this.shadowRoot.querySelector("#phone-size")?.addEventListener("change",ev=>{
        this._phoneSize=Number(ev.target.value);
        this._prefs._phoneSize=this._phoneSize;
        try{localStorage.setItem(this._prefsKey,JSON.stringify(this._prefs));}catch(_){}
        this._lastHtml=null;this.render();
      });
      this.shadowRoot.querySelector("#font-size")?.addEventListener("change",ev=>{
        this._fontSize=Number(ev.target.value);
        this._prefs._fontSize=this._fontSize;
        try{localStorage.setItem(this._prefsKey,JSON.stringify(this._prefs));}catch(_){}
        this._lastHtml=null;this.render();
      });
      this._mountCallButtons();
      this.shadowRoot.querySelector("#own-status")?.addEventListener("click",()=>{this._editMode=true;this._lastHtml=null;this.render();});
      this.shadowRoot.querySelector("#edit-toggle")?.addEventListener("click", () => { this._editMode = !this._editMode; this._lastHtml = null; this.render(); });
      this.shadowRoot.querySelector("#add-btn")?.addEventListener("click", () => {
        const id = this.shadowRoot.querySelector("#add-participant")?.value;
        if (!id) return;
        this._selected = this._selected === null ? [id] : [...new Set([...this._selected, id])];
        this.saveSelection();
      });
      this.shadowRoot.querySelector("#all-btn")?.addEventListener("click", () => {
        this._selected = null;
        this.saveSelection();
      });
      this.shadowRoot.querySelectorAll("[data-delete]").forEach(btn => btn.addEventListener("click", () => {
        const id=btn.dataset.delete;
        this._selected=(this._selected===null ? rows.map(p=>p.extension) : this._selected).filter(x=>x!==id);
        this.saveSelection();
      }));
      this.shadowRoot.querySelectorAll("[data-edit]").forEach(btn => btn.addEventListener("click", () => {
        const id=btn.dataset.edit, p=rows.find(x=>x.extension===id);
        const prev=this._prefs[id]||{};
        const name=prompt("Anzeigename (nur Calling Card)",prev.name||p?.name||id);
        if(name===null)return;
        this._prefs[id]={...prev,name:name.trim().slice(0,100)};
        try{localStorage.setItem(this._prefsKey,JSON.stringify(this._prefs));}catch(_){}
        this._lastHtml=null;this.render();
      }));
      this.shadowRoot.querySelectorAll(".person[data-id] .grab").forEach(handle => {
        handle.addEventListener("pointerdown", ev => {
          if(ev.button!==0 || !this._selected && !rows.length)return;
          const source=handle.closest(".person[data-id]");
          const from=source?.dataset.id;
          if(!from)return;
          this._dragging=true;
          handle.setPointerCapture(ev.pointerId);
          source.classList.add("dragged");
          let target=null;
          const move=e=>{
            const hit=this.shadowRoot.elementFromPoint(e.clientX,e.clientY)?.closest(".person[data-id]");
            this.shadowRoot.querySelectorAll(".person.target").forEach(el=>el.classList.remove("target"));
            target=hit&&hit!==source?hit:null;
            target?.classList.add("target");
          };
          const done=e=>{
            handle.removeEventListener("pointermove",move);
            handle.removeEventListener("pointerup",done);
            handle.removeEventListener("pointercancel",cancel);
            this._dragging=false;
            const to=target?.dataset.id;
            if(to){
              const order=this._selected===null?rows.map(p=>p.extension):[...this._selected];
              const a=order.indexOf(from),b=order.indexOf(to);
              if(a>=0&&b>=0){order.splice(a,1);order.splice(b,0,from);this._selected=order;}
            }
            this.saveSelection();
          };
          const cancel=()=>{this._dragging=false;this._lastHtml=null;this.render();};
          handle.addEventListener("pointermove",move);
          handle.addEventListener("pointerup",done,{once:true});
          handle.addEventListener("pointercancel",cancel,{once:true});
        });
      });
      this.shadowRoot.querySelectorAll("[data-remove]").forEach(btn => btn.addEventListener("click", () => {
        this._selected = this._selected.filter(id => id !== btn.dataset.remove);
        this.saveSelection();
      }));
    }
  }
  async _mountCallButtons() {
    const hosts=[...this.shadowRoot.querySelectorAll(".call-host[data-call]")];
    if(!hosts.length)return;
    try {
      if(!window.loadCardHelpers)throw Error("SIP Core Kartenhelfer nicht geladen");
      const helpers=await window.loadCardHelpers();
      for(const host of hosts){
        if(!host.isConnected || host.children.length)continue;
        const id=host.dataset.call;
        const el=helpers.createCardElement({type:"custom:sip-call-button",extension:id,name:"",rainbow_border:false});
        if(this._hass)el.hass=this._hass;
        host.replaceChildren(el);
      }
    }catch(err){
      for(const host of hosts) if(host.isConnected&&!host.children.length)host.textContent="SIP Core fehlt";
    }
  }
  saveSelection() {
    try { localStorage.setItem(this._selectionKey, JSON.stringify(this._selected)); } catch (_) {}
    this._lastHtml = null;
    this.render();
  }
}
if (!customElements.get("smartify-sip-calling-card")) customElements.define("smartify-sip-calling-card",SmartifySipCallingCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c=>c.type==="smartify-sip-calling-card"))
  window.customCards.push({type:"smartify-sip-calling-card",name:"Smartify SIP Calling Card",description:"Asterisk-Teilnehmer und Browser-Mod-Bereitschaft"});
