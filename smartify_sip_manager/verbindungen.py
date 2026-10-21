"""Smartify SIP Manager – welche Verbindungen sind möglich? (v1.12)

Berechnet aus Anlagen-Modell, Endpoint-Kontexten und dem tatsächlichen Dialplan,
wer wen anrufen kann. Ergebnis: Knoten und Kanten für die Grafik „Verbindungen“.

Kantenarten
- direkt       interne Nummer im Kontext des Anrufers erreichbar (exakt oder per Muster)
- weg          Anrufer → Weg (Rufnummer) bzw. Weg → Ziel
- cloud_aus    lokal → externes Ziel (Direktwahl über Ausgang)
- cloud_ein    externes Ziel → lokal (Freigabe im Eingang)
- cloud_direkt externes Ziel ↔ externes Ziel über den Cloud-Server (ohne Anlage)
- kamera       Kamera → Teilnehmer, dessen Anrufe ihr Bild zeigen (Video HA)
Status: aktiv (im Dialplan) oder geplant (nur im Modell, noch nicht übernommen).
"""
import re

from anlage import ref_of

INTERNAL = ('ha_geraet', 'sip_telefon', 'tuerstation')


# ---------------------------------------------------------------------------
# Dialplan lesen: Kontexte, Erweiterungen (auch Muster) und include =>
# ---------------------------------------------------------------------------

def parse_dialplan(text):
    """{kontext: {'extens': [str], 'includes': [str]}} – Kommentare und Vorlagen-Kontexte ignoriert."""
    out, ctx = {}, None
    for raw in (text or '').splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        head = re.match(r'^\[([^\]]+)\](\(([^)]*)\))?', line)
        if head:
            ctx = head.group(1).strip()
            if '!' in (head.group(3) or ''):
                ctx = None                     # Vorlage
                continue
            out.setdefault(ctx, {'extens': [], 'includes': []})
            continue
        if ctx is None:
            continue
        m = re.match(r'^exten\s*=>?\s*([^,]+?)\s*,', line)
        if m and m.group(1) not in out[ctx]['extens']:
            out[ctx]['extens'].append(m.group(1))
            continue
        inc = re.match(r'^include\s*=>?\s*([A-Za-z0-9_.+-]+)', line)
        if inc and inc.group(1) not in out[ctx]['includes']:
            out[ctx]['includes'].append(inc.group(1))
    return out


def pattern_matches(pattern, number):
    """Asterisk-Muster: _X Z N [1-5] . ! sowie exakte Nummern."""
    if not pattern.startswith('_'):
        return pattern == number
    regex = ''
    i, p = 0, pattern[1:]
    while i < len(p):
        c = p[i].upper()
        if c == 'X':
            regex += '[0-9]'
        elif c == 'Z':
            regex += '[1-9]'
        elif c == 'N':
            regex += '[2-9]'
        elif c == '.':
            regex += '.+'
        elif c == '!':
            regex += '.*'
        elif c == '[':
            j = p.find(']', i)
            if j < 0:
                return False
            regex += '[' + re.sub(r'[^0-9\-]', '', p[i + 1:j]) + ']'
            i = j
        elif c.isdigit() or c in '*#+':
            regex += re.escape(c)
        else:
            return False
        i += 1
    return re.fullmatch(regex, number) is not None


def reachable(dialplan, ctx, number, _seen=None):
    """(True, 'exakt'|'Muster _X.'|'über include x') or (False, '')."""
    seen = _seen or set()
    if not ctx or ctx in seen or ctx not in dialplan:
        return False, ''
    seen.add(ctx)
    entry = dialplan[ctx]
    if number in entry['extens']:
        return True, f'Eintrag {number}@{ctx}'
    for ext in entry['extens']:
        if ext.startswith('_') and pattern_matches(ext, number):
            return True, f'Muster {ext}@{ctx}'
    for inc in entry['includes']:
        ok, why = reachable(dialplan, inc, number, seen)
        if ok:
            return True, why + f' (über include in {ctx})'
    return False, ''


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def graph(model, endpoints, dialplan_text):
    """Knoten und Kanten für die Grafik."""
    dp = parse_dialplan(dialplan_text)
    t_all = model.get('teilnehmer', [])
    nodes, edges = [], []

    def ctx_of(t):
        # Asterisk nimmt „default“, wenn ein Endpoint keinen context hat
        if t['typ'] in INTERNAL:
            return (endpoints.get(t['nummer']) or {}).get('context') or 'default'
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            return (endpoints.get(t['eingang']) or {}).get('context') or 'default'
        return ''

    def node_id(t):
        return 'tn:' + ref_of(t) if t['typ'] != 'kamera' else 'cam:' + t['stream']

    for t in t_all:
        if t['typ'] in INTERNAL:
            ep = endpoints.get(t['nummer'])
            nodes.append({'id': node_id(t), 'gruppe': 'lokal', 'typ': t['typ'], 'nummer': t['nummer'], 'name': t['name'],
                          'kontext': ctx_of(t) or '–', 'endpoint': bool(ep),
                          'anruf_ziele': t.get('anruf_ziele'), 'angerufen_von': t.get('angerufen_von'),
                          'video_ha': bool(t['faehigkeiten'].get('kamerabild')), 'video_sip': bool(t['faehigkeiten'].get('video_im_anruf'))})
        elif t['typ'] == 'extern_ziel':
            nodes.append({'id': node_id(t), 'gruppe': 'cloud', 'typ': t['typ'], 'nummer': t['nummer'], 'name': t['name'],
                          'adresse': t.get('sip_adresse', ''), 'ausgang': t.get('endpoint', ''), 'eingang': t.get('eingang', ''),
                          'kontext': ctx_of(t) or '–', 'video_sip': bool(t['faehigkeiten'].get('video_im_anruf'))})
        elif t['typ'] == 'kamera':
            nodes.append({'id': node_id(t), 'gruppe': 'kamera', 'typ': 'kamera', 'nummer': '', 'name': t['name'], 'stream': t['stream']})

    trunks = sorted({n for t in t_all if t['typ'] == 'extern_ziel' for n in (t.get('endpoint'), t.get('eingang')) if n})
    for n in trunks:
        nodes.append({'id': 'an:' + n, 'gruppe': 'anschluss', 'typ': 'anschluss', 'nummer': '', 'name': n,
                      'kontext': (endpoints.get(n) or {}).get('context') or '–'})
    nodes.append({'id': 'asterisk', 'gruppe': 'zentrale', 'typ': 'asterisk', 'nummer': '', 'name': 'Asterisk'})

    def edge(src, dst, art, status, grund, via=''):
        edges.append({'von': src, 'nach': dst, 'art': art, 'status': status, 'grund': grund, 'via': via})

    internal = [t for t in t_all if t['typ'] in INTERNAL and t['nummer']]
    wege_by_nr = {w['nummer']: w for w in model.get('wege', []) if w.get('nummer')}

    def darf_waehlen(a, nr, b=None):
        """Erlaubt die Erreichbarkeit (Teilnehmer-Einstellung) a → Nummer nr? b = angerufener interner Teilnehmer."""
        if a['typ'] in INTERNAL and a.get('anruf_ziele') is not None and nr not in a['anruf_ziele']:
            return False
        return not (b and b.get('angerufen_von') is not None and ref_of(a) not in b['angerufen_von'])

    def weg_laesst_zu(w, t):
        """Berechtigungen für Rufgruppen. Ein leerer Anruferkreis gibt Cloud-Konten keine pauschale Freigabe."""
        if not w:
            return False
        if t['typ'] == 'extern_ziel' and w['nummer'] in (t.get('darf_anrufen') or []):
            return True
        if not w['von'] and t['typ'] != 'extern_ziel':
            return True
        r = ref_of(t)
        refs = {r} | {ref_of(x) for x in t_all if x.get('gleiches_geraet') == r}
        if refs & set(w['von']):
            return True
        return bool(w.get('mitglieder_rufen') and
                    (r in w['ziele'] or (t.get('gleiches_geraet') or '') in w['ziele']))
    externals = [t for t in t_all if t['typ'] == 'extern_ziel']
    weg_nr = {w['nummer'] for w in model.get('wege', []) if w.get('nummer')}

    # direkt: intern → intern
    for a in internal:
        for b in internal:
            if a is b or not darf_waehlen(a, b['nummer'], b):
                continue
            ok, why = reachable(dp, ctx_of(a), b['nummer'])
            if ok:
                edge(node_id(a), node_id(b), 'direkt', 'aktiv', why)

    # Wege
    by_ref = {ref_of(t): t for t in t_all}
    for w in model.get('wege', []):
        if not w.get('nummer'):
            continue
        wid = 'weg:' + w['nummer']
        callers = [by_ref[r] for r in w['von'] if r in by_ref]
        if w.get('mitglieder_rufen'):
            callers += [by_ref[r] for r in w['ziele'] if r in by_ref and by_ref[r] not in callers]
        callers = [c for c in callers if darf_waehlen(c, w['nummer'])]
        live = any(reachable(dp, ctx_of(c), w['nummer'])[0] for c in callers) if callers else bool(reachable(dp, 'default', w['nummer'])[0])
        if not w['von']:
            # keine Anrufer festgelegt: alle lokalen, deren Kontext die Nummer erreicht (bzw. erreichen wird)
            callers = [t for t in internal if (reachable(dp, ctx_of(t), w['nummer'])[0] or not live) and darf_waehlen(t, w['nummer'])]
        nodes.append({'id': wid, 'gruppe': 'weg', 'typ': 'weg', 'nummer': w['nummer'], 'name': w['name'],
                      'klingelzeit': w['klingelzeit'], 'status': 'aktiv' if live else 'geplant'})
        for c in callers:
            # Cloud-Anrufe auf Gruppen werden separat als cloud_ein gezeichnet.
            if c['typ'] == 'extern_ziel':
                continue
            ok, why = reachable(dp, ctx_of(c), w['nummer'])
            edge(node_id(c), wid, 'weg', 'aktiv' if ok else 'geplant',
                 why or f'{w["nummer"]} noch nicht im Kontext „{ctx_of(c) or "?"}“ – „Erzeugen & Übernehmen“')
        for r in w['ziele']:
            z = by_ref.get(r)
            if z:
                via = z.get('endpoint', '') if z['typ'] == 'extern_ziel' else ''
                edge(wid, node_id(z), 'weg', 'aktiv' if live else 'geplant',
                     f'klingelt {w["klingelzeit"]} s' + (f' über {via}' if via else ''), via)

    # Hinweis statt irreführender Freigabe: ein fremder Eintrag/Muster im Eingangs-Kontext
    # kann eine NICHT freigegebene Nummer dennoch zur Auswahl stellen. Ob eine Bedingung
    # im Dialplan blockiert, kann die statische Kontextsuche nicht entscheiden.
    pruefhinweise = []

    def hinweis(z, nr, why, zieltyp):
        pruefhinweise.append({
            'von': node_id(z), 'nummer': nr, 'zieltyp': zieltyp,
            'grund': (f'{nr} ist über {why} im Asterisk-Eingangskontext von {z["name"]} sichtbar, '
                      'steht aber nicht in dessen Freigaben. Bitte tatsächliche '
                      'Anruferprüfung bzw. Kontext-Isolierung prüfen.')
        })

    # Cloud: lokal → externes Ziel (Direktwahl), externes Ziel → lokal (Freigaben), extern ↔ extern
    for z in externals:
        if z['nummer']:
            for a in internal:
                if not darf_waehlen(a, z['nummer']):
                    continue
                if z.get('angerufen_von') is not None and ref_of(a) not in z['angerufen_von']:
                    continue
                ok, why = reachable(dp, ctx_of(a), z['nummer'])
                if ok or a['typ'] in ('ha_geraet', 'sip_telefon'):
                    edge(node_id(a), node_id(z), 'cloud_aus', 'aktiv' if ok else 'geplant',
                         (why if ok else f'Direktwahl {z["nummer"]} noch nicht im Dialplan') + f' · über {z["endpoint"]}', z['endpoint'])
        ctx = ctx_of(z)
        if z.get('eingang'):
            for b in internal:
                if b['nummer'] in weg_nr:
                    continue
                ok, why = reachable(dp, ctx, b['nummer'])
                freigegeben = b['nummer'] in (z.get('darf_anrufen') or [])
                if freigegeben:
                    edge(node_id(z), node_id(b), 'cloud_ein', 'aktiv' if ok else 'geplant',
                         (why if ok else 'freigegeben, noch nicht übernommen') + f' · über {z["eingang"]}', z['eingang'])
                elif ok:
                    hinweis(z, b['nummer'], why, 'direkt')
            for nr in sorted(weg_nr):
                ok, why = reachable(dp, ctx, nr)
                # Auch die ausdrückliche Berechtigung als Gruppenanrufer/Mitglied zählt.
                # Ein gemeinsamer Dialplan-Kontext allein ist KEINE Teilnehmerfreigabe.
                freigegeben = weg_laesst_zu(wege_by_nr.get(nr), z)
                if freigegeben:
                    edge(node_id(z), 'weg:' + nr, 'cloud_ein', 'aktiv' if ok else 'geplant',
                         (why if ok else 'Freigabe vorhanden, noch nicht übernommen') + f' · über {z["eingang"]}', z['eingang'])
                elif ok:
                    hinweis(z, nr, why, 'rufgruppe')
    for i, a in enumerate(externals):
        for b in externals[i + 1:]:
            da, db = a.get('sip_adresse', '').split('@')[-1], b.get('sip_adresse', '').split('@')[-1]
            if da and da == db:
                edge(node_id(a), node_id(b), 'cloud_direkt', 'aktiv', f'direkt über {da} – ohne Anlage')

    # Kameras
    for cam in [t for t in t_all if t['typ'] == 'kamera']:
        for t in t_all:
            if t['typ'] != 'kamera' and t['stream'] == cam['stream'] and t['faehigkeiten'].get('kamerabild'):
                edge(node_id(cam), node_id(t), 'kamera', 'aktiv', f'Bild „{cam["stream"]}“ im HA-Popup, wenn {t["name"]} anruft')

    # Zusammenfassung „alle lokal erreichen sich“
    pairs = len(internal) * (len(internal) - 1)
    direct = sum(1 for e in edges if e['art'] == 'direkt')
    return {'knoten': nodes, 'kanten': edges, 'pruefhinweise': pruefhinweise,
            'zusammenfassung': {'lokal': len(internal), 'cloud': len(externals), 'wege': len(weg_nr),
                                'direkt': direct, 'direkt_moeglich': pairs,
                                'alle_lokal': pairs > 0 and direct == pairs}}
