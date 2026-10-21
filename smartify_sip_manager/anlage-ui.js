/* Smartify SIP Manager 1.8 – Start: Prüfbericht, Anlagen-Modell, Kamerasuche, Erzeugen & Übernehmen.
 * Nutzt $, esc, msg, request, post aus app.js. Speichert nur das Modell (/data/anlage.json). */
(() => {
  'use strict';
  const LEVEL = {error: ['Rot', '✕'], warn: ['Gelb', '!'], info: ['Hinweis', 'i'], ok: ['OK', '✓']};
  const TYPES_DEFAULT = {ha_geraet: 'HA-Gerät (SIP Core)', sip_telefon: 'SIP-Telefon', tuerstation: 'Türstation',
    kamera: 'Kamera ohne SIP', extern: 'Externer Anschluss'};
  const FAE = ['kamerabild', 'video_im_anruf', 'ios', 'tuer_oeffnen'];
  const refOf = t => t.nummer || (t.typ === 'extern_ziel' && t.sip_adresse ? 'sip:' + t.sip_adresse.replace(/^sip:/i, '') : '') || t.endpoint || '';
  let state = {model: null, hash: null, typen: TYPES_DEFAULT, faehigkeiten: {}, dirty: false, loaded: false, hersteller: [], rtspPw: [], sipPw: []};
  let auswahl = {sip_users: [], endpoints_extern: [], streams: [], entities: {}, frei: []};
  let kameras = [];
  let preview = null;

  // ---------------------------------------------------------------- Prüfbericht
  async function pruefbericht() {
    const sum = $('pbSum'), root = $('pbRows');
    sum.textContent = 'Prüfe Asterisk, SIP Core, go2rtc …';
    sum.className = 'pb-sum';
    try {
      const r = await request('api/pruefbericht');
      const c = r.zusammenfassung;
      sum.innerHTML = `<b class="lv-error">${c.error} Rot</b> · <b class="lv-warn">${c.warn} Gelb</b> · ` +
        `<span class="muted">${c.info} Hinweise</span> · <span class="lv-ok">${c.ok} OK</span>`;
      const groups = {};
      for (const z of r.zeilen) (groups[z.bereich] = groups[z.bereich] || []).push(z);
      root.innerHTML = Object.entries(groups).map(([bereich, zeilen]) => {
        const worst = zeilen[0].level;
        const okOnly = zeilen.every(z => z.level === 'ok');
        return `<details class="pb-group" ${okOnly ? '' : 'open'}><summary><span class="pb-dot lv-${worst}">${LEVEL[worst][1]}</span>${esc(bereich)} <small>${zeilen.length}</small></summary>` +
          zeilen.map(z => `<div class="pb-row lv-${z.level}"><span class="pb-dot lv-${z.level}" title="${LEVEL[z.level][0]}">${LEVEL[z.level][1]}</span>` +
            `<div><b>${esc(z.titel)}</b>${z.detail ? `<p>${esc(z.detail)}</p>` : ''}${z.beheben ? `<p class="pb-fix">→ ${esc(z.beheben)}</p>` : ''}${z.aktion === 'ami_einrichten' ? '<p><button class="primary pb-ami">AMI-Zugang einrichten</button></p>' : ''}</div></div>`).join('') +
          '</details>';
      }).join('');
    } catch (e) {
      sum.textContent = 'Prüfung fehlgeschlagen: ' + e.message;
      root.innerHTML = '';
    }
  }


  // ---------------------------------------------------------------- AMI-Zugang (1.7)
  async function amiEinrichten(target) {
    if (!confirm('Eigenen AMI-Benutzer „smartify“ anlegen?\n\n· neues sicheres Passwort\n· nur aus dem internen Add-on-Netz erreichbar (172.30.32.0/23)\n· Eintrag in manager_custom.conf mit Backup\n\nBindet das Asterisk-Add-on manager_custom.conf nicht ein, legt der Manager zusätzlich custom/manager.conf an ([admin] bleibt gleich) – dann ist ein Neustart des Asterisk-Add-ons nötig.')) return;
    const box = target || $('amiSetupOut');
    try {
      const r = await post('api/ami/einrichten', {confirm: true});
      const html = `<div class="note"><b>${esc(r.note)}</b>
        ${r.neustart_noetig ? `<p><b>Nächster Schritt:</b> ${esc(r.befehl)}</p><p class="hint">Kontrolle danach im HA-Terminal:</p><pre class="diff ami-cmd">${esc(r.pruefen)}</pre>`
          : `<p>Im HA-Terminal ausführen:</p><pre class="diff ami-cmd">${esc(r.befehl)}</pre>`}
        <div class="toolbar"><button class="ami-copy">Befehl kopieren</button><button class="primary ami-test">Verbindung prüfen</button></div><div class="ami-test-out"></div></div>`;
      box.innerHTML = html;
      box.querySelector('.ami-copy').onclick = async () => { try { await navigator.clipboard.writeText(r.neustart_noetig ? r.pruefen : r.befehl); msg('Befehl kopiert'); } catch (_e) { msg('Kopieren nicht möglich – bitte markieren'); } };
      box.querySelector('.ami-test').onclick = async () => {
        const out = box.querySelector('.ami-test-out');
        out.textContent = 'Prüfe …';
        try {
          const d = await request('api/ami/diagnose');
          out.innerHTML = d.steps.map(s => `<div class="issue ${s.level === 'ok' ? 'ok' : s.level}">${esc(s.message)}</div>`).join('');
        } catch (e) { out.textContent = e.message; }
      };
    } catch (e) { msg('AMI-Zugang nicht eingerichtet: ' + e.message); }
  }

  // ---------------------------------------------------------------- Anlage
  const field = (id, key) => ({id, key});
  const ANLAGE_FIELDS = [field('anName', 'name'), field('anKunde', 'kunde'), field('anVon', 'nummer_von'), field('anBis', 'nummer_bis'),
    field('anLan', 'lan_ip'), field('anTs', 'tailscale_name'), field('anTsIp', 'tailscale_ip'), field('anHttps', 'go2rtc_https_url')];

  function setState(text, kind) {
    const el = $('anState');
    el.textContent = text;
    el.className = 'slot-info' + (kind ? ' ' + kind : '');
  }

  function markDirty() {
    state.dirty = true;
    setState('Ungespeicherte Änderungen', 'caution');
  }

  function blankTeilnehmer() {
    return {nummer: '', name: '', typ: 'sip_telefon', ha_benutzer: '', endpoint: '', stream: '', tuer_entity: '',
      licht_entity: '', klingel_entity: '', notiz: '', faehigkeiten: {kamerabild: false, video_im_anruf: false, ios: false, tuer_oeffnen: false}};
  }

  function render() {
    const m = state.model;
    for (const f of ANLAGE_FIELDS) $(f.id).value = m.anlage[f.key] || '';
    const typeOpts = typ => Object.entries(state.typen).filter(([k]) => k !== 'kamera').map(([k, v]) => `<option value="${k}" ${k === typ ? 'selected' : ''}>${esc(v)}</option>`).join('');
    renderKameraListe();
    $('anRows').innerHTML = m.teilnehmer.some(t => t.typ !== 'kamera') ? m.teilnehmer.map((t, i) => {
      if (t.typ === 'kamera') return '';
      const who = t.typ === 'ha_geraet' ? 'ha_benutzer' : (t.typ === 'extern_ziel' ? 'ziel' : '');
      return `<tr data-i="${i}">
        <td><input data-k="nummer" value="${esc(t.nummer)}" inputmode="numeric" size="5" list="anDlFrei" ${t.typ === 'kamera' ? 'placeholder="–"' : (t.typ === 'extern_ziel' ? 'placeholder="optional"' : 'placeholder="frei …"')}/></td>
        <td><input data-k="name" value="${esc(t.name)}" size="14"/>${erreichbarkeit(t)}</td>
        <td><select data-k="typ">${typeOpts(t.typ)}</select></td>
        <td>${who === 'ha_benutzer' ? selectBox('ha_benutzer', t.ha_benutzer, auswahl.ha_users || [], '– HA-Benutzer –')
          : who === 'endpoint' ? selectBox('endpoint', t.endpoint, auswahl.endpoints_extern, '– Endpoint –')
          : who === 'ziel' ? `<div class="an-ziel"><label>Ausgang ${anschlussBox('endpoint', t.endpoint, 'ausgang', '– Anschluss –')}</label><label>Eingang ${anschlussBox('eingang', t.eingang || '', 'eingang', '– keiner –')}</label><label>Adresse <input data-k="sip_adresse" value="${esc(t.sip_adresse || '')}" placeholder="name@sip.linphone.org"/></label><label title="Tailscale-IP des Handys (in der Tailscale-App). Nur nötig, wenn das Handy über den Eingang direkt anruft. Mehrere mit Komma.">IP Handy <input data-k="quell_ips" value="${esc(ipText(t.quell_ips))}" placeholder="${t.eingang ? 'z. B. 100.64.10.20' : 'erst Eingang wählen'}" ${t.eingang ? '' : 'disabled'}/></label><div class="an-darf"><span>darf anrufen</span>${t.eingang ? checkList('darf_anrufen', t.darf_anrufen || [], anrufOptionen()) : '<small class="muted">erst Eingang wählen</small>'}</div></div>`
          : '<span class="muted">–</span>'}</td>
        <td><input data-k="stream" value="${esc(t.stream)}" size="11" list="anDlStream" placeholder="${t.typ === 'ha_geraet' ? 'z. B. ipad_gang' : 'go2rtc-Name'}"/>${t.rtsp ? `<small class="an-src" title="RTSP-Quelle">${esc(t.rtsp.host)}:${t.rtsp.port}${esc(t.rtsp.pfad)}${t.rtsp.video?.length ? ' · ' + esc(t.rtsp.video.join('/')) : ''}${t.rtsp.benutzer && !state.rtspPw.includes(t.stream) ? ' · <b class="lv-warn">Passwort fehlt</b>' : ''}</small>` : ''}</td>
        ${FAE.map(f => `<td class="an-check"><input type="checkbox" data-f="${f}" ${t.faehigkeiten[f] ? 'checked' : ''} title="${esc(state.faehigkeiten[f] || f)}"/></td>`).join('')}
        <td class="an-ent">${t.typ === 'tuerstation' || t.tuer_entity || t.licht_entity || t.klingel_entity ? `
          <label>Tür <input data-k="tuer_entity" value="${esc(t.tuer_entity)}" list="anDlTuer" placeholder="switch./lock.…"/></label>
          <label>Licht <input data-k="licht_entity" value="${esc(t.licht_entity)}" list="anDlLicht" placeholder="light.…"/></label>
          <label>Klingel <input data-k="klingel_entity" value="${esc(t.klingel_entity)}" list="anDlKlingel" placeholder="binary_sensor.…"/></label>` : '<span class="muted">–</span>'}</td>
        <td class="an-zugang">${['sip_telefon', 'tuerstation'].includes(t.typ) && t.nummer && state.sipPw.includes(t.nummer) ? `<button class="an-zug" data-n="${esc(t.nummer)}">Zugang</button>` : '<span class="muted">–</span>'}${['sip_telefon', 'tuerstation'].includes(t.typ) ? `<label class="an-realm" title="Anmelde-Bereich (realm). Leer = automatisch: Handy über Tailscale (gleiches Handy wie …) → Tailscale-IP von HA, sonst LAN-IP von HA. Nur ausfüllen, wenn das Gerät eine andere Domain nutzt.">Domain/Realm <input data-k="realm" value="${esc(t.realm || '')}" placeholder="${esc(realmAuto(t) ? 'auto: ' + realmAuto(t) : 'leer = asterisk')}" size="14" list="anDlRealm"/></label>` : ''}${t.typ === 'sip_telefon' ? `<label class="an-realm" title="Ist dieses SIP-Konto auf einem Handy, das auch als Cloud-Teilnehmer (Linphone-Konto) eingetragen ist? Dann klingelt es nicht bei sich selbst, wenn es eine Rufgruppe anruft, und zählt als Mitglied.">gleiches Handy wie <select data-k="gleiches_geraet"><option value="">– eigenes Gerät –</option>${state.model.teilnehmer.filter(x => x.typ === 'extern_ziel').map(x => `<option value="${esc(refOf(x))}" ${refOf(x) === t.gleiches_geraet ? 'selected' : ''}>${esc((x.nummer ? x.nummer + ' ' : '') + x.name)}</option>`).join('')}</select></label>` : ''}</td>
        <td><button class="an-del" title="Zeile entfernen">✕</button></td></tr>`;
    }).join('') : '<tr><td colspan="12" class="muted">Noch keine Teilnehmer. „Aus bestehender Konfiguration übernehmen“ oder „Teilnehmer hinzufügen“.</td></tr>';
    renderSide();
  }

  // Alles außer der Teilnehmertabelle neu zeichnen (Fokus und Eingaben in der Tabelle bleiben erhalten)
  function renderSide() {
    const m = state.model;
    renderKameraListe();
    renderTrunks();
    renderEingaenge();
    const byRef = Object.fromEntries(m.teilnehmer.map(t => [refOf(t), t]));
    const names = refs => refs.map(r => byRef[r] ? (byRef[r].nummer ? byRef[r].nummer + ' ' : '') + byRef[r].name : r).join(', ') || '<span class="muted">–</span>';
    $('anWege').innerHTML = m.wege.length ? m.wege.map(w => `<tr>
        <td><b>${esc(w.nummer || '–')}</b></td><td>${esc(w.name)}</td>
        <td>${names(w.von)}</td><td>${names(w.ziele)}</td><td>${w.klingelzeit} s</td></tr>`).join('')
      : '<tr><td colspan="5" class="muted">Noch keine Rufgruppen. Im Rufgruppen-Manager Teilnehmer auf „＋ Neue Gruppe“ ziehen.</td></tr>';
  }

  // Erreichbarkeit interner Teilnehmer: ohne Haken keine Einschränkung; mit Haken nur die angehakten Nummern
  function erreichbarkeit(t) {
    if (!INTERN.includes(t.typ) || !t.nummer) return '';
    const box = (key, titel, hinweis, options) => {
      const an = Array.isArray(t[key]);
      return `<div class="an-lim"><label title="${esc(hinweis)}"><input type="checkbox" data-lim="${key}" ${an ? 'checked' : ''}/>${titel}</label>${an ? checkList(key, t[key], options) : ''}</div>`;
    };
    const an = Array.isArray(t.anruf_ziele) || Array.isArray(t.angerufen_von);
    return `<details class="an-erreich" ${an ? 'open' : ''}><summary>Erreichbarkeit${an ? ' <b class="lv-warn">eingeschränkt</b>' : ''}</summary>`
      + box('anruf_ziele', 'darf nur anrufen:', 'Ohne Haken darf dieser Teilnehmer alle erreichbaren Nummern wählen. Mit Haken nur die angehakten.', limOptionen('ziele', t))
      + box('angerufen_von', 'darf nur angerufen werden von:', 'Ohne Haken darf jeder diesen Teilnehmer direkt wählen. Rufgruppen steuern ihre Anrufer selbst (Rufgruppen-Manager).', limOptionen('von', t))
      + '</details>';
  }
  // Optionslisten ohne Neuzeichnen der Eingabezeilen aktualisieren.
  // Dadurch bleiben Fokus, geöffnete Details und ausgewählte Berechtigungen erhalten.
  function refreshErreichbarkeit() {
    const rows = [...document.querySelectorAll('#anRows tr[data-i]')];
    // Noch nicht gespeicherte Checkboxen übernehmen, bevor ihre Listen ersetzt werden.
    for (const tr of rows) {
      const t = state.model.teilnehmer[Number(tr.dataset.i)];
      if (!t) continue;
      tr.querySelectorAll('[data-pick="anruf_ziele"], [data-pick="angerufen_von"], [data-pick="darf_anrufen"]').forEach(list => {
        t[list.dataset.pick] = [...list.querySelectorAll('input:checked')].map(input => input.value);
      });
    }
    for (const tr of rows) {
      const t = state.model.teilnehmer[Number(tr.dataset.i)];
      if (!t) continue;
      const nameCell = tr.querySelector('[data-k="name"]')?.parentElement;
      const oldDetails = nameCell?.querySelector('.an-erreich');
      const wasOpen = oldDetails?.open;
      oldDetails?.remove();
      if (nameCell) {
        const html = erreichbarkeit(t);
        if (html) {
          nameCell.insertAdjacentHTML('beforeend', html);
          // Beim erstmaligen Anzeigen gelten die Voreinstellungen, sonst der bisherige Zustand.
          if (oldDetails) nameCell.querySelector('.an-erreich').open = wasOpen;
        }
      }
      // Auch die Auswahl "darf anrufen" der externen Cloud-Teilnehmer live nachziehen.
      const cloudBox = tr.querySelector('.an-darf');
      if (cloudBox) {
        cloudBox.innerHTML = '<span>darf anrufen</span>' + (t.eingang
          ? checkList('darf_anrufen', t.darf_anrufen || [], anrufOptionen())
          : '<small class="muted">erst Eingang wählen</small>');
      }
    }
  }
  const INTERN = ['ha_geraet', 'sip_telefon', 'tuerstation'];
  function limOptionen(art, t) {
    if (art === 'von') {
      return state.model.teilnehmer.filter(x => INTERN.includes(x.typ) && x.nummer && x !== t)
        .map(x => ({value: x.nummer, label: `${x.nummer} ${x.name}`, typ: state.typen[x.typ] || x.typ}));
    }
    const cloud = state.model.teilnehmer.filter(x => x.typ === 'extern_ziel' && x.nummer).map(x => ({value: x.nummer, label: `${x.nummer} ${x.name}`, typ: 'Cloud-Teilnehmer'}));
    return [...anrufOptionen().filter(o => o.value !== t.nummer), ...cloud].sort((a, b) => a.value.localeCompare(b.value, 'de', {numeric: true}));
  }

  function checkList(key, selected, options) {
    const unknown = selected.filter(v => !options.some(o => o.value === v)).map(v => ({value: v, label: v + ' ?', typ: ''}));
    const items = [...options, ...unknown];
    if (!items.length) return '<small class="muted">keine internen Nummern</small>';
    return `<div class="an-checks" data-pick="${key}">` + items.map(o => `<label title="${esc(o.typ)}"><input type="checkbox" value="${esc(o.value)}" ${selected.includes(o.value) ? 'checked' : ''}/>${esc(o.label)}</label>`).join('') + '</div>';
  }

  // Kameras ohne SIP sind keine Teilnehmer: eigene Liste; ihr Bild erscheint, wenn ein Teilnehmer mit diesem Stream anruft
  function renderKameraListe() {
    const el = $('anKams');
    if (!el) return;
    const m = state.model;
    const kams = m.teilnehmer.map((t, i) => [t, i]).filter(([t]) => t.typ === 'kamera');
    if (!kams.length) { el.innerHTML = '<tr><td colspan="6" class="muted">Noch keine Kameras. Unten „Netzwerk durchsuchen“ oder „Kamera von Hand eintragen“.</td></tr>'; return; }
    el.innerHTML = kams.map(([t, i]) => {
      const users = m.teilnehmer.filter(x => x.typ !== 'kamera' && x.stream && x.stream === t.stream);
      const src = t.rtsp ? `${esc(t.rtsp.host)}:${t.rtsp.port}${esc(t.rtsp.pfad)}` : '<span class="muted">keine RTSP-Quelle</span>';
      const codec = t.rtsp?.video?.length ? esc(t.rtsp.video.join('/')) + (t.rtsp.audio?.length ? ' · ' + esc(t.rtsp.audio.join('/')) : '') : '<span class="muted">–</span>';
      const pw = t.rtsp?.benutzer ? (state.rtspPw.includes(t.stream) ? '<span class="lv-ok">gespeichert</span>' : '<b class="lv-warn">fehlt</b>') : '<span class="muted">–</span>';
      return `<tr data-i="${i}"><td><input data-k="name" value="${esc(t.name)}" size="14"/></td>
        <td><input data-k="stream" value="${esc(t.stream)}" size="12"/></td><td><small>${src}</small></td><td><small>${codec}</small></td><td><small>${pw}</small></td>
        <td><small>${users.length ? users.map(x => esc([x.nummer, x.name].filter(Boolean).join(' '))).join(', ') : '<span class="lv-warn">von keinem Teilnehmer genutzt</span>'}</small></td>
        <td><button class="an-del" title="Kamera entfernen">✕</button></td></tr>`;
    }).join('');
  }

  // Anschlüsse (z. B. linphone-cloud / linphone-in) sind keine Teilnehmer – nur Info, wer sie nutzt
  function renderTrunks() {
    const el = $('anTrunks');
    if (!el) return;
    const trunks = (auswahl.endpoints_extern || []).map(e => e.value);
    if (!trunks.length) { el.innerHTML = ''; return; }
    const ziele = state.model.teilnehmer.filter(t => t.typ === 'extern_ziel');
    el.innerHTML = '<b>Anschlüsse</b> (keine Teilnehmer, werden über die externen Ziele genutzt): ' + trunks.map(n => {
      const aus = ziele.filter(t => t.endpoint === n).map(t => t.name), ein = ziele.filter(t => t.eingang === n).map(t => t.name);
      const video = ziele.some(t => (t.endpoint === n || t.eingang === n) && t.faehigkeiten.video_im_anruf);
      const use = [aus.length ? 'Ausgang für ' + aus.join(', ') : '', ein.length ? 'Eingang für ' + ein.join(', ') : ''].filter(Boolean).join(' · ') || 'nicht genutzt';
      return `<span class="an-chip" title="${video ? 'Video-Codecs werden beim Übernehmen ergänzt' : ''}">${esc(n)}: ${esc(use)}${video ? ' · Video' : ''}</span>`;
    }).join(' ');
  }

  // Eingänge aus dem Vorschlag: bisherige Freigaben des alten Werkzeugs in „darf anrufen“ der Nutzer übertragen
  function eingaengeUebernehmen() {
    const callable = new Set(anrufOptionen().map(o => o.value));
    for (const e of state.model.eingaenge || []) {
      if (!e.freigaben) continue;
      const nutzer = state.model.teilnehmer.filter(t => t.typ === 'extern_ziel' && t.eingang === e.name);
      for (const t of nutzer) t.darf_anrufen = [...new Set([...(t.darf_anrufen || []), ...e.freigaben.filter(n => callable.has(n))])];
      // genau ein Nutzer ohne eigene IP: die IPs des Eingangs gehören zu seinem Handy
      if (nutzer.length === 1 && !ipList(nutzer[0].quell_ips).length && ipList(e.quell_ips).length) { nutzer[0].quell_ips = e.quell_ips; e.quell_ips = []; }
      e.uebernommen = nutzer.length > 0 || !e.freigaben.length;
      delete e.freigaben;
    }
  }

  const realmAuto = t => { const a = state.model?.anlage || {}; return t.gleiches_geraet && a.tailscale_ip ? a.tailscale_ip : (a.lan_ip || ''); };
  const ipList = v => (Array.isArray(v) ? v : String(v || '').split(/[\s,;]+/)).map(x => String(x).trim()).filter(Boolean);
  const ipText = v => ipList(v).map(x => x.replace(/\/(32|128)$/, '')).join(', ');
  function renderEingaenge() {
    const el = $('anEingaenge');
    if (!el) return;
    const eg = state.model.eingaenge || [];
    const ziele = state.model.teilnehmer.filter(t => t.typ === 'extern_ziel');
    el.innerHTML = `<div class="an-eg-head"><b>Eingänge</b> <small class="muted">Anrufe von außen ohne Anmeldung (z. B. Linphone über Tailscale direkt an <code>sip:104@&lt;Tailscale-IP von HA&gt;</code>). Asterisk nimmt sie nur von den Geräte-IPs an, die beim Teilnehmer unter „IP Handy“ stehen. Was erreichbar ist, steht dort unter „darf anrufen“. Änderungen wirken in Asterisk erst nach „Erzeugen &amp; Übernehmen“.</small></div>`
      + eg.map((e, i) => {
        const nutzer = ziele.filter(t => t.eingang === e.name);
        const tnIps = nutzer.filter(t => ipList(t.quell_ips).length).map(t => `${t.name}: ${ipText(t.quell_ips)}`);
        const keine = !ipList(e.quell_ips).length && !tnIps.length;
        return `<div class="an-eg" data-e="${i}"><input data-eg="name" value="${esc(e.name)}" size="14" placeholder="tailscale-in"/>
          <span class="an-eg-ips">nimmt an von: ${tnIps.length ? esc(tnIps.join(' · ')) : '<i class="muted">IP beim Teilnehmer eintragen</i>'}</span>
          <label title="Nur für Geräte, die keinen eigenen Teilnehmer haben (selten nötig). IPs der Teilnehmer stehen links und werden hier nicht wiederholt.">weitere IPs (ohne Teilnehmer) <input data-eg="ips" value="${esc(ipText(ipList(e.quell_ips).filter(ip => !nutzer.some(t => ipList(t.quell_ips).map(x => x.replace(/\/(32|128)$/, '')).includes(ip.replace(/\/(32|128)$/, ''))))))}" placeholder="meist leer" size="18"/></label>
          <small class="${nutzer.length ? 'muted' : 'lv-warn'}">${nutzer.length ? 'genutzt von ' + esc(nutzer.map(t => t.name).join(', ')) : 'noch von keinem Teilnehmer als Eingang gewählt'}</small>
          ${keine ? '<small class="lv-warn">keine IP – nimmt keine Anrufe an</small>' : ''}
          <button class="an-egdel" title="Eingang aus dem Modell entfernen (Asterisk-Endpoint bleibt)">✕</button></div>`;
      }).join('') + '<button id="anEgAdd" class="an-egadd">＋ Eingang anlegen</button>';
  }

  // Was ein externes Ziel (z. B. Linphone-Handy) direkt anrufen darf: interne Nummern und Weg-Rufnummern
  function anrufOptionen() {
    const typeLabel = typ => state.typen[typ] || typ;
    const intern = state.model.teilnehmer.filter(t => ['ha_geraet', 'sip_telefon', 'tuerstation'].includes(t.typ) && t.nummer)
      .map(t => ({value: t.nummer, label: `${t.nummer} ${t.name}`, typ: typeLabel(t.typ)}));
    const wege = state.model.wege.filter(w => w.nummer).map(w => ({value: w.nummer, label: `${w.nummer} ${w.name}`, typ: 'Rufgruppe'}));
    return [...intern, ...wege].sort((a, b) => a.value.localeCompare(b.value, 'de', {numeric: true}));
  }

  // Auswahl für Wege: nur vorhandene Teilnehmer der Anlage
  function wegOptionen() {
    const typeLabel = typ => state.typen[typ] || typ;
    const opt = t => ({value: refOf(t), label: t.nummer ? `${t.nummer} ${t.name}` : (t.typ === 'extern_ziel' ? `${t.name} (${(t.sip_adresse || '').replace(/^sip:/i, '')})` : `${t.name || t.endpoint} (extern)`), typ: typeLabel(t.typ), t});
    const all = state.model.teilnehmer.filter(t => refOf(t) && t.typ !== 'kamera').map(opt);
    const rank = {tuerstation: 0, sip_telefon: 1, ha_geraet: 2, extern_ziel: 3, extern: 4};
    const sorted = list => list.sort((a, b) => (rank[a.t.typ] - rank[b.t.typ]) || a.label.localeCompare(b.label, 'de', {numeric: true}));
    const vonOpts = all
      .map(o => o.t.typ === 'extern_ziel' ? {...o, label: o.label + (o.t.eingang ? ` – kommt über ${o.t.eingang}` : ' – kein Eingang gewählt')} : o);
    return {von: sorted(vonOpts), ziele: sorted(all.filter(o => ['ha_geraet', 'sip_telefon', 'extern_ziel'].includes(o.t.typ)))};
  }
  function pickSummary(selected, options, empty) {
    if (!selected.length) return `<span class="muted">${esc(empty)}</span>`;
    return selected.map(v => {
      const o = options.find(x => x.value === v);
      return `<span class="an-chip${o ? '' : ' an-chip-bad'}" title="${o ? esc(o.typ) : 'Nicht mehr in der Anlage'}">${esc(o ? o.label : v + ' ?')}</span>`;
    }).join('');
  }
  function picker(kind, selected, options, empty) {
    const unknown = selected.filter(v => !options.some(o => o.value === v)).map(v => ({value: v, label: v + ' (nicht mehr vorhanden)', typ: ''}));
    const items = [...options, ...unknown];
    return `<details class="an-pick" data-pick="${kind}"><summary>${pickSummary(selected, options, empty)}</summary><div class="an-pick-list">` +
      (items.length ? items.map(o => `<label><input type="checkbox" value="${esc(o.value)}" ${selected.includes(o.value) ? 'checked' : ''}/><span>${esc(o.label)}</span><small>${esc(o.typ)}</small></label>`).join('')
        : '<span class="muted">Keine passenden Teilnehmer</span>') + '</div></details>';
  }

  function readForm() {
    const m = state.model;
    for (const f of ANLAGE_FIELDS) m.anlage[f.key] = $(f.id).value.trim();
    document.querySelectorAll('#anRows tr[data-i], #anKams tr[data-i]').forEach(tr => {
      const t = m.teilnehmer[Number(tr.dataset.i)];
      tr.querySelectorAll('[data-k]').forEach(inp => { t[inp.dataset.k] = inp.value.trim(); });
      tr.querySelectorAll('[data-f]').forEach(inp => { t.faehigkeiten[inp.dataset.f] = inp.checked; });
      tr.querySelectorAll('[data-pick]').forEach(d => { t[d.dataset.pick] = [...d.querySelectorAll('input:checked')].map(x => x.value); });
    });
    document.querySelectorAll('#anEingaenge .an-eg[data-e]').forEach(row => {
      const e = (m.eingaenge || [])[Number(row.dataset.e)];
      if (!e) return;
      e.name = row.querySelector('[data-eg="name"]').value.trim();
      e.quell_ips = row.querySelector('[data-eg="ips"]').value.split(/[\s,;]+/).map(x => x.trim()).filter(Boolean);
    });
    document.querySelectorAll('#anWege tr[data-w]').forEach(tr => {
      const w = m.wege[Number(tr.dataset.w)];
      tr.querySelectorAll('[data-k]').forEach(inp => {
        const v = inp.value.trim();
        w[inp.dataset.k] = inp.dataset.k === 'klingelzeit' ? Number(v || 20) : v;
      });
      tr.querySelectorAll('[data-pick]').forEach(d => {
        w[d.dataset.pick] = [...d.querySelectorAll('input:checked')].map(x => x.value);
      });
      if (!w.name && w.von.length) {
        const t = m.teilnehmer.find(x => refOf(x) === w.von[0]);
        if (t) w.name = (t.typ === 'tuerstation' ? 'Klingel ' : 'Ruf von ') + t.name;
      }
    });
    return m;
  }

  async function load(force) {
    if (state.loaded && !force) return;
    try {
      const d = await request('api/anlage');
      Object.assign(state, {model: d.model, hash: d.hash, typen: d.typen || TYPES_DEFAULT, faehigkeiten: d.faehigkeiten || {}, dirty: false, loaded: true,
        hersteller: d.hersteller || [], rtspPw: d.rtsp_passwoerter || [], sipPw: d.sip_passwoerter || []});
      $('anTailscale').innerHTML = (d.tailscale || []).map(x => `<li>${esc(x)}</li>`).join('');
      $('anFaeHelp').textContent = FAE.map(f => (state.faehigkeiten[f] || f)).join(' · ');
      render();
      setState(d.saved ? 'Gespeichertes Modell geladen' : 'Noch kein Modell gespeichert', d.saved ? 'free' : 'caution');
      if (d.hinweise && d.hinweise.length) {
        $('anHints').innerHTML = d.hinweise.map(h => `<li class="lv-warn">${esc(h)}</li>`).join('');
        state.dirty = true;
        setState('Beim Laden korrigiert – bitte prüfen und speichern', 'caution');
      }
      loadAuswahl();
    } catch (e) {
      setState('Laden fehlgeschlagen: ' + e.message, 'busy');
      msg('Anlage konnte nicht geladen werden: ' + e.message);
    }
  }

  async function vorschlag() {
    setState('Lese Asterisk, SIP Core und go2rtc …');
    try {
      const d = await request('api/anlage/vorschlag');
      if (d.rtsp_passwoerter) state.rtspPw = d.rtsp_passwoerter;
      if (d.sip_passwoerter) state.sipPw = d.sip_passwoerter;
      readForm();
      const have = state.model.teilnehmer.length;
      let added = d.model.teilnehmer.length;
      if (have) {
        // Nur ergänzen: vorhandene Teilnehmer (auch geänderte) bleiben, neue kommen dazu
        const known = new Set(state.model.teilnehmer.flatMap(t => [refOf(t), t.nummer, t.stream, t.endpoint].filter(Boolean)));
        const neu = d.model.teilnehmer.filter(t => ![refOf(t), t.nummer, t.stream].filter(Boolean).some(k => known.has(k))
);
        added = neu.length;
        state.model.teilnehmer.push(...neu);
        const wegeNr = new Set(state.model.wege.map(w => w.nummer).filter(Boolean));
        const neueWege = (d.model.wege || []).filter(w => w.nummer && !wegeNr.has(w.nummer));
        state.model.wege.push(...neueWege);
        added += neueWege.length;
        const sipOk = !(d.hinweise || []).some(h => h.startsWith('SIP Core nicht lesbar'));
        const gone = sipOk ? state.model.teilnehmer.filter(t => t.typ === 'ha_geraet' && t.nummer
          && !d.model.teilnehmer.some(x => x.typ === 'ha_geraet' && x.nummer === t.nummer)) : [];
        if (gone.length && confirm(`Diese HA-Geräte gibt es in SIP Core nicht mehr:\n· ${gone.map(t => t.nummer + ' ' + t.name).join('\n· ')}\n\nAus dem Modell (und allen Rufgruppen) entfernen?`)) {
          const refs = new Set(gone.map(refOf));
          state.model.teilnehmer = state.model.teilnehmer.filter(t => !gone.includes(t));
          for (const w of state.model.wege) { w.von = w.von.filter(r => !refs.has(r)); w.ziele = w.ziele.filter(r => !refs.has(r)); }
          for (const t of state.model.teilnehmer) if (t.darf_anrufen) t.darf_anrufen = t.darf_anrufen.filter(r => !refs.has(r));
          msg(`${gone.length} entfernt – speichern nicht vergessen.`);
        }
        for (const [k, v] of Object.entries(d.model.anlage)) if (v && !state.model.anlage[k]) state.model.anlage[k] = v;
        state.model.eingaenge = state.model.eingaenge || [];
        const egNames = new Set(state.model.eingaenge.map(e => e.name));
        const neueEg = (d.model.eingaenge || []).filter(e => !egNames.has(e.name));
        state.model.eingaenge.push(...neueEg);
        added += neueEg.length;
      } else {
        state.model = d.model;
      }
      eingaengeUebernehmen();
      render(); renderAddMenu();
      $('anHints').innerHTML = (d.hinweise || []).map(h => `<li>${esc(h)}</li>`).join('');
      markDirty();
      msg(have ? (added ? `${added} neue Teilnehmer/Rufgruppen ergänzt – bestehende blieben unverändert. Prüfen und speichern.` : 'Nichts Neues gefunden – das Modell ist vollständig.')
        : `${added} Teilnehmer übernommen – prüfen und speichern.`);
    } catch (e) {
      setState('Vorschlag fehlgeschlagen: ' + e.message, 'busy');
    }
  }

  async function save() {
    try {
      const d = await post('api/anlage', {model: readForm(), hash: state.hash});
      Object.assign(state, {model: d.model, hash: d.hash, dirty: false});
      render();
      setState('Gespeichert', 'free');
      msg(d.note);
    } catch (e) {
      setState('Nicht gespeichert: ' + e.message, 'busy');
      msg('Nicht gespeichert: ' + e.message);
    }
  }

  async function exportModel() {
    if (state.dirty) { msg('Zuerst speichern – exportiert wird der gespeicherte Stand.'); return; }
    try {
      const d = await request('api/anlage/export');
      const name = (d.anlage.kunde || d.anlage.name || 'anlage').replace(/[^A-Za-z0-9_-]+/g, '-').slice(0, 40) || 'anlage';
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], {type: 'application/json'}));
      a.download = `smartify-anlage-${name}-${d.exportiert.slice(0, 10)}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { msg('Export fehlgeschlagen: ' + e.message); }
  }

  function importModel() {
    const f = $('anImport').files[0];
    if (!f) return;
    if (f.size > 2_000_000) { msg('Datei zu groß'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      $('anImport').value = '';
      let data;
      try { data = JSON.parse(reader.result); } catch (_e) { msg('Keine gültige JSON-Datei'); return; }
      if (!confirm(`Anlage „${data?.anlage?.name || data?.anlage?.kunde || '?'}“ importieren? Das aktuelle Modell wird ersetzt (Backup bleibt).`)) return;
      try {
        const d = await post('api/anlage/import', {data, confirm: true});
        msg('Importiert – ' + d.model.teilnehmer.length + ' Teilnehmer.');
        await load(true);
      } catch (e) { msg('Import fehlgeschlagen: ' + e.message); }
    };
    reader.readAsText(f);
  }



  // ---------------------------------------------------------------- Auswahllisten (1.6)
  function selectBox(key, value, options, empty) {
    const opts = options.slice();
    if (value && !opts.some(o => o.value === value)) opts.unshift({value, label: value + ' (nicht gefunden)'});
    return `<select data-k="${key}"><option value="">${esc(empty)}</option>${opts.map(o => `<option value="${esc(o.value)}" ${o.value === value ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select>`;
  }
  // Anschluss-Auswahl: passende zuerst (Ausgang bzw. Eingang), unpassende unter „andere“
  const ROLLE_TXT = {ausgang: 'Ausgang', eingang: 'Eingang', beide: 'Ein- und Ausgang'};
  function anschlussPassend(e, soll) { return e.rolle === soll || e.rolle === 'beide' || !e.rolle; }
  function anschlussBox(key, value, soll, empty) {
    const all = (auswahl.endpoints_extern || []).slice();
    for (const e of state.model.eingaenge || []) if (e.name && !all.some(o => o.value === e.name)) all.push({value: e.name, label: e.name + ' · neu (Eingang)', rolle: 'eingang', grund: 'Eingang im Modell'});
    if (value && !all.some(o => o.value === value)) all.unshift({value, label: value + ' (nicht gefunden)', rolle: ''});
    const opt = o => `<option value="${esc(o.value)}" ${o.value === value ? 'selected' : ''} title="${esc(o.grund ? 'erkannt an: ' + o.grund : 'nicht eindeutig erkennbar')}">${esc(o.label)}${o.rolle && o.rolle !== soll ? ' – ist ' + esc(ROLLE_TXT[o.rolle]) : ''}</option>`;
    const gut = all.filter(o => anschlussPassend(o, soll)), rest = all.filter(o => !anschlussPassend(o, soll));
    const warn = value && rest.some(o => o.value === value);
    return `<select data-k="${key}" class="${warn ? 'an-falsch' : ''}"><option value="">${esc(empty)}</option>`
      + (gut.length ? `<optgroup label="passend als ${ROLLE_TXT[soll]}">${gut.map(opt).join('')}</optgroup>` : '')
      + (rest.length ? `<optgroup label="andere (eher ${soll === 'ausgang' ? 'Eingang' : 'Ausgang'})">${rest.map(opt).join('')}</optgroup>` : '')
      + '</select>' + (warn ? `<small class="lv-warn an-rolle-hint">passt eher als ${soll === 'ausgang' ? 'Eingang' : 'Ausgang'}</small>` : '');
  }
  function fillDatalist(id, items) {
    let dl = document.getElementById(id);
    if (!dl) { dl = document.createElement('datalist'); dl.id = id; document.body.appendChild(dl); }
    dl.innerHTML = items.map(o => `<option value="${esc(o.value)}" label="${esc(o.label || '')}"></option>`).join('');
  }
  function nextWegNummer() {
    const used = new Set([...state.model.teilnehmer.map(t => t.nummer), ...state.model.wege.map(w => w.nummer), ...(auswahl.belegt || [])].filter(Boolean));
    for (let n = 600; n < 700; n++) if (!used.has(String(n))) return String(n);
    return '';
  }
  function nextFree() {
    const used = new Set(state.model.teilnehmer.map(t => t.nummer).filter(Boolean));
    return (auswahl.frei || []).find(n => !used.has(n)) || '';
  }
  function renderAddMenu() {
    const inModel = new Set(state.model.teilnehmer.map(t => t.ha_benutzer || t.endpoint || t.nummer).filter(Boolean));
    const users = auswahl.sip_users.filter(u => !inModel.has(u.ha_benutzer) && !state.model.teilnehmer.some(t => t.nummer === u.nummer));
    $('anAddTyp').innerHTML = '<option value="">＋ Teilnehmer hinzufügen …</option>' +
      '<optgroup label="Neu anlegen"><option value="neu:tuerstation">Türstation</option><option value="neu:sip_telefon">SIP-Telefon (meldet sich direkt an Asterisk an)</option>' +
      '<option value="neu:ha_geraet">HA-Gerät (Tablet mit SIP Core)</option><option value="neu:extern_ziel">Handy über Linphone Cloud / externe SIP-Adresse</option></optgroup>' +
      (users.length ? `<optgroup label="Aus SIP Core übernehmen">${users.map(u => `<option value="sip:${esc(u.ha_benutzer)}">${esc(u.nummer + ' · ' + (u.name || u.ha_benutzer))}</option>`).join('')}</optgroup>` : '');
  }
  async function loadAuswahl() {
    try {
      auswahl = await request('api/anlage/auswahl');
    } catch (e) { auswahl = {sip_users: [], endpoints_extern: [], streams: [], entities: {}, frei: [], meldungen: [e.message]}; }
    fillDatalist('anDlFrei', (auswahl.frei || []).map(n => ({value: n, label: 'frei'})));
    fillDatalist('anDlRealm', [[state.model?.anlage?.lan_ip, 'LAN-IP von HA'], [state.model?.anlage?.tailscale_ip, 'Tailscale-IP von HA']].filter(x => x[0]).map(([v, l]) => ({value: v, label: l})));
    fillDatalist('anDlWeg', [nextWegNummer()].filter(Boolean).map(n => ({value: n, label: 'nächste freie Rufnummer'})));
    fillDatalist('anDlStream', auswahl.streams || []);
    fillDatalist('anDlTuer', auswahl.entities.tuer || []);
    fillDatalist('anDlLicht', auswahl.entities.licht || []);
    fillDatalist('anDlKlingel', auswahl.entities.klingel || []);
    if (state.model) { render(); renderAddMenu(); }
  }
  function addTeilnehmer(choice) {
    readForm();
    const [kind, val] = [choice.split(':')[0], choice.slice(choice.indexOf(':') + 1)];
    const t = blankTeilnehmer();
    if (kind === 'neu') {
      t.typ = val;
      if (!['kamera', 'extern_ziel'].includes(val)) t.nummer = nextFree();
      t.name = {tuerstation: 'Türstation', sip_telefon: 'Telefon', ha_geraet: 'Tablet', kamera: 'Kamera', extern: 'Extern', extern_ziel: 'Handy'}[val] + (t.nummer ? ' ' + t.nummer : '');
      if (val === 'extern_ziel') {
        const eps = auswahl.endpoints_extern || [];
        const aus = eps.filter(e => e.rolle === 'ausgang'), beide = eps.filter(e => e.rolle === 'beide');
        const ep = aus.length === 1 ? aus[0] : (aus[0] || beide[0] || eps.find(e => !e.rolle));
        t.endpoint = ep ? ep.value : '';
        const prefix = (t.endpoint.split(/[-_]/)[0] || '').toLowerCase();
        const ein = eps.filter(e => e.rolle === 'eingang')
          .sort((a, b) => !(prefix && b.value.toLowerCase().startsWith(prefix)) - !(prefix && a.value.toLowerCase().startsWith(prefix)));
        t.eingang = ein[0] ? ein[0].value : (ep && ep.rolle === 'beide' ? ep.value : '');
        t.sip_adresse = '';
      }
      if (val === 'tuerstation') t.faehigkeiten.tuer_oeffnen = true;
      if (val === 'kamera') { t.faehigkeiten.kamerabild = true; msg('Tipp: Kameras findest du schneller unter „Kameras finden“.'); }
    } else if (kind === 'sip') {
      const u = auswahl.sip_users.find(x => x.ha_benutzer === val);
      Object.assign(t, {typ: 'ha_geraet', nummer: u.nummer, name: u.name || u.ha_benutzer, ha_benutzer: u.ha_benutzer});
    }
    state.model.teilnehmer.push(t);
    render(); renderAddMenu(); markDirty();
    const row = document.querySelector(`#anRows tr[data-i="${state.model.teilnehmer.length - 1}"] [data-k="name"]`);
    if (row) { row.focus(); row.select(); }
  }
  async function netzErkennen() {
    try {
      const n = await request('api/anlage/netz');
      const set = (id, v) => { if (v && !$(id).value) { $(id).value = v; markDirty(); } };
      set('anLan', n.lan_ip); set('anTs', n.tailscale_name); set('anTsIp', n.tailscale_ip); set('anHttps', n.go2rtc_https_url);
      if (!$('anHttps').value && $('anTs').value) { $('anHttps').value = `https://${$('anTs').value}:8443`; markDirty(); }
      msg(n.quellen.length ? 'Erkannt: ' + n.quellen.join(' · ') + ' – leere Felder wurden ausgefüllt.' : 'Nichts erkannt – Felder bitte von Hand ausfüllen.');
    } catch (e) { msg('Erkennen fehlgeschlagen: ' + e.message); }
  }


  // ---------------------------------------------------------------- Rufgruppen-Manager (1.13): Teilnehmer auf Gruppen ziehen
  const RG_ZIEL_TYPEN = ['ha_geraet', 'sip_telefon', 'extern_ziel'];
  const RG_ICON = {tuerstation: '🚪', sip_telefon: '☎', ha_geraet: '▣', extern_ziel: '☁'};
  let rgPick = null;
  const rgLabel = t => (t.nummer ? t.nummer + ' ' : '') + (t.name || t.endpoint || '');

  function rgPalette() {
    const tn = state.model.teilnehmer.filter(t => t.typ !== 'kamera' && refOf(t));
    const sect = (titel, list) => list.length ? `<div class="rg-sec"><h4>${titel}</h4>${list.map(t => `<div class="rg-chip rg-t-${t.typ} ${rgPick === refOf(t) ? 'rg-picked' : ''}" draggable="true" data-ref="${esc(refOf(t))}" title="${esc(state.typen[t.typ] || t.typ)} – ziehen oder antippen"><span class="rg-ic">${RG_ICON[t.typ] || '•'}</span>${esc(rgLabel(t))}</div>`).join('')}</div>` : '';
    $('rgPal').innerHTML = sect('Türstationen', tn.filter(t => t.typ === 'tuerstation')) + sect('Lokal', tn.filter(t => ['ha_geraet', 'sip_telefon'].includes(t.typ)))
      + sect('Cloud', tn.filter(t => t.typ === 'extern_ziel')) || '<p class="muted">Noch keine Teilnehmer – unter „Anlage &amp; Teilnehmer“ ergänzen.</p>';
  }

  function rgGroups() {
    const byRef = Object.fromEntries(state.model.teilnehmer.map(t => [refOf(t), t]));
    const chip = (w, zone, r) => {
      const t = byRef[r];
      return `<span class="rg-mem rg-t-${t ? t.typ : 'x'}" data-ref="${esc(r)}">${t ? `<span class="rg-ic">${RG_ICON[t.typ] || '•'}</span>${esc(rgLabel(t))}` : esc(r) + ' ?'}<button class="rg-x" data-zone="${zone}" data-ref="${esc(r)}" title="entfernen">×</button></span>`;
    };
    const zeiten = w => [10, 15, 20, 25, 30, 45, 60, 90, 120].concat([w.klingelzeit]).filter((v, j, a) => a.indexOf(v) === j).sort((a, b) => a - b);
    $('rgGroups').innerHTML = state.model.wege.map((w, i) => `<div class="rg-group" data-w="${i}">
        <div class="rg-head"><input class="rg-nr" data-wk="nummer" value="${esc(w.nummer || '')}" placeholder="Nr." inputmode="numeric"/>
          <input class="rg-name" data-wk="name" value="${esc(w.name)}" placeholder="Name der Gruppe"/>
          <select data-wk="klingelzeit">${zeiten(w).map(v => `<option value="${v}" ${v === w.klingelzeit ? 'selected' : ''}>${v} s</option>`).join('')}</select>
          <button class="rg-del" title="Gruppe löschen">✕</button></div>
        <div class="rg-zone" data-zone="von"><span class="rg-zl">Anrufer <small>${w.von.length ? `nur diese${w.mitglieder_rufen ? ' + Mitglieder' : ''} dürfen ${esc(w.nummer || '…')} wählen` : `leer = alle dürfen ${esc(w.nummer || '…')} wählen`}</small></span>${w.von.map(r => chip(w, 'von', r)).join('') || '<span class="rg-empty">hierher ziehen</span>'}</div>
        <div class="rg-zone rg-ziele" data-zone="ziele"><span class="rg-zl">Klingelt bei <small>gleichzeitig</small></span>${w.ziele.map(r => chip(w, 'ziele', r)).join('') || '<span class="rg-empty">hierher ziehen</span>'}</div>
        <label class="rg-note rg-ers" title="Alle unter „Klingelt bei“ dürfen die Gruppennummer auch selbst wählen – auch Cloud-Handys über ihren Eingang. Wer anruft, klingelt nicht bei sich selbst."><input type="checkbox" data-wk="mitglieder_rufen" ${w.mitglieder_rufen ? 'checked' : ''}/> Mitglieder dürfen die Gruppe anrufen (Anrufer wird übersprungen)</label>
        <label class="rg-note rg-ers" title="Gibt es diese Nummer schon als eigenen Eintrag in extensions.conf, ersetzt der Manager ihn beim Übernehmen (mit Backup)."><input type="checkbox" data-wk="ersetzen" ${w.ersetzen ? 'checked' : ''}/> bestehenden Dialplan-Eintrag dieser Nummer ersetzen</label></div>`).join('')
      + '<div class="rg-group rg-new" data-new="1"><div class="rg-zone rg-ziele" data-zone="neu"><span class="rg-zl">＋ Neue Gruppe</span><span class="rg-empty">Teilnehmer hierher ziehen</span></div></div>';
  }

  function rgLines() {
    const svg = $('rgLines'), board = $('rgBoard');
    const br = board.getBoundingClientRect();
    svg.setAttribute('width', board.scrollWidth); svg.setAttribute('height', board.scrollHeight);
    svg.innerHTML = '';
    const ns = 'http://www.w3.org/2000/svg';
    document.querySelectorAll('#rgGroups .rg-mem').forEach(m => {
      const src = document.querySelector(`#rgPal .rg-chip[data-ref="${CSS.escape(m.dataset.ref)}"]`);
      if (!src) return;
      const a = src.getBoundingClientRect(), b = m.getBoundingClientRect();
      const x1 = a.right - br.left + board.scrollLeft, y1 = a.top + a.height / 2 - br.top + board.scrollTop;
      const g = m.closest('.rg-group').getBoundingClientRect();
      const x2 = g.left - br.left + board.scrollLeft, y2 = b.top + b.height / 2 - br.top + board.scrollTop;
      const mx = (x1 + x2) / 2;
      const zone = m.closest('.rg-zone').dataset.zone;
      const p = document.createElementNS(ns, 'path');
      p.setAttribute('d', `M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`);
      p.setAttribute('class', `rg-line rg-l-${zone} ${m.classList.contains('rg-t-extern_ziel') ? 'rg-l-cloud' : ''} ${rgPick && rgPick !== m.dataset.ref ? 'rg-l-dim' : ''}`);
      p.dataset.ref = m.dataset.ref;
      svg.appendChild(p);
      const dot = document.createElementNS(ns, 'circle');
      dot.setAttribute('cx', x2); dot.setAttribute('cy', y2); dot.setAttribute('r', 3.5);
      dot.setAttribute('class', p.getAttribute('class') + ' rg-dot');
      svg.appendChild(dot);
    });
  }

  function rgRender() {
    if (!state.model) return;
    rgPalette(); rgGroups();
    requestAnimationFrame(rgLines);
    $('rgState').textContent = state.dirty ? 'Ungespeicherte Änderungen' : (state.loaded ? 'Gespeichert' : '');
    $('rgState').className = 'slot-info ' + (state.dirty ? 'caution' : 'free');
  }

  function rgChanged() {
    render(); renderAddMenu(); markDirty(); rgRender();
  }

  function rgAdd(zone, wIdx, ref) {
    const t = state.model.teilnehmer.find(x => refOf(x) === ref);
    if (!t) return;
    if ((zone === 'ziele' || zone === 'neu') && !RG_ZIEL_TYPEN.includes(t.typ)) { msg(`${rgLabel(t)} kann nicht angerufen werden (${state.typen[t.typ] || t.typ}) – nur als Anrufer.`); return; }
    if (zone === 'von' && t.typ === 'extern_ziel' && !t.eingang) { msg(`${rgLabel(t)} hat keinen Eingang – beim Teilnehmer den Eingang wählen.`); return; }
    readForm();
    let w;
    if (zone === 'neu') {
      w = {name: 'Ruf ' + (t.name || t.nummer || 'Gruppe'), nummer: nextWegNummer(), von: [], ziele: [], klingelzeit: 20, kontexte: [], ersetzen: false, mitglieder_rufen: false};
      state.model.wege.push(w);
      zone = 'ziele';
    } else {
      w = state.model.wege[wIdx];
    }
    if (!w[zone].includes(ref)) w[zone].push(ref);
    rgPick = null;
    rgChanged();
  }

  function rgWire() {
    const board = $('rgBoard');
    board.addEventListener('dragstart', e => {
      const c = e.target.closest('.rg-chip');
      if (c) { e.dataTransfer.setData('text/plain', c.dataset.ref); e.dataTransfer.effectAllowed = 'copy'; }
    });
    board.addEventListener('dragover', e => { const z = e.target.closest('.rg-zone'); if (z) { e.preventDefault(); z.classList.add('rg-over'); } });
    board.addEventListener('dragleave', e => { const z = e.target.closest('.rg-zone'); if (z) z.classList.remove('rg-over'); });
    board.addEventListener('drop', e => {
      const z = e.target.closest('.rg-zone');
      if (!z) return;
      e.preventDefault(); z.classList.remove('rg-over');
      const g = z.closest('.rg-group');
      rgAdd(z.dataset.zone, g.dataset.w === undefined ? -1 : Number(g.dataset.w), e.dataTransfer.getData('text/plain'));
    });
    board.addEventListener('click', e => {
      const chip = e.target.closest('.rg-chip');
      if (chip) { rgPick = rgPick === chip.dataset.ref ? null : chip.dataset.ref; rgRender(); return; }
      const x = e.target.closest('.rg-x');
      if (x) {
        readForm();
        const w = state.model.wege[Number(x.closest('.rg-group').dataset.w)];
        w[x.dataset.zone] = w[x.dataset.zone].filter(r => r !== x.dataset.ref);
        rgChanged(); return;
      }
      const del = e.target.closest('.rg-del');
      if (del) {
        const i = Number(del.closest('.rg-group').dataset.w), w = state.model.wege[i];
        if (!confirm(`Gruppe ${w.nummer || ''} „${w.name}“ löschen? Beim nächsten Übernehmen wird sie aus dem Dialplan entfernt.`)) return;
        readForm(); state.model.wege.splice(i, 1); rgChanged(); return;
      }
      const z = e.target.closest('.rg-zone');
      if (z && rgPick && !e.target.closest('input,select,button')) {
        const g = z.closest('.rg-group');
        rgAdd(z.dataset.zone, g.dataset.w === undefined ? -1 : Number(g.dataset.w), rgPick);
      }
    });
    board.addEventListener('change', e => {
      const k = e.target.dataset.wk;
      if (!k) return;
      readForm();
      const w = state.model.wege[Number(e.target.closest('.rg-group').dataset.w)];
      w[k] = k === 'klingelzeit' ? Number(e.target.value) : (k === 'ersetzen' || k === 'mitglieder_rufen') ? e.target.checked : e.target.value.trim();
      rgChanged();
    });
    board.addEventListener('scroll', () => requestAnimationFrame(rgLines));
    window.addEventListener('resize', () => { if ($('rufgruppen').classList.contains('active')) requestAnimationFrame(rgLines); });
    $('rgNeu').onclick = () => { readForm(); state.model.wege.push({name: 'Neue Gruppe', nummer: nextWegNummer(), von: [], ziele: [], klingelzeit: 20, kontexte: [], ersetzen: false}); rgChanged(); };
    $('rgSave').onclick = async () => { await save(); rgRender(); };
  }

  // ---------------------------------------------------------------- Kameras finden
  const slug = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
  function vendorOptions(sel) {
    return state.hersteller.map(h => `<option value="${esc(h.hersteller)}" ${h.hersteller === sel ? 'selected' : ''}>${esc(h.bezeichnung)}</option>`).join('');
  }
  function renderKameras() {
    const root = $('kamRows');
    if (!kameras.length) { root.innerHTML = '<tr><td colspan="9" class="muted">Keine RTSP-Geräte gefunden.</td></tr>'; return; }
    root.innerHTML = kameras.map((k, i) => `<tr data-k="${i}" class="${k.go2rtc ? 'kam-go2rtc' : ''}">
      <td>${k.manuell ? `<input data-f="host" value="${esc(k.host)}" placeholder="192.168.2.50" size="12"/><input data-f="port" value="${k.port}" size="4"/>` : `<b>${esc(k.host)}</b>:${k.port}`}</td>
      <td><small>${esc([k.onvif_name, k.onvif_hardware, k.server].filter(Boolean).join(' · ') || (k.manuell ? 'von Hand' : '–'))}${k.go2rtc ? '<br><b>go2rtc auf HA – keine Kamera</b>' : ''}${k.im_modell ? `<br>im Modell: ${esc(k.im_modell)}` : ''}</small></td>
      <td><select data-f="hersteller">${vendorOptions(k.hersteller)}</select></td>
      <td><input data-f="pfad" value="${esc(k.pfad)}" size="20"/></td>
      <td><input data-f="benutzer" value="${esc(k.benutzer || '')}" size="8" placeholder="admin"/></td>
      <td><input data-f="passwort" type="password" value="${esc(k.passwort || '')}" size="8" autocomplete="off"/></td>
      <td><input data-f="stream" value="${esc(k.stream)}" size="12"/></td>
      <td class="kam-res">${k.ergebnis ? `<span class="${k.ergebnis.ok ? 'lv-ok' : 'lv-error'}">${esc(k.ergebnis.meldung)}</span>${k.ergebnis.video?.length ? `<br><small>Video ${esc(k.ergebnis.video.join(', '))}${k.ergebnis.audio?.length ? ' · Audio ' + esc(k.ergebnis.audio.join(', ')) : ''}</small>` : ''}` : ''}</td>
      <td class="kam-act"><button class="kam-test">Testen</button> <button class="kam-add primary" ${k.ergebnis?.ok ? '' : 'disabled title="Erst erfolgreich testen"'}>Übernehmen</button></td></tr>`).join('');
  }
  function readKamera(tr) {
    const k = kameras[Number(tr.dataset.k)];
    tr.querySelectorAll('[data-f]').forEach(inp => { k[inp.dataset.f] = inp.dataset.f === 'port' ? Number(inp.value || 554) : inp.value.trim(); });
    return k;
  }
  async function kameraSuche() {
    readForm();
    $('kamState').textContent = 'Suche im Netz ' + (state.model.anlage.lan_ip || '?') + '/24 … (ca. 5–15 s)';
    try {
      const d = await post('api/kameras/suche', {lan_ip: state.model.anlage.lan_ip});
      kameras = d.kameras.map(k => ({...k, stream: k.im_modell || slug((k.onvif_name || k.hersteller) + '_' + k.host.split('.').pop()), benutzer: '', passwort: ''}));
      $('kamState').textContent = `${kameras.filter(k => !k.go2rtc).length} Gerät(e) in ${d.netz}`;
      renderKameras();
    } catch (e) { $('kamState').textContent = 'Suche fehlgeschlagen: ' + e.message; }
  }
  function kameraManuell() {
    const g = state.hersteller.find(h => h.hersteller === 'generic') || {hersteller: 'generic', pfad: '/stream1'};
    kameras.push({manuell: true, host: '', port: 554, hersteller: g.hersteller, pfad: g.pfad, benutzer: '', passwort: '', stream: 'kamera_' + (kameras.length + 1)});
    renderKameras();
  }
  async function kameraTest(tr) {
    const k = readKamera(tr);
    k.ergebnis = {ok: false, meldung: 'Teste …'};
    renderKameras();
    try {
      k.ergebnis = await post('api/kameras/test', {host: k.host, port: k.port, pfad: k.pfad, benutzer: k.benutzer, passwort: k.passwort});
    } catch (e) { k.ergebnis = {ok: false, meldung: e.message}; }
    renderKameras();
  }
  async function kameraAdd(tr) {
    const k = readKamera(tr);
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(k.stream)) { msg('Streamname: nur Buchstaben, Ziffern, _ und -'); return; }
    readForm();
    try {
      if (k.passwort) await post('api/kameras/passwort', {stream: k.stream, passwort: k.passwort});
      if (!state.rtspPw.includes(k.stream) && k.passwort) state.rtspPw.push(k.stream);
      const rtsp = {host: k.host, port: k.port, pfad: k.pfad, benutzer: k.benutzer, hersteller: k.hersteller,
        video: k.ergebnis?.video || [], audio: k.ergebnis?.audio || [], zusatz: ''};
      let t = state.model.teilnehmer.find(x => x.stream === k.stream);
      if (!t) { t = {...blankTeilnehmer(), typ: 'kamera', name: k.onvif_name || k.stream, stream: k.stream}; state.model.teilnehmer.push(t); }
      t.rtsp = rtsp;
      t.faehigkeiten.kamerabild = true;
      k.im_modell = k.stream;
      render(); renderKameras(); markDirty();
      msg(`Kamera ${k.stream} übernommen – Modell speichern, dann „Erzeugen & Übernehmen“.`);
    } catch (e) { msg('Nicht übernommen: ' + e.message); }
  }

  async function zugang(btn) {
    try {
      const z = await request('api/anlage/zugang?nummer=' + encodeURIComponent(btn.dataset.n));
      btn.closest('td').innerHTML = `<small>Benutzer <b>${esc(z.benutzer)}</b><br>Passwort <code>${esc(z.passwort)}</code><br>Server ${esc(z.server || 'IP von HA')}</small>`;
    } catch (e) { msg(e.message); }
  }

  // ---------------------------------------------------------------- Erzeugen & Übernehmen
  const ZIEL_ORDER = ['asterisk', 'dialplan', 'go2rtc', 'sip_core'];
  async function erzVorschau() {
    if (state.dirty) { msg('Das Modell hat ungespeicherte Änderungen – zuerst unter „Anlage & Teilnehmer“ speichern.'); }
    $('erzState').textContent = 'Berechne …';
    $('erzResult').innerHTML = '';
    try {
      preview = await request('api/erzeugen/vorschau');
      $('erzHints').innerHTML = (preview.hinweise || []).map(h => `<li>${esc(h)}</li>`).join('');
      $('erzZiele').innerHTML = ZIEL_ORDER.map(z => {
        const p = preview.ziele[z];
        const status = p.fehler ? `<span class="lv-error">${esc(p.fehler)}</span>` : (p.changed ? '<span class="lv-warn">Änderungen</span>' : '<span class="lv-ok">schon aktuell</span>');
        const lint = p.lint_fehler ? `<p class="lv-error">Erzeugte Datei hat ${p.lint_fehler} Fehler – Übernahme gesperrt: ${esc((p.lint || []).map(i => i.message).join(' · '))}</p>` : '';
        return `<div class="erz-ziel"><label class="erz-head"><input type="checkbox" data-z="${z}" ${p.changed && !p.fehler && !p.lint_fehler ? 'checked' : 'disabled'}/> <b>${esc(p.titel)}</b> ${status}</label>
          ${lint}${p.hinweis ? `<p class="hint">${esc(p.hinweis)}</p>` : ''}
          <ul class="erz-akt">${(p.aktionen || []).map(a => `<li class="lv-${a.level}">${esc(a.text)}${a.aktion === 'rufgruppe_ersetzen' ? ` <button class="erz-ersetzen" data-nr="${esc(a.bezug)}">Bestehenden Eintrag ersetzen</button>` : ''}</li>`).join('') || '<li class="muted">Keine Aktionen</li>'}</ul>
          ${p.changed ? `<details><summary>Unterschiede anzeigen</summary><pre class="diff">${esc(p.diff)}</pre></details>` : ''}</div>`;
      }).join('');
      const any = ZIEL_ORDER.some(z => preview.ziele[z].changed && !preview.ziele[z].fehler);
      $('erzApplyBar').hidden = !any;
      $('erzState').textContent = any ? 'Vorschau bereit – Ziele auswählen und übernehmen.' : 'Alles ist bereits auf dem Stand des Modells.';
    } catch (e) { $('erzState').textContent = 'Vorschau fehlgeschlagen: ' + e.message; }
  }
  async function erzApply() {
    if (!preview) return;
    const ziele = [...document.querySelectorAll('#erzZiele [data-z]:checked')].map(x => x.dataset.z);
    if (!ziele.length) { msg('Nichts ausgewählt'); return; }
    const names = ziele.map(z => preview.ziele[z].titel).join('\n· ');
    if (!confirm('Jetzt übernehmen?\n· ' + names + '\n\nVorher wird jeweils ein Backup angelegt. go2rtc wird neu gestartet, SIP Core neu geladen.')) return;
    $('erzState').textContent = 'Übernehme …';
    try {
      const tokens = Object.fromEntries(ZIEL_ORDER.map(z => [z, preview.ziele[z].token]));
      const r = await post('api/erzeugen/uebernehmen', {ziele, tokens, confirm: true, reload: $('erzReload').checked});
      const e = r.ergebnisse;
      $('erzResult').innerHTML = '<div class="note">' + esc(r.note) + '<ul>' +
        (e.asterisk ? `<li>Asterisk: gespeichert${e.asterisk.reload ? ' · ' + esc(e.asterisk.reload) : ' · Reload nicht ausgeführt – „pjsip reload“ nötig'}</li>` : '') +
        (e.dialplan ? `<li>Dialplan: gespeichert${e.dialplan.reload ? ' · ' + esc(e.dialplan.reload) : ' · Reload nicht ausgeführt – „dialplan reload“ nötig'}</li>` : '') +
        (e.go2rtc ? `<li>go2rtc: gespeichert (Backup ${esc(e.go2rtc.backup)})${e.go2rtc.restarted ? ' · neu gestartet' : ' · Neustart nicht bestätigt'}</li>` : '') +
        (e.sip_core ? `<li>SIP Core: ${esc(e.sip_core.note || 'übernommen')}</li>` : '') + '</ul></div>';
      preview = null;
      $('erzApplyBar').hidden = true;
      $('erzState').textContent = 'Übernommen.';
    } catch (err) { $('erzState').textContent = 'Nicht übernommen: ' + err.message; msg('Nicht übernommen: ' + err.message); }
  }

  async function erzErsetzen(nr) {
    if (!state.loaded) await load(false);
    const w = state.model.wege.find(x => x.nummer === nr);
    if (!w) { msg(`Rufgruppe ${nr} nicht im Modell`); return; }
    if (!confirm(`Den eigenen Eintrag ${nr} in extensions.conf durch die Rufgruppe „${w.name}“ ersetzen?\n\nBeim Übernehmen wird vorher ein Backup angelegt.`)) return;
    readForm(); w.ersetzen = true; render(); markDirty();
    await save();
    if (!state.dirty) erzVorschau();
  }
  function wire() {
    $('erzZiele').addEventListener('click', e => { const b = e.target.closest('.erz-ersetzen'); if (b) erzErsetzen(b.dataset.nr); });
    $('pbRun').onclick = pruefbericht;
    $('pbRows').addEventListener('click', e => {
      if (e.target.classList.contains('pb-ami')) {
        const holder = document.createElement('div');
        e.target.closest('div').appendChild(holder);
        e.target.remove();
        amiEinrichten(holder);
      }
    });
    if ($('amiSetup')) $('amiSetup').onclick = () => amiEinrichten($('amiSetupOut'));
    $('anVorschlag').onclick = vorschlag;
    $('anSave').onclick = save;
    $('anExport').onclick = exportModel;
    $('anImport').onchange = importModel;
    $('anAddTyp').onchange = e => { if (e.target.value) addTeilnehmer(e.target.value); e.target.value = ''; };
    $('anErkennen').onclick = netzErkennen;
    $('anTs').addEventListener('change', () => { if (!$('anHttps').value && $('anTs').value) $('anHttps').value = `https://${$('anTs').value}:8443`; });
    $('anWegAdd').onclick = () => { readForm(); document.querySelector('[data-tab="rufgruppen"]').click(); };
    $('anlage').addEventListener('input', markDirty);
    $('anRows').addEventListener('input', e => {
      const k = e.target.dataset.k;
      if (k !== 'nummer' && k !== 'name') return;
      const tr = e.target.closest('tr[data-i]');
      if (!tr) return;
      const t = state.model.teilnehmer[Number(tr.dataset.i)];
      if (!t) return;
      // Ursprüngliche Nummer für die Zuordnung beim Verlassen des Eingabefeldes merken.
      if (k === 'nummer' && e.target.dataset.originalRef === undefined) e.target.dataset.originalRef = refOf(t);
      t[k] = e.target.value.trim();
      refreshErreichbarkeit();
    });
    $('anRows').addEventListener('change', e => {
      const lim = e.target.dataset.lim;
      if (lim) {
        readForm();
        const t = state.model.teilnehmer[Number(e.target.closest('tr').dataset.i)];
        t[lim] = e.target.checked ? limOptionen(lim === 'anruf_ziele' ? 'ziele' : 'von', t).map(o => o.value) : null;
        render();
        markDirty();
        return;
      }
      const pick = e.target.closest('[data-pick]');
      if (pick) {
        readForm();
        markDirty();
        return;
      }
      const k = e.target.dataset.k;
      if (k === 'ha_benutzer') {
        const t = state.model.teilnehmer[Number(e.target.closest('tr').dataset.i)];
        readForm();
        const twin = state.model.teilnehmer.find(x => x !== t && x.typ === 'ha_geraet' && x.ha_benutzer && x.ha_benutzer === t.ha_benutzer);
        if (twin) msg(`Achtung: „${t.ha_benutzer}“ ist auch bei ${twin.nummer} ${twin.name} eingetragen – dort einen anderen Benutzer wählen.`);
        else if (t.ha_benutzer) msg(`${t.nummer}: HA-Benutzer „${t.ha_benutzer}“ – wird bei „Erzeugen & Übernehmen“ in SIP Core gesetzt.`);
        if (!t.name || /^Tablet( \d+)?$/.test(t.name)) t.name = t.ha_benutzer;
        render(); renderAddMenu();
      } else if (k === 'endpoint') {
        readForm();
        const t = state.model.teilnehmer[Number(e.target.closest('tr').dataset.i)];
        if (!t.name || t.name === 'Extern') t.name = t.endpoint;
        render(); renderAddMenu();
      } else if (k === 'quell_ips') {
        readForm();
        const t = state.model.teilnehmer[Number(e.target.closest('tr').dataset.i)];
        const bad = ipList(t.quell_ips).filter(x => !/^\d{1,3}(\.\d{1,3}){3}(\/32)?$|^[0-9a-f:]+(\/128)?$/i.test(x));
        if (bad.length) msg('Keine gültige IP: ' + bad.join(', ') + ' – nur einzelne Geräte-IPs, keine Netzbereiche.');
        renderSide();
      } else if (['typ', 'nummer', 'name', 'sip_adresse', 'eingang'].includes(k)) {
        const t = state.model.teilnehmer[Number(e.target.closest('tr').dataset.i)];
        const before = k === 'nummer' && e.target.dataset.originalRef !== undefined ? e.target.dataset.originalRef : refOf(t);
        readForm();
        const after = refOf(t);
        if (before && after && before !== after) {
          for (const w of state.model.wege) { w.von = w.von.map(r => r === before ? after : r); w.ziele = w.ziele.map(r => r === before ? after : r); }
          // Umnummerierung darf bestehende Zugriffsrechte nicht auf der alten Nummer zurücklassen.
          if (k === 'nummer' && /^\\d{2,8}$/.test(before) && /^\\d{2,8}$/.test(after)) {
            for (const other of state.model.teilnehmer) {
              for (const key of ['anruf_ziele', 'angerufen_von', 'darf_anrufen']) {
                if (Array.isArray(other[key])) other[key] = [...new Set(other[key].map(r => r === before ? after : r))];
              }
            }
          }
        }
        if (k === 'nummer') delete e.target.dataset.originalRef;
        if (k === 'typ' || k === 'eingang') render();
        else { renderSide(); if (k === 'nummer' || k === 'name' || k === 'sip_adresse') refreshErreichbarkeit(); }
        renderAddMenu();
      }
      markDirty();
    });
    const delHandler = e => {
      if (!e.target.classList.contains('an-del')) return;
      readForm();
      const idx = Number(e.target.closest('tr').dataset.i), t = state.model.teilnehmer[idx];
      const label = [t.nummer, t.name].filter(Boolean).join(' ') || 'diesen Teilnehmer';
      const inWege = state.model.wege.filter(w => w.von.includes(refOf(t)) || w.ziele.includes(refOf(t)));
      if (!confirm(`${label} aus dem Modell entfernen?\n\nErst beim nächsten „Erzeugen & Übernehmen“ wird die Nebenstelle aus Asterisk entfernt (nur wenn der Manager sie verwaltet). SIP-Core-Benutzer bleiben unverändert.`
        + (inWege.length ? `\n\nAuch aus ${inWege.length} Rufgruppe(n) austragen.` : ''))) return;
      const ref = refOf(t);
      for (const w of state.model.wege) { w.von = w.von.filter(x => x !== ref); w.ziele = w.ziele.filter(x => x !== ref); }
      state.model.teilnehmer.splice(idx, 1);
      render(); renderAddMenu(); markDirty();
    };
    $('anRows').addEventListener('click', delHandler);
    $('anKams').addEventListener('click', delHandler);
    $('anKams').addEventListener('input', markDirty);
    document.addEventListener('click', e => {
      document.querySelectorAll('.an-pick[open]').forEach(d => { if (!d.contains(e.target)) d.open = false; });
    });
    $('anEingaenge').addEventListener('click', e => {
      if (e.target.id === 'anEgAdd') {
        readForm();
        state.model.eingaenge = state.model.eingaenge || [];
        const used = new Set([...(auswahl.endpoints_extern || []).map(x => x.value), ...state.model.eingaenge.map(x => x.name)]);
        let name = 'tailscale-in', k = 2;
        while (used.has(name)) name = 'tailscale-in' + k++;
        state.model.eingaenge.push({name, quell_ips: [], uebernommen: true});
        render(); markDirty();
        document.querySelector('#anEingaenge .an-eg:last-of-type [data-eg="ips"]')?.focus();
      } else if (e.target.classList.contains('an-egdel')) {
        readForm();
        const i = Number(e.target.closest('.an-eg').dataset.e), eg = state.model.eingaenge[i];
        if (!confirm(`Eingang „${eg.name}“ nicht mehr verwalten?\n\nDer Asterisk-Endpoint bleibt bestehen; vom Manager neu angelegte Teile fallen beim nächsten Übernehmen weg.`)) return;
        state.model.eingaenge.splice(i, 1); render(); markDirty();
      }
    });
    $('anEingaenge').addEventListener('change', () => { readForm(); renderSide(); });
    $('kamSuche').onclick = kameraSuche;
    $('kamManuell').onclick = kameraManuell;
    $('kamRows').addEventListener('click', e => {
      const tr = e.target.closest('tr[data-k]');
      if (!tr) return;
      if (e.target.classList.contains('kam-test')) kameraTest(tr);
      if (e.target.classList.contains('kam-add')) kameraAdd(tr);
    });
    $('kamRows').addEventListener('change', e => {
      const tr = e.target.closest('tr[data-k]');
      if (tr && e.target.dataset.f === 'hersteller') {
        const k = readKamera(tr), h = state.hersteller.find(x => x.hersteller === k.hersteller);
        if (h) { k.pfad = h.pfad; k.ergebnis = null; renderKameras(); }
      }
    });
    $('anRows').addEventListener('click', e => { if (e.target.classList.contains('an-zug')) zugang(e.target); });
    $('erzVorschau').onclick = erzVorschau;
    $('erzApply').onclick = erzApply;
    window.addEventListener('beforeunload', e => { if (state.dirty) { e.preventDefault(); e.returnValue = ''; } });
  }

  window.smartifyPruefbericht = pruefbericht;
  window.smartifyAnlage = () => load(false);
  window.smartifyErzeugen = () => { if (!preview) erzVorschau(); };
  window.smartifyRufgruppen = async () => { if (!state.loaded) await load(false); rgRender(); };
  rgWire();
  wire();
  if ($('start').classList.contains('active')) pruefbericht();
})();
