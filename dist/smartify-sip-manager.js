/* Smartify SIP Manager v1.18.4 -- HACS frontend bundle: Doorstation Card v2.7.0 and Popup v3.3.1. */
/* Smartify Doorstation v2.7.0 – HA frontend custom card.
 * Official SIP Core call card is embedded, not reimplemented.
 * go2rtc camera is independent; MSE by default.
 */
class SmartifyDoorstationCard extends HTMLElement {
  setConfig(config) {
    if (!config) throw new Error('Konfiguration fehlt');
    this._config = {
      title: 'Smartify Klingel', subtitle: 'KLINGEL',
      mode: 'mse', camera_ui: true, media: 'video', sip_extension: '200',
      sip_name: 'Türklingel', door_service: 'turn_on', light_service: 'toggle',
      camera_ratio: '16/9', camera_name: '', show_header: true, compact_video: false, camera_mode: 'always', theme: 'auto', show_sip: true, show_status: true, follow_sip_core: true,
      ...config
    };
    if (!['always','auto','hidden'].includes(this._config.camera_mode)) throw new Error('camera_mode: always, auto oder hidden');
    if (!['auto','light','dark'].includes(this._config.theme)) throw new Error('theme: auto, light oder dark');
    if (this._config.camera_mode !== 'hidden' && !this._config.follow_sip_core && (!this._config.stream || typeof this._config.stream !== 'string')) throw new Error('stream: go2rtc-Streamname erforderlich');
    if (this._config.actions && !Array.isArray(this._config.actions)) throw new Error('actions muss eine Liste sein');
    // Validate contacts early; entries with visible:false are omitted before passing to SIP Core.
    if (this._config.sip_extensions !== undefined && (typeof this._config.sip_extensions !== 'object' || this._config.sip_extensions === null || Array.isArray(this._config.sip_extensions))) throw new Error('sip_extensions muss eine Zuordnung sein');
    this._build();
  }
  connectedCallback() {
    if (this._config && !this._cameraHost) this._build();
    if (!this._sipListener) {
      this._sipListener = () => this._updateState();
      for (const ev of ['sipcore-update', 'sipcore-call-started', 'sipcore-call-ended'])
        window.addEventListener(ev, this._sipListener);
    }
    this._updateState();
  }
  disconnectedCallback() {
    this._mountId = (this._mountId || 0) + 1;
    if (this._sipListener) {
      for (const ev of ['sipcore-update', 'sipcore-call-started', 'sipcore-call-ended'])
        window.removeEventListener(ev, this._sipListener);
      this._sipListener = null;
    }
  }
  set hass(value) { this._hass = value; this._updateState(); this._forwardHass(); }
  getCardSize() { return this._cameraVisible ? 9 : 4; }
  static getStubConfig() {
    return { stream:'akuvox_s535',mode:'mse',sip_extension:'200',
      door_entity:'switch.flur_kg_sa1_a8_haustuer',light_entity:'light.flur' };
  }
  _build() {
    const c = this._config;
    const shadow = this.shadowRoot || this.attachShadow({mode:'open'});
    shadow.replaceChildren();
    const style=document.createElement('style');
    style.textContent=`
      :host {
        display:block;
        --s-accent:var(--primary-color, #44739e);
        --s-text:var(--primary-text-color, #202124);
        --s-muted:var(--secondary-text-color, #61666b);
        --s-surface:var(--ha-card-background, var(--card-background-color, #f9f9f9));
        --s-control:var(--secondary-background-color, rgba(130,130,130,.08));
        --s-border:var(--divider-color, rgba(120,120,120,.20));
        --s-active:var(--state-active-color, var(--accent-color, #ff9800));
      }
      * {box-sizing:border-box}
      .panel {
        color:var(--s-text);
        overflow:hidden;border-radius:var(--ha-card-border-radius,22px);
        border:1px solid var(--s-border);
        background:var(--s-surface);
        box-shadow:var(--ha-card-box-shadow,0 8px 25px rgba(0,0,0,.08));
      }
      /* Light: Raffstore theme: dezentes Hellgrau, dunkelgraue Schrift. */
      .panel[data-theme='light'] {
        --s-text:#282b2e;--s-muted:#696d72;--s-surface:#f5f5f5;
        --s-control:#ebebeb;--s-border:rgba(0,0,0,.13);
        --s-accent:var(--primary-color,#44739e);
        --s-active:var(--state-active-color,#ff9800);
        background:var(--s-surface);color:var(--s-text);
        box-shadow:0 5px 19px rgba(0,0,0,.07);
      }
      /* Dark: HA Theme übernimmt Grundfarben, keine erzwungene Blaupalette. */
      .panel[data-theme='dark'] {
        --s-text:var(--primary-text-color,#edf0f4);
        --s-muted:var(--secondary-text-color,#adb4bc);
        --s-surface:var(--ha-card-background,var(--card-background-color,#20252c));
        --s-control:var(--secondary-background-color,rgba(255,255,255,.06));
        --s-border:var(--divider-color,rgba(255,255,255,.12));
        --s-active:var(--state-active-color,#ff9800);
        background:var(--s-surface);color:var(--s-text);
      }
      .header {display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px 12px}
      .brand {display:flex; align-items:center; gap:11px; min-width:0}
      .logo {width:37px;height:37px;display:grid;place-items:center;border-radius:12px;
        color:var(--s-accent); background:color-mix(in srgb,var(--s-accent) 13%,transparent)}
      .logo ha-icon {--mdc-icon-size:22px}
      .name {font-size:15px;font-weight:700;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .sub {font-size:10px;font-weight:700;letter-spacing:.16em;color:var(--s-muted);margin-top:3px}
      .status {display:flex;align-items:center;gap:7px;padding:7px 9px;border-radius:12px;
        background:var(--s-control);font-size:11px;white-space:nowrap}
      .dot {width:7px;height:7px;border-radius:50%;background:var(--s-accent)}
      .status.ringing .dot {background:var(--warning-color,#ffac40);animation:pulse 1s infinite}
      @keyframes pulse {50%{opacity:.3}}
      .cam-frame {position:relative;margin:0 12px;overflow:hidden;border-radius:16px;background:#10151c;
        aspect-ratio:var(--cam-ratio,16/9)}
      .panel.compact-video .cam-frame {margin:0 1px;border-radius:10px;}
      .cam-host {position:absolute;inset:0;overflow:hidden}
      .cam-host > * {height:100%;width:100%;display:block}
      .cam-host custom-web-rtc-card, .cam-host webrtc-camera {width:100%;height:100%}
      .cam-badge {position:absolute;z-index:2;left:11px;top:11px;padding:5px 9px;border-radius:8px;
        font-size:10px;font-weight:750;letter-spacing:.10em;pointer-events:none;color:#fff;
        background:rgba(0,0,0,.55);backdrop-filter:blur(4px)}
      .cam-badge b {color:#5de5bc;font-weight:900}
      .actions {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:12px}
      .action {appearance:none;min-height:52px;border:1px solid var(--s-border);
        border-radius:14px;background:var(--s-control);
        color:var(--s-text);display:flex;align-items:center;gap:10px;
        justify-content:center;padding:8px 10px;font:600 13px/1.2 inherit;cursor:pointer;transition:background .15s,transform .12s}
      .action:active {transform:scale(.98)}
      .action:hover {background:color-mix(in srgb,var(--s-accent) 15%,var(--s-control))}
      .action ha-icon {--mdc-icon-size:22px;color:var(--s-accent)}
      .action.door {background:color-mix(in srgb,var(--s-accent) 16%,var(--s-control));}
      .action.on ha-icon {color:var(--s-active)}
      .action.on {border-color:color-mix(in srgb,var(--s-active) 38%,var(--s-border));}
      .action:disabled {opacity:.45;cursor:not-allowed}
      .sip-section {padding:0 12px 13px}
      .sip-label {display:flex;gap:7px;align-items:center;margin:1px 3px 8px;color:var(--s-muted);
        font-size:11px;font-weight:750;letter-spacing:.09em}
      .sip-label ha-icon {--mdc-icon-size:16px}
      .sip-host {border:1px solid var(--s-border);border-radius:14px;
        overflow:hidden;background:var(--s-surface)}
      .sip-host > * {display:block;width:100%}
      .hint {font-size:11px;color:var(--s-muted);padding:9px 14px 13px}
      .error {margin:8px;padding:10px;border-radius:9px;color:var(--error-color,#ec6d6d);
        background:color-mix(in srgb,var(--error-color,#ec6d6d) 12%,transparent);font-size:12px}
      @media (min-width:650px){.actions {grid-template-columns:repeat(4,minmax(0,1fr))}}
    `;
    shadow.append(style);
    const panel=document.createElement('div');panel.className='panel';panel.setAttribute('data-theme',c.theme);if(c.compact_video)panel.classList.add('compact-video');shadow.append(panel);
    const header=document.createElement('div');header.className='header';if(c.show_header!==false)panel.append(header);
    const brand=document.createElement('div');brand.className='brand';header.append(brand);
    const logo=document.createElement('div');logo.className='logo';logo.innerHTML='<ha-icon icon="mdi:doorbell-video"></ha-icon>';brand.append(logo);
    const titles=document.createElement('div');brand.append(titles);
    const name=document.createElement('div');name.className='name';name.textContent=c.title;titles.append(name);
    const sub=document.createElement('div');sub.className='sub';sub.textContent=c.subtitle;titles.append(sub);
    this._status=document.createElement('div');this._status.className='status';
    this._status.innerHTML='<span class="dot"></span><span class="status-text"></span>';
    if(c.show_status!==false) header.append(this._status);
    const frame=document.createElement('div');frame.className='cam-frame';frame.style.setProperty('--cam-ratio',/^[0-9]+\s*\/\s*[0-9]+$/.test(String(c.camera_ratio))?c.camera_ratio:'16/9');panel.append(frame);this._cameraFrame=frame;
    this._cameraHost=document.createElement('div');this._cameraHost.className='cam-host';frame.append(this._cameraHost);
    this._buttons=[];
    this._activeActionKey='';
    this._actionArea=null;
    if(c.show_actions!==false) {
      this._actionArea=document.createElement('div');
      this._actionArea.className='actions';
      panel.append(this._actionArea);
    }
    this._renderActions(this._effectiveStation());
    if(c.show_sip!==false) {
      const section=document.createElement('section');section.className='sip-section';panel.append(section);
      const label=document.createElement('div');label.className='sip-label';label.innerHTML='<ha-icon icon="mdi:phone-in-talk"></ha-icon><span>SIP CORE · SPRECHVERBINDUNG</span>';section.append(label);
      this._sipHost=document.createElement('div');this._sipHost.className='sip-host';section.append(this._sipHost);
    } else this._sipHost=null;
    if(c.footer_text) {const foot=document.createElement('div');foot.className='hint';foot.textContent=c.footer_text;panel.append(foot);}
    this._cameraCard=null;this._cameraKey='';this._sipCard=null;this._cameraVisible=false;
    this._updateState();this._mountCards();
  }
  _caller() {
    if (this._config?.follow_sip_core === false) return '';
    return String(window.sipCore?.remoteExtension ?? '').trim();
  }

  _managerMap() {
    if (this._config?.camera_by_caller && typeof this._config.camera_by_caller === 'object')
      return this._config.camera_by_caller;
    if (this._config?.follow_sip_core === false) return {};
    return window.sipCore?.config?.popup_config?.smartify?.camera_by_caller || {};
  }

  _effectiveStation() {
    const caller = this._caller();
    const map = this._managerMap();
    // In idle state a particular door card may be bound to a station_extension.
    const selected = caller || String(this._config?.station_extension || '');
    const station = map[selected] || {};
    const c = this._config || {};
    return {
      caller, selected, station,
      stream: station.stream || c.stream || '',
      mode: station.stream_mode || station.mode || c.mode || 'mse',
      media: station.stream_media || station.media || c.media || 'video',
      camera_ui: station.stream_ui ?? station.camera_ui ?? c.camera_ui,
      camera_mode: station.camera_mode || c.camera_mode || 'always',
      bell_entity: station.bell_entity || station.bell || c.bell_entity || ''
    };
  }

  _renderActions(effective) {
    if (!this._actionArea) return;
    const c = this._config;
    const station = effective.station;
    const mappedCall = Boolean(effective.caller && Object.keys(this._managerMap()).length);
    // During calls, never expose a different door's static fallback button.
    // Missing/unknown caller -> generic controls only, no station-specific unlock.
    const door = station.door_entity || station.door || (mappedCall ? '' : c.door_entity);
    const light = station.light_entity || station.light || (mappedCall ? '' : c.light_entity);
    const actions = [];
    if (door) actions.push({entity:door,label:c.door_label||'Tür öffnen',icon:c.door_icon||'mdi:door-open',service:station.door_service||c.door_service,kind:'door',confirm:station.door_confirm ?? c.door_confirm ?? true});
    if (light) actions.push({entity:light,label:c.light_label||'Licht',icon:c.light_icon||'mdi:lightbulb',service:station.light_service||c.light_service,kind:'light'});
    if(Array.isArray(c.actions)) actions.push(...c.actions);
    const key=JSON.stringify(actions);
    if(key===this._activeActionKey) return;
    this._activeActionKey=key;
    this._buttons=[];
    this._actionArea.replaceChildren();
    this._actionArea.style.display=actions.length?'':'none';
    for (const action of actions) {
      if (!action.entity || !/^[a-z_]+\.[a-zA-Z0-9_]+$/.test(action.entity)) continue;
      const btn=document.createElement('button');btn.type='button';btn.className='action '+(action.kind||'');
      const ico=document.createElement('ha-icon');ico.setAttribute('icon',action.icon||'mdi:flash');btn.append(ico);
      const txt=document.createElement('span');txt.textContent=action.label||action.entity;btn.append(txt);
      btn.addEventListener('click',()=>this._perform(action,btn));this._actionArea.append(btn);
      this._buttons.push({btn,action});
    }
  }

  _sipExtensions() {
    const c=this._config;
    // New form first; legacy extensions and the original single-contact settings remain supported.
    const mapping=this._managerMap();
    const generated=Object.keys(mapping).length
      ? Object.fromEntries(Object.entries(mapping).map(([number,station]) => [number,{
          name:station.label || number, override_icon:'mdi:doorbell-video'
        }]))
      : {[String(c.sip_extension)]: {name:c.sip_name,override_icon:'mdi:doorbell-video'}};
    const source=c.sip_extensions !== undefined ? c.sip_extensions :
      c.extensions !== undefined ? c.extensions : generated;
    const result={};
    for(const [number, original] of Object.entries(source||{})) {
      if(!/^[0-9A-Za-z_.+*-]+$/.test(number)) continue;
      if(original === false || original == null) continue;
      const entry=typeof original==='string' ? {name:original} : original;
      if(typeof entry !== 'object' || Array.isArray(entry)) continue;
      if(entry.visible===false || entry.enabled===false || entry.show===false) continue;
      const {visible,enabled,show,...sipOptions}=entry;
      result[number]=sipOptions;
    }
    return result;
  }
  async _mountCards() {
    const token=this._mountId=(this._mountId||0)+1;
    const c=this._config;
    try {
      if(!window.loadCardHelpers) throw new Error('Home Assistant loadCardHelpers nicht gefunden');
      const helpers=await window.loadCardHelpers();
      if(token!==this._mountId) return;
      this._helpers=helpers;
      this._syncCamera();
      if(this._sipHost) {
        // Don't duplicate the user-supplied action buttons inside SIP Core.
        const sipCfg={type:'custom:sip-call-card',extensions:this._sipExtensions()};
        if (!Object.keys(sipCfg.extensions).length) throw new Error('Kein sichtbarer SIP-Kontakt definiert');
        const sip=helpers.createCardElement(sipCfg);
        this._sipHost.replaceChildren(sip);this._sipCard=sip;
        this._sipContactsKey=JSON.stringify(sipCfg.extensions);
      }
      this._forwardHass();
    } catch(err) {this._showError(this._cameraHost,'Karteninitialisierung fehlgeschlagen: '+String(err.message||err));}
  }
  _syncCamera() {
    if (!this._config || !this._cameraFrame || !this._cameraHost) return;
    const current=this._effectiveStation();
    const shouldShow=Boolean(current.stream) &&
      (current.camera_mode==='always' ||
      (current.camera_mode==='auto' &&
        (Boolean(current.caller) || Boolean(current.bell_entity && this._hass?.states[current.bell_entity]?.state==='on'))));
    this._cameraFrame.style.display=shouldShow?'':'none';
    this._cameraVisible=shouldShow;
    if (!shouldShow) {
      this._cameraHost.replaceChildren();
      this._cameraCard=null;
      this._cameraKey='';
    } else {
      const opts={type:'custom:webrtc-camera',url:current.stream,mode:current.mode,media:current.media,ui:current.camera_ui!==false};
      const key=JSON.stringify(opts);
      if (key!==this._cameraKey && this._helpers) {
        try {
          const camera=this._helpers.createCardElement(opts);
          this._cameraHost.replaceChildren(camera);
          this._cameraCard=camera;
          this._cameraKey=key;
          if (this._hass) camera.hass=this._hass;
        } catch(err) {
          this._cameraCard=null;this._cameraKey='';
          this._showError(this._cameraHost,'Kamera konnte nicht geladen werden: '+String(err.message||err));
        }
      }
    }
  }
  _syncSipContacts() {
    if(!this._sipHost || !this._helpers || !this._sipCard) return;
    const extensions=this._sipExtensions();
    const key=JSON.stringify(extensions);
    if(key===this._sipContactsKey || !Object.keys(extensions).length) return;
    try {
      const sip=this._helpers.createCardElement({type:'custom:sip-call-card',extensions});
      this._sipHost.replaceChildren(sip);
      this._sipCard=sip;
      this._sipContactsKey=key;
      if(this._hass) sip.hass=this._hass;
    } catch(e) {console.warn('Smartify: SIP contact refresh failed',e);}
  }
  _forwardHass() {if(!this._hass)return;for(const card of [this._cameraCard,this._sipCard]) if(card)card.hass=this._hass;}
  _updateState() {
    if(!this._config||!this._status)return;
    const effective=this._effectiveStation();
    this._renderActions(effective);
    const ring=Boolean(effective.bell_entity && this._hass?.states?.[effective.bell_entity]?.state==='on');
    this._status.classList.toggle('ringing',!!ring);
    this._status.querySelector('.status-text').textContent=ring?'KLINGELT':effective.caller?'SIP · '+effective.caller:'BEREIT';
    this._syncCamera();
    this._syncSipContacts();
    if(!this._hass) return;
    for(const {btn,action} of this._buttons||[]) {
      const state=this._hass.states[action.entity];
      btn.classList.toggle('on',state?.state==='on');
      btn.disabled=!state || ['unavailable','unknown'].includes(state.state);
    }
  }
  _showError(host,message) {const p=document.createElement('div');p.className='error';p.textContent=message;host.replaceChildren(p);}
  async _perform(action,button) {
    if(!this._hass)return;
    if(action.confirm && !window.confirm(`Aktion „${action.label||action.entity}“ ausführen?`))return;
    const domain=action.domain || action.entity.split('.')[0];
    const service=action.service || 'toggle';
    const serviceData={entity_id:action.entity,...(action.service_data||{})};
    button.disabled=true;
    try {await this._hass.callService(domain,service,serviceData)}
    catch(err){console.error('Smartify Doorstation service error',err);this._showError(this.shadowRoot.querySelector('.actions'),'Aktion fehlgeschlagen: '+(err.message||err));}
    finally {button.disabled=false;this._updateState();}
  }
}
if (!customElements.get('smartify-doorstation-card')) customElements.define('smartify-doorstation-card',SmartifyDoorstationCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'smartify-doorstation-card',name:'Smartify Doorstation 2.7',description:'go2rtc/MSE + mehrere ein- und ausblendbare SIP-Kontakte + HA-Aktionen'});

;
/* Smartify Doorstation Popup v3.3.1
 *
 * Optisch und funktional 1:1 das originale SIP-Core-Popup (sip-call-dialog),
 * weil es direkt davon erbt. Erweitert um:
 *   - Livestream per go2rtc (RTSP) über custom:webrtc-camera
 *   - Kamera je anrufender SIP-Nummer (popup_config.smartify.camera_by_caller)
 *   - Token-Fix für /api/sip-core/* (Upstream-Issue #195 / PR #235)
 *
 * Konfiguration vollständig über SIP Core. Reihenfolge der Auswertung für die
 * aktuelle Gegenstelle (sipCore.remoteExtension), spätere Quelle gewinnt:
 *   1. popup_config.smartify                     gemeinsame Standardwerte
 *   2. popup_config.extensions['<Nummer>']       Einträge wie beim Original
 *   3. popup_config.smartify.camera_by_caller['<Nummer>']   (Smartify SIP Manager)
 *
 *   popup_override_component: smartify-doorstation-popup
 *   popup_config:
 *     smartify:
 *       stream: cam_pt2                # Standard-Stream, falls kein Eintrag passt
 *       mode: mse
 *       camera_mode: always
 *       camera_by_caller:
 *         '200':
 *           label: Haustür
 *           stream: akuvox_s535
 *           mode: mse
 *           camera_mode: auto
 *           bell_entity: binary_sensor.akuvox_s535_klingel
 *     extensions:
 *       '104':
 *         name: iPad
 *         stream: cam_pt2              # go2rtc-Streamname
 *         stream_mode: mse             # optional: mse | webrtc | hls | mjpeg (auch: mode)
 *         stream_media: video          # optional: video | audio | video,audio (auch: media)
 *         stream_ui: false             # optional: Kamera-Bedienelemente (auch: camera_ui)
 *         stream_max_height: 70vh      # optional, Standard 70vh (auch: max_height)
 *         camera_mode: auto            # optional: always (Standard) | auto | hidden
 *
 * camera_mode:
 *   always  Video zeigen, sobald eine Quelle (stream oder camera_entity) da ist.
 *   hidden  Nie Video, stattdessen die Audio-Animation des Originals.
 *   auto    Video, wenn die Quelle verfügbar ist; camera_entity darf nicht
 *           unavailable/unknown sein. bell_entity wird nur ohne laufendes
 *           Gespräch ausgewertet (kurze Klingelimpulse beenden das Video nicht).
 *
 * Der Videobereich passt sich an das Seitenverhältnis des Streams an (bis er
 * bekannt ist: 16:9); Hochformat wird auf stream_max_height begrenzt.
 *
 * Changelog:
 *   3.3.1  Nur Dokumentation: camera_by_caller und Auswertungsreihenfolge beschrieben.
 *   3.3.0  camera_by_caller, gemeinsame smartify-Standardwerte, Aliasnamen der
 *          Stream-Optionen, Video bleibt während des Gesprächs trotz kurzer Klingelimpulse.
 *   3.2.0  Videobereich passt sich dem Seitenverhältnis an.
 *   3.1.0  camera_mode always | auto | hidden mit Original-Animation.
 *   3.0.0  Neuaufbau als Erweiterung des Original-Popups.
 */

// Token-Fix: SIP Core ruft /api/sip-core/config und /api/sip-core/asterisk-ingress
// mit dem gerade gespeicherten Zugriffstoken auf. Nach Standby oder einem
// Websocket-Neuaufbau ist das oft abgelaufen, und HA meldet einen fehlgeschlagenen
// Login. Hier wird vor genau diesen Anfragen ein gültiges Token eingesetzt.
(function patchSipCoreFetch() {
  if (window.__smartifySipConfigFetchPatched) return;
  window.__smartifySipConfigFetchPatched = true;
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : (input?.url || String(input));
    if (!url.includes('/api/sip-core/')) return originalFetch(input, init);
    const auth = document.querySelector('home-assistant')?.hass?.auth;
    if (!auth) return originalFetch(input, init);
    try {
      if (auth.expired) await auth.refreshAccessToken();
    } catch (e) {
      console.warn('Smartify: Token-Erneuerung für SIP Core fehlgeschlagen', e);
    }
    const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined));
    headers.set('Authorization', `Bearer ${auth.accessToken}`);
    if (input instanceof Request) return originalFetch(new Request(input, { ...init, headers }));
    return originalFetch(input, { ...init, headers });
  };
})();

(function defineSmartifyPopup() {
  const TAG = 'smartify-doorstation-popup';
  const CAMERA_TAG = 'webrtc-camera';
  const liveHass = () => document.querySelector('home-assistant')?.hass;

  customElements.whenDefined('sip-call-dialog').then(() => {
    if (customElements.get(TAG)) return;
    const Base = customElements.get('sip-call-dialog');

    class SmartifyDoorstationPopup extends Base {
      _smartifyCamWrap = null;
      _smartifyCamCard = null;
      _smartifyCamKey = '';
      _smartifyWaiting = false;

      _smartifyCaller() {
        const core = window.sipCore;
        return String(core?.remoteExtension ?? this.remoteExtension ?? '').trim();
      }

      _smartifySettings() {
        return window.sipCore?.config?.popup_config?.smartify || this.config?.smartify || {};
      }

      // Manager output is stored in SIP Core: popup_config.smartify.camera_by_caller.
      // It has priority over legacy popup_config.extensions[caller], followed by
      // a generic smartify.stream. Missing matches never borrow another caller's video.
      _smartifyExtension() {
        const caller = this._smartifyCaller();
        const popup = window.sipCore?.config?.popup_config || this.config || {};
        const common = popup.smartify || {};
        const legacy = caller ? (popup.extensions?.[caller] || {}) : {};
        const mapped = caller ? common.camera_by_caller?.[caller] : null;
        const result = {...common, ...legacy, ...(mapped || {})};
        if (mapped) result._smartifyMapped = true;
        return Object.keys(result).length ? result : null;
      }

      _smartifyStreamConfig() {
        const ext = this._smartifyExtension();
        const stream = ext?.stream;
        if (!stream || typeof stream !== 'string') return null;
        return {
          url: stream,
          mode: ext.stream_mode || ext.mode || 'mse',
          media: ext.stream_media || ext.media || 'video',
          ui: ext.stream_ui === true || ext.camera_ui === true,
          maxHeight: typeof (ext.stream_max_height || ext.max_height) === 'string'
            && /^[0-9.]+(px|vh|%)$/.test(ext.stream_max_height || ext.max_height)
              ? (ext.stream_max_height || ext.max_height) : '70vh',
        };
      }

      // null = leave unchanged if no Smartify stream was configured.
      _smartifyWantsVideo(ext) {
        const hasStream = typeof ext.stream === 'string' && ext.stream.length > 0;
        const mode = ext.camera_mode || 'always';
        if (!hasStream && !ext.camera_mode) return null;
        if (mode === 'hidden') return false;
        const hasSource = hasStream || Boolean(ext.camera_entity);
        if (!hasSource) return false;
        if (mode !== 'auto') return true;
        const hass = liveHass() || this.hass;
        // A late-loaded camera element is handled by _smartifyBuildCamera().
        if (ext.camera_entity) {
          const cam = hass?.states?.[ext.camera_entity];
          if (!hasStream && !cam) return false;
          if (cam && ['unavailable', 'unknown'].includes(cam.state)) return false;
        }
        // SIP calls outlast short (e.g. 2-second) bell sensors. A current caller
        // is sufficient to keep video on until the call ends.
        if (!this._smartifyCaller() && ext.bell_entity
            && hass?.states?.[ext.bell_entity]?.state !== 'on') return false;
        return true;
      }

      render() {
        const ext = this._smartifyExtension();
        const want = ext ? this._smartifyWantsVideo(ext) : null;
        if (want === null) return super.render();
        const caller = this._smartifyCaller();
        if (!caller) return super.render();

        // SIP Core's original popup decides between camera and visualizer via
        // extensions[remoteExtension].camera_entity. Temporarily provide the
        // marker during synchronous render, without persisting any changes.
        const corePopup = window.sipCore?.config?.popup_config;
        const containers = [...new Set([corePopup, this.config])]
          .filter(obj => obj && typeof obj === 'object');
        const restore = [];
        try {
          for (const p of containers) {
            const hadExtensions = Object.prototype.hasOwnProperty.call(p, 'extensions');
            const extensions = p.extensions || (p.extensions = {});
            const hadCaller = Object.prototype.hasOwnProperty.call(extensions, caller);
            const previous = extensions[caller];
            const next = {...(previous || {})};
            if (want) {
              if (!next.camera_entity) next.camera_entity = ext.camera_entity || 'smartify.stream';
            } else {
              delete next.camera_entity;
              this._smartifyDropCamera();
            }
            extensions[caller] = next;
            restore.push(() => {
              if (hadCaller) extensions[caller] = previous;
              else delete extensions[caller];
              if (!hadExtensions) delete p.extensions;
            });
          }
          return super.render();
        } finally {
          for (const restoreOne of restore.reverse()) restoreOne();
        }
      }

      _smartifyDropCamera() {
        if (this._smartifySizeTimer) clearInterval(this._smartifySizeTimer);
        this._smartifySizeTimer = undefined;
        this._smartifyCamWrap?.remove();
        this._smartifyCamWrap = null;
        this._smartifyCamCard = null;
        this._smartifyCamKey = '';
      }

      _smartifyBuildCamera(cfg, key) {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'position:relative;display:block;width:100%;aspect-ratio:16/9;'
          + 'background:#000;overflow:hidden;margin:0 auto;';
        this._smartifyApplySize(wrap, 16, 9, cfg.maxHeight);

        if (!customElements.get(CAMERA_TAG)) {
          // Karte noch nicht geladen: kurz Platzhalter zeigen, danach neu aufbauen.
          wrap.style.display = 'flex';
          wrap.style.alignItems = 'center';
          wrap.style.justifyContent = 'center';
          wrap.style.color = '#aaa';
          wrap.textContent = 'Kamera wird geladen …';
          if (!this._smartifyWaiting) {
            this._smartifyWaiting = true;
            customElements.whenDefined(CAMERA_TAG).then(() => {
              this._smartifyWaiting = false;
              this._smartifyDropCamera();
              this.requestUpdate();
            });
          }
          return { wrap, card: null };
        }

        const card = document.createElement(CAMERA_TAG);
        try {
          card.setConfig({ url: cfg.url, mode: cfg.mode, media: cfg.media, ui: cfg.ui });
        } catch (e) {
          wrap.style.display = 'flex';
          wrap.style.alignItems = 'center';
          wrap.style.justifyContent = 'center';
          wrap.style.color = 'var(--error-color, #db4437)';
          wrap.textContent = 'Kamera-Konfiguration ungültig: ' + String(e?.message || e);
          return { wrap, card: null };
        }
        card.style.cssText = 'display:block;width:100%;height:100%;';
        wrap.append(card);
        this._smartifyWatchVideoSize(wrap, card, cfg.maxHeight);
        return { wrap, card };
      }

      // Breite so wählen, dass das Video bei seinem Seitenverhältnis nicht höher
      // als maxHeight wird; die Höhe ergibt sich dann aus aspect-ratio.
      _smartifyApplySize(wrap, w, h, maxHeight) {
        if (!(w > 0 && h > 0)) return;
        const ratio = w / h;
        wrap.style.aspectRatio = `${w} / ${h}`;
        wrap.style.width = `min(100%, calc(${maxHeight} * ${ratio.toFixed(4)}))`;
      }

      // Das <video> der webrtc-camera suchen und auf dessen echte Größe reagieren.
      _smartifyWatchVideoSize(wrap, card, maxHeight) {
        let tries = 0;
        const findVideo = () => card.video instanceof HTMLVideoElement ? card.video
          : (card.querySelector?.('video') || card.shadowRoot?.querySelector?.('video'));
        const attach = (video) => {
          const update = () => this._smartifyApplySize(wrap, video.videoWidth, video.videoHeight, maxHeight);
          video.addEventListener('loadedmetadata', update);
          video.addEventListener('resize', update);
          update();
        };
        this._smartifySizeTimer = setInterval(() => {
          const video = findVideo();
          if (video) {
            clearInterval(this._smartifySizeTimer);
            this._smartifySizeTimer = undefined;
            attach(video);
          } else if (++tries > 40) {
            clearInterval(this._smartifySizeTimer);
            this._smartifySizeTimer = undefined;
          }
        }, 250);
      }

      renderCameraStream(entity) {
        const cfg = this._smartifyStreamConfig();
        if (!cfg) return super.renderCameraStream(entity);

        // Bei geschlossenem Fenster keinen versteckten Stream weiterlaufen lassen.
        if (!this.open) {
          this._smartifyDropCamera();
          return '';
        }

        this.stopCameraRefresh?.();
        const key = JSON.stringify(cfg);
        if (!this._smartifyCamWrap || this._smartifyCamKey !== key) {
          this._smartifyDropCamera();
          const { wrap, card } = this._smartifyBuildCamera(cfg, key);
          this._smartifyCamWrap = wrap;
          this._smartifyCamCard = card;
          this._smartifyCamKey = card ? key : '';
        }

        const hass = liveHass() || this.hass;
        if (hass && this._smartifyCamCard) this._smartifyCamCard.hass = hass;
        return this._smartifyCamWrap;
      }

      connectedCallback() {
        super.connectedCallback?.();
        if (!this._smartifySipUpdate) {
          this._smartifySipUpdate = () => this.requestUpdate?.();
          for (const ev of ['sipcore-update', 'sipcore-call-started', 'sipcore-call-ended'])
            window.addEventListener(ev, this._smartifySipUpdate);
        }
      }

      closePopup() {
        super.closePopup();
        this._smartifyDropCamera();
      }

      disconnectedCallback() {
        if (this._smartifySipUpdate) {
          for (const ev of ['sipcore-update', 'sipcore-call-started', 'sipcore-call-ended'])
            window.removeEventListener(ev, this._smartifySipUpdate);
          this._smartifySipUpdate = null;
        }
        super.disconnectedCallback();
        this._smartifyDropCamera();
      }
    }

    customElements.define(TAG, SmartifyDoorstationPopup);
  });

  // SIP Core legt das Popup nur beim Start an. Wird popup_override_component
  // später in der Konfiguration gesetzt, das Element hier nachträglich anlegen.
  const reconcile = () => {
    const core = window.sipCore;
    if (core?.config?.popup_override_component !== TAG || core.config.popup_config == null) return;
    if (!document.querySelector(TAG)) document.body.appendChild(document.createElement(TAG));
  };
  window.addEventListener('sipcore-update', reconcile);
  window.addEventListener('sipcore-call-started', reconcile);
  window.addEventListener('location-changed', reconcile);
})();

