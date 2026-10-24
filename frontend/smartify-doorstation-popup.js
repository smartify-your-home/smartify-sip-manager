/* Smartify Doorstation Popup v3.3.3
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
 *   3.3.3  Videohöhe an freie Bildschirmhöhe angepasst; Platz für SIP-Bedienelemente reserviert.
 *   3.3.2  Empfangenen go2rtc-Stream im Gespräch ein-/ausblenden; keine Änderung an SIP-Videoübertragung.
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
      _smartifyVideoShown = true;

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
        // Reserve viewport height for the original SIP Core call buttons.
        // Viewport units react to iPad rotation and browser toolbar changes.
        const available = `max(96px, min(${maxHeight}, 42dvh, calc(100dvh - 320px)))`;
        wrap.style.maxHeight = available;
        wrap.style.width = `min(100%, calc(${available} * ${ratio.toFixed(4)}))`;
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
        if (!this._smartifyVideoShown) {
          this._smartifyDropCamera();
          const button=document.createElement('button');
          button.type='button';
          button.textContent='Video anzeigen';
          button.setAttribute('aria-label','Empfangenes Video wieder anzeigen');
          button.style.cssText='display:block;width:100%;padding:13px;border-radius:10px;'
            +'background:var(--secondary-background-color,#333);'
            +'color:var(--primary-text-color,white);border:1px solid var(--divider-color,#666);cursor:pointer;';
          button.addEventListener('click',()=>{
            this._smartifyVideoShown=true;
            this.requestUpdate();
          });
          return button;
        }
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
        const outer=document.createElement('div');
        outer.style.cssText='position:relative;width:100%;';
        outer.append(this._smartifyCamWrap);
        const toggle=document.createElement('button');
        toggle.type='button';
        toggle.textContent='Video ausblenden';
        toggle.setAttribute('aria-label','Empfangenes Video ausblenden');
        toggle.style.cssText='position:absolute;z-index:5;right:8px;top:8px;border-radius:9px;'
          +'background:rgba(0,0,0,.75);color:white;border:1px solid #ffffff80;'
          +'padding:8px 12px;font:600 12px sans-serif;cursor:pointer;';
        toggle.addEventListener('click',()=>{
          this._smartifyVideoShown=false;
          this._smartifyDropCamera();
          this.requestUpdate();
        });
        outer.append(toggle);
        return outer;
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
        this._smartifyVideoShown = true;
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
