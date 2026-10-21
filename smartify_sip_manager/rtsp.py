"""Smartify SIP Manager – RTSP-Kameras erkennen und testen (v1.5).

- RTSP-Adressen zerlegen, maskieren und wieder zusammensetzen
- OPTIONS/DESCRIBE mit Basic- und Digest-Anmeldung, Codecs aus dem SDP
- Netzwerksuche: TCP-Port 554/8554 im /24-Netz, ONVIF-Probe (Unicast, Port 3702)
- Herstellertypische Pfade als Vorschlag

Nur Standardbibliothek. Keine Passwörter in Rückgaben, außer explizit gewünscht.
"""
import concurrent.futures
import hashlib
import ipaddress
import re
import socket
import uuid
from urllib.parse import quote, unquote, urlsplit

RTSP_PORTS = (554, 8554)
USER_AGENT = 'Smartify-SIP-Manager'

# Herstellerpfade: (Schlüssel, Bezeichnung, Hauptstream, Nebenstream)
VENDORS = [
    ('sonoff', 'SONOFF / eWeLink', '/av_stream/ch0', '/av_stream/ch1'),
    ('hikvision', 'Hikvision / HiLook', '/Streaming/Channels/101', '/Streaming/Channels/102'),
    ('dahua', 'Dahua / Imou / Amcrest', '/cam/realmonitor?channel=1&subtype=0', '/cam/realmonitor?channel=1&subtype=1'),
    ('reolink', 'Reolink', '/h264Preview_01_main', '/h264Preview_01_sub'),
    ('akuvox', 'Akuvox', '/live/ch00_0', '/live/ch00_1'),
    ('axis', 'Axis', '/axis-media/media.amp', '/axis-media/media.amp?resolution=640x360'),
    ('tapo', 'TP-Link Tapo', '/stream1', '/stream2'),
    ('2n', '2N', '/h264_stream', '/mjpeg_stream'),
    ('doorbird', 'DoorBird', '/mpeg/media.amp', '/mpeg/media.amp'),
    ('uniview', 'Uniview', '/media/video1', '/media/video2'),
    ('generic', 'Allgemein / ONVIF', '/stream1', '/live'),
]
VENDOR_HINTS = [
    ('hikvision', r'hikvision|hik|dnvrs|ds-\d'), ('dahua', r'dahua|imou|amcrest|dh-'),
    ('reolink', r'reolink'), ('akuvox', r'akuvox'), ('axis', r'axis'), ('tapo', r'tapo|tp-link'),
    ('2n', r'\b2n\b|helios'), ('doorbird', r'doorbird|bird home'), ('uniview', r'uniview|unv'),
    ('sonoff', r'sonoff|ewelink|itead|cam-pt|anyka'),
]


# ---------------------------------------------------------------------------
# Adressen
# ---------------------------------------------------------------------------

def parse_url(url):
    """rtsp://user:pw@host:port/path#extra -> dict. Raises ValueError."""
    url = (url or '').strip()
    main, _, extra = url.partition('#')
    parts = urlsplit(main)
    if parts.scheme.lower() not in ('rtsp', 'rtsps') or not parts.hostname:
        raise ValueError('Keine RTSP-Adresse')
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    return {'schema': parts.scheme.lower(), 'host': parts.hostname, 'port': parts.port or 554,
            'pfad': path, 'benutzer': unquote(parts.username or ''), 'passwort': unquote(parts.password or ''),
            'zusatz': extra}


def build_url(cam, password=None, with_extra=True):
    user = cam.get('benutzer') or ''
    pw = cam.get('passwort', '') if password is None else password
    auth = ''
    if user:
        auth = quote(user, safe='') + (':' + quote(pw, safe='') if pw else '') + '@'
    host = cam['host']
    if ':' in host and not host.startswith('['):
        host = '[' + host + ']'
    port = int(cam.get('port') or 554)
    path = cam.get('pfad') or '/'
    if not path.startswith('/'):
        path = '/' + path
    url = f"{cam.get('schema') or 'rtsp'}://{auth}{host}{'' if port == 554 else ':' + str(port)}{path}"
    if with_extra and cam.get('zusatz'):
        url += '#' + cam['zusatz']
    return url


def mask_url(url):
    try:
        cam = parse_url(url)
    except ValueError:
        return re.sub(r'(//[^:/@]+:)[^@]*@', r'\1•••@', url or '')
    if not cam['passwort']:
        return build_url(cam)
    return build_url(cam, password='SMARTIFYMASK').replace('SMARTIFYMASK', '•••')


# ---------------------------------------------------------------------------
# RTSP-Protokoll
# ---------------------------------------------------------------------------

def _recv_response(sock, limit=65536):
    data = b''
    while b'\r\n\r\n' not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > limit:
            break
    head, _, body = data.partition(b'\r\n\r\n')
    lines = head.decode('utf-8', 'replace').split('\r\n')
    status_line = lines[0] if lines else ''
    m = re.match(r'RTSP/\d\.\d\s+(\d{3})\s*(.*)', status_line)
    if not m:
        raise ValueError('Keine RTSP-Antwort')
    headers = {}
    for line in lines[1:]:
        key, sep, val = line.partition(':')
        if sep:
            headers.setdefault(key.strip().lower(), []).append(val.strip())
    length = int((headers.get('content-length') or ['0'])[0] or 0)
    while len(body) < min(length, limit):
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return int(m.group(1)), m.group(2), headers, body[:length].decode('utf-8', 'replace')


def _digest(params, method, uri, user, password):
    realm, nonce = params.get('realm', ''), params.get('nonce', '')
    ha1 = hashlib.md5(f'{user}:{realm}:{password}'.encode()).hexdigest()
    ha2 = hashlib.md5(f'{method}:{uri}'.encode()).hexdigest()
    qop = params.get('qop', '')
    fields = [f'username="{user}"', f'realm="{realm}"', f'nonce="{nonce}"', f'uri="{uri}"']
    if 'auth' in [q.strip() for q in qop.split(',')]:
        cnonce, nc = uuid.uuid4().hex[:16], '00000001'
        resp = hashlib.md5(f'{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}'.encode()).hexdigest()
        fields += ['qop=auth', f'nc={nc}', f'cnonce="{cnonce}"']
    else:
        resp = hashlib.md5(f'{ha1}:{nonce}:{ha2}'.encode()).hexdigest()
    fields.append(f'response="{resp}"')
    if params.get('opaque'):
        fields.append(f'opaque="{params["opaque"]}"')
    return 'Digest ' + ', '.join(fields)


def _auth_params(header):
    return {k.lower(): v for k, v in re.findall(r'(\w+)="?([^",]*)"?', header)}


def request(host, port, method, path, user='', password='', timeout=3.0, accept_sdp=False):
    """One RTSP request on a fresh connection, repeated once with credentials on 401."""
    uri = f'rtsp://{host}:{port}{path}'
    auth = None
    for attempt in range(2):
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            lines = [f'{method} {uri} RTSP/1.0', f'CSeq: {attempt + 1}', f'User-Agent: {USER_AGENT}']
            if accept_sdp:
                lines.append('Accept: application/sdp')
            if auth:
                lines.append('Authorization: ' + auth)
            sock.sendall(('\r\n'.join(lines) + '\r\n\r\n').encode())
            status, reason, headers, body = _recv_response(sock)
        if status != 401 or attempt or not user:
            return status, reason, headers, body
        challenges = headers.get('www-authenticate') or []
        digest = next((c for c in challenges if c.lower().startswith('digest')), None)
        if digest:
            auth = _digest(_auth_params(digest[6:]), method, uri, user, password)
        else:
            import base64
            auth = 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()
    return status, reason, headers, body


def parse_sdp(sdp):
    media, current = {'video': [], 'audio': []}, None
    payload_names = {}
    for line in (sdp or '').splitlines():
        line = line.strip()
        if line.startswith('m='):
            kind = line[2:].split(' ', 1)[0]
            current = kind if kind in media else None
            if current:
                for pt in line.split()[3:]:
                    payload_names[(current, pt)] = None
        elif line.startswith('a=rtpmap:') and current:
            m = re.match(r'a=rtpmap:(\d+)\s+([A-Za-z0-9._-]+)', line)
            if m:
                name = m.group(2).upper()
                if name not in media[current]:
                    media[current].append(name)
    static = {'0': 'PCMU', '8': 'PCMA', '26': 'JPEG'}
    for (kind, pt), _ in payload_names.items():
        if pt in static and static[pt] not in media[kind] and not media[kind]:
            media[kind].append(static[pt])
    return media


def describe(cam, timeout=4.0):
    """Test a camera. Returns a dict without password."""
    out = {'ok': False, 'status': None, 'video': [], 'audio': [], 'server': '', 'meldung': ''}
    try:
        status, reason, headers, body = request(cam['host'], cam.get('port') or 554, 'DESCRIBE', cam.get('pfad') or '/',
                                                cam.get('benutzer', ''), cam.get('passwort', ''), timeout, accept_sdp=True)
    except socket.timeout:
        out['meldung'] = 'Keine Antwort (Zeitüberschreitung)'
        return out
    except (OSError, ValueError) as exc:
        out['meldung'] = f'Nicht erreichbar: {str(exc)[:100]}'
        return out
    out['status'] = status
    out['server'] = (headers.get('server') or [''])[0][:80]
    if status == 200:
        out.update(parse_sdp(body))
        out['ok'] = bool(out['video'] or out['audio'])
        out['meldung'] = 'Stream gefunden' if out['ok'] else 'Antwort ohne Medienbeschreibung'
        if 'H265' in out['video'] or 'HEVC' in out['video']:
            out['meldung'] += ' – H.265: viele Browser spielen das nicht ab, Nebenstream oder Umwandlung nutzen'
    elif status == 401:
        out['meldung'] = 'Anmeldung abgelehnt – Benutzer/Passwort prüfen'
    elif status in (404, 454):
        out['meldung'] = 'Pfad nicht gefunden – anderen Pfad wählen'
    else:
        out['meldung'] = f'Antwort {status} {reason}'[:100]
    return out


# ---------------------------------------------------------------------------
# Netzwerksuche
# ---------------------------------------------------------------------------

def _port_open(ip, port, timeout):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def onvif_probe(ip, timeout=0.8):
    """Unicast WS-Discovery probe. Returns {'name','hardware'} or {}."""
    msg = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
           'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
           'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
           'xmlns:dn="http://www.onvif.org/ver10/network/wsdl"><e:Header>'
           f'<w:MessageID>uuid:{uuid.uuid4()}</w:MessageID>'
           '<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
           '<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>'
           '</e:Header><e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(msg.encode(), (ip, 3702))
            data, _ = sock.recvfrom(65535)
    except OSError:
        return {}
    text = data.decode('utf-8', 'replace')
    out = {}
    for key in ('name', 'hardware'):
        m = re.search(rf'onvif://www\.onvif\.org/{key}/([^\s<]+)', text)
        if m:
            out[key] = unquote(m.group(1)).replace('_', ' ')[:60]
    return out


def guess_vendor(*texts):
    blob = ' '.join(t for t in texts if t).lower()
    for key, pattern in VENDOR_HINTS:
        if re.search(pattern, blob):
            return key
    return 'generic'


def vendor_info(key):
    for k, label, main, sub in VENDORS:
        if k == key:
            return {'hersteller': k, 'bezeichnung': label, 'pfad': main, 'nebenstream': sub}
    return vendor_info('generic')


def subnet_hosts(lan_ip):
    net = ipaddress.ip_network(f'{lan_ip}/24', strict=False)
    if not net.is_private:
        raise ValueError('Netzwerksuche nur in privaten Netzen (z. B. 192.168.x.x)')
    return [str(h) for h in net.hosts()]


def discover(lan_ip, ports=RTSP_PORTS, timeout=0.35, workers=96, skip=()):
    """Find RTSP devices in the /24 network of lan_ip. Returns list of candidates."""
    hosts = subnet_hosts(lan_ip)
    targets = [(ip, port) for ip in hosts for port in ports]
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for (ip, port), is_open in zip(targets, pool.map(lambda t: _port_open(t[0], t[1], timeout), targets)):
            if is_open and (ip, port) not in skip:
                found.append((ip, port))
    result = []

    def inspect(item):
        ip, port = item
        server = ''
        try:
            _, _, headers, _ = request(ip, port, 'OPTIONS', '/', timeout=1.5)
            server = (headers.get('server') or [''])[0][:80]
        except (OSError, ValueError):
            pass
        onvif = onvif_probe(ip)
        vendor = guess_vendor(server, onvif.get('name', ''), onvif.get('hardware', ''))
        info = vendor_info(vendor)
        go2rtc = 'go2rtc' in server.lower() or (ip == lan_ip and port == 8554)
        return {'host': ip, 'port': port, 'server': server, 'onvif_name': onvif.get('name', ''),
                'onvif_hardware': onvif.get('hardware', ''), 'go2rtc': go2rtc, **info}

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        result = list(pool.map(inspect, found))
    return sorted(result, key=lambda r: (r['go2rtc'], tuple(int(x) for x in r['host'].split('.')), r['port']))
