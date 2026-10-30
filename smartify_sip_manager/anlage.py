"""Smartify SIP Manager – Anlagen-Modell (v1.4).

Reine Funktionen ohne Seiteneffekte: Validierung des Modells, Import aus der
bestehenden Konfiguration, effektive PJSIP-Codecs und der Prüfbericht.
app.py liefert die Eingaben (Dateien, SIP Core, go2rtc, AMI) und speichert.

Das Modell beschreibt die Anlage; in v1.4 wird daraus noch nichts geschrieben.
"""
import re

FORMAT = 'smartify-anlage'
FORMAT_VERSION = 1

TYPEN = {
    'ha_geraet': 'HA-Gerät (SIP Core)',
    'sip_telefon': 'SIP-Telefon',
    'tuerstation': 'Türstation',
    'kamera': 'Kamera ohne SIP',
    'extern_ziel': 'Externes Ziel (SIP-Adresse)',
}
FAEHIGKEITEN = {
    'kamerabild': 'Video HA – Kamerabild im HA-Popup (go2rtc)',
    'video_im_anruf': 'Video SIP – Video im SIP-Anruf (z. B. zu Linphone)',
    'ios': 'iOS-Gerät (iPhone/iPad) – braucht WebRTC',
    'tuer_oeffnen': 'Türöffner-Button bei Anrufen dieser Station',
}
VIDEO_CODECS = ('vp8', 'vp9', 'h264', 'h265')
POPUP_COMPONENT = 'smartify-doorstation-popup'

RE_NUMMER = re.compile(r'^[0-9]{2,8}$')
RE_STREAM = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
RE_ENTITY = re.compile(r'^[a-z_]+\.[A-Za-z0-9_]+$')
RE_ENDPOINT = re.compile(r'^[A-Za-z0-9_.+-]{1,80}$')
RE_HOST = re.compile(r'^[A-Za-z0-9.\-]{0,253}$')
BACKUP = '*'          # HA-Benutzer-Platzhalter für SIP Core backup_user (alle übrigen HA-Benutzer)


def sip_core_users(cfg):
    """users plus backup_user (marked with ha_username '*')."""
    out = [dict(u) for u in (cfg or {}).get('users') or [] if isinstance(u, dict)]
    backup = (cfg or {}).get('backup_user')
    if isinstance(backup, dict) and backup.get('extension'):
        out.append({**backup, 'ha_username': BACKUP, '_backup': True})
    return out


RE_SIP_ADDR = re.compile(r'^[A-Za-z0-9_.+!~*()%-]{1,64}@[A-Za-z0-9.\-]{1,253}(:\d{1,5})?$')


def ref_of(t):
    """How a participant is referenced in Wege: number, else endpoint (Anschluss), else sip:address."""
    if t.get('nummer'):
        return t['nummer']
    if t.get('typ') == 'extern_ziel' and t.get('sip_adresse'):
        return 'sip:' + t['sip_adresse']
    return t.get('endpoint') or ''


# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------

def leer():
    return {'format': FORMAT, 'format_version': FORMAT_VERSION,
            'anlage': {'name': '', 'kunde': '', 'nummer_von': '100', 'nummer_bis': '199',
                       'lan_ip': '', 'tailscale_name': '', 'tailscale_ip': '', 'go2rtc_https_url': ''},
            'teilnehmer': [], 'wege': [], 'eingaenge': []}


RE_TS_IP = re.compile(r'^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}$')
RE_REALM = re.compile(r'^[A-Za-z0-9][A-Za-z0-9.:-]{0,99}$')


def _tn_ips(item, typ):
    """Geräte-IPs eines Cloud-Teilnehmers (z. B. Tailscale-IP des Handys) – nur für Anrufe über einen Eingang."""
    import inbound_routes
    raw = item.get('quell_ips') or []
    if isinstance(raw, str):
        raw = re.split(r'[\s,;]+', raw)
    ips = [str(x).strip() for x in raw if str(x).strip()]
    if typ != 'extern_ziel' or not ips:
        return []
    try:
        return inbound_routes.normal_ips(ips)
    except ValueError as exc:
        raise ValueError(f'{item.get("name") or "Teilnehmer"}: {exc}') from None


def realm_fuer(t, anlage):
    """Anmelde-Bereich (realm) für SIP-Telefone/Türstationen: eigener Wert, sonst die Domain, mit der das Gerät
    sich anmeldet – Handy über Tailscale (gleiches Handy wie …) → Tailscale-IP von HA, sonst LAN-IP von HA."""
    if t.get('realm'):
        return t['realm']
    if t['typ'] not in ('sip_telefon', 'tuerstation'):
        return ''
    if t.get('gleiches_geraet') and anlage.get('tailscale_ip'):
        return anlage['tailscale_ip']
    return anlage.get('lan_ip') or ''


def eingaenge_effektiv(model):
    """Alle Eingänge mit ihren Quell-IPs: eigene Liste des Eingangs plus die IPs der Teilnehmer, die ihn nutzen."""
    out = {e['name']: {'name': e['name'], 'quell_ips': list(e['quell_ips']), 'eigene': list(e['quell_ips'])} for e in model.get('eingaenge', [])}
    for t in model.get('teilnehmer', []):
        if t['typ'] == 'extern_ziel' and t.get('eingang') and t.get('quell_ips'):
            e = out.setdefault(t['eingang'], {'name': t['eingang'], 'quell_ips': [], 'eigene': []})
            e['quell_ips'] += [ip for ip in t['quell_ips'] if ip not in e['quell_ips']]
    return list(out.values())


def _eingaenge(raw):
    """Eingänge (Anrufe von außen ohne Anmeldung, z. B. über Tailscale): Name und erlaubte Quell-IPs."""
    import inbound_routes
    if raw in (None, ''):
        return []
    if not isinstance(raw, list) or len(raw) > 20:
        raise ValueError('Eingänge ungültig (maximal 20)')
    out, names = [], set()
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Eingang {i} ist kein Objekt')
        name = str(item.get('name') or '').strip()
        if not inbound_routes.PROFILE.fullmatch(name):
            raise ValueError(f'Eingang {i}: Name nur Kleinbuchstaben, Ziffern, - und _ (z. B. linphone-in)')
        if name in names:
            raise ValueError(f'Eingang {name} doppelt')
        names.add(name)
        ips = [str(x).strip() for x in (item.get('quell_ips') or []) if str(x).strip()]
        if ips:
            try:
                ips = inbound_routes.normal_ips(ips)
            except ValueError as exc:
                raise ValueError(f'Eingang {name}: {exc}') from None
        out.append({'name': name, 'quell_ips': ips, 'uebernommen': bool(item.get('uebernommen'))})
    return out


def _text(value, field, limit=80, required=False):
    if value is None:
        value = ''
    if not isinstance(value, str) or len(value) > limit or any(c in value for c in '\r\n\x00'):
        raise ValueError(f'Ungültiger Wert: {field}')
    value = value.strip()
    if required and not value:
        raise ValueError(f'{field} fehlt')
    return value


def _opt(value, regex, field):
    value = _text(value, field, 253)
    if value and not regex.fullmatch(value):
        raise ValueError(f'Ungültiger Wert: {field}')
    return value


def repair(model):
    """Fix known problems in stored models so they load again (never raises). Returns (model, hinweise)."""
    import copy as _copy
    hinweise = []
    if not isinstance(model, dict):
        return leer(), ['Gespeichertes Modell war unlesbar – leeres Modell geladen.']
    m = _copy.deepcopy(model)
    m.setdefault('format', FORMAT)
    if not isinstance(m.get('anlage'), dict):
        m['anlage'] = leer()['anlage']
    items = m.get('teilnehmer') if isinstance(m.get('teilnehmer'), list) else []
    m['teilnehmer'] = [t for t in items if isinstance(t, dict)]
    m['wege'] = [w for w in (m.get('wege') if isinstance(m.get('wege'), list) else []) if isinstance(w, dict)]
    seen = {}
    for t in m['teilnehmer']:
        if t.get('typ') == 'ha_geraet' and t.get('ha_benutzer'):
            if t['ha_benutzer'] in seen:
                hinweise.append(f'HA-Benutzer „{t["ha_benutzer"]}“ war bei {seen[t["ha_benutzer"]]} und {t.get("nummer")} eingetragen – '
                                f'bei {t.get("nummer")} geleert, bitte neu wählen.')
                t['ha_benutzer'] = ''
            else:
                seen[t['ha_benutzer']] = t.get('nummer')
    return m, hinweise


def validate_lenient(model):
    """Load path: repair, then validate; drop single broken participants/routes instead of failing."""
    m, hinweise = repair(model)
    for _ in range(60):
        try:
            return validate(m), hinweise
        except ValueError as exc:
            text = str(exc)
            hit = re.match(r'^(?:Teilnehmer (\d+)|Rufgruppe (\d+))', text)
            if hit and hit.group(1) and int(hit.group(1)) <= len(m['teilnehmer']):
                gone = m['teilnehmer'].pop(int(hit.group(1)) - 1)
                hinweise.append(f'Teilnehmer „{gone.get("name") or gone.get("nummer") or "?"}“ entfernt: {text}')
            elif hit and hit.group(2) and int(hit.group(2)) <= len(m['wege']):
                gone = m['wege'].pop(int(hit.group(2)) - 1)
                hinweise.append(f'Rufgruppe „{gone.get("name") or "?"}“ entfernt: {text}')
            elif text.startswith('Eingang') and m.get('eingaenge'):
                m['eingaenge'] = []
                hinweise.append('Eingänge entfernt: ' + text)
            else:
                hinweise.append('Modell konnte nicht vollständig geladen werden: ' + text)
                return validate(dict(m, wege=[])) if m['wege'] else leer(), hinweise
    return leer(), hinweise + ['Modell konnte nicht geladen werden.']


def _video_codec_choice(value):
    """Per-participant video policy; empty/auto keeps the legacy default."""
    value = str(value or 'auto').strip().lower()
    if value not in ('auto', 'vp8', 'h264', 'vp9', 'vp8,h264', 'none'):
        raise ValueError('Video-Codecs: ungültige Auswahl')
    return value


def validate(model):
    """Return a normalized copy or raise ValueError with a German message."""
    if not isinstance(model, dict) or model.get('format') != FORMAT:
        raise ValueError('Kein Smartify-Anlagenmodell')
    if int(model.get('format_version', 0) or 0) > FORMAT_VERSION:
        raise ValueError('Das Modell stammt aus einer neueren Manager-Version')
    raw = model.get('anlage') or {}
    if not isinstance(raw, dict):
        raise ValueError('anlage muss ein Objekt sein')
    anlage = {
        'name': _text(raw.get('name'), 'Anlagenname'),
        'kunde': _text(raw.get('kunde'), 'Kunde'),
        'nummer_von': _opt(str(raw.get('nummer_von') or ''), RE_NUMMER, 'Nummernbereich von'),
        'nummer_bis': _opt(str(raw.get('nummer_bis') or ''), RE_NUMMER, 'Nummernbereich bis'),
        'lan_ip': _opt(raw.get('lan_ip'), RE_HOST, 'LAN-IP'),
        'tailscale_name': _opt(raw.get('tailscale_name'), RE_HOST, 'Tailscale-Name'),
        'tailscale_ip': _opt(raw.get('tailscale_ip'), RE_TS_IP, 'Tailscale-IP'),
        'go2rtc_https_url': _text(raw.get('go2rtc_https_url'), 'go2rtc-HTTPS-Adresse', 200),
    }
    url = anlage['go2rtc_https_url']
    if url and not re.fullmatch(r'https://[A-Za-z0-9.\-]+(:\d{1,5})?', url.rstrip('/')):
        raise ValueError('go2rtc-HTTPS-Adresse: Format https://name.tailnet.ts.net:8443')
    anlage['go2rtc_https_url'] = url.rstrip('/')
    if anlage['nummer_von'] and anlage['nummer_bis'] and int(anlage['nummer_von']) > int(anlage['nummer_bis']):
        raise ValueError('Nummernbereich: „von“ ist größer als „bis“')

    teilnehmer, seen = [], set()
    items = model.get('teilnehmer') or []
    if not isinstance(items, list) or len(items) > 200:
        raise ValueError('Teilnehmerliste ungültig (maximal 200)')
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Teilnehmer {index} ist kein Objekt')
        typ = item.get('typ')
        if typ not in TYPEN and typ != 'extern':
            raise ValueError(f'Teilnehmer {index}: unbekannter Typ')
        nummer = str(item.get('nummer') or '').strip()
        if typ in ('kamera', 'extern', 'extern_ziel'):
            if nummer and not RE_NUMMER.fullmatch(nummer):
                raise ValueError(f'Teilnehmer {index}: Nummer nur Ziffern (2–8)')
        elif not RE_NUMMER.fullmatch(nummer):
            raise ValueError(f'Teilnehmer {index}: Nummer fehlt oder ungültig (2–8 Ziffern)')
        sip_addr = str(item.get('sip_adresse') or '').strip()
        if sip_addr.lower().startswith('sip:'):
            sip_addr = sip_addr[4:]
        if typ == 'extern_ziel':
            if not RE_SIP_ADDR.fullmatch(sip_addr):
                raise ValueError(f'{item.get("name") or index}: SIP-Adresse im Format name@sip.linphone.org angeben')
            if not str(item.get('endpoint') or '').strip():
                raise ValueError(f'{item.get("name") or index}: Anschluss (z. B. linphone-cloud) auswählen')
        else:
            sip_addr = ''
        key = nummer or ('#' + (('sip:' + sip_addr) if sip_addr else str(item.get('endpoint') or item.get('stream') or index)))
        if key in seen:
            raise ValueError(f'Nummer {nummer or key} ist doppelt vergeben')
        seen.add(key)
        fae = item.get('faehigkeiten') or {}
        if not isinstance(fae, dict):
            raise ValueError(f'Teilnehmer {index}: Fähigkeiten ungültig')
        entry = {
            'nummer': nummer,
            'name': _text(item.get('name'), f'Name von Teilnehmer {index}', required=True),
            'typ': typ,
            'ha_benutzer': _text(item.get('ha_benutzer'), f'HA-Benutzer von {nummer}'),
            'endpoint': _opt(item.get('endpoint'), RE_ENDPOINT, f'Endpoint von {nummer}'),
            'stream': _opt(item.get('stream'), RE_STREAM, f'Streamname von {nummer}'),
            'tuer_entity': _opt(item.get('tuer_entity'), RE_ENTITY, f'Türöffner-Entität von {nummer}'),
            'licht_entity': _opt(item.get('licht_entity'), RE_ENTITY, f'Licht-Entität von {nummer}'),
            'klingel_entity': _opt(item.get('klingel_entity'), RE_ENTITY, f'Klingel-Entität von {nummer}'),
            'faehigkeiten': {k: bool(fae.get(k)) for k in FAEHIGKEITEN},
            'video_codecs': _video_codec_choice(item.get('video_codecs')),
            'qualify_frequency': _qualify_frequency(item.get('qualify_frequency')),
            'ring_output': str(item.get('ring_output') or 'standard'),
            'ring_player': _opt(item.get('ring_player'), RE_ENTITY, f'Klingel-Mediaplayer von {nummer}'),
            'ring_media': _text(item.get('ring_media') or '/local/ring-tone.mp3', f'Klingelton von {nummer}', 200),

            'notiz': _text(item.get('notiz'), f'Notiz von {nummer}', 300),
            'rtsp': _rtsp(item.get('rtsp'), f'RTSP-Quelle von {item.get("name") or index}'),
            'sip_adresse': sip_addr,
            'eingang': _opt(item.get('eingang'), RE_ENDPOINT, f'Eingang von {item.get("name") or index}') if typ == 'extern_ziel' else '',
            'darf_anrufen': [str(x).strip() for x in (item.get('darf_anrufen') or []) if str(x).strip()][:50] if typ == 'extern_ziel' else [],
            'anruf_ziele': _begrenzung(item.get('anruf_ziele')) if typ in ('ha_geraet', 'sip_telefon', 'tuerstation') else None,
            'angerufen_von': _begrenzung(item.get('angerufen_von')) if typ in ('ha_geraet', 'sip_telefon', 'tuerstation', 'extern_ziel') else None,
            'quell_ips': _tn_ips(item, typ),
            'realm': _opt(item.get('realm'), RE_REALM, f'Anmelde-Bereich von {nummer}') if typ in ('sip_telefon', 'tuerstation') else '',
            'gleiches_geraet': str(item.get('gleiches_geraet') or '').strip()[:120] if typ == 'sip_telefon' else '',
        }
        if entry['ring_output'] not in ('standard', 'media_player'):
            raise ValueError(f'{entry["name"]}: Klingeltonausgabe ist ungültig')
        if entry['ring_output'] == 'media_player' and (not entry['ring_player'].startswith('media_player.') or
            not re.fullmatch(r'/local/[a-zA-Z0-9_./-]+\\.(mp3|wav)', entry['ring_media'])):
            raise ValueError(f'{entry["name"]}: Für die externe Klingeltonausgabe einen HA-Mediaplayer und eine /local/*.mp3- oder *.wav-Datei wählen')
        if entry['rtsp'] and not entry['stream']:
            raise ValueError(f'{entry["name"]}: Eine RTSP-Kamera braucht einen Streamnamen')
        if entry['faehigkeiten']['kamerabild'] and not entry['stream']:
            raise ValueError(f'{entry["name"]}: „Video HA“ braucht einen Streamnamen')
        teilnehmer.append(entry)

    seen_ha = {}
    for t in teilnehmer:
        if t['typ'] == 'ha_geraet' and t['ha_benutzer']:
            if t['ha_benutzer'] in seen_ha:
                raise ValueError(f'HA-Benutzer „{t["ha_benutzer"]}“ ist bei {seen_ha[t["ha_benutzer"]]} und {t["nummer"]} eingetragen – '
                                 'je HA-Benutzer nur ein HA-Gerät')
            seen_ha[t['ha_benutzer']] = t['nummer']

    # Anschlüsse (früher Typ „extern“) sind keine Teilnehmer: Video-Wunsch an die externen Ziele weitergeben, Zeile entfernen
    trunks = [t for t in teilnehmer if t['typ'] == 'extern']
    teilnehmer = [t for t in teilnehmer if t['typ'] != 'extern']
    for tr in trunks:
        if tr['faehigkeiten']['video_im_anruf']:
            for t in teilnehmer:
                if t['typ'] == 'extern_ziel' and tr['endpoint'] in (t['endpoint'], t['eingang']):
                    t['faehigkeiten']['video_im_anruf'] = True
    dropped = {tr['endpoint'] for tr in trunks if tr['endpoint']}

    wege = []
    items = model.get('wege') or []
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError('Rufgruppen ungültig (maximal 100)')
    known = {ref_of(t) for t in teilnehmer if ref_of(t)}
    # Externe Ziele bleiben in Wegen gültig, wenn sie später eine Nummer bekommen (oder verlieren)
    alias = {('sip:' + t['sip_adresse']): ref_of(t) for t in teilnehmer if t['sip_adresse']}
    alias.update({t['nummer']: ref_of(t) for t in teilnehmer if t['nummer']})
    used_numbers = {t['nummer'] for t in teilnehmer if t['nummer']}
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Rufgruppe {index} ist kein Objekt')
        norm = lambda refs: list(dict.fromkeys(alias.get(r, r) for r in (str(x).strip() for x in refs or []) if r))
        von = [r for r in norm(item.get('von')) if r not in dropped]
        ziele = [r for r in norm(item.get('ziele')) if r not in dropped]
        for ref in von + ziele:
            if ref not in known:
                raise ValueError(f'Rufgruppe {index}: „{ref}“ ist kein Teilnehmer der Anlage')
        try:
            zeit = int(item.get('klingelzeit', 20))
        except (TypeError, ValueError):
            raise ValueError(f'Rufgruppe {index}: Klingelzeit ungültig') from None
        if not 5 <= zeit <= 300:
            raise ValueError(f'Rufgruppe {index}: Klingelzeit 5–300 Sekunden')
        rufnummer = str(item.get('nummer') or '').strip()
        if rufnummer:
            if not RE_NUMMER.fullmatch(rufnummer):
                raise ValueError(f'Rufgruppe {index}: Rufnummer nur Ziffern (2–8)')
            if rufnummer in used_numbers:
                raise ValueError(f'Rufgruppe {index}: Rufnummer {rufnummer} ist schon vergeben')
            used_numbers.add(rufnummer)
        kontexte = [str(c).strip() for c in (item.get('kontexte') or []) if re.fullmatch(r'[A-Za-z0-9_.+-]{1,80}', str(c).strip())][:10]
        wege.append({'name': _text(item.get('name'), f'Name von Rufgruppe {index}', required=True), 'nummer': rufnummer,
                     'von': von, 'ziele': ziele, 'klingelzeit': zeit, 'kontexte': kontexte,
                     'ersetzen': bool(item.get('ersetzen')), 'mitglieder_rufen': bool(item.get('mitglieder_rufen'))})
    callable_refs = {t['nummer'] for t in teilnehmer if t['typ'] in ('ha_geraet', 'sip_telefon', 'tuerstation') and t['nummer']}
    callable_refs |= {w['nummer'] for w in wege if w['nummer']}
    for t in teilnehmer:
        if t['typ'] != 'extern_ziel':
            continue
        refs = list(dict.fromkeys(alias.get(r, r) for r in t['darf_anrufen']))
        for r in refs:
            if r not in callable_refs:
                raise ValueError(f'{t["name"]}: „{r}“ bei „darf anrufen“ ist keine interne Nummer oder Rufgruppen-Nummer')
        if refs and not t['eingang']:
            raise ValueError(f'{t["name"]}: für „darf anrufen“ bitte den Eingang (z. B. linphone-in) wählen')
        t['darf_anrufen'] = refs
    # Erreichbarkeit interner Teilnehmer: nur bekannte Nummern (Unbekanntes fällt weg – die Einschränkung wird dadurch nie lockerer)
    anrufbar = callable_refs | {t['nummer'] for t in teilnehmer if t['typ'] == 'extern_ziel' and t['nummer']}
    intern_refs = {t['nummer'] for t in teilnehmer if t['typ'] in ('ha_geraet', 'sip_telefon', 'tuerstation') and t['nummer']}
    for t in teilnehmer:
        if t.get('anruf_ziele') is not None:
            t['anruf_ziele'] = [r for r in dict.fromkeys(alias.get(r, r) for r in t['anruf_ziele']) if r in anrufbar]
        if t.get('angerufen_von') is not None:
            t['angerufen_von'] = [r for r in dict.fromkeys(alias.get(r, r) for r in t['angerufen_von']) if r in intern_refs]
    # „gleiches Handy wie“: SIP-Konto eines Cloud-Teilnehmers (z. B. Android über Tailscale) – nur auf vorhandene Cloud-Teilnehmer
    cloud_refs = {ref_of(x) for x in teilnehmer if x['typ'] == 'extern_ziel'}
    for t in teilnehmer:
        if t.get('gleiches_geraet') and alias.get(t['gleiches_geraet'], t['gleiches_geraet']) not in cloud_refs:
            t['gleiches_geraet'] = ''
        elif t.get('gleiches_geraet'):
            t['gleiches_geraet'] = alias.get(t['gleiches_geraet'], t['gleiches_geraet'])
    eingaenge = _eingaenge(model.get('eingaenge'))
    for e in eingaenge:      # „weitere IPs“ nur für Geräte ohne eigenen Teilnehmer – IPs der Teilnehmer nicht doppelt führen
        tn_ips = {ip for t in teilnehmer if t['typ'] == 'extern_ziel' and t.get('eingang') == e['name'] for ip in t.get('quell_ips') or []}
        e['quell_ips'] = [ip for ip in e['quell_ips'] if ip not in tn_ips]
    return {'format': FORMAT, 'format_version': FORMAT_VERSION, 'anlage': anlage,
            'teilnehmer': sorted(teilnehmer, key=_sort_key), 'wege': wege, 'eingaenge': eingaenge}


def _qualify_frequency(value):
    """AoR OPTIONS interval: empty uses existing Asterisk value; 0 disables probing."""
    if value is None or str(value).strip() == '':
        return None
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError('Erreichbarkeitsprüfung: Sekunden als ganze Zahl von 0 bis 3600 angeben') from None
    if not 0 <= n <= 3600:
        raise ValueError('Erreichbarkeitsprüfung: Wert muss zwischen 0 und 3600 liegen')
    return n


def _begrenzung(value):
    """None = keine Einschränkung, Liste = nur diese Nummern (leere Liste = niemand)."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError('Erreichbarkeit ungültig')
    return list(dict.fromkeys(str(x).strip() for x in value if str(x).strip()))[:100]


RE_RTSP_PATH = re.compile(r'^/[A-Za-z0-9_./?=&%:+,;~-]{0,200}$')
RE_RTSP_EXTRA = re.compile(r'^[A-Za-z0-9_=&,.#-]{0,120}$')


def _rtsp(value, field):
    """RTSP source without password (the password lives in /data/secrets.json)."""
    if not value:
        return None
    if not isinstance(value, dict):
        raise ValueError(f'{field}: ungültig')
    host = _opt(value.get('host'), RE_HOST, f'{field}: Adresse')
    if not host:
        raise ValueError(f'{field}: Adresse fehlt')
    try:
        port = int(value.get('port') or 554)
    except (TypeError, ValueError):
        raise ValueError(f'{field}: Port ungültig') from None
    if not 1 <= port <= 65535:
        raise ValueError(f'{field}: Port ungültig')
    path = _text(value.get('pfad') or '/', f'{field}: Pfad', 200)
    if not RE_RTSP_PATH.fullmatch(path):
        raise ValueError(f'{field}: Pfad muss mit / beginnen')
    extra = _text(value.get('zusatz'), f'{field}: Zusatz', 120)
    if not RE_RTSP_EXTRA.fullmatch(extra):
        raise ValueError(f'{field}: Zusatz ungültig (z. B. video=h264&audio=pcma)')
    codecs = lambda key: [c for c in (value.get(key) or []) if isinstance(c, str) and re.fullmatch(r'[A-Za-z0-9._-]{1,20}', c)][:6]
    return {'host': host, 'port': port, 'pfad': path, 'benutzer': _text(value.get('benutzer'), f'{field}: Benutzer', 64),
            'zusatz': extra, 'hersteller': _text(value.get('hersteller'), f'{field}: Hersteller', 40),
            'video': codecs('video'), 'audio': codecs('audio')}


def _sort_key(t):
    order = list(TYPEN).index(t['typ'])
    return (0 if t['nummer'] else 1, int(t['nummer']) if t['nummer'] else 0, order, t['name'].lower())


# ---------------------------------------------------------------------------
# PJSIP: Abschnitte mit Vorlagen auflösen und effektive Codecs berechnen
# ---------------------------------------------------------------------------

def parse_conf_sections(files):
    """files: list of (label, content). Returns a list of sections in file order.
    Each section: name, templates, is_template, lines [(key, value)], file."""
    sections = []
    for label, content in files:
        current = None
        for raw in content.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line:
                continue
            head = re.match(r'^\[([^\]]+)\]\s*(?:\(([^)]*)\))?\s*$', line)
            if head:
                opts = [o.strip() for o in (head.group(2) or '').split(',') if o.strip()]
                current = {'name': head.group(1).strip(), 'is_template': '!' in opts,
                           'templates': [o for o in opts if o not in ('!', '+')], 'lines': [], 'file': label}
                sections.append(current)
            elif current is not None and '=' in line:
                key, val = line.split('=', 1)
                current['lines'].append((key.strip().lower(), val.strip()))
    return sections


def _effective_lines(section, templates, depth=0):
    if depth > 8:
        return []
    lines = []
    for name in section['templates']:
        tpl = templates.get(name)
        if tpl:
            lines += _effective_lines(tpl, templates, depth + 1)
    return lines + section['lines']


def _codecs(lines):
    codecs = []
    for key, val in lines:
        if key not in ('allow', 'disallow'):
            continue
        for part in [p.strip().lower() for p in val.split(',') if p.strip()]:
            if key == 'disallow' or part.startswith('!'):
                name = part.lstrip('!')
                codecs = [] if name == 'all' else [c for c in codecs if c != name]
            elif part == 'all':
                codecs.append('all')
            elif part not in codecs:
                codecs.append(part)
    return codecs


def endpoints_from_conf(files):
    """Effective endpoint attributes from config files (templates resolved).
    Later definitions of the same endpoint name (custom after default) win."""
    sections = parse_conf_sections(files)
    templates = {s['name']: s for s in sections if s['is_template']}
    result = {}
    for sec in sections:
        if sec['is_template'] or not RE_ENDPOINT.fullmatch(sec['name']):
            continue
        lines = _effective_lines(sec, templates)
        types = [v.lower() for k, v in lines if k == 'type']
        tpl_hint = any('endpoint' in t.lower() for t in sec['templates'])
        if (types[-1] if types else '') != 'endpoint' and not (not types and tpl_hint):
            continue
        attrs = {}
        for k, v in lines:
            attrs[k] = v
        callerid = attrs.get('callerid', '')
        m = re.match(r'\s*"?([^"<]+)"?\s*(?:<[^>]*>)?', callerid)
        result[sec['name']] = {
            'name': sec['name'], 'file': sec['file'],
            'codecs': _codecs(lines),
            'codecs_bekannt': any(k in ('allow', 'disallow') for k, _ in lines),
            'webrtc': attrs.get('webrtc', '').lower() in ('yes', 'true', '1'),
            'context': attrs.get('context', ''), 'transport': attrs.get('transport', ''),
            'aors': attrs.get('aors', ''), 'auth': attrs.get('auth', ''),
            'outbound_auth': attrs.get('outbound_auth', ''), 'outbound_proxy': attrs.get('outbound_proxy', ''),
            'from_domain': attrs.get('from_domain', ''),
            'display_name': (m.group(1).strip() if (m and callerid) else '')[:100],
        }
    # identify (Zuordnung ankommender Anrufe) und registration (Anmeldung beim Anbieter) gehören zum Endpoint
    for sec in sections:
        if sec['is_template']:
            continue
        lines = _effective_lines(sec, templates)
        attrs = dict(lines)
        typ = (attrs.get('type') or '').lower()
        if typ == 'identify' and attrs.get('endpoint') in result:
            result[attrs['endpoint']]['identify'] = attrs.get('match', '') or True
        elif typ == 'registration':
            ep = attrs.get('endpoint') or (sec['name'] if sec['name'] in result else '')
            if ep in result:
                result[ep]['registration'] = True
    return result


RE_IN_NAME = re.compile(r'(^|[-_])(in|incoming|inbound|eingang)($|[-_])', re.I)
RE_OUT_NAME = re.compile(r'(^|[-_])(out|outgoing|outbound|ausgang|trunk|cloud)($|[-_])', re.I)


def anschluss_rolle(name, ep):
    """Wofür ein externer Anschluss taugt: ('ausgang'|'eingang'|'beide'|'', Begründung).
    Ausgang = Asterisk meldet sich beim Anbieter an (outbound_auth/registration/outbound_proxy).
    Eingang = ankommende Anrufe werden zugeordnet (identify) und landen in einem eigenen Kontext."""
    ep = ep or {}
    aus, ein = [], []
    if ep.get('outbound_auth'):
        aus.append('Anmeldedaten (outbound_auth)')
    if ep.get('registration'):
        aus.append('Registrierung beim Anbieter')
    if ep.get('outbound_proxy'):
        aus.append('outbound_proxy')
    if ep.get('identify'):
        ein.append('Zuordnung ankommender Anrufe (identify)')
    ctx = ep.get('context') or ''
    if ctx and ctx not in ('default', 'from-internal', 'internal'):
        ein.append(f'eigener Kontext „{ctx}“')
    if not aus and RE_OUT_NAME.search(name):
        aus.append('Name')
    if not ein and RE_IN_NAME.search(name):
        ein.append('Name')
    strong_aus = [a for a in aus if a != 'Name']
    strong_ein = [e for e in ein if e != 'Name']
    if strong_aus and strong_ein:
        return 'beide', ', '.join(aus + ein)
    if strong_aus or (aus and not strong_ein):
        return 'ausgang', ', '.join(aus)
    if strong_ein or ein:
        return 'eingang', ', '.join(ein)
    return '', ''


def parse_ami_allow(text):
    """Codecs from `pjsip show endpoint X` output: ' allow : (opus|ulaw|alaw)'."""
    m = re.search(r'^\s*allow\s*:\s*\(([^)]*)\)', text or '', re.M)
    if not m:
        return None
    return [c.strip().lower() for c in m.group(1).split('|') if c.strip()]


def has_video(codecs):
    return any(c in VIDEO_CODECS for c in codecs or [])


# ---------------------------------------------------------------------------
# Import aus der bestehenden Konfiguration
# ---------------------------------------------------------------------------

def _popup_maps(sip_core):
    popup = (sip_core or {}).get('popup_config') or {}
    if not isinstance(popup, dict):
        popup = {}
    common = popup.get('smartify') or {}
    if not isinstance(common, dict):
        common = {}
    legacy = popup.get('extensions') or {}
    mapped = common.get('camera_by_caller') or {}
    return popup, common, (legacy if isinstance(legacy, dict) else {}), (mapped if isinstance(mapped, dict) else {})


def caller_camera(sip_core, nummer):
    """Effective popup settings for a caller, same order as the popup (3.3.x)."""
    _, common, legacy, mapped = _popup_maps(sip_core)
    result = {k: v for k, v in common.items() if k != 'camera_by_caller'}
    sources = []
    if isinstance(legacy.get(nummer), dict):
        result.update(legacy[nummer])
        if any(k in legacy[nummer] for k in ('stream', 'stream_mode', 'mode', 'camera_mode', 'camera_entity')):
            sources.append('extensions')
    if isinstance(mapped.get(nummer), dict):
        result.update(mapped[nummer])
        sources.append('camera_by_caller')
    result['_quellen'] = sources
    return result


def guess_eingang(endpoints, ausgang=''):
    """Inbound endpoint for calls from an external target, e.g. linphone-in next to linphone-cloud."""
    cands = [n for n, ep in (endpoints or {}).items()
             if not RE_NUMMER.fullmatch(n) and n != ausgang and not ep.get('aors') and not ep.get('webrtc') and ep.get('context')]
    prefix = re.split(r'[-_]', ausgang or '')[0].lower()
    cands.sort(key=lambda n: (not (prefix and n.lower().startswith(prefix)), not re.search(r'(^|[-_])in($|[-_])|eingang|inbound', n, re.I), n))
    return cands[0] if cands else ''


def import_from(sip_core, endpoints, streams, camera_map=None, anlage=None, rtsp_sources=None, extern_ziele=None, dialplan=None, gruppen=None):
    """Build a model proposal from what is configured today. Nothing is written.
    rtsp_sources: {stream: {host, port, pfad, benutzer, zusatz}} from the go2rtc config (no passwords)."""
    rtsp_sources = rtsp_sources or {}
    model = leer()
    if anlage:
        model['anlage'].update({k: v for k, v in anlage.items() if k in model['anlage'] and v})
    sip_core = sip_core or {}
    camera_map = camera_map or {}
    teilnehmer, numbers = [], set()
    users = sip_core_users(sip_core)
    sip_video = bool(sip_core.get('sip_video'))
    stream_names = set(streams or {})
    used_streams = set()

    def camera_fields(nummer):
        cam = caller_camera(sip_core, nummer)
        manager = camera_map.get(nummer) or {}
        stream = str(manager.get('stream') or cam.get('stream') or '')
        if stream and not RE_STREAM.fullmatch(stream):
            stream = ''
        return cam, manager, stream

    for user in users:
        nummer = str(user.get('extension') or '').strip()
        if not RE_NUMMER.fullmatch(nummer) or nummer in numbers:
            continue
        numbers.add(nummer)
        cam, manager, stream = camera_fields(nummer)
        if stream:
            used_streams.add(stream)
        mode = str(manager.get('mode') or cam.get('stream_mode') or cam.get('mode') or '')
        teilnehmer.append({
            'nummer': nummer, 'typ': 'ha_geraet',
            'name': str(user.get('display_name') or cam.get('name') or nummer)[:80],
            'ha_benutzer': str(user.get('ha_username') or '')[:80],
            'endpoint': '', 'stream': stream,
            'tuer_entity': str(manager.get('door') or '') if RE_ENTITY.fullmatch(str(manager.get('door') or '')) else '',
            'licht_entity': str(manager.get('light') or '') if RE_ENTITY.fullmatch(str(manager.get('light') or '')) else '',
            'klingel_entity': '',
            'faehigkeiten': {'kamerabild': bool(stream), 'video_im_anruf': sip_video,
                             'ios': mode == 'webrtc', 'tuer_oeffnen': False},
            'notiz': 'SIP Core backup_user – alle übrigen HA-Benutzer' if user.get('_backup') else 'Importiert aus SIP Core',
        })

    for name, ep in sorted((endpoints or {}).items()):
        if name in numbers:
            continue
        if RE_NUMMER.fullmatch(name):
            numbers.add(name)
            cam, manager, stream = camera_fields(name)
            if stream:
                used_streams.add(stream)
            door = str(manager.get('door') or cam.get('door_entity') or '')
            label = (ep.get('display_name') or str(manager.get('label') or '') or name)
            is_door = bool(door) or bool(re.search(r't[üu]r|door|akuvox|2n|klingel', label, re.I))
            teilnehmer.append({
                'nummer': name, 'typ': 'tuerstation' if is_door else 'sip_telefon',
                'name': label[:80], 'ha_benutzer': '', 'endpoint': '', 'stream': stream,
                'tuer_entity': door if RE_ENTITY.fullmatch(door) else '',
                'licht_entity': '', 'klingel_entity': str(manager.get('bell') or '') if RE_ENTITY.fullmatch(str(manager.get('bell') or '')) else '',
                'faehigkeiten': {'kamerabild': bool(stream), 'video_im_anruf': has_video(ep.get('codecs')),
                                 'ios': False, 'tuer_oeffnen': bool(door)},
                'notiz': 'Importiert aus ' + ep.get('file', 'PJSIP'),
            })

    for z in extern_ziele or []:
        if z['nummer'] in numbers or z['endpoint'] not in (endpoints or {}):
            continue
        numbers.add(z['nummer'])
        teilnehmer.append({
            'nummer': z['nummer'], 'typ': 'extern_ziel', 'name': z['name'][:80], 'ha_benutzer': '', 'endpoint': z['endpoint'],
            'sip_adresse': z['sip_adresse'], 'stream': '', 'tuer_entity': '', 'licht_entity': '', 'klingel_entity': '',
            'faehigkeiten': {'kamerabild': False, 'video_im_anruf': has_video((endpoints.get(z['endpoint']) or {}).get('codecs')),
                             'ios': False, 'tuer_oeffnen': False},
            'notiz': 'Aus eigenem Dialplan-Eintrag erkannt',
            'eingang': guess_eingang(endpoints, z['endpoint']),
        })
    internal = {t['nummer'] for t in teilnehmer if t['typ'] in ('ha_geraet', 'sip_telefon', 'tuerstation')}
    seen_ha = set()
    for t in teilnehmer:
        if t['typ'] == 'ha_geraet' and t['ha_benutzer']:
            if t['ha_benutzer'] in seen_ha:
                t['notiz'] = f'HA-Benutzer „{t["ha_benutzer"]}“ war in SIP Core doppelt vergeben – bitte hier den richtigen wählen'
                t['ha_benutzer'] = ''
            else:
                seen_ha.add(t['ha_benutzer'])
    for t in teilnehmer:
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            ctx = (endpoints.get(t['eingang']) or {}).get('context') or t['eingang']
            t['darf_anrufen'] = sorted(n for n, ctxs in (dialplan or {}).items() if ctx in ctxs and n in internal)
    for t in teilnehmer:
        if t['stream'] in rtsp_sources:
            t['rtsp'] = rtsp_sources[t['stream']]
    for stream in sorted((stream_names | set(rtsp_sources)) - used_streams):
        if not RE_STREAM.fullmatch(stream):
            continue
        teilnehmer.append({
            'nummer': '', 'typ': 'kamera', 'name': stream, 'ha_benutzer': '', 'endpoint': '', 'stream': stream,
            'tuer_entity': '', 'licht_entity': '', 'klingel_entity': '',
            'faehigkeiten': {'kamerabild': True, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False},
            'notiz': 'RTSP-Kamera aus go2rtc' if stream in rtsp_sources else 'go2rtc-Stream ohne SIP-Nummer',
            'rtsp': rtsp_sources.get(stream),
        })
    # vorhandene einfache Rufgruppen → Wege (Ziele unbekannter Linphone-Adressen werden als externe Ziele angelegt)
    wege = []
    used = {t['nummer'] for t in teilnehmer if t['nummer']}
    for g in gruppen or []:
        if g['nummer'] in used:
            continue
        ziele = []
        for z in g['ziele']:
            if z.get('nummer'):
                if z['nummer'] in used:
                    ziele.append(z['nummer'])
                continue
            hit = next((t for t in teilnehmer if t['typ'] == 'extern_ziel' and t.get('sip_adresse') == z['adresse']), None)
            if not hit and z['endpoint'] in (endpoints or {}):
                hit = {'nummer': '', 'typ': 'extern_ziel', 'name': z['adresse'].split('@')[0][:80], 'ha_benutzer': '', 'endpoint': z['endpoint'],
                       'sip_adresse': z['adresse'], 'eingang': guess_eingang(endpoints, z['endpoint']), 'stream': '', 'tuer_entity': '',
                       'licht_entity': '', 'klingel_entity': '',
                       'faehigkeiten': {'kamerabild': False, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False},
                       'notiz': f'Ziel aus Rufgruppe {g["nummer"]}'}
                teilnehmer.append(hit)
            if hit:
                ziele.append('sip:' + hit['sip_adresse'] if not hit['nummer'] else hit['nummer'])
        if ziele:
            wege.append({'name': g['name'][:80], 'nummer': g['nummer'], 'von': [], 'ziele': ziele, 'klingelzeit': g['klingelzeit'],
                         'kontexte': g['kontexte'], 'ersetzen': True, 'mitglieder_rufen': False})
            used.add(g['nummer'])
    model['teilnehmer'] = teilnehmer
    model['wege'] = wege
    # Eingänge mit Quell-IPs (z. B. Tailscale) samt bisheriger Freigaben in ihrem Kontext
    import inbound_routes
    for name, ep in sorted((endpoints or {}).items()):
        match = ep.get('identify')
        if not match or match is True or anschluss_rolle(name, ep)[0] not in ('eingang', 'beide'):
            continue
        try:
            ips = inbound_routes.normal_ips([x.strip() for x in str(match).split(',') if x.strip()])
        except ValueError:
            continue                                   # Hostnamen oder Netzbereiche: nicht verwalten
        ctx = ep.get('context') or name
        freigaben = sorted(n for n, ctxs in (dialplan or {}).items() if ctx in ctxs)
        model['eingaenge'].append({'name': name, 'quell_ips': ips, 'uebernommen': False, 'freigaben': freigaben})
    freigaben = {e['name']: e.pop('freigaben') for e in model['eingaenge']}
    result = validate(model)
    for e in result['eingaenge']:            # nur im Vorschlag: bisherige Freigaben (zum Übernehmen in „darf anrufen“)
        e['freigaben'] = freigaben.get(e['name'], [])
    return result


# ---------------------------------------------------------------------------
# Prüfbericht
# ---------------------------------------------------------------------------

def _row(rows, level, bereich, titel, detail='', beheben='', bezug='', aktion=''):
    rows.append({'level': level, 'bereich': bereich, 'titel': titel, 'detail': detail,
                 'beheben': beheben, 'bezug': bezug, 'aktion': aktion})


def pruefbericht(model, ctx):
    """Cross-layer checks. ctx keys (each optional, None = nicht verfügbar):
    asterisk_dir (bool), endpoints {name: ep}, ami_codecs {name: [codecs]},
    sip_core (dict) / sip_core_error (str), streams {name: {...go2rtc}} / go2rtc_error,
    cors (True/False/None), ami_error (str), registered {name: contacts:int}.
    """
    rows = []
    t_all = model.get('teilnehmer', [])
    endpoints = ctx.get('endpoints') or {}
    ami_codecs = ctx.get('ami_codecs') or {}
    sip_core = ctx.get('sip_core')
    streams = ctx.get('streams')
    anlage = model.get('anlage', {})

    # 1 Voraussetzungen
    B = 'Voraussetzungen'
    if ctx.get('asterisk_dir'):
        _row(rows, 'ok', B, 'Asterisk-Konfiguration gefunden')
    else:
        _row(rows, 'error', B, 'Asterisk-Konfiguration nicht gefunden',
             'Der Ordner des Asterisk-Add-ons ist nicht eingebunden.',
             'In den App-Optionen asterisk_slug prüfen (Standard 3e533915_asterisk).')
    if sip_core is None:
        _row(rows, 'error', B, 'SIP Core nicht lesbar', ctx.get('sip_core_error', ''),
             'SIP-Core-Integration installiert? Add-on mit HA-API-Zugriff neu bauen.')
    else:
        _row(rows, 'ok', B, f'SIP Core erreichbar ({len(sip_core.get("users") or [])} Benutzer)')
    if streams is None:
        _row(rows, 'warn', B, 'go2rtc nicht erreichbar', ctx.get('go2rtc_error', ''),
             'In den App-Optionen go2rtc_url setzen, z. B. http://192.168.2.65:1984.')
    else:
        _row(rows, 'ok', B, f'go2rtc erreichbar ({len(streams)} Streams)')
    if ctx.get('ami_error'):
        err = ctx['ami_error']
        denied = bool(re.search(r'verweigert|authentic|acl', err, re.I))
        _row(rows, 'warn' if denied else 'info', B, 'AMI nicht verfügbar – Codecs nur aus Dateien, kein Live-Status', err,
             ('Asterisk lehnt den Manager ab (oft die IP-Freigabe des Benutzers). „AMI-Zugang einrichten“ legt einen eigenen Benutzer an.'
              if denied else 'AMI-Zugang einrichten oder Benutzer und Passwort in den App-Optionen eintragen.'),
             aktion='ami_einrichten')
    elif ctx.get('registered') is not None:
        _row(rows, 'ok', B, 'AMI erreichbar (Live-Status aktiv)')
    if not t_all:
        _row(rows, 'warn', 'Modell', 'Noch keine Teilnehmer im Modell',
             'Ohne Modell kann der Manager nichts gegeneinander prüfen.',
             'Unter „Anlage“ auf „Aus bestehender Konfiguration übernehmen“ klicken.')
        return _summary(rows)

    # 2 Nummernplan
    B = 'Nummernplan'
    lo, hi = anlage.get('nummer_von'), anlage.get('nummer_bis')
    for t in t_all:
        n = t['nummer']
        if n and lo and hi and not int(lo) <= int(n) <= int(hi) and t['typ'] != 'extern_ziel':
            _row(rows, 'info', B, f'{n} {t["name"]} liegt außerhalb des Nummernbereichs {lo}–{hi}',
                 bezug=n)

    # 3 Teilnehmer und Endpoints
    B = 'Teilnehmer'
    users = {str(u.get('extension')): u for u in sip_core_users(sip_core)}
    for t in t_all:
        n, name = t['nummer'], t['name']
        label = f'{n} {name}'.strip()
        ep_name = n if t['typ'] in ('ha_geraet', 'sip_telefon', 'tuerstation') else t['endpoint']
        if t['typ'] == 'extern_ziel':
            label = f'{n} {name}'.strip() + f' ({t["sip_adresse"]})'
        ep = endpoints.get(ep_name) if ep_name else None
        if t['typ'] == 'sip_telefon' and t.get('gleiches_geraet') and not t.get('realm') and not (model.get('anlage') or {}).get('tailscale_ip'):
            _row(rows, 'warn', B, f'{label}: Tailscale-IP von HA fehlt',
                 'Das Handy meldet sich über Tailscale an; ohne die Tailscale-IP von HA kann der Manager den Anmelde-Bereich (Realm) nicht setzen – '
                 'Linphone meldet dann „Failed to authenticate“.', 'Unter Anlage die Tailscale-IP von HA eintragen (Tailscale-App, Gerät „homeassistant“).', n)
        if t['typ'] == 'extern_ziel' and t.get('eingang'):
            eg = next((e for e in eingaenge_effektiv(model) if e['name'] == t['eingang']), None)
            if eg and not eg['quell_ips']:
                _row(rows, 'warn', B, f'{label}: Eingang „{eg["name"]}“ hat keine Quell-IP',
                     'Ohne Quell-IP ordnet Asterisk keinen Anruf diesem Eingang zu – Anrufe von außen kommen nicht an.',
                     'Beim Teilnehmer die IP des Handys eintragen (z. B. Tailscale-IP).', t['eingang'])
        if t['typ'] == 'extern_ziel':
            for feld, soll, text in (('endpoint', 'ausgang', 'Ausgang'), ('eingang', 'eingang', 'Eingang')):
                nm = t.get(feld) or ''
                if nm and nm in endpoints:
                    rolle, grund = anschluss_rolle(nm, endpoints[nm])
                    if rolle and rolle not in (soll, 'beide'):
                        _row(rows, 'warn', B, f'{label}: „{nm}“ ist eher ein {"Eingang" if rolle == "eingang" else "Ausgang"} als ein {text}',
                             f'Erkannt an: {grund}. '
                             + ('Ohne Anmeldung beim Anbieter werden Anrufe darüber abgewiesen.' if soll == 'ausgang'
                                else 'Freigaben („darf anrufen“) landen sonst im falschen Kontext.'),
                             f'Beim Teilnehmer einen passenden {text} wählen.', n or ep_name)
        if t['typ'] == 'ha_geraet' and sip_core is not None and n in users and t.get('ha_benutzer') \
                and str(users[n].get('ha_username') or '') != t['ha_benutzer']:
            _row(rows, 'info', B, f'{label}: HA-Benutzer in SIP Core ist „{users[n].get("ha_username") or "–"}“, im Modell „{t["ha_benutzer"]}“',
                 '', 'Mit „Erzeugen & Übernehmen“ wird SIP Core angepasst.', n)
        if t['typ'] == 'ha_geraet' and sip_core is not None and n not in users:
            _row(rows, 'error', B, f'{label}: kein SIP-Core-Benutzer',
                 'Das HA-Gerät ist im Modell, aber SIP Core kennt die Nummer nicht.',
                 'SIP-Core-Benutzer anlegen (Reiter „Aktive Konfiguration & Teilnehmer“).', n)
        if ep_name and t['typ'] != 'kamera':
            live = ctx.get('registered')
            if not ep and live is not None and ep_name in live:
                pass                                    # zur Laufzeit erzeugt, Asterisk kennt ihn
            elif not ep and endpoints:
                runtime = t['typ'] == 'ha_geraet' and live is None
                _row(rows, 'warn' if runtime else 'error', B, f'{label}: kein Asterisk-Endpoint gefunden',
                     f'In den Asterisk-Dateien gibt es keinen Endpoint „{ep_name}“.'
                     + (' Das Asterisk-Add-on erzeugt SIP-Core-Endpoints teils erst zur Laufzeit; mit AMI lässt sich das prüfen.' if runtime else ''),
                     'Nebenstelle im Reiter „Vorhandene & neue Nebenstellen“ anlegen.', n or ep_name)
            elif ep and t['typ'] == 'ha_geraet' and ep['file'].startswith('default/'):
                addon = ctx.get('asterisk_addon') or {}
                opts = ', '.join(f'{k}: {v}' for k, v in addon.items()) if addon else ''
                _row(rows, 'info', B, f'{label}: Endpoint wird vom Asterisk-Add-on erzeugt',
                     'Der Manager legt ihn nicht doppelt an.' + (f' Add-on-Optionen: {opts}.' if opts else ''),
                     'Für eigene Codecs je Gerät die automatische Erzeugung im Asterisk-Add-on abschalten; dann erzeugt der Manager den Endpoint.'
                     if t['faehigkeiten']['video_im_anruf'] else '', n)
        reg = (ctx.get('registered') or {})
        if ep_name and ctx.get('registered') is not None and t['typ'] in ('sip_telefon', 'tuerstation'):
            if not reg.get(ep_name):
                _row(rows, 'warn', B, f'{label}: nicht angemeldet',
                     'Asterisk meldet keinen Kontakt für diese Nebenstelle.',
                     'Gerät einschalten, Zugangsdaten und Netzwerk prüfen.', n)

        # 4 Video im Anruf
        if t['faehigkeiten']['video_im_anruf'] and ep_name:
            codecs = ami_codecs.get(ep_name)
            source = 'Asterisk (live)'
            if codecs is None and ep and ep['codecs_bekannt']:
                codecs, source = ep['codecs'], 'Konfigurationsdatei'
            if codecs is None:
                _row(rows, 'warn', 'Video', f'{label}: Codecs nicht ermittelbar',
                     'Weder AMI noch Konfiguration liefern die erlaubten Codecs.',
                     'AMI einrichten oder „pjsip show endpoint ' + ep_name + '“ in der Konsole prüfen.', n or ep_name)
            elif not has_video(codecs):
                addon = ctx.get('asterisk_addon') or {}
                video_keys = [k for k in addon if 'video' in k.lower()]
                hint = (f'Im Asterisk-Add-on die Option „{video_keys[0]}“ einschalten und das Add-on neu starten'
                        if video_keys else 'Im Asterisk-Add-on Video aktivieren (falls angeboten)')
                fix = (hint + ' – oder die automatische Erzeugung abschalten, dann setzt der Manager die Codecs (Erzeugen & Übernehmen).'
                       if t['typ'] == 'ha_geraet' else
                       f'Im Endpoint „{ep_name}“ allow um vp8,h264 ergänzen, dann pjsip reload.')
                _row(rows, 'error', 'Video', f'{label}: Video SIP gewünscht, Endpoint erlaubt nur Audio',
                     f'Erlaubt ({source}): {", ".join(codecs) or "keine"}. Asterisk entfernt das Video aus dem Anruf.', fix, n or ep_name)
            else:
                _row(rows, 'ok', 'Video', f'{label}: Video-Codecs vorhanden ({", ".join(c for c in codecs if c in VIDEO_CODECS)})', bezug=n or ep_name)
            if t['typ'] == 'ha_geraet' and sip_core is not None and not sip_core.get('sip_video'):
                _row(rows, 'error', 'Video', f'{label}: Video SIP gewünscht, aber sip_video: false',
                     'SIP Core bietet dann im Anruf kein Video an.', 'In SIP Core sip_video: true setzen, App am Gerät neu laden.', n)

    # 5 Kameras und Popup
    B = 'Kamera'
    ios_present = any(t['faehigkeiten']['ios'] for t in t_all)
    popup = (sip_core or {}).get('popup_config') or {}
    publishers = []
    for t in t_all:
        if not t['faehigkeiten']['kamerabild'] or not t['stream']:
            continue
        n, s = t['nummer'], t['stream']
        label = f'{n} {t["name"]}'.strip()
        info = (streams or {}).get(s) if streams is not None else None
        if streams is not None and info is None:
            _row(rows, 'error', B, f'{label}: Stream „{s}“ fehlt in go2rtc',
                 'go2rtc kennt keinen Stream mit diesem Namen.',
                 f'In der go2rtc-Konfiguration ergänzen: „{s}: []“ (HA-Gerät) bzw. „{s}: - rtsp://…“.', n or s)
        elif info is not None:
            producers = info.get('producers') or []
            active = [p for p in producers if p.get('bytes_recv') or p.get('receivers') or p.get('medias')]
            if t['typ'] == 'ha_geraet':
                publishers.append(t)
                if not active:
                    _row(rows, 'warn', B, f'{label}: Stream „{s}“ hat keinen Sender',
                         'Das Gerät publiziert gerade nicht.',
                         f'Am Gerät in Browser Mod die Browser-ID exakt auf „{s}“ setzen, „Enable go2rtc publishing“ aktivieren, Gerät wach halten.', n)
                else:
                    _row(rows, 'ok', B, f'{label}: Kamerastream „{s}“ in go2rtc aktiv',
                         'Die Stream-Aktivität bestätigt nicht, dass dieses HA-Gerät selbst Video sendet.', bezug=n)
            elif producers:
                _row(rows, 'ok', B, f'{label}: Stream „{s}“ eingerichtet', bezug=n or s)
            else:
                _row(rows, 'warn', B, f'{label}: Stream „{s}“ ohne Quelle', 'Der Stream hat keine Quelle.',
                     'RTSP-Adresse in der go2rtc-Konfiguration eintragen.', n or s)
        cam_src = t.get('rtsp')
        if cam_src:
            if cam_src.get('benutzer') and ctx.get('rtsp_passwords') is not None and s not in ctx['rtsp_passwords']:
                _row(rows, 'warn', B, f'{label}: Passwort der RTSP-Kamera fehlt im Manager',
                     'Ohne Passwort kann der Manager den Stream nicht erzeugen.', 'Unter „Kameras finden“ testen und Passwort speichern.', s)
            if any(c in ('H265', 'HEVC') for c in cam_src.get('video') or []):
                _row(rows, 'warn', B, f'{label}: Kamera liefert H.265',
                     'Browser und die HA-App spielen H.265 meist nicht ab (schwarzes Bild).',
                     f'Nebenstream mit H.264 wählen oder in der Kamera auf H.264 umstellen.', s)
        if n and sip_core is not None:
            cam = caller_camera(sip_core, n)
            if not cam['_quellen'] and cam.get('stream') != s:
                _row(rows, 'error', B, f'{label}: Popup zeigt beim Anruf kein Bild',
                     'Für diese Nummer gibt es keine Kamera-Zuordnung im Popup.',
                     'Im Reiter „Kameras pro Anrufer“ eine Zuordnung anlegen.', n)
            elif cam.get('stream') and cam.get('stream') != s:
                _row(rows, 'warn', B, f'{label}: Popup nutzt „{cam.get("stream")}“, Modell „{s}“', '',
                     'Zuordnung im Reiter „Kameras pro Anrufer“ anpassen.', n)
            if cam.get('camera_mode') == 'hidden':
                _row(rows, 'warn', B, f'{label}: camera_mode „hidden“ – Bild wird nie gezeigt', '',
                     'camera_mode auf „always“ oder „auto“ stellen.', n)
            mode = str(cam.get('stream_mode') or cam.get('mode') or 'mse')
            if ios_present and mode != 'webrtc':
                _row(rows, 'warn', B, f'{label}: Wiedergabe „{mode}“, im System gibt es iOS-Geräte',
                     'Auf iPhone und iPad bleibt das Bild mit MSE oft schwarz.', 'Wiedergabemodus auf webrtc stellen.', n)
            if set(cam['_quellen']) == {'extensions', 'camera_by_caller'}:
                _row(rows, 'info', B, f'{label}: Kamera an zwei Stellen eingetragen',
                     'extensions und smartify.camera_by_caller – camera_by_caller gewinnt.', '', n)
    for t in t_all:
        if t['typ'] == 'kamera' and t['stream'] and not any(x['typ'] != 'kamera' and x['stream'] == t['stream'] for x in t_all):
            _row(rows, 'info', B, f'Kamera „{t["name"]}“ ({t["stream"]}) wird von keinem Teilnehmer genutzt',
                 'Ihr Bild erscheint nur, wenn ein Teilnehmer mit diesem Stream anruft.',
                 f'Beim passenden Teilnehmer (z. B. der Türstation) als Stream „{t["stream"]}“ eintragen und „Video HA“ anhaken.', t['stream'])
    if any(t['faehigkeiten']['kamerabild'] for t in t_all) and sip_core is not None:
        comp = (sip_core or {}).get('popup_override_component')
        if comp != POPUP_COMPONENT:
            _row(rows, 'error', B, 'Smartify-Popup ist in SIP Core nicht aktiv',
                 f'popup_override_component ist „{comp or "nicht gesetzt"}“.',
                 f'In SIP Core popup_override_component: {POPUP_COMPONENT} setzen.')
        if not isinstance(popup, dict) or not popup.get('auto_open'):
            _row(rows, 'info', B, 'Popup öffnet sich nicht automatisch', 'popup_config.auto_open ist nicht gesetzt.',
                 'auto_open: true setzen, wenn das Popup beim Klingeln erscheinen soll.')

    # 6 Netzwerk für Geräte-Kameras (Browser Mod publishing)
    B = 'Netzwerk'
    if publishers:
        url = anlage.get('go2rtc_https_url')
        if not url:
            _row(rows, 'error', B, 'Keine HTTPS-Adresse für go2rtc hinterlegt',
                 'HA-Geräte, die über HTTPS geöffnet werden, können nicht an http://…:1984 senden (Mixed Content).',
                 'Tailscale Serve einrichten (Befehl unter „Anlage“) und die Adresse dort eintragen; '
                 'dieselbe Adresse in Browser Mod → Frontend Settings → go2rtc base URL.')
        else:
            _row(rows, 'ok', B, f'HTTPS-Adresse für go2rtc: {url}',
                 'Aus dem Add-on nicht erreichbar prüfbar; am Gerät im Browser öffnen.')
        cors = ctx.get('cors')
        if cors is False:
            _row(rows, 'error', B, 'go2rtc erlaubt keine Anfragen anderer Adressen (CORS)',
                 'Ohne api.origin blockiert der Browser die Übertragung.',
                 'In der go2rtc-Konfiguration ergänzen:  api:  origin: "*"  – dann go2rtc neu starten.')
        elif cors is True:
            _row(rows, 'ok', B, 'go2rtc: CORS aktiv (api.origin)')

    # 7 Wege
    B = 'Rufgruppen'
    doors = [t for t in t_all if t['typ'] == 'tuerstation']
    by_ref = {ref_of(t): t for t in t_all}
    dial = ctx.get('dialplan')            # {nummer: [kontexte]} aus extensions.conf, None = unbekannt
    if not model.get('wege'):
        if doors:
            _row(rows, 'info', B, 'Noch keine Rufgruppen im Modell', 'Ohne Rufgruppe klingelt bei einem Druck auf die Klingel nichts.',
                 'Unter „Start → Rufgruppen-Manager“ anlegen.')
    else:
        sources = {ref for w in model['wege'] for ref in w['von']}
        for d in doors:
            if d['nummer'] not in sources:
                _row(rows, 'warn', B, f'{d["nummer"]} {d["name"]}: keine Rufgruppe festgelegt',
                     'Für diese Türstation ist nicht beschrieben, wo es klingelt.', 'Im Rufgruppen-Manager eine Gruppe anlegen und die Türstation als Anrufer hineinziehen.', d['nummer'])
        for w in model['wege']:
            label = f'Rufgruppe „{w["name"]}“'
            if not w['ziele']:
                _row(rows, 'warn', B, f'{label}: keine Ziele', 'Es würde nirgends klingeln.', 'Ziele auswählen.')
                continue
            if not w.get('nummer'):
                _row(rows, 'warn', B, f'{label}: keine Rufnummer',
                     'Ohne Rufnummer wird die Rufgruppe nicht in den Dialplan geschrieben.', 'Rufnummer eintragen, z. B. 600.')
                continue
            names = ', '.join(by_ref[r]['name'] for r in w['ziele'] if r in by_ref)
            if dial is not None and w['nummer'] not in dial:
                _row(rows, 'warn', B, f'{label} ({w["nummer"]}): noch nicht im Dialplan',
                     f'Ziele: {names}.', 'Unter „Erzeugen & Übernehmen“ den Dialplan übernehmen.', w['nummer'])
            else:
                _row(rows, 'ok', B, f'{label}: {w["nummer"]} → {names}', bezug=w['nummer'])
            for ref in w['von']:
                t = by_ref.get(ref)
                if t and t['typ'] == 'extern_ziel' and not t.get('eingang'):
                    _row(rows, 'warn', B, f'{label}: {t["name"]} hat keinen Eingang',
                         'Ohne Eingang weiß der Manager nicht, in welchem Kontext Anrufe von diesem Teilnehmer ankommen.',
                         'Beim Teilnehmer den Eingang (z. B. linphone-in) wählen.')
                if t and t['typ'] in ('tuerstation', 'sip_telefon'):
                    _row(rows, 'info', B, f'{t["nummer"]} {t["name"]}: am Gerät {w["nummer"]} als Rufziel eintragen',
                         'Die Türstation bzw. das Telefon muss diese Nummer wählen, damit die Rufgruppe greift.', bezug=t['nummer'])
    for t in t_all:
        if t['typ'] == 'extern_ziel' and t['nummer'] and dial is not None and t['nummer'] not in dial:
            _row(rows, 'info', B, f'{t["nummer"]} {t["name"]}: Direktwahl noch nicht im Dialplan', '',
                 'Unter „Erzeugen & Übernehmen“ den Dialplan übernehmen.', t['nummer'])
    return _summary(rows)


def _summary(rows):
    order = {'error': 0, 'warn': 1, 'info': 2, 'ok': 3}
    count = {k: sum(1 for r in rows if r['level'] == k) for k in order}
    return {'zusammenfassung': count, 'zeilen': sorted(rows, key=lambda r: order[r['level']])}


def tailscale_serve_anleitung(port=8443, go2rtc_port=1984):
    return [
        'Advanced SSH & Web Terminal öffnen (Protection mode aus).',
        "Container-Namen ermitteln:  docker ps --format '{{.Names}}' | grep -i tail",
        f'Freigabe setzen (NAME = Ausgabe von oben):  docker exec NAME /opt/tailscale serve --bg --https={port} http://127.0.0.1:{go2rtc_port}',
        'Kontrolle:  docker exec NAME /opt/tailscale serve status',
        f'Adresse https://<name>.<tailnet>.ts.net:{port} hier eintragen und in Browser Mod als go2rtc base URL.',
    ]
