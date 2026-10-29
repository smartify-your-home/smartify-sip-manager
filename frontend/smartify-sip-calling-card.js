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
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    if (this.config && this.isConnected) this.render();
  }
  connectedCallback() { if (this.config) this.render(); this._ticker = setInterval(() => this.render(), 5000); }
  disconnectedCallback() { clearInterval(this._ticker); }
  getCardSize() { return 5; }
  static getStubConfig() { return {title:"Smartify SIP · Calling", browser_mod:{"104":"sensor.ipadvisu_browser_visibility"}}; }
  render() {
    const h = this._hass, c = this.config;
    if (!c || !this.shadowRoot) return;
    const s = h?.states?.[c.entity];
    const attrs = s?.attributes || {};
    const age = attrs.updated ? (Date.now() - Date.parse(attrs.updated))/1000 : Infinity;
    const fresh = s && s.state !== "unavailable" && s.state !== "unknown" && age >= 0 && age <= Number(c.stale_seconds);
    const rows = fresh && Array.isArray(attrs.participants) ? attrs.participants : [];
    const selected = this._selected;
    const displayed = selected === null ? rows : rows.filter(p => selected.includes(p.extension));
    const reachable = displayed.filter(p=>p.reachable).length;
    const unavailable = displayed.filter(p=>!p.reachable).length;
    const esc = (v) => String(v ?? "").replace(/[&<>"']/g, ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    const state = (p) => p.reachable ? ["ok","Erreichbar"] : p.status==="unknown" ? ["warn","Ungeprüft"] : p.registered ? ["bad","Nicht erreichbar"] : ["bad","Nicht registriert"];
    const browser = (id) => {
      const eid = c.browser_mod?.[id];
      if (!eid) return null;
      const raw = h?.states?.[eid]?.state;
      if (!raw || ["unknown","unavailable"].includes(raw)) return ["bad","Browser Mod offline"];
      if (["visible","on"].includes(raw.toLowerCase())) return ["ok","Browser Mod sichtbar"];
      if (["hidden","off"].includes(raw.toLowerCase())) return ["warn","Browser Mod verborgen"];
      return ["warn","Browser Mod: " + raw];
    };
    const line = (text, css) => `<span class="flag ${css}">${esc(text)}</span>`;
    const participant = p => {
      const [cls, desc]=state(p);
      const b=browser(p.extension);
      return `<div class="person"><span class="avatar">☎</span><div class="info">
        <strong>${esc((c.names || {})[p.extension] || p.name || p.extension)}</strong>
        <small>Nebenstelle ${esc(p.extension)} · ${p.contacts ?? 0} Kontakt(e)</small>
        </div><div class="flags">${line(desc,cls)}${b ? line(b[1],b[0]) : ""}</div></div>`;
    };
    const browserOnly = Object.entries(c.browser_mod||{}).filter(([id])=>(selected===null || selected.includes(id)) && !displayed.some(p=>p.extension===id))
      .map(([id])=>{const b=browser(id);return `<div class="person"><span class="avatar">▣</span><div class="info"><strong>${esc((c.names||{})[id] || id)}</strong><small>Browser Mod · keine SIP-Kontaktzuordnung</small></div><div class="flags">${line(b[1],b[0])}</div></div>`;}).join("");
    const choices = rows.filter(p=>selected===null || !selected.includes(p.extension))
      .map(p=>`<option value="${esc(p.extension)}">${esc(p.name || p.extension)} (${esc(p.extension)})</option>`).join("");
    const removeButtons = selected===null ? "" : selected.map(id=>`<button class="remove" data-remove="${esc(id)}" title="Teilnehmer entfernen">× ${esc((rows.find(p=>p.extension===id)||{}).name || id)}</button>`).join("");
    const picker = `<div class="picker"><select id="add-participant" aria-label="Teilnehmer auswählen"><option value="">Teilnehmer auswählen …</option>${choices}</select>
      <button id="add-btn" title="Ausgewählten Teilnehmer hinzufügen">+ Hinzufügen</button>
      <button id="all-btn" title="Alle Teilnehmer anzeigen">Alle</button></div>
      ${selected===null ? '<small class="help">Alle erkannten SIP-Teilnehmer werden angezeigt. Mit „Hinzufügen“ auf eine eigene Auswahl umstellen.</small>' :
        '<div class="chosen">'+removeButtons+'</div>'}`;
    const html = `<style>
      :host{display:block;color:var(--primary-text-color)}
      ha-card{padding:16px;overflow:hidden}
      .head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;gap:10px}
      .head h3{font-size:17px;margin:0;font-weight:600}
      .summary{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:12px}
      .stat{background:var(--secondary-background-color);border-radius:12px;text-align:center;padding:9px 4px}
      .num{font-size:23px;font-weight:650;display:block;font-variant-numeric:tabular-nums}
      .stat small,.info small,.foot{color:var(--secondary-text-color);font-size:11px}
      .person{display:flex;align-items:center;gap:10px;border-top:1px solid var(--divider-color);padding:10px 0}
      .avatar{display:grid;place-items:center;border-radius:12px;background:var(--secondary-background-color);width:38px;height:38px;flex-shrink:0}
      .info{min-width:0;flex:1;display:flex;flex-direction:column;gap:3px}
      .info strong{font-size:13px;overflow-wrap:anywhere}
      .flags{display:flex;flex-direction:column;align-items:flex-end;gap:4px}
      .flag{font-size:11px;border-radius:9px;padding:3px 6px;white-space:nowrap;background:var(--secondary-background-color)}
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
      .help{display:block;color:var(--secondary-text-color);font-size:11px;margin-bottom:10px}
    </style><ha-card>
    <div class="head"><h3>☎ ${esc(c.title)}</h3>${line(fresh?"AMI verbunden":"Daten veraltet",""+(fresh?"ok":"bad"))}</div>
    <div class="summary"><div class="stat"><span class="num ok">${fresh?reachable:"–"}</span><small>Erreichbar</small></div>
    <div class="stat"><span class="num bad">${fresh?unavailable:"–"}</span><small>Nicht erreichbar</small></div>
    <div class="stat"><span class="num">${fresh?displayed.length:"–"}</span><small>Gesamt</small></div></div>
    ${picker}
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
      this.shadowRoot.querySelectorAll("[data-remove]").forEach(btn => btn.addEventListener("click", () => {
        this._selected = this._selected.filter(id => id !== btn.dataset.remove);
        this.saveSelection();
      }));
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
