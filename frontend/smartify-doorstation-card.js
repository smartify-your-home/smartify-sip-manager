/* Smartify Doorstation v2.7.8 – HA frontend custom card.
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
      .video-toggle {position:absolute;z-index:5;right:10px;top:10px;padding:9px 12px;cursor:pointer;
        border:1px solid rgba(255,255,255,.4);border-radius:10px;color:#fff;background:rgba(0,0,0,.7);
        font:600 12px/1.2 inherit;touch-action:manipulation}
      .video-toggle:focus-visible{outline:3px solid var(--s-accent)}
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
      .sip-host video {max-height:min(60dvh,calc(100dvh - 180px)) !important;max-width:100% !important;object-fit:contain !important}
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
    const frame=document.createElement('div');frame.className='cam-frame';
    const ratio=/^[0-9]+\s*\/\s*[0-9]+$/.test(String(c.camera_ratio))?c.camera_ratio:'16/9';
    frame.style.setProperty('--cam-ratio',ratio);
    const dimensions=ratio.split('/').map(Number);
    const factor=dimensions[1]>0?dimensions[0]/dimensions[1]:16/9;
    frame.style.width=`min(calc(max(96px, min(60dvh, 100dvh - 180px)) * ${factor.toFixed(4)}), 100%)`;
    frame.style.marginInline='auto';
    panel.append(frame);this._cameraFrame=frame;
    this._cameraHost=document.createElement('div');this._cameraHost.className='cam-host';frame.append(this._cameraHost);
    this._videoShown=true;
    this._videoToggle=document.createElement('button');
    this._videoToggle.type='button';
    this._videoToggle.className='video-toggle';
    this._videoToggle.addEventListener('click',()=>{
      this._videoShown=!this._videoShown;
      this._syncCamera();
    });
    frame.append(this._videoToggle);
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
    this._videoToggle.hidden=!shouldShow;
    this._videoToggle.textContent=this._videoShown?'Video ausblenden':'Video anzeigen';
    this._videoToggle.setAttribute('aria-pressed',String(!this._videoShown));
    this._cameraVisible=shouldShow;
    if (!shouldShow || !this._videoShown) {
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
  _syncLocalPip() {
    try {
      if (!this._sipHost) return;
      const core=window.sipCore;
      const caller=this._caller();
      const station=this._managerMap()?.[caller] || {};
      const isDoor=Boolean(station.door_entity||station.door||station.bell_entity
        ||station.typ==='tuerstation'||station.type==='doorstation');
      let track=null;
      const session=core?.RTCSession;
      const pc=session?.connection;
      if (caller && !isDoor && session?.isEstablished?.()
          && !session.isMuted?.().video && typeof pc?.getSenders==='function') {
        track=pc.getSenders().map(sender=>sender?.track)
          .find(t=>t?.kind==='video'&&t.readyState==='live'&&t.enabled) || null;
      }
      if (!track) {
        this._localPip?.remove();this._localPip=null;this._localPipTrack=null;
        return;
      }
      if (this._localPipTrack===track && this._localPip) return;
      this._localPip?.remove();
      this._sipHost.style.position='relative';
      const box=document.createElement('div');
      box.style.cssText='position:absolute;z-index:5;right:8px;top:8px;'
        +'width:min(30%,160px);aspect-ratio:3/4;max-height:30dvh;border-radius:10px;'
        +'background:#111;border:2px solid #fff9;overflow:hidden;pointer-events:none;';
      const video=document.createElement('video');
      video.autoplay=true;video.playsInline=true;video.muted=true;
      video.style.cssText='width:100%;height:100%;object-fit:contain;';
      video.srcObject=new MediaStream([track]);
      const updateRatio=()=>{
        const w=video.videoWidth||track.getSettings?.().width;
        const h=video.videoHeight||track.getSettings?.().height;
        if(w>0&&h>0)box.style.aspectRatio=w+'/'+h;
      };
      video.addEventListener('loadedmetadata',updateRatio);
      video.addEventListener('resize',updateRatio);
      updateRatio();
      box.append(video);
      this._sipHost.append(box);
      video.play().catch(()=>{});
      this._localPip=box;this._localPipTrack=track;
    } catch(e) { console.warn('Smartify: lokales SIP-Video in Card nicht verfügbar',e); }
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
    this._syncLocalPip();
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
window.customCards.push({type:'smartify-doorstation-card',name:'Smartify Doorstation 2.7.8',description:'go2rtc/MSE + mehrere ein- und ausblendbare SIP-Kontakte + HA-Aktionen'});
