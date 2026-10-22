"""Smartify SIP Manager – Konfiguration aus dem Anlagen-Modell erzeugen (v1.5).

Reine Funktionen: bekommen den aktuellen Stand (Text/Dicts) und liefern den neuen
Stand plus eine Liste verständlicher Aktionen. Geschrieben wird in app.py.

Grundsätze
- Asterisk: nur ein klar markierter, verwalteter Block in custom/pjsip_custom.conf.
  Einfache bestehende Definitionen derselben Nummer werden in den Block übernommen
  (Passwort und Einstellungen bleiben), komplexe bleiben unangetastet.
  Vom Asterisk-Add-on erzeugte Endpoints (default/) werden nie doppelt angelegt.
- SIP Core: sip_video, Popup und smartify.camera_by_caller; Benutzer werden nicht verändert.
- go2rtc: Streams aus dem Modell, api.origin und WebRTC-Candidates; fremde Streams bleiben.
"""
import copy
import re
import secrets as _secrets

import rtsp as rtsp_mod
from anlage import POPUP_COMPONENT, VIDEO_CODECS, eingaenge_effektiv, endpoints_from_conf, parse_conf_sections, realm_fuer

BEGIN = '; >>> SMARTIFY-VERWALTET – Inhalt wird vom Smartify SIP Manager erzeugt, Änderungen hier gehen verloren'
END = '; <<< SMARTIFY-VERWALTET'
SIMPLE_TYPES = {'aor', 'auth', 'endpoint'}
KEEP_AOR = ('max_contacts', 'remove_existing', 'remove_unavailable', 'qualify_frequency',
            'minimum_expiration', 'default_expiration', 'maximum_expiration')
KEEP_ENDPOINT = ('context', 'transport', 'dtmf_mode', 'direct_media', 'force_rport', 'rewrite_contact',
                 'rtp_symmetric', 'ice_support', 'media_encryption', 'webrtc', 'callerid', 'mailboxes',
                 'trust_id_inbound', 'send_pai', 'language', 'device_state_busy_at')


def _row(rows, level, ziel, text, bezug='', **extra):
    rows.append({'level': level, 'ziel': ziel, 'text': text, 'bezug': bezug, **extra})


def new_password():
    return _secrets.token_urlsafe(15)


# ---------------------------------------------------------------------------
# Textabschnitte (unverändert erhalten, was nicht angefasst wird)
# ---------------------------------------------------------------------------

def split_managed(text):
    """Return (outside_text, inside_text). Missing END closes at file end."""
    if BEGIN not in text:
        return text, ''
    before, _, rest = text.partition(BEGIN)
    inside, sep, after = rest.partition(END)
    return before.rstrip('\n') + ('\n' + after.lstrip('\n') if sep and after.strip() else '\n'), inside


def split_sections(text):
    """Preamble + list of {name, header, opts, raw, attrs[(k,v)]}; raw includes the header line."""
    heads = list(re.finditer(r'^[ \t]*\[([^\]\r\n]+)\]([^\r\n]*)$', text, re.M))
    pre = text[:heads[0].start()] if heads else text
    out = []
    lead = ''
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        chunk = text[h.start():end]
        trail = ''
        if i + 1 < len(heads):
            # Kommentare/Leerzeilen am Ende gehören zum nächsten Abschnitt (Überschriften-Banner)
            lines = chunk.splitlines(keepends=True)
            last = max((j for j, l in enumerate(lines) if l.strip() and not l.lstrip().startswith((';', '#'))), default=0)
            trail = ''.join(lines[last + 1:])
            chunk = ''.join(lines[:last + 1])
            blank = re.match(r'(\s*\n)', trail)
            if blank:
                chunk += blank.group(1)
                trail = trail[len(blank.group(1)):]
        raw = lead + chunk
        lead = trail
        opts = [o.strip() for o in re.sub(r'^\s*\(|\)\s*$', '', h.group(2).split(';', 1)[0].strip()).split(',') if o.strip()]
        attrs = []
        for line in raw.splitlines()[1:]:
            clean = line.split(';', 1)[0].strip()
            if '=' in clean:
                k, v = clean.split('=', 1)
                attrs.append((k.strip().lower(), v.strip()))
        out.append({'name': h.group(1).strip(), 'header': h.group(0), 'opts': opts, 'raw': raw, 'attrs': attrs})
    return pre, out


def _type(sec):
    types = [v.lower() for k, v in sec['attrs'] if k == 'type']
    return types[-1] if types else ''


def _get(sec, key, default=''):
    vals = [v for k, v in sec['attrs'] if k == key]
    return vals[-1] if vals else default


def _codec_list(sec):
    lines = [(k, v) for k, v in sec['attrs'] if k in ('allow', 'disallow')]
    codecs = []
    for k, v in lines:
        for part in [p.strip().lower() for p in v.split(',') if p.strip()]:
            if k == 'disallow' or part.startswith('!'):
                name = part.lstrip('!')
                codecs = [] if name == 'all' else [c for c in codecs if c != name]
            elif part not in codecs:
                codecs.append(part)
    return codecs


def _transports(files):
    found = {}
    for sec in parse_conf_sections(files):
        if sec['is_template']:
            continue
        attrs = dict(sec['lines'])
        if attrs.get('type', '').lower() == 'transport':
            found[sec['name']] = attrs.get('protocol', '').lower()
    return found


# ---------------------------------------------------------------------------
# Asterisk
# ---------------------------------------------------------------------------

def _codecs_for(t, base):
    audio = [c for c in base if c not in VIDEO_CODECS] or (['opus', 'ulaw', 'alaw'] if t['typ'] == 'ha_geraet' else ['alaw', 'ulaw'])
    if not t['faehigkeiten'].get('video_im_anruf'):
        return audio
    video = ['vp8', 'h264'] if t['typ'] == 'ha_geraet' else ['h264', 'vp8']
    return audio + [v for v in video if v not in audio]


AUDIO_EXTERN = ('opus', 'ulaw', 'alaw')


def gen_pjsip(model, custom_text, files, secrets, sip_users=None):
    """custom_text: current custom/pjsip_custom.conf; files: [(label, content)] of all conf files.
    secrets: {'sip': {nummer: password}} – updated in place with new passwords.
    Returns {'content', 'aktionen', 'neu': [nummern mit neuem Passwort]}."""
    rows, created = [], []
    sip_users = {str(u.get('extension')): u for u in (sip_users or []) if isinstance(u, dict)}
    secrets.setdefault('sip', {})
    outside, inside = split_managed(custom_text or '')
    pre, sections = split_sections(outside)
    _, old_block = split_sections(inside)
    default_eps = endpoints_from_conf([f for f in files if f[0].startswith('default/')])
    transports = _transports(files)
    udp = next((n for n, p in transports.items() if p == 'udp'), '')
    wss = next((n for n, p in transports.items() if p == 'wss'), '')
    old_pw = {s['name']: _get(s, 'password') for s in old_block if _type(s) == 'auth'}
    old_attrs = {(s['name'], _type(s)): s for s in old_block}
    remove = set()
    block = []

    for t in model.get('teilnehmer', []):
        n = t['nummer']
        if t['typ'] not in ('ha_geraet', 'sip_telefon', 'tuerstation') or not n:
            continue
        label = f'{n} {t["name"]}'
        if n in default_eps:
            ep = default_eps[n]
            needs = t['faehigkeiten'].get('video_im_anruf') and not any(c in VIDEO_CODECS for c in ep['codecs'])
            _row(rows, 'warn' if needs else 'info', 'Asterisk',
                 f'{label}: wird vom Asterisk-Add-on erzeugt – nicht doppelt angelegt.'
                 + (' Für Video: im Asterisk-Add-on Video aktivieren (falls angeboten) oder die automatische Erzeugung abschalten – '
                    'dann erzeugt der Manager diesen Endpoint mit Video-Codecs.' if needs else ''), n)
            continue
        own = [s for s in sections if s['name'] == n]
        complex_ = [s for s in own if s['opts'] or _type(s) not in SIMPLE_TYPES]
        if complex_:
            _row(rows, 'warn', 'Asterisk', f'{label}: eigene Definition mit Vorlagen oder Sondertyp – bleibt unverändert, '
                 'wird nicht verwaltet.', n)
            continue
        by_type = {_type(s): s for s in own}
        prev = {k: by_type.get(k) or old_attrs.get((n, k)) for k in SIMPLE_TYPES}
        password = ''
        if prev['auth']:
            password = _get(prev['auth'], 'password')
        if not password and t['typ'] == 'ha_geraet':
            password = str(sip_users.get(n, {}).get('password') or '')
        if not password:
            password = old_pw.get(n) or secrets['sip'].get(n) or ''
        if not password:
            password = new_password()
            created.append(n)
            _row(rows, 'info', 'Asterisk', f'{label}: neues SIP-Passwort erzeugt (unter Teilnehmer → Zugangsdaten abrufbar).', n)
        secrets['sip'][n] = password
        if by_type:
            remove.update(id(s) for s in own)
            _row(rows, 'ok', 'Asterisk', f'{label}: bestehende Definition in die Verwaltung übernommen (Passwort und Einstellungen bleiben).', n)
        elif not prev['endpoint']:
            _row(rows, 'ok', 'Asterisk', f'{label}: Nebenstelle wird neu angelegt.', n)
        if t['typ'] == 'ha_geraet' and not prev['endpoint']:
            _row(rows, 'warn', 'Asterisk', f'{label}: HA-Gerät neu als WebRTC-Endpoint angelegt'
                 + (f' (Transport {wss}).' if wss else ' – kein WSS-Transport gefunden, Transport bitte prüfen.'), n)
        base = _codec_list(prev['endpoint']) if prev['endpoint'] else []
        codecs = _codecs_for(t, base)
        lines = [f'; {t["name"]} ({t["typ"]})', f'[{n}]', 'type=aor']
        aor_keep = dict(prev['aor']['attrs']) if prev['aor'] else {}
        aor_keep.setdefault('max_contacts', '5' if t['typ'] == 'ha_geraet' else '1')
        aor_keep.setdefault('remove_existing', 'yes')
        lines += [f'{k}={aor_keep[k]}' for k in KEEP_AOR if aor_keep.get(k)]
        lines += ['', f'[{n}]', 'type=auth', 'auth_type=userpass', f'username={_get(prev["auth"], "username") if prev["auth"] else n}',
                  f'password={password}']
        # Realm: Linphone u. a. legen die Zugangsdaten für den Bereich = Domain ab (z. B. die Tailscale-IP von HA).
        # Ohne passenden realm scheitert die Anmeldung mit „Failed to authenticate“, obwohl das Passwort stimmt.
        realm = realm_fuer(t, model.get('anlage') or {}) or (_get(prev['auth'], 'realm') if prev['auth'] else '')
        if realm:
            lines.append(f'realm={realm}')
        lines += ['', f'[{n}]', 'type=endpoint', f'aors={n}', f'auth={n}']
        ep_keep = dict(prev['endpoint']['attrs']) if prev['endpoint'] else {}
        defaults = {'context': 'default', 'dtmf_mode': 'rfc4733', 'direct_media': 'no', 'force_rport': 'yes',
                    'rewrite_contact': 'yes', 'rtp_symmetric': 'yes'}
        if t['typ'] == 'ha_geraet':
            defaults.update(webrtc='yes')
            if wss:
                defaults['transport'] = wss
        elif udp:
            defaults['transport'] = udp
        for k, v in defaults.items():
            ep_keep.setdefault(k, v)
        ep_keep['callerid'] = f'"{t["name"]}" <{n}>'
        lines += [f'{k}={ep_keep[k]}' for k in KEEP_ENDPOINT if ep_keep.get(k)]
        lines += ['disallow=all', 'allow=' + ','.join(codecs)]
        if t['faehigkeiten'].get('video_im_anruf'):
            lines.append('max_video_streams=1')
            _row(rows, 'ok', 'Asterisk', f'{label}: Video-Codecs {", ".join(c for c in codecs if c in VIDEO_CODECS)}.', n)
        block.append('\n'.join(lines))

    # Nebenstellen, die bisher verwaltet wurden, aber nicht mehr im Modell stehen, fallen weg – deutlich melden
    still = {t['nummer'] for t in model.get('teilnehmer', []) if t['nummer']} | {e['name'] for e in eingaenge_effektiv(model)}
    for gone in sorted({s['name'] for s in old_block if _type(s) == 'endpoint'} - still):
        _row(rows, 'warn', 'Asterisk', f'{gone}: steht nicht mehr im Modell – die Nebenstelle wird aus Asterisk ENTFERNT '
             '(Geräte mit dieser Nummer können sich danach nicht mehr anmelden).', gone)
        secrets.get('sip', {}).pop(gone, None)

    # externe Anschlüsse (Ausgang/Eingang): nur die allow-Zeile ergänzen, Abschnitt bleibt an seinem Platz.
    # Audio: Linphone bietet je nach Einstellung nur Opus an – ohne gemeinsamen Codec scheitert der Anruf
    # („Couldn't negotiate stream … audio“). Daher opus,ulaw,alaw sicherstellen; Video nur bei Bedarf.
    patched = {}
    need = {}
    for t in model.get('teilnehmer', []):
        if t['typ'] != 'extern_ziel':
            continue
        for n in (t['endpoint'], t.get('eingang')):
            if n:
                need.setdefault(n, set()).update(AUDIO_EXTERN)
                if t['faehigkeiten'].get('video_im_anruf'):
                    need[n].update(('vp8', 'h264'))
    eingang_namen = {t.get('eingang') for t in model.get('teilnehmer', []) if t['typ'] == 'extern_ziel' and t.get('eingang')}
    for trunk, want in sorted(need.items()):
        for s_ in sections:
            if id(s_) in patched or s_['name'] != trunk or _type(s_) != 'endpoint' or s_['opts']:
                continue
            have = _codec_list(s_)
            fehlt = [c for c in list(AUDIO_EXTERN) + ['vp8', 'h264'] if c in want and c not in have]
            raw = s_['raw']
            if fehlt:
                allow = list(re.finditer(r'^([ \t]*allow[ \t]*=[ \t]*)([^;\r\n]*)', raw, re.M))
                if allow:
                    m = allow[-1]
                    raw = raw[:m.start(2)] + m.group(2).rstrip() + ',' + ','.join(fehlt) + raw[m.end(2):]
                else:
                    raw = raw.rstrip('\n') + '\nallow=' + ','.join(fehlt) + '\n'
                _row(rows, 'ok', 'Asterisk', f'{trunk}: Codecs {",".join(fehlt)} ergänzt (Anschluss, bleibt außerhalb der Verwaltung).', trunk)
            # Linphone bietet mit AVPF „RTP/AVPF“ an; ohne use_avpf lehnt Asterisk das ab („Couldn't negotiate stream … audio“).
            # use_received_transport=yes übernimmt das angebotene Profil (AVP oder AVPF) – passt für alle Linphone-Einstellungen.
            # 1.17.2 schrieb versehentlich „use_received_transport“ (ungültig → Asterisk lädt den Endpoint nicht) – reparieren
            if re.search(r'(?im)^[ \t]*use_received_transport[ \t]*=', raw):
                raw = re.sub(r'(?im)^([ \t]*)use_received_transport([ \t]*=)', r'\1media_use_received_transport\2', raw)
                _row(rows, 'warn', 'Asterisk', f'{trunk}: ungültige Zeile „use_received_transport“ korrigiert zu „media_use_received_transport“ '
                     '(ohne Korrektur lädt Asterisk den Anschluss nicht).', trunk)
            if not re.search(r'(?im)^[ \t]*(media_use_received_transport|use_avpf)[ \t]*=', raw):
                raw = raw.rstrip('\n') + '\nmedia_use_received_transport=yes\n'
                _row(rows, 'ok', 'Asterisk', f'{trunk}: media_use_received_transport=yes – Linphone mit AVPF wird angenommen (sonst „Couldn\'t negotiate stream … audio“).', trunk)
            # Eingang: Linphone bietet bei eingeschalteter Verschlüsselung RTP/SAVPF mit a=crypto an. Mit
            # media_use_received_transport antwortet Asterisk dann ebenfalls „SAVPF“ – ohne SDES aber ohne Schlüssel,
            # und Linphone legt sofort nach dem Abnehmen auf (BYE). SDES optimistisch: verschlüsselt, wenn angeboten.
            if trunk in eingang_namen and not re.search(r'(?im)^[ \t]*media_encryption[ \t]*=', raw):
                raw = raw.rstrip('\n') + '\nmedia_encryption=sdes\nmedia_encryption_optimistic=yes\n'
                _row(rows, 'ok', 'Asterisk', f'{trunk}: media_encryption=sdes (optimistisch) – Linphone mit SRTP wird angenommen '
                     '(sonst Auflegen direkt nach dem Abnehmen).', trunk)
            if raw != s_['raw']:
                patched[id(s_)] = raw

    # Eingänge mit Quell-IPs (Anrufe ohne Anmeldung, z. B. über Tailscale): identify-match pflegen bzw. anlegen
    all_eps = endpoints_from_conf(files)
    video_in = {t.get('eingang') for t in model.get('teilnehmer', []) if t['typ'] == 'extern_ziel' and t['faehigkeiten'].get('video_im_anruf')}
    for e in eingaenge_effektiv(model):
        name, ips = e['name'], e['quell_ips']
        idents = [x for x in sections if _type(x) == 'identify' and _get(x, 'endpoint') == name]
        if not ips:
            simple = [x for x in idents if not x['opts']]
            if len(simple) == 1 and len(idents) == 1:
                remove.add(id(simple[0]))       # keine IP mehr im Modell → Zuordnung entfernen (Backup beim Übernehmen)
                _row(rows, 'warn', 'Asterisk', f'Eingang {name}: keine Quell-IP mehr – Zuordnung (identify) wird entfernt, '
                     'der Eingang nimmt keine Anrufe ohne Anmeldung mehr an.', name)
            else:
                _row(rows, 'warn', 'Asterisk', f'Eingang {name}: keine Quell-IP eingetragen – identify wird nicht angelegt.', name)
            continue
        own_ep = [x for x in sections if x['name'] == name and _type(x) == 'endpoint']
        if len(idents) > 1 or any(x['opts'] for x in idents):
            _row(rows, 'warn', 'Asterisk', f'Eingang {name}: mehrere oder besondere identify-Abschnitte – Quell-IPs nicht geändert.', name)
        elif idents:
            ident = idents[0]
            current = [m.strip() for v in [_get(ident, 'match')] for m in (v or '').split(',') if m.strip()]
            if current != ips:
                raw = patched.get(id(ident), ident['raw'])
                raw = re.sub(r'(?im)^[ \t]*match[ \t]*=[^\r\n]*\r?\n?', '', raw).rstrip('\n') + '\nmatch=' + ','.join(ips) + '\n'
                patched[id(ident)] = raw
                _row(rows, 'ok', 'Asterisk', f'Eingang {name}: Quell-IPs {", ".join(current) or "–"} → {", ".join(ips)}.', name)
        elif (all_eps.get(name) or {}).get('identify') and not any(_type(x) == 'identify' and _get(x, 'endpoint') == name for x in old_block):
            _row(rows, 'warn', 'Asterisk', f'Eingang {name}: identify steht in einer anderen Datei – Quell-IPs dort ändern.', name)
        else:
            block.append('\n'.join([f'; Eingang {name}: Anrufe nur von diesen Geräten (ohne Anmeldung)', f'[{name}-identify]',
                                     'type=identify', f'endpoint={name}', 'match=' + ','.join(ips)]))
            _row(rows, 'ok', 'Asterisk', f'Eingang {name}: nimmt Anrufe von {", ".join(ips)} an (identify).', name)
        if not own_ep and name not in all_eps:
            codecs = list(AUDIO_EXTERN) + (['vp8', 'h264'] if name in video_in else [])
            lines = [f'; Eingang {name} (Anrufe von außen, eigener Kontext)', f'[{name}]', 'type=endpoint', f'context={name}']
            lines += ([f'transport={udp}'] if udp else []) + ['direct_media=no', 'force_rport=yes', 'rewrite_contact=yes', 'rtp_symmetric=yes',
                                                             'media_use_received_transport=yes', 'media_encryption=sdes',
                                                             'media_encryption_optimistic=yes',
                                                             'disallow=all', 'allow=' + ','.join(codecs)]
            if name in video_in:
                lines.append('max_video_streams=1')
            block.insert(0, '\n'.join(lines))
            _row(rows, 'ok', 'Asterisk', f'Eingang {name}: Endpoint mit eigenem Kontext „{name}“ angelegt.', name)

    body = pre + ''.join(patched.get(id(s), s['raw']) for s in sections if id(s) not in remove)
    body = re.sub(r'\n{3,}', '\n\n', body).rstrip('\n')
    content = (body + '\n\n' if body.strip() else '')
    if block:
        content += BEGIN + '\n\n' + '\n\n'.join(block) + '\n\n' + END + '\n'
    return {'content': content, 'aktionen': rows, 'neu': created}


# ---------------------------------------------------------------------------
# SIP Core
# ---------------------------------------------------------------------------

def gen_sip_core(model, cfg):
    cfg = copy.deepcopy(cfg or {})
    rows = []
    t_all = model.get('teilnehmer', [])
    user_list = [u for u in cfg.get('users') or [] if isinstance(u, dict)]
    users = {str(u.get('extension')): u for u in user_list}
    if isinstance(cfg.get('backup_user'), dict) and cfg['backup_user'].get('extension'):
        users.setdefault(str(cfg['backup_user']['extension']), cfg['backup_user'])
    for t in t_all:
        if t['typ'] != 'ha_geraet':
            continue
        if t['nummer'] not in users:
            _row(rows, 'warn', 'SIP Core', f'{t["nummer"]} {t["name"]}: kein SIP-Core-Benutzer – Benutzer werden nicht automatisch angelegt '
                 '(Reiter „Aktive Konfiguration & Teilnehmer“).', t['nummer'])
            continue
        want = t.get('ha_benutzer') or ''
        user = users[t['nummer']]
        is_backup = isinstance(cfg.get('backup_user'), dict) and str(cfg['backup_user'].get('extension')) == t['nummer'] \
            and not any(str(x.get('extension')) == t['nummer'] for x in user_list if x is not cfg.get('backup_user'))
        if is_backup or want == '*':
            if want == '*' and not is_backup:
                _row(rows, 'warn', 'SIP Core', f'{t["nummer"]}: „alle übrigen HA-Benutzer“ geht nur für den backup_user – nicht geändert.', t['nummer'])
            elif want and want != '*':
                _row(rows, 'warn', 'SIP Core', f'{t["nummer"]} ist der backup_user (gilt für alle übrigen HA-Benutzer) – '
                     f'HA-Benutzer „{want}“ nicht gesetzt.', t['nummer'])
            continue
        if want and str(user.get('ha_username') or '') != want:
            others = [str(u.get('extension')) for u in user_list
                      if str(u.get('ha_username') or '') == want and str(u.get('extension')) != t['nummer']]
            if others and not any(x['typ'] == 'ha_geraet' and x['nummer'] in others and x.get('ha_benutzer') != want for x in t_all):
                _row(rows, 'warn', 'SIP Core', f'{t["nummer"]}: HA-Benutzer „{want}“ ist schon bei {", ".join(others)} eingetragen – '
                     'nicht geändert. Dort zuerst einen anderen Benutzer wählen.', t['nummer'])
                continue
            _row(rows, 'ok', 'SIP Core', f'{t["nummer"]} {t["name"]}: HA-Benutzer „{user.get("ha_username") or "–"}“ → „{want}“.', t['nummer'])
            user['ha_username'] = want
    if any(t['typ'] == 'ha_geraet' and t['faehigkeiten'].get('video_im_anruf') for t in t_all) and not cfg.get('sip_video'):
        cfg['sip_video'] = True
        _row(rows, 'ok', 'SIP Core', 'sip_video: true – HA-Geräte bieten Video im Anruf an.')
    cams = [t for t in t_all if t['nummer'] and t['stream'] and t['faehigkeiten'].get('kamerabild')]
    if not cams:
        return {'config': cfg, 'aktionen': rows}
    ios = any(t['faehigkeiten'].get('ios') for t in t_all)
    mode = 'webrtc' if ios else 'mse'
    if cfg.get('popup_override_component') != POPUP_COMPONENT:
        cfg['popup_override_component'] = POPUP_COMPONENT
        _row(rows, 'ok', 'SIP Core', f'popup_override_component: {POPUP_COMPONENT}')
    popup = cfg.get('popup_config') if isinstance(cfg.get('popup_config'), dict) else {}
    cfg['popup_config'] = popup
    if 'auto_open' not in popup:
        popup['auto_open'] = True
        _row(rows, 'ok', 'SIP Core', 'Popup öffnet sich beim Klingeln automatisch (auto_open).')
    smartify = popup.get('smartify') if isinstance(popup.get('smartify'), dict) else {}
    popup['smartify'] = smartify
    old_mode = smartify.get('mode')
    smartify['mode'] = mode
    smartify.setdefault('camera_mode', 'always')
    if old_mode != mode:
        _row(rows, 'ok', 'SIP Core', f'Wiedergabe {mode}' + (' (iOS-Geräte in der Anlage).' if ios else '.'))
    mapping = {}
    for t in cams:
        entry = {'label': t['name'], 'stream': t['stream'], 'mode': mode, 'camera_mode': 'always'}
        if t['klingel_entity']:
            entry['bell_entity'] = t['klingel_entity']
        mapping[t['nummer']] = entry
    if smartify.get('camera_by_caller') != mapping:
        _row(rows, 'ok', 'SIP Core', 'Kamera je Anrufer: ' + ', '.join(f'{n} → {e["stream"]}' for n, e in mapping.items()))
    smartify['camera_by_caller'] = mapping
    ext = popup.get('extensions') if isinstance(popup.get('extensions'), dict) else None
    if ext:
        cleaned = []
        for n in mapping:
            entry = ext.get(n)
            if isinstance(entry, dict):
                for key in ('stream', 'stream_mode', 'mode', 'camera_mode', 'stream_media', 'media'):
                    if key in entry:
                        entry.pop(key)
                        cleaned.append(n)
        if cleaned:
            _row(rows, 'info', 'SIP Core', 'Doppelte Kamera-Einträge unter extensions entfernt: ' + ', '.join(sorted(set(cleaned)))
                 + ' (Name und Symbol bleiben).')
    return {'config': cfg, 'aktionen': rows, 'camera_map': mapping}


# ---------------------------------------------------------------------------
# go2rtc
# ---------------------------------------------------------------------------

def rtsp_from_go2rtc(cfg):
    """Sources from a go2rtc config: ({stream: rtsp-dict ohne Passwort}, {stream: passwort})."""
    sources, passwords = {}, {}
    for name, value in ((cfg or {}).get('streams') or {}).items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, str) and item.lower().startswith(('rtsp://', 'rtsps://')):
                try:
                    cam = rtsp_mod.parse_url(item)
                except ValueError:
                    continue
                passwords[str(name)] = cam.pop('passwort')
                cam.pop('schema', None)
                sources[str(name)] = cam
                break
    return sources, passwords


def gen_go2rtc(model, cfg, secrets):
    cfg = copy.deepcopy(cfg or {})
    rows = []
    secrets.setdefault('rtsp', {})
    streams = cfg.get('streams') if isinstance(cfg.get('streams'), dict) else {}
    cfg['streams'] = streams
    publishers = []
    for t in model.get('teilnehmer', []):
        s = t['stream']
        if not s:
            continue
        if t.get('rtsp'):
            cam = dict(t['rtsp'])
            pw = secrets['rtsp'].get(s, '')
            if cam.get('benutzer') and not pw:
                _row(rows, 'warn', 'go2rtc', f'{s}: Passwort für die RTSP-Kamera fehlt – Stream bleibt unverändert.', s)
                continue
            url = rtsp_mod.build_url(cam, password=pw)
            current = streams.get(s)
            items = current if isinstance(current, list) else ([current] if current else [])
            rtsp_items = [i for i in items if isinstance(i, str) and i.lower().startswith(('rtsp://', 'rtsps://'))]
            others = [i for i in items if i not in rtsp_items]

            def same(a, b):
                try:
                    pa, pb = rtsp_mod.parse_url(a), rtsp_mod.parse_url(b)
                except ValueError:
                    return False
                return all(pa[k] == pb[k] for k in ('host', 'port', 'pfad', 'benutzer', 'passwort', 'zusatz'))
            if rtsp_items and same(rtsp_items[0], url):
                url = rtsp_items[0]          # gleiche Quelle, nur anders geschrieben (z. B. :554) – nicht umschreiben
            new = [url] + others
            if items != new:
                streams[s] = new
                _row(rows, 'ok', 'go2rtc', f'{s}: RTSP-Quelle {rtsp_mod.mask_url(url)}', s)
        elif t['typ'] == 'ha_geraet' and t['faehigkeiten'].get('kamerabild'):
            publishers.append(t)
            if s not in streams:
                streams[s] = []
                _row(rows, 'ok', 'go2rtc', f'{s}: leerer Stream für die Gerätekamera angelegt (Browser-ID am Gerät: {s}).', s)
        elif s not in streams:
            _row(rows, 'warn', 'go2rtc', f'{s}: Stream ohne Quelle im Modell – bitte RTSP-Adresse eintragen.', s)
    if publishers:
        api = cfg.get('api') if isinstance(cfg.get('api'), dict) else {}
        cfg['api'] = api
        if api.get('origin') != '*':
            api['origin'] = '*'
            _row(rows, 'ok', 'go2rtc', 'api.origin: "*" – Geräte dürfen ihr Kamerabild senden (CORS).')
    lan = model.get('anlage', {}).get('lan_ip')
    if lan and (publishers or any(t['stream'] for t in model.get('teilnehmer', []))):
        webrtc = cfg.get('webrtc') if isinstance(cfg.get('webrtc'), dict) else {}
        cfg['webrtc'] = webrtc
        webrtc.setdefault('listen', ':8555')
        port = str(webrtc['listen']).rsplit(':', 1)[-1] or '8555'
        cands = webrtc.get('candidates') if isinstance(webrtc.get('candidates'), list) else []
        want = f'{lan}:{port}'
        if want not in cands:
            cands.append(want)
            _row(rows, 'ok', 'go2rtc', f'WebRTC-Candidate {want}.')
        webrtc['candidates'] = cands
    return {'config': cfg, 'aktionen': rows}


def mask_go2rtc_text(text):
    return re.sub(r'(rtsps?://[^:/@\s]+:)[^@\s]*@', r'\1•••@', text or '')


# ---------------------------------------------------------------------------
# Dialplan: Wege und Direktwahl externer Ziele (verwalteter Block in custom/extensions.conf)
# ---------------------------------------------------------------------------
from anlage import ref_of  # noqa: E402

INTERNAL = ('ha_geraet', 'sip_telefon', 'tuerstation')


def dialplan_numbers(text):
    """{nummer: [kontext, …]} for simple 'exten => N,' lines (patterns ignored)."""
    out, ctx = {}, None
    for raw in (text or '').splitlines():
        line = raw.split(';', 1)[0].strip()
        head = re.match(r'^\[([^\]]+)\]', line)
        if head:
            ctx = head.group(1).strip()
            continue
        m = re.match(r'^exten\s*=>?\s*([0-9]{2,8})\s*,', line)
        if m and ctx:
            out.setdefault(m.group(1), [])
            if ctx not in out[m.group(1)]:
                out[m.group(1)].append(ctx)
    return out


def _contexts_outside(text):
    return {m.group(1).strip() for m in re.finditer(r'^[ \t]*\[([^\]\r\n]+)\]', text or '', re.M)}


def _dial_steps(targets, timeout, label, allow=None, deny=None):
    """Asterisk steps that ring all reachable targets at once. targets: [('contacts', '104') | ('uri', 'PJSIP/…')].
    allow: optional list of Asterisk conditions; only callers matching one of them get through (others: Hangup(21)).
    deny: optional list of Asterisk conditions; callers matching one of them are rejected first (Hangup(21))."""
    steps, pending, k = [(None, f'NoOp(Smartify: {label})')], None, 0

    def add(step):
        nonlocal pending
        steps.append((pending, step))
        pending = None
    if allow or deny or any(len(t) > 2 and t[2] for t in targets):
        add('Set(SM_EP=${CHANNEL(endpoint)})')
    if any('${SM_IP}' in c for c in list(allow or []) + [t[2] for t in targets if len(t) > 2 and t[2]]):
        add('Set(SM_IP=${CHANNEL(pjsip,remote_addr)})')   # z. B. 100.64.10.20:53384
        add('Set(SM_IP=${CUT(SM_IP,:,1)})')
    for cond in deny or []:
        add(f'GotoIf($[{cond}]?gesperrt)')
    if allow:
        for cond in allow:
            add(f'GotoIf($[{cond}]?erlaubt)')
        add('NoOp(Smartify: ${SM_EP} ${CALLERID(num)} darf nicht anrufen)')
        add('Hangup(21)')
        pending = 'erlaubt'
    add('Set(SM_DIAL=)')
    for target in targets:
        kind, value = target[0], target[1]
        skip = target[2] if len(target) > 2 else ''
        if kind == 'contacts':
            k += 1
            if skip:                                   # Anrufer klingelt nicht bei sich selbst
                add(f'GotoIf($[{skip}]?z{k})')
            add(f'Set(SM_C=${{PJSIP_DIAL_CONTACTS({value})}})')
            add(f'GotoIf($["${{SM_C}}" = ""]?z{k})')
            add('Set(SM_DIAL=${SM_DIAL}&${SM_C})')
            pending = f'z{k}'
        elif skip:
            k += 1
            add(f'GotoIf($[{skip}]?z{k})')
            add(f'Set(SM_DIAL=${{SM_DIAL}}&{value})')
            pending = f'z{k}'
        else:
            add(f'Set(SM_DIAL=${{SM_DIAL}}&{value})')
    add('GotoIf($["${SM_DIAL}" = ""]?leer)')
    add(f'Dial(${{SM_DIAL:1}},{int(timeout)})')
    add('Hangup()')
    steps.append(('leer', 'Hangup()'))
    if deny:
        steps.append(('gesperrt', 'NoOp(Smartify: ${SM_EP} ${CALLERID(num)} darf nicht anrufen)'))
        steps.append((None, 'Hangup(21)'))
    return steps


def _render_exten(number, steps):
    lines = []
    for i, (lbl, step) in enumerate(steps):
        prio = '1' if i == 0 else (f'n({lbl})' if lbl else 'n')
        lines.append(f'exten => {number},{prio},{step}' if i == 0 else f' same => {prio},{step}')
    return lines


def gen_dialplan(model, ext_text, endpoints, other_text=''):
    """ext_text: current custom/extensions.conf (or the default copy). endpoints: effective endpoints {name: ep}.
    Returns {'content', 'aktionen'}."""
    rows = []
    outside, _inside = split_managed(ext_text or '')
    t_all = model.get('teilnehmer', [])
    by_ref = {ref_of(t): t for t in t_all if ref_of(t)}
    internal_ctx = sorted({(endpoints.get(t['nummer']) or {}).get('context') or 'default'
                           for t in t_all if t['typ'] in ('ha_geraet', 'sip_telefon') and t['nummer']}) or ['default']

    def weg_kontexte(w):
        ctxs = []
        for ref in w['von']:
            t = by_ref.get(ref)
            if not t:
                continue
            key = t['nummer'] if t['typ'] in INTERNAL else (t.get('eingang') or t['endpoint'])
            ctx = (endpoints.get(key) or {}).get('context') or 'default'
            if ctx not in ctxs:
                ctxs.append(ctx)
        ctxs = ctxs or list(w.get('kontexte') or []) or list(internal_ctx)
        for c in w.get('kontexte') or []:
            if c not in ctxs:
                ctxs.append(c)
        if w.get('mitglieder_rufen'):                  # Mitglieder rufen aus ihrem eigenen Kontext an
            for t in (by_ref.get(r) for r in w['ziele']):
                if not t:
                    continue
                key = t['nummer'] if t['typ'] in INTERNAL else t.get('eingang')
                if key:
                    ctx = (endpoints.get(key) or {}).get('context') or ('default' if t['typ'] in INTERNAL else key)
                    if ctx not in ctxs:
                        ctxs.append(ctx)
        return ctxs

    def weg_ziele(w, mit_skip):
        """[(art, wert[, überspringen-wenn])] – mit_skip: der Anrufer klingelt nicht bei sich selbst."""
        out, names = [], []
        for ref in w['ziele']:
            t = by_ref.get(ref)
            if not t:
                continue
            # [(Bedingung, Kontext)]: wer hier anruft, klingelt nicht bei sich – immer, wenn der Anrufer dasselbe Gerät/dieselbe Person ist
            selbst = mit_skip or ref_of(t) in w['von'] or any(x.get('gleiches_geraet') == ref_of(t) and ref_of(x) in w['von'] for x in t_all)
            skip = bedingungen(t) if selbst else []
            if t['typ'] in INTERNAL:
                out.append(('contacts', t['nummer'], skip))
            elif t['typ'] == 'extern_ziel':
                out.append(('uri', f'PJSIP/{t["endpoint"]}/sip:{t["sip_adresse"]}', skip))
            else:
                _row(rows, 'warn', 'Dialplan', f'Rufgruppe „{w["name"]}“: {t["name"]} ist kein anrufbares Ziel – übersprungen.', w['nummer'])
                continue
            names.append(t['name'])
        return out, names

    def erlaubt_bedingung(t):
        if t['typ'] in INTERNAL and t['nummer']:
            return f'"${{SM_EP}}" = "{t["nummer"]}"'
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            ep = f'"${{SM_EP}}" = "{t["eingang"]}"'
            # Eine konfigurierte Quell-IP immer pruefen, auch bei nur einem Teilnehmer.
            v4 = [ip.split('/')[0] for ip in t.get('quell_ips') or [] if ':' not in ip]
            if v4:
                ips = ' | '.join(f'"${{SM_IP}}" = "{ip}"' for ip in v4)
                return f'{ep} & ' + (f'({ips})' if len(v4) > 1 else ips)
            # Ohne Quell-IP bei gemeinsamem Eingang zusaetzlich Caller-ID pruefen.
            shared = sum(1 for x in t_all if x['typ'] == 'extern_ziel' and x.get('eingang') == t['eingang']) > 1
            if not shared:
                return ep
            user = (t.get('sip_adresse') or '').split('@')[0]
            return ep + (f' & "${{CALLERID(num)}}" = "{user}"' if user else '')
        return ''

    def bedingungen(t):
        """[(Bedingung, Kontext)] für „dieser Teilnehmer ruft gerade an“ – inkl. SIP-Konten desselben Handys."""
        out = []
        c = erlaubt_bedingung(t)
        if c:
            out.append((c, kontext_von(t)))
        for x in t_all:
            if x.get('gleiches_geraet') and x['gleiches_geraet'] == ref_of(t) and x is not t:
                cx = erlaubt_bedingung(x)
                if cx:
                    out.append((cx, kontext_von(x)))
        return out

    def oder(conds):
        conds = list(dict.fromkeys(conds))
        if len(conds) == 1:
            return conds[0]
        return ' | '.join(f'({c})' if '&' in c else c for c in conds)

    def kontext_von(t):
        """Kontext, in dem Anrufe dieses Teilnehmers landen."""
        if t['typ'] in INTERNAL:
            return (endpoints.get(t['nummer']) or {}).get('context') or 'default'
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            return (endpoints.get(t['eingang']) or {}).get('context') or t['eingang']
        return ''

    def weg_erlaubt(w):
        """Bedingungen für erlaubte Anrufer: Anrufer der Gruppe plus externe Ziele mit Freigabe dieser Nummer.
        Leere Anrufer-Liste = alle im Kontext dürfen (keine Prüfung)."""
        if not w['von']:
            return []
        conds = []
        callers = [by_ref[r] for r in w['von'] if r in by_ref]
        if w.get('mitglieder_rufen'):
            callers += [by_ref[r] for r in w['ziele'] if r in by_ref and by_ref[r] not in callers]
        callers += [t for t in t_all if t['typ'] == 'extern_ziel' and w['nummer'] in (t.get('darf_anrufen') or []) and t not in callers]
        for t in callers:
            for pair in (bedingungen(t) if w.get('mitglieder_rufen') and ref_of(t) in w['ziele'] else
                         ([(erlaubt_bedingung(t), kontext_von(t))] if erlaubt_bedingung(t) else [])):
                if pair not in conds:
                    conds.append(pair)
        return conds

    def intern_nr(t):
        return t['typ'] in INTERNAL and t['nummer']

    def sperr_bedingungen(nr):
        """Interne Anrufer, deren Liste „darf anrufen“ die Nummer nr nicht enthält."""
        return list(dict.fromkeys(c for c in (erlaubt_bedingung(t) for t in t_all
                                              if intern_nr(t) and t.get('anruf_ziele') is not None and t['nummer'] != nr and nr not in t['anruf_ziele']) if c))

    def fuer_kontext(conds, ctx):
        """Nur die Prüfungen, die in diesem Kontext greifen können. Bleibt keine übrig, gelten alle (nie offen)."""
        own = [c for c, k in conds if k == ctx]
        return own or [c for c, _ in conds]

    # „bestehenden Eintrag ersetzen“: eigenen Eintrag dieser Nummer in den Kontexten der Rufgruppe entfernen
    # (nur in extensions.conf außerhalb des verwalteten Blocks; mit Backup beim Übernehmen)
    for w in model.get('wege', []):
        nr = w.get('nummer') or ''
        if not (w.get('ersetzen') and nr and w['ziele']):
            continue
        hit = [c for c in weg_kontexte(w) if c in dialplan_numbers(outside).get(nr, [])]
        if hit:
            outside = split_managed(remove_manual_exten(outside, nr, hit))[0]
            _row(rows, 'ok', 'Dialplan', f'{nr} „{w["name"]}“: bisheriger eigener Eintrag ({", ".join(hit)}) wird vom Manager ersetzt (Backup wird angelegt).', nr)
    # Einfache Einträge des alten Werkzeugs „Externe SIP-Eingänge“ im Kontext eines Eingangs: übernehmen,
    # sobald der Manager dieselbe Nummer dort selbst einträgt (Freigabe oder Rufgruppe) – sonst bleiben sie stehen
    import inbound_routes
    geplant = {}
    for t in t_all:
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            geplant.setdefault(kontext_von(t), set()).update(t.get('darf_anrufen') or [])
    for w in model.get('wege', []):
        if w.get('nummer') and w['ziele']:
            for c in weg_kontexte(w):
                geplant.setdefault(c, set()).add(w['nummer'])
    for e in eingaenge_effektiv(model):
        ctx = (endpoints.get(e['name']) or {}).get('context') or e['name']
        try:
            old = inbound_routes.inspect_context(outside, ctx)
        except ValueError:
            continue                                   # eigene, komplexere Regeln: nicht anfassen
        alt = (old or {}).get('targets') or []
        # Alte, eindeutig als Legacy-Eingangsregeln erkannte Routen mit dem
        # aktuellen Modell abgleichen. Nicht mehr erlaubte Ziele entfernen.
        # Unbekannte/manuelle Kontexte bleiben durch inspect_context geschuetzt.
        weg = list(alt)
        for nr in weg:
            outside = split_managed(remove_manual_exten(outside, nr, [ctx]))[0]
        if weg:
            _row(rows, 'warn', 'Dialplan', f'Eingang {e["name"]}: bisherige Legacy-Routen {", ".join(weg)} werden entfernt; nur laut aktuellen Einstellungen erlaubte Routen werden neu erzeugt (Backup/Vorschau pruefen).', e['name'])
        for nr in alt:
            if nr not in weg:
                _row(rows, 'info', 'Dialplan', f'Eingang {e["name"]}: eigener Eintrag {nr} bleibt (beim Cloud-Teilnehmer unter „darf anrufen“ anhaken, '
                     'dann übernimmt ihn der Manager).', nr)
    existing_main = dialplan_numbers(outside)
    existing = {k: list(v) for k, v in existing_main.items()}
    for nr, ctxs in dialplan_numbers(other_text).items():
        existing.setdefault(nr, [])
        existing[nr] += [c for c in ctxs if c not in existing[nr]]
    contexts_out = _contexts_outside(outside)
    per_ctx = {}

    def put(ctx, number, lines, what, weg=False):
        if ctx in existing.get(number, []):
            if weg and ctx in existing_main.get(number, []):
                _row(rows, 'warn', 'Dialplan', f'{number} ({what}): im Kontext „{ctx}“ gibt es schon einen eigenen Eintrag in extensions.conf – '
                     'nicht überschrieben. „Bestehenden Eintrag ersetzen“ wählen (mit Backup) oder eine andere Nummer.', number,
                     aktion='rufgruppe_ersetzen')
            else:
                _row(rows, 'warn', 'Dialplan', f'{number} ({what}): im Kontext „{ctx}“ gibt es schon einen eigenen Eintrag'
                     + ('' if ctx in existing_main.get(number, []) else ' in einer anderen Datei unter custom/')
                     + ' – nicht überschrieben. Eigenen Eintrag entfernen oder andere Nummer wählen.', number)
            return False
        per_ctx.setdefault(ctx, []).extend(lines)
        return True

    for w in model.get('wege', []):
        if not w.get('nummer') or not w['ziele']:
            continue
        targets, names = weg_ziele(w, bool(w.get('mitglieder_rufen')))
        if not targets:
            continue
        ctxs = weg_kontexte(w)
        allow = weg_erlaubt(w)
        deny = sperr_bedingungen(w['nummer'])
        if w.get('mitglieder_rufen'):
            for t in (by_ref.get(r) for r in w['ziele']):
                if t and t['typ'] == 'extern_ziel' and not t.get('eingang'):
                    _row(rows, 'warn', 'Dialplan', f'Rufgruppe „{w["name"]}“: {t["name"]} hat keinen Eingang – kann {w["nummer"]} vom Handy aus nicht anrufen. '
                         'Beim Teilnehmer den Eingang wählen (z. B. linphone-in) und die IP des Handys beim Eingang eintragen.', w['nummer'])
        head = [f'; Rufgruppe „{w["name"]}“ – von {", ".join(w["von"]) or "allen"} → {", ".join(names)}'
                + (' (nur diese Anrufer)' if allow else '') + (' · einzelne Teilnehmer gesperrt' if deny else '') + (' · Mitglieder dürfen anrufen, Anrufer wird übersprungen' if w.get('mitglieder_rufen') else '')]

        def fuer(ctx):
            ziele = [(a, b, oder([c for c, k in sk if k == ctx]) if any(k == ctx for _, k in sk) else '') for a, b, sk in targets]
            return head + _render_exten(w['nummer'], _dial_steps(ziele, w['klingelzeit'], 'Rufgruppe ' + w['name'],
                                                                  fuer_kontext(allow, ctx) if allow else None, deny)) + ['']
        done = [c for c in ctxs if put(c, w['nummer'], fuer(c), 'Rufgruppe ' + w['name'], weg=True)]
        if done:
            _row(rows, 'ok', 'Dialplan', f'{w["nummer"]} „{w["name"]}“ → {", ".join(names)} ({w["klingelzeit"]} s, Kontext {", ".join(done)}).', w['nummer'])

    # Erreichbarkeit interner Teilnehmer: wer darf wen direkt wählen (Einschränkung „darf anrufen“ / „darf angerufen werden von“)
    for t in t_all:
        if not intern_nr(t):
            continue
        nr, deny, inbound = t['nummer'], sperr_bedingungen(t['nummer']), t.get('angerufen_von')
        if not deny and inbound is None:
            continue
        allow = None
        if inbound is not None:
            wer = [by_ref[r] for r in inbound if r in by_ref and intern_nr(by_ref[r]) and r != nr]
            wer = [x for x in wer if x.get('anruf_ziele') is None or nr in x['anruf_ziele']]
            wer += [x for x in t_all if x['typ'] == 'extern_ziel' and x.get('eingang') and nr in (x.get('darf_anrufen') or [])]
            allow = list(dict.fromkeys(c for c in (erlaubt_bedingung(x) for x in wer) if c)) or ['1 = 0']
        was = []
        if inbound is not None:
            was.append('nur ' + (', '.join(inbound) if inbound else 'niemand') + ' darf anrufen')
        if deny:
            was.append(f'{len(deny)} Teilnehmer gesperrt')
        lines = [f'; Erreichbarkeit {t["name"]} ({nr}): {"; ".join(was)}'] + _render_exten(nr, _dial_steps([('contacts', nr)], 30, t['name'], allow, deny)) + ['']
        done = [c for c in internal_ctx if put(c, nr, lines, 'Erreichbarkeit ' + t['name'])]
        if done:
            _row(rows, 'ok', 'Dialplan', f'{nr} {t["name"]}: Erreichbarkeit eingeschränkt ({"; ".join(was)}; Kontext {", ".join(done)}).', nr)

    manual = {(z['nummer'], z['endpoint'], z['sip_adresse']) for z in dialplan_extern_targets(outside + '\n' + (other_text or ''))}
    for t in t_all:
        if t['typ'] != 'extern_ziel' or not t['nummer']:
            continue
        deny = sperr_bedingungen(t['nummer'])
        inbound = t.get('angerufen_von')
        if inbound is not None:
            local = [by_ref[r] for r in inbound if r in by_ref and intern_nr(by_ref[r]) and r != t['nummer']]
            local = [x for x in local if x.get('anruf_ziele') is None or t['nummer'] in x['anruf_ziele']]
            allow = list(dict.fromkeys(c for c in (erlaubt_bedingung(x) for x in local) if c)) or ['1 = 0']
        else:
            allow = None
        if (t['nummer'], t['endpoint'], t['sip_adresse']) in manual:
            if deny or inbound is not None:
                _row(rows, 'warn', 'Dialplan',
                     f'{t["nummer"]}: eigener Dialplan-Eintrag bleibt – '
                     'die konfigurierte Direktwahl-Sperre greift dort nicht. '
                     'Eigenen Eintrag entfernen, dann übernimmt ihn der Manager.', t['nummer'])
            _row(rows, 'info', 'Dialplan', f'{t["nummer"]}: eigener Dialplan-Eintrag für {t["sip_adresse"]} vorhanden und passend – bleibt unverändert.', t['nummer'])
            continue
        if deny or inbound is not None:
            lines = [f'; Direktwahl {t["name"]} über {t["endpoint"]} (Berechtigungen geprüft)'] + _render_exten(
                t['nummer'], _dial_steps([('uri', f'PJSIP/{t["endpoint"]}/sip:{t["sip_adresse"]}')], 60, t['name'], allow, deny)) + ['']
        else:
            lines = [f'; Direktwahl {t["name"]} über {t["endpoint"]}',
                     f'exten => {t["nummer"]},1,NoOp(Smartify: {t["name"]})',
                     f' same => n,Dial(PJSIP/{t["endpoint"]}/sip:{t["sip_adresse"]},60)', ' same => n,Hangup()', '']
        done = [c for c in internal_ctx if put(c, t['nummer'], lines, t['name'])]
        if done:
            _row(rows, 'ok', 'Dialplan', f'{t["nummer"]}: Direktwahl {t["name"]} ({t["sip_adresse"]}).', t['nummer'])

    # Freigaben: externe Ziele dürfen interne Nummern bzw. Wege direkt anrufen (im Kontext ihres Eingangs)
    wege_by_nr = {w['nummer']: w for w in model.get('wege', []) if w.get('nummer') and w['ziele']}
    allowed = {}
    for t in t_all:
        if t['typ'] != 'extern_ziel' or not t.get('eingang'):
            continue
        ctx = (endpoints.get(t['eingang']) or {}).get('context') or t['eingang']
        for nr in t.get('darf_anrufen') or []:
            allowed.setdefault((ctx, nr), []).append(t)
    for (ctx, nr), wer in sorted(allowed.items()):
        who = [t['name'] for t in wer]
        allow = [c for c in (erlaubt_bedingung(t) for t in wer) if c]
        if ctx in existing.get(nr, []):
            _row(rows, 'warn', 'Dialplan', f'{nr} im Eingang „{ctx}“ hat bereits einen eigenen Eintrag. Neue Freigaben und IP-Pruefungen greifen dort NICHT; bestehende Route pruefen.', nr)
            continue
        if nr in wege_by_nr:
            w = wege_by_nr[nr]
            targets = [(a, b, oder([c for c, k in sk if k == ctx]) if any(k == ctx for _, k in sk) else '')
                       for a, b, sk in weg_ziele(w, bool(w.get('mitglieder_rufen')))[0]]
            label, timeout = 'Rufgruppe ' + w['name'], w['klingelzeit']
        else:
            z = by_ref.get(nr)
            if not z:
                continue
            targets, label, timeout = [('contacts', nr)], z['name'], 30
        if any(ctx in per_ctx and f'exten => {nr},1,' in line for line in per_ctx.get(ctx, [])):
            continue                                # schon als Rufgruppe in diesem Kontext erzeugt
        lines = [f'; Freigabe für {", ".join(who)}: {nr} ({label})'] + _render_exten(nr, _dial_steps(targets, timeout, label, allow)) + ['']
        if put(ctx, nr, lines, 'Freigabe ' + label):
            _row(rows, 'ok', 'Dialplan', f'{", ".join(who)} darf {nr} ({label}) anrufen – Eingang „{ctx}“.', nr)

    # Was bisher verwaltet erreichbar war und jetzt wegfällt, deutlich melden (z. B. 600 aus linphone-in)
    before = dialplan_numbers(_inside)
    after = dialplan_numbers('\n'.join(f'[{c}]\n' + '\n'.join(l) for c, l in per_ctx.items()))
    for nr, ctxs in sorted(before.items()):
        for c in ctxs:
            if c not in after.get(nr, []) and c not in existing.get(nr, []):
                _row(rows, 'warn', 'Dialplan', f'{nr} ist danach aus dem Kontext „{c}“ NICHT mehr erreichbar (bisher vom Manager eingetragen). '
                     'Falls das weiter gehen soll: Anrufer aus diesem Eingang in die Rufgruppe ziehen bzw. „darf anrufen“ anhaken.', nr)
    body = outside.rstrip('\n')
    content = body + '\n' if body.strip() else ''
    if per_ctx:
        parts = []
        for ctx in sorted(per_ctx):
            parts.append(f'[{ctx}](+)' if ctx in contexts_out else f'[{ctx}]')
            parts.extend(per_ctx[ctx])
        content += '\n' + BEGIN + '\n' + '\n'.join(parts).rstrip('\n') + '\n' + END + '\n'
    return {'content': content, 'aktionen': rows}


def dialplan_extern_targets(text):
    """Existing manual entries like 'exten => 906,…Dial(PJSIP/linphone-cloud/sip:user@host,…)' outside the managed block."""
    outside, _ = split_managed(text or '')
    found, names, ctx = [], {}, None
    for raw in outside.splitlines():
        line = raw.split(';', 1)[0].strip()
        m = re.match(r'^exten\s*=>?\s*([0-9]{2,8})\s*,\s*1\s*,\s*NoOp\((.*)\)', line, re.I)
        if m:
            names[m.group(1)] = m.group(2).strip()[:60]
        num = re.match(r'^exten\s*=>?\s*([0-9]{2,8})\s*,', line)
        if num:
            ctx = num.group(1)
        d = re.search(r'Dial\(PJSIP/([A-Za-z0-9_.+-]+)/sip:([A-Za-z0-9_.+!~*()%-]+@[A-Za-z0-9.\-]+(?::\d+)?)', line)
        if d and ctx and not any(f['nummer'] == ctx for f in found):
            found.append({'nummer': ctx, 'endpoint': d.group(1), 'sip_adresse': d.group(2),
                          'name': names.get(ctx) or d.group(2).split('@')[0]})
    return found


# ---------------------------------------------------------------------------
# Vorhandene einfache Rufgruppen erkennen und übernehmen (v1.13)
# ---------------------------------------------------------------------------
RE_DIAL_LOCAL = re.compile(r'^\$\{PJSIP_DIAL_CONTACTS\((\d{2,8})\)\}$|^PJSIP/(\d{2,8})$', re.I)
RE_DIAL_EXT = re.compile(r'^PJSIP/([A-Za-z][A-Za-z0-9_.+-]{0,63})/sip:([A-Za-z0-9_.+!~*()%-]+@[A-Za-z0-9.\-]+(?::\d{1,5})?)$', re.I)


def _exten_steps(text):
    """{(kontext, nummer): [schritt, …]} for numeric extens outside the managed block."""
    outside, _ = split_managed(text or '')
    steps, ctx, cur = {}, None, None
    for raw in outside.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        head = re.match(r'^\[([^\]]+)\]', line)
        if head:
            ctx, cur = head.group(1).strip(), None
            continue
        m = re.match(r'^exten\s*=>?\s*([0-9]{2,8})\s*,\s*([^,]+)\s*,\s*(.+)$', line)
        if m and ctx:
            cur = (ctx, m.group(1))
            steps.setdefault(cur, []).append(m.group(3).strip())
            continue
        s = re.match(r'^same\s*=>?\s*[^,]+\s*,\s*(.+)$', line)
        if s and cur:
            steps[cur].append(s.group(1).strip())
            continue
        if re.match(r'^exten\s*=>', line):
            cur = None
    return steps


def _simple_group(step_list):
    """Only NoOp/Answer · one Dial(…,timeout[,opts]) · Hangup. Returns dict or None."""
    name, dial = '', None
    for i, st in enumerate(step_list):
        noop = re.fullmatch(r'NoOp\(([^()]*)\)', st, re.I)
        if noop and dial is None:
            name = name or noop.group(1).strip()
            continue
        if re.fullmatch(r'Answer\(\)', st, re.I) and dial is None:
            continue
        d = re.fullmatch(r'Dial\(([^,()]+(?:\([^()]*\)[^,()]*)*),\s*(\d{1,3})\s*(?:,[A-Za-z()0-9]*)?\)', st, re.I)
        if d and dial is None:
            dial = d
            continue
        if re.fullmatch(r'Hangup\(\)', st, re.I) and dial is not None and i == len(step_list) - 1:
            continue
        return None
    if not dial:
        return None
    ziele = []
    for part in [p.strip() for p in dial.group(1).split('&') if p.strip()]:
        loc, ext = RE_DIAL_LOCAL.match(part), RE_DIAL_EXT.match(part)
        if loc:
            ziele.append({'nummer': loc.group(1) or loc.group(2)})
        elif ext:
            ziele.append({'endpoint': ext.group(1), 'adresse': ext.group(2)})
        else:
            return None
    return {'name': name, 'ziele': ziele, 'klingelzeit': max(5, min(300, int(dial.group(2))))} if ziele else None


def dialplan_groups(text):
    """Simple groups (2+ targets, or one target that is not the number itself), per number with their contexts."""
    groups = {}
    for (ctx, nr), st in _exten_steps(text).items():
        g = _simple_group(st)
        if not g:
            continue
        if len(g['ziele']) == 1 and (g['ziele'][0].get('nummer') == nr or 'adresse' in g['ziele'][0]):
            continue                                 # Direktwahl/Freigabe, keine Gruppe
        cur = groups.setdefault(nr, {'nummer': nr, 'name': g['name'] or f'Rufgruppe {nr}', 'ziele': g['ziele'],
                                     'klingelzeit': g['klingelzeit'], 'kontexte': []})
        if ctx not in cur['kontexte']:
            cur['kontexte'].append(ctx)
    return sorted(groups.values(), key=lambda g: int(g['nummer']))


def remove_manual_exten(text, nummer, contexts):
    """Remove a simple manual exten (all its lines) from the given contexts, outside the managed block."""
    outside, inside = split_managed(text or '')
    lines, out, ctx, skipping = outside.splitlines(keepends=True), [], None, False
    for raw in lines:
        line = raw.split(';', 1)[0].strip()
        head = re.match(r'^\[([^\]]+)\]', line)
        if head:
            ctx, skipping = head.group(1).strip(), False
            out.append(raw)
            continue
        m = re.match(r'^exten\s*=>?\s*([^,]+?)\s*,', line)
        if m:
            skipping = ctx in contexts and m.group(1) == nummer
        elif not re.match(r'^same\s*=>', line):
            skipping = skipping and not line   # leere Zeilen/Kommentare beenden die Gruppe nicht, andere Zeilen schon
            if line:
                skipping = False
        if not skipping:
            out.append(raw)
    body = ''.join(out)
    if inside or BEGIN in (text or ''):
        body = body.rstrip('\n') + '\n\n' + BEGIN + inside + END + '\n'
    return body
