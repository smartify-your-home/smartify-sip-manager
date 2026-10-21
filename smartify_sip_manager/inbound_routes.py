"""Conservative tabular manager for trusted-IP PJSIP inbound routes.

No AMI, password or Asterisk reload. Never edits unknown contexts or config files.
The caller supplies storage / PJSIP APIs so the same safety guards as the
existing manager apply to all reads and writes.
"""
import ipaddress
import re

PROFILE = re.compile(r'^[a-z][a-z0-9_-]{1,39}$')
NUMBER = re.compile(r'^\d{2,6}$')
CTX_HEADER = re.compile(r'(?m)^[ \t]*\[([^\]\r\n]+)\]\s*(?:;[^\r\n]*)?$', re.I)
STEP = re.compile(r'(?i)^\s*(?:exten\s*=>\s*(\d{2,6})\s*,\s*1\s*,\s*NoOp\([^\r\n;]*\)|same\s*=>\s*n\s*,\s*(?:Dial\(\$\{PJSIP_DIAL_CONTACTS\(\d{2,6}\)\},\d{1,3}\)|Hangup\(\)))\s*$')


def normal_ips(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 20:
        raise ValueError('1–20 IP-Adressen von vertrauenswürdigen externen Geräten eingeben')
    out = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('Ungültige IP-Adresse')
        try:
            network = ipaddress.ip_network(value.strip(), strict=False)
        except ValueError:
            raise ValueError('Keine gültige IP-Adresse: ' + str(value)[:55]) from None
        if network.prefixlen != network.max_prefixlen or network.is_unspecified or network.is_multicast:
            raise ValueError('Nur einzelne Quell-IPs (/32 bzw. /128), keine ganzen Netzbereiche zulassen')
        # For an IP-based, passwordless endpoint never accept all-network/broadcast.
        entry = network.with_prefixlen
        if entry in out:
            raise ValueError('Quell-IP mehrfach angegeben: ' + entry)
        out.append(entry)
    return out


def valid_targets(values, available):
    if not isinstance(values, list) or not 1 <= len(values) <= 20:
        raise ValueError('1–20 erlaubte bestehende Asterisk-Nebenstellen auswählen')
    if any(not isinstance(v, str) or not NUMBER.fullmatch(v) for v in values) or len(set(values)) != len(values):
        raise ValueError('Ungültige oder doppelte Zielnummer')
    missing = sorted(set(values) - set(available))
    if missing:
        raise ValueError('Keine vorhandene Asterisk-Nebenstelle: ' + ', '.join(missing))
    return values


def list_sections(text):
    heads = list(CTX_HEADER.finditer(text))
    return [{'name': h.group(1).strip(), 'start': h.start(),
             'end': heads[i+1].start() if i+1 < len(heads) else len(text),
             'raw': text[h.start():heads[i+1].start() if i+1 < len(heads) else len(text)]}
            for i, h in enumerate(heads)]


def inspect_context(text, name):
    found = [s for s in list_sections(text) if s['name'] == name]
    if not found:
        return None
    if len(found) != 1:
        raise ValueError('Dialplan-Kontext ['+name+'] mehrfach in der Datei definiert')
    s = found[0]
    lines = s['raw'].splitlines()[1:]
    active = [l.strip() for l in lines if l.strip() and not l.lstrip().startswith(';')]
    numbers = []
    for i in range(0, len(active), 3):
        chunk = active[i:i+3]
        if len(chunk) != 3:
            raise ValueError('Kontext ['+name+'] enthält unbekannte Dialplan-Schritte – nur Datei-Editor')
        h = re.fullmatch(r'exten\s*=>\s*(\d{2,6})\s*,\s*1\s*,\s*NoOp\([^\r\n;]*\)', chunk[0], re.I)
        if not h:
            raise ValueError('Kontext ['+name+'] enthält nicht unterstützte Regeln – nur Datei-Editor')
        n = h.group(1)
        if not re.fullmatch(r'same\s*=>\s*n\s*,\s*Dial\(\$\{PJSIP_DIAL_CONTACTS\('+n+r'\)\},\d{1,3}\)', chunk[1], re.I) or not re.fullmatch(r'same\s*=>\s*n\s*,\s*Hangup\(\)', chunk[2], re.I):
            raise ValueError('Kontext ['+name+'] hat andere Dial-Ziele oder Aktionen – nur Datei-Editor')
        numbers.append(n)
    if len(set(numbers)) != len(numbers):
        raise ValueError('Dialplan enthält doppelte Zielnummern in ['+name+']')
    # Comment lines and whitespace are preserved rather than silently discarded.
    comments = [l for l in lines if l.lstrip().startswith(';')]
    return {'section': s, 'targets': numbers, 'comments': comments}


def render_dialplan(name, targets, seconds, comments=()):
    lines = ['['+name+']']
    lines.extend(comments)
    for number in targets:
        lines.extend(('exten => '+number+',1,NoOp(Externer SIP-Zugang '+name+' zu '+number+')',
                      ' same => n,Dial(${PJSIP_DIAL_CONTACTS('+number+')},'+str(seconds)+')',
                      ' same => n,Hangup()', ''))
    return '\n'.join(lines).rstrip() + '\n'


def render_pjsip(name, ips, transport='transport-udp'):
    return (f'[{name}]\n'
            'type=endpoint\n'
            f'transport={transport}\n'
            f'context={name}\n'
            'disallow=all\nallow=alaw,ulaw\n'
            'direct_media=no\nforce_rport=yes\nrewrite_contact=yes\nrtp_symmetric=yes\n\n'
            f'[{name}-identify]\n'
            'type=identify\n'
            f'endpoint={name}\n'
            'match='+','.join(ips)+'\n')


def _append(text, fragment):
    return text.rstrip() + ('\n\n' if text.strip() else '') + fragment.rstrip() + '\n'


def _replace_many(text, changes):
    for start, end, new in sorted(changes, key=lambda c: c[0], reverse=True):
        text = text[:start] + new + text[end:]
    return text


def _raw_matches(block):
    out = []
    for match in re.finditer(r'(?im)^\s*match\s*=\s*([^;\r\n]+)', block['raw']):
        out.extend(x.strip() for x in match.group(1).split(',') if x.strip())
    return out


def _ip_conflicts(ips, sources, name):
    for filename, blocks in sources:
        for b in blocks:
            if b['type'] != 'identify' or (b['name'] == name+'-identify' and b['attrs'].get('endpoint') == name):
                continue
            for token in _raw_matches(b):
                try:
                    network = ipaddress.ip_network(token, strict=False)
                except ValueError:
                    continue  # hostname/port; cannot prove overlap
                if any(network.overlaps(ipaddress.ip_network(x, strict=False)) for x in ips):
                    raise ValueError('IP überschneidet sich mit Identify ['+b['name']+'] aus '+filename)


def workspace(read_file, custom_folder, default_folder, pjsip_blocks, scan_endpoints):
    sources, profile_list = [], []
    for folder in (custom_folder, default_folder):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.conf')):
            if path.is_symlink() or path.stat().st_size > 300000 or not (path.name.startswith('pjsip') or path.name == 'custom.conf'):
                continue
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}\.conf', path.name):
                continue
            content = path.read_text(encoding='utf-8') if folder == default_folder else read_file(path.name)['content']
            sources.append((('custom/' if folder == custom_folder else 'default/')+path.name, pjsip_blocks(content)))
    contexts = []
    for folder in (custom_folder, default_folder):
        if folder.is_dir():
            for path in sorted(folder.glob('extensions*.conf')):
                if path.is_symlink() or path.stat().st_size > 300000:
                    continue
                contexts.append((('custom/' if folder == custom_folder else 'default/')+path.name,
                                 path.read_text(encoding='utf-8')))
    for location, blocks in sources:
        for ident in blocks:
            epname = ident['attrs'].get('endpoint','')
            if ident['type']!='identify' or not PROFILE.fullmatch(epname):
                continue
            eps = [b for b in blocks if b['name'] == epname and b['type'] == 'endpoint']
            if len(eps) != 1 or eps[0]['attrs'].get('context') != epname:
                continue
            for context_file, text in contexts:
                try:
                    ctx = inspect_context(text, epname)
                except ValueError:
                    ctx = None
                if ctx:
                    profile_list.append({'name': epname, 'ips': _raw_matches(ident), 'targets':ctx['targets'],
                                         'pjsip_file': location, 'extensions_file': context_file,
                                         'readonly': not (location.startswith('custom/') and context_file.startswith('custom/'))})
    avail = sorted({str(e['extension']) for e in scan_endpoints()['endpoints']
                    if NUMBER.fullmatch(str(e.get('extension','')))})
    return {'profiles':profile_list, 'available_extensions':avail,
            'note':'Nur ausgelesene PJSIP-Nebenstellen auswählbar. Quell-IP muss zur anrufenden Tailscale-Adresse gehören. Keine automatische Neuladung.'}


def prepare(data, read_file, custom_folder, default_folder, pjsip_blocks, scan_endpoints):
    name = str(data.get('name','')).strip()
    if not PROFILE.fullmatch(name):
        raise ValueError('Zugangsname: 2–40 Zeichen, nur Kleinbuchstaben, Zahlen, - und _')
    if name in ('default', 'general', 'globals', 'parkedcallstimeout'):
        raise ValueError('Dieser Kontextname ist reserviert')
    ips = normal_ips(data.get('ips'))
    targets = valid_targets(data.get('targets'),
                            [str(e['extension']) for e in scan_endpoints()['endpoints']])
    seconds = data.get('timeout', 30)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 5 <= seconds <= 120:
        raise ValueError('Rufdauer muss zwischen 5 und 120 Sekunden liegen')
    p_name = data.get('pjsip_file') or 'pjsip_custom.conf'
    e_name = data.get('extensions_file') or 'extensions.conf'
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}\.conf', p_name) or not re.fullmatch(r'extensions(?:_[A-Za-z0-9_-]+)?\.conf', e_name):
        raise ValueError('Nur erlaubte Asterisk-Dateinamen verwenden')
    pi, ex = read_file(p_name), read_file(e_name)
    if pi['source'] != 'custom' or ex['source'] != 'custom':
        raise ValueError('Beide Custom-Dateien müssen bereits vorhanden sein. Keine Standarddatei überschreiben.')
    hashes = data.get('hashes') or {}
    if hashes.get('pjsip') != pi['hash'] or hashes.get('extensions') != ex['hash']:
        raise ValueError('Dateien wurden geändert – Konfiguration erneut laden')
    ptext, etext = pi['content'], ex['content']
    all_blocks = pjsip_blocks(ptext)
    eps = [b for b in all_blocks if b['name'] == name and b['type']=='endpoint']
    ids = [b for b in all_blocks if b['name'] == name+'-identify' and b['type']=='identify']
    # Never overwrite similarly named auth, AOR, transport or non-standard sections.
    if len(eps)>1 or len(ids)>1 or any(b['name'] in (name,name+'-identify') and b not in eps+ids for b in all_blocks):
        raise ValueError('Mehrdeutige PJSIP-Definition, bitte Rohdatei-Editor verwenden')
    if bool(eps) != bool(ids):
        raise ValueError('Endpoint/Identify ist unvollständig, bitte in Asterisk-Dateien prüfen')
    if eps and (eps[0]['attrs'].get('context') != name or eps[0]['attrs'].get('auth') or eps[0]['attrs'].get('aors')):
        raise ValueError('Bestehender Endpoint hat einen anderen Kontext oder Auth-/AOR-Regeln – nicht automatisch ändern')
    if ids and (ids[0]['attrs'].get('endpoint') != name or set(ids[0]['attrs'])-{'type','endpoint','match'}):
        raise ValueError('Identify enthält zusätzliche Regeln; nicht automatisch überschreiben')
    src = []
    for folder in (custom_folder, default_folder):
        if folder.is_dir():
            for path in folder.glob('*.conf'):
                if path.is_symlink() or path.stat().st_size > 300000 or not (path.name.startswith('pjsip') or path.name=='custom.conf'):
                    continue
                source = path.read_text(encoding='utf-8')
                label = ('custom/' if folder == custom_folder else 'default/') + path.name
                bs = pjsip_blocks(source)
                # Existing same profile in a second file may hide conflicting definitions.
                if label != 'custom/'+p_name and any(b['name'] in (name,name+'-identify') for b in bs):
                    raise ValueError('Identischer Endpoint/Identify auch in '+label+' definiert')
                src.append((label,bs))
    _ip_conflicts(ips,src,name)
    p_changes = []
    if eps:
        # Preserve all original endpoint parameters (including codecs and NAT flags).
        endpoint = eps[0]
        identify = ids[0]
        original = identify['raw']
        matches = list(re.finditer(r'(?im)^\s*match\s*=\s*[^\r\n]*\r?\n?', original))
        if not matches:
            raise ValueError('Identify hat keine vorhandene match-Zeile')
        replaced = _replace_many(original, [(m.start(),m.end(),'') for m in matches])
        replaced = replaced.rstrip()+'\nmatch='+','.join(ips)+'\n'
        p_changes.append((identify['start'],identify['end'],replaced))
        pnext = _replace_many(ptext,p_changes)
    else:
        pnext = _append(ptext,render_pjsip(name,ips))
    # Reject duplicate dialplan contexts in *all* custom/default extension files.
    for folder in (custom_folder,default_folder):
        if not folder.is_dir():
            continue
        for path in folder.glob('extensions*.conf'):
            if path.is_symlink() or path.stat().st_size > 300000:
                continue
            label = ('custom/' if folder == custom_folder else 'default/')+path.name
            if label!='custom/'+e_name and any(s['name']==name for s in list_sections(path.read_text(encoding='utf-8'))):
                raise ValueError('Dialplan-Kontext ['+name+'] ist bereits in '+label+' definiert')
    old_ctx = inspect_context(etext,name)
    if bool(eps) != bool(old_ctx):
        raise ValueError('Vorhandener PJSIP-Endpoint und Dialplan-Kontext sind nicht konsistent – manuell prüfen')
    new_dial = render_dialplan(name,targets,seconds,old_ctx['comments'] if old_ctx else ())
    if old_ctx:
        block = old_ctx['section']
        enext = etext[:block['start']]+new_dial+'\n'+etext[block['end']:]
    else:
        enext = _append(etext,new_dial)
    if len(pnext.encode('utf-8'))>300000 or len(enext.encode('utf-8'))>300000:
        raise ValueError('Konfigurationsdatei würde zu groß')
    return {'name':name, 'ips':ips, 'targets':targets, 'timeout':seconds,
            'pjsip_file':p_name, 'extensions_file':e_name,
            'pjsip_content':pnext,'extensions_content':enext,
            'original_pjsip':pi,'original_extensions':ex,
            'pjsip_preview':render_pjsip(name,ips) if not eps else eps[0]['raw'].rstrip()+'\n\n'+replaced,
            'extensions_preview':new_dial, 'updated':bool(eps)}
