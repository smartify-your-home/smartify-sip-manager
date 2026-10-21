/* Smartify SIP Manager 1.12 – Grafik „Verbindungen“ (SVG, ohne Bibliotheken). Nutzt $, esc, request aus app.js. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const COLS = [
    {gruppe: 'kamera', x: 20, w: 150, titel: 'Kameras'},
    {gruppe: 'lokal', x: 220, w: 200, titel: 'Lokal (Asterisk)'},
    {gruppe: 'mitte', x: 480, w: 190, titel: 'Asterisk · Rufgruppen'},
    {gruppe: 'anschluss', x: 730, w: 160, titel: 'Anschlüsse'},
    {gruppe: 'cloud', x: 950, w: 210, titel: 'Cloud'},
  ];
  const ART_LABEL = {direkt: 'ruft direkt an', weg: 'Rufgruppe', cloud_aus: 'ruft in die Cloud', cloud_ein: 'ruft aus der Cloud', cloud_direkt: 'direkt über Cloud', kamera: 'Kamerabild'};
  const TYP_LABEL = {ha_geraet: 'HA-Gerät', sip_telefon: 'SIP-Telefon', tuerstation: 'Türstation', extern_ziel: 'Linphone / extern',
    kamera: 'Kamera', anschluss: 'Anschluss', weg: 'Rufgruppe', asterisk: 'Zentrale'};
  let data = null, selected = null;

  const el = (name, attrs = {}, text) => {
    const n = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const colOf = n => n.gruppe === 'weg' || n.gruppe === 'zentrale' ? 'mitte' : n.gruppe;
  const artOn = art => document.querySelector(`.vb-bar [data-art="${art}"]`)?.checked;

  function layout() {
    const pos = {};
    let maxRows = 0;
    for (const c of COLS) {
      const list = data.knoten.filter(n => colOf(n) === c.gruppe)
        .sort((a, b) => (a.typ === 'asterisk' ? -1 : b.typ === 'asterisk' ? 1 : 0) || String(a.nummer || a.name).localeCompare(String(b.nummer || b.name), 'de', {numeric: true}));
      list.forEach((n, i) => { pos[n.id] = {x: c.x, y: 70 + i * 66, w: c.w, h: n.gruppe === 'kamera' || n.gruppe === 'anschluss' ? 40 : 48}; });
      maxRows = Math.max(maxRows, list.length);
    }
    return {pos, height: 90 + Math.max(maxRows, 1) * 66};
  }

  function pathBetween(a, b) {
    const ax = a.x + a.w, ay = a.y + a.h / 2, bx = b.x, by = b.y + b.h / 2;
    if (Math.abs(a.x - b.x) < 2) {            // gleiche Spalte: Bogen links außen
      const lx = a.x - 40 - Math.min(60, Math.abs(ay - by) / 4);
      return `M${a.x} ${ay} C${lx} ${ay}, ${lx} ${by}, ${b.x} ${by}`;
    }
    if (a.x > b.x) {                            // rückwärts
      const sx = a.x, ex = b.x + b.w, mx = (sx + ex) / 2;
      return `M${sx} ${ay} C${mx} ${ay}, ${mx} ${by}, ${ex} ${by}`;
    }
    const mx = (ax + bx) / 2;
    return `M${ax} ${ay} C${mx} ${ay}, ${mx} ${by}, ${bx} ${by}`;
  }

  function draw() {
    const svg = $('vbSvg');
    svg.innerHTML = '';
    if (!data) return;
    const {pos, height} = layout();
    svg.setAttribute('viewBox', `0 0 1180 ${height}`);
    const defs = el('defs');
    for (const art of Object.keys(ART_LABEL)) {
      const m = el('marker', {id: 'vb-arrow-' + art, viewBox: '0 0 10 10', refX: '9', refY: '5', markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse'});
      m.appendChild(el('path', {d: 'M0 0L10 5L0 10z', class: 'vb-head vb-' + art}));
      defs.appendChild(m);
    }
    svg.appendChild(defs);
    for (const c of COLS) {
      svg.appendChild(el('text', {x: c.x, y: 36, class: 'vb-col'}, c.titel));
      svg.appendChild(el('line', {x1: c.x, x2: c.x + c.w, y1: 46, y2: 46, class: 'vb-rule'}));
    }
    const gEdges = el('g'), gNodes = el('g');
    svg.appendChild(gEdges); svg.appendChild(gNodes);
    const touches = e => !selected || e.von === selected || e.nach === selected;
    for (const e of data.kanten) {
      const a = pos[e.von], b = pos[e.nach];
      if (!a || !b) continue;
      const onByFilter = artOn(e.art) || (e.art === 'direkt' && selected && touches(e));
      if (!onByFilter) continue;
      // Alles, was über die Anlage läuft, führt sichtbar durch Asterisk und den Anschluss
      const hub = pos['asterisk'], trunk = e.via ? pos['an:' + e.via] : null;
      let stops = [a, b];
      if (e.art === 'cloud_aus' && trunk) stops = [a, hub, trunk, b];
      else if (e.art === 'cloud_ein' && trunk) stops = [a, trunk, hub, b];
      else if (e.art === 'weg' && trunk) stops = [a, trunk, b];
      const parts = [];
      for (let i = 0; i < stops.length - 1; i++) if (stops[i] && stops[i + 1]) parts.push(pathBetween(stops[i], stops[i + 1]));
      parts.forEach((d, i) => {
        const p = el('path', {d, class: `vb-edge vb-${e.art} ${e.status === 'geplant' ? 'vb-plan' : ''} ${touches(e) ? '' : 'vb-dim'}`,
          'marker-end': i === parts.length - 1 && e.art !== 'cloud_direkt' ? `url(#vb-arrow-${e.art})` : ''});
        p.appendChild(el('title', {}, `${name(e.von)} → ${name(e.nach)}: ${ART_LABEL[e.art]} – ${e.grund}${e.status === 'geplant' ? ' (geplant)' : ''}`));
        gEdges.appendChild(p);
      });
    }
    for (const n of data.knoten) {
      const p = pos[n.id];
      if (!p) continue;
      const g = el('g', {class: `vb-node vb-n-${n.gruppe} ${selected === n.id ? 'vb-sel' : ''} ${selected && selected !== n.id && !linked(n.id) ? 'vb-dim' : ''}`,
        tabindex: '0', 'data-id': n.id});
      g.appendChild(el('rect', {x: p.x, y: p.y, width: p.w, height: p.h, rx: '9'}));
      const title = (n.nummer ? n.nummer + ' ' : '') + n.name;
      g.appendChild(el('text', {x: p.x + 12, y: p.y + (p.h > 42 ? 20 : 24), class: 'vb-name'}, title.length > 24 ? title.slice(0, 23) + '…' : title));
      if (p.h > 42) {
        const sub = n.typ === 'extern_ziel' ? (n.adresse || '') : n.typ === 'weg' ? `${n.klingelzeit} s · ${n.status}` :
          `${TYP_LABEL[n.typ] || n.typ}${n.kontext && n.kontext !== '–' ? ' · ' + n.kontext : ''}`;
        g.appendChild(el('text', {x: p.x + 12, y: p.y + 37, class: 'vb-sub'}, sub.length > 30 ? sub.slice(0, 29) + '…' : sub));
      }
      const badges = [n.video_ha ? 'HA' : '', n.video_sip ? 'SIP' : ''].filter(Boolean);
      badges.forEach((b, i) => {
        const bx = p.x + p.w - 30 - i * 32;
        g.appendChild(el('rect', {x: bx, y: p.y + 6, width: 26, height: 14, rx: '7', class: 'vb-badge'}));
        g.appendChild(el('text', {x: bx + 13, y: p.y + 16, class: 'vb-badge-t', 'text-anchor': 'middle'}, b));
      });
      g.appendChild(el('title', {}, `${title} – ${TYP_LABEL[n.typ] || n.typ}${n.kontext ? ' · Kontext ' + n.kontext : ''}`));
      g.addEventListener('click', () => select(n.id));
      g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(n.id); } });
      gNodes.appendChild(g);
    }
  }

  const name = id => { const n = data.knoten.find(k => k.id === id); return n ? ((n.nummer ? n.nummer + ' ' : '') + n.name) : id; };
  const linked = id => data.kanten.some(e => (e.von === selected && e.nach === id) || (e.nach === selected && e.von === id));

  function select(id) {
    selected = selected === id ? null : id;
    draw();
    detail();
  }

  function detail() {
    const box = $('vbDetail');
    if (!selected) { box.innerHTML = '<span class="muted">Teilnehmer anklicken für Details.</span>'; return; }
    const out = data.kanten.filter(e => e.von === selected), inn = data.kanten.filter(e => e.nach === selected);
    const row = (e, other) => `<li class="${e.status === 'geplant' ? 'vb-li-plan' : ''}"><span class="vb-key vb-${e.art}"></span><b>${esc(name(other))}</b> – ${esc(ART_LABEL[e.art])}: ${esc(e.grund)}${e.status === 'geplant' ? ' <i>(geplant)</i>' : ''}</li>`;
    box.innerHTML = `<h3>${esc(name(selected))}</h3><div class="vb-cols"><div><h4>Kann erreichen (${out.length})</h4><ul>${out.map(e => row(e, e.nach)).join('') || '<li class="muted">nichts</li>'}</ul></div>
      <div><h4>Wird erreicht von (${inn.length})</h4><ul>${inn.map(e => row(e, e.von)).join('') || '<li class="muted">niemandem</li>'}</ul></div></div>`;
  }

  function summary() {
    const s = data.zusammenfassung, box = $('vbSum');
    const parts = [`${s.lokal} lokal`, `${s.cloud} Cloud`, `${s.wege} Rufgruppe${s.wege === 1 ? "" : "n"}`];
    const direkt = s.direkt_moeglich === 0 ? '' : s.alle_lokal ? '<span class="lv-ok">Alle lokalen Teilnehmer erreichen sich direkt.</span>'
      : `<span class="lv-warn">${s.direkt} von ${s.direkt_moeglich} lokalen Direktverbindungen möglich</span> – „Direkt (lokal)“ einschalten oder Teilnehmer anklicken.`;
    const plan = data.kanten.filter(e => e.status === 'geplant').length;
    box.innerHTML = parts.join(' · ') + (direkt ? ' · ' + direkt : '') + (plan ? ` · <span class="lv-warn">${plan} geplant, noch nicht übernommen</span>` : '');
  }

  async function laden() {
    $('vbSum').textContent = 'Berechne …';
    try {
      data = await request('api/verbindungen');
      if (selected && !data.knoten.some(n => n.id === selected)) selected = null;
      summary(); draw(); detail();
    } catch (e) { $('vbSum').textContent = 'Fehler: ' + e.message; }
  }

  $('vbLaden').onclick = laden;
  document.querySelectorAll('.vb-bar [data-art]').forEach(c => c.addEventListener('change', draw));
  window.smartifyVerbindungen = laden;
})();
