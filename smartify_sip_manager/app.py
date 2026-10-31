"""Smartify SIP Manager: minimal local ingress service. No Asterisk or HA API mutations."""
import hashlib
import copy
import sys
from pathlib import Path as _ImportPath
if str(_ImportPath(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(_ImportPath(__file__).resolve().parent))
import inbound_routes
import sip_status_worker
import ring_router
import migration
import anlage as anlage_model
import generator
import rtsp as rtsp_mod
import verbindungen as verbindungen_mod
import logging
from logging.handlers import RotatingFileHandler
import threading
import secrets
import socket
import urllib.request
import urllib.error
import json
import os
import re
import tempfile
import difflib
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote

try:
    import yaml  # PyYAML, installed in the Dockerfile
except ImportError:  # pragma: no cover - only without rebuilt image
    yaml = None

APP_DIR = Path(__file__).resolve().parent


def read_addon_version():
    """Single source of truth: 'version' in the add-on's config.yaml (copied into the image)."""
    try:
        for line in (APP_DIR / 'config.yaml').read_text(encoding='utf-8').splitlines():
            match = re.match(r'^version:\s*["\']?([0-9][0-9A-Za-z.+-]*)', line)
            if match:
                return match.group(1)
    except OSError:
        pass
    return 'unbekannt'


ADDON_VERSION = read_addon_version()
# Versions of the frontend files shipped alongside this add-on release (frontend/ folder).
# Keep in sync with the header comment of each JS file and the CHANGELOG.
FRONTEND_VERSIONS = {'popup': '3.3.13', 'card': '2.7.10'}

ROOT = Path(os.environ.get('ADDON_CONFIGS_ROOT', '/addon_configs')).resolve()
PORT = int(os.environ.get('PORT', '8099'))
# Only .conf files in known Asterisk config folders, never arbitrary paths.
RE_CONF = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}\.conf$')
DATA_DIR = Path(os.environ.get('SMARTIFY_DATA_DIR', '/data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SIP_CORE_FILE = DATA_DIR / 'sip_core_draft.yaml'
LOG_DIR = DATA_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGER = logging.getLogger('smartify')
LOGGER.setLevel(logging.INFO)
if not LOGGER.handlers:
    h = RotatingFileHandler(LOG_DIR / 'smartify-manager.log', maxBytes=1_500_000, backupCount=4, encoding='utf-8')
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOGGER.addHandler(h)
LOCK = threading.RLock()
BACKUP_KEEP = int(os.environ.get('SMARTIFY_BACKUP_KEEP', '30'))


def prune_backups(folder, pattern, keep=None):
    """Keep only the newest backups matching pattern (names carry sortable UTC stamps)."""
    keep = BACKUP_KEEP if keep is None else keep
    try:
        files = sorted(p for p in Path(folder).glob(pattern) if p.is_file() and not p.is_symlink())
        for old in files[:-keep] if keep > 0 else files:
            old.unlink()
    except OSError:
        pass


def allowed_name(name):
    return isinstance(name,str) and bool(RE_CONF.fullmatch(name)) and name.lower() not in {'manager.conf'}


def reload_hint(name):
    if name == 'sip_core_draft.yaml':
        return 'Nur Entwurf gespeichert. In HA: Einstellungen → Geräte & Dienste → SIP Core → Konfigurieren; anschließend SIP-Funktionen testen.'
    if name.startswith('extensions'):
        return 'Nach Kontrolle: asterisk -rx "dialplan reload". Kein Add-on-Neustart normalerweise nötig.'
    if name.startswith('pjsip'):
        return 'Endpoint/AOR/Auth: asterisk -rx "pjsip reload". Transporte/Listener benötigen unter Umständen Asterisk-Neustart – NICHT automatisch durchführen.'
    if name.startswith('manager'):
        return 'AMI-Konfiguration: asterisk -rx "manager reload". Vorher Zugangsdaten und laufende Verbindungen prüfen.'
    if name.startswith('rtp'):
        return 'RTP-Änderungen können einen kontrollierten Asterisk-Neustart erfordern; zuerst bestehende Calls und Ports prüfen.'
    if name.startswith('modules'):
        return 'Moduländerungen benötigen oft Asterisk-Neustart; nur mit Wartungsfenster.'
    return 'Abhängig von der Datei: Konfiguration und Asterisk-Logs prüfen. Kein automatischer Neustart.'


def audit(event, name='', result='ok', detail=''):
    # No passwords, file contents or auth headers in logs.
    safe = lambda x: re.sub(r'[\r\n\t]', ' ', str(x))[:170]
    LOGGER.info('event=%s file=%s result=%s detail=%s',safe(event),safe(name),safe(result),safe(detail))


def available_files():
    names = {'pjsip_custom.conf','extensions.conf','extensions_custom.conf','pjsip.conf',
             'pjsip_default.conf','manager_custom.conf','rtp_custom.conf',
             'modules_custom.conf','users.conf','sip_custom.conf'}
    for folder in (CUSTOM, DEFAULT):
        if folder.is_dir():
            names.update(f.name for f in folder.iterdir() if f.is_file() and allowed_name(f.name))
    return sorted(x for x in names if allowed_name(x))

# All add-on configs mounted by Supervisor; restrict this manager to a known single installation.
slug = '3e533915_asterisk'
try:
    options = json.loads((DATA_DIR / 'options.json').read_text())
    candidate = options.get('asterisk_slug', slug)
    if re.fullmatch(r'[A-Za-z0-9_-]{3,80}', candidate):
        slug = candidate
except (OSError, ValueError, TypeError):
    pass
ASTERISK_DIR = ROOT / slug / 'asterisk'
CUSTOM = ASTERISK_DIR / 'custom'
DEFAULT = ASTERISK_DIR / 'default'
MAX_SIZE = 300_000


def file_path(name):
    if not allowed_name(name):
        raise ValueError('Datei nicht zugelassen')
    path = CUSTOM / name
    # Do not follow symlinks or permit unexpected root escapes.
    if path.is_symlink() or CUSTOM.is_symlink() or ASTERISK_DIR.is_symlink() or ROOT.is_symlink():
        raise ValueError('Symlinks sind nicht erlaubt')
    if not path.resolve().is_relative_to(CUSTOM.resolve()):
        raise ValueError('Ungültiger Pfad')
    return path


def digest(contents):
    return hashlib.sha256(contents.encode('utf-8')).hexdigest()


def read_file(name):
    path = file_path(name)
    if path.exists():
        if path.stat().st_size > MAX_SIZE:
            raise ValueError('Datei zu groß')
        source = 'custom'
    else:
        path = DEFAULT / name
        if path.is_symlink() or DEFAULT.is_symlink() or ASTERISK_DIR.is_symlink() or not path.exists():
            return {'name': name, 'content': '', 'source': 'missing', 'hash': digest(''), 'hint': reload_hint(name)}
        source = 'default (nur lesen)'
    if path.stat().st_size > MAX_SIZE:
        raise ValueError('Datei zu groß')
    content = path.read_text(encoding='utf-8')
    return {'name': name, 'content': content, 'source': source,
            'hash': digest(content), 'hint': reload_hint(name)}


def write_file(name, content, expected_hash):
    with LOCK:
        target = file_path(name)
        if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_SIZE:
            raise ValueError('Ungültiger oder zu langer Inhalt')
        if '\x00' in content:
            raise ValueError('Ungültige Steuerzeichen')
        if not isinstance(expected_hash, str):
            raise ValueError('Versionskennung fehlt')
        if target.exists():
            if target.stat().st_size > MAX_SIZE:
                raise ValueError('Datei zu groß')
            old = target.read_text(encoding='utf-8')
        else:
            old = ''
        # Protect existing custom files; new creation requires explicit blank hash.
        if digest(old) != expected_hash:
            raise ValueError('Die Datei wurde zwischenzeitlich geändert: erneut laden')
        if not ASTERISK_DIR.is_dir():
            raise ValueError('Asterisk-Verzeichnis nicht gefunden; keine neue Struktur erzeugt')
        CUSTOM.mkdir(parents=True, exist_ok=True)
        if target.exists():
            backup_dir = CUSTOM / '.smartify-backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backup_dir / f'{name}.{stamp}.bak'
            backup.write_text(old, encoding='utf-8')
            os.chmod(backup, 0o600)
            prune_backups(backup_dir, f'{name}.*.bak')
        fd, temp = tempfile.mkstemp(prefix='.smartify-', dir=str(CUSTOM))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        audit('file_saved',name,detail=('backup_created' if old else 'new_file'))
        return {'name': name, 'hash': digest(content), 'saved': True,
                'hint': reload_hint(name), 'note': 'Gespeichert. KEIN Reload/Neustart ausgeführt.'}

def read_sip_core():
    if SIP_CORE_FILE.exists():
        value=SIP_CORE_FILE.read_text(encoding='utf-8')
        return {'name':SIP_CORE_FILE.name,'content':value,'hash':digest(value),'source':'Manager-Entwurf', 'hint':reload_hint('sip_core_draft.yaml')}
    return {'name':SIP_CORE_FILE.name,'content':'','hash':digest(''),'source':'Entwurf noch nicht angelegt','hint':reload_hint('sip_core_draft.yaml')}


def write_sip_core(content,expected_hash):
    if not isinstance(content,str) or len(content.encode('utf-8'))>MAX_SIZE or '\x00' in content:
        raise ValueError('Ungültiger Inhalt')
    with LOCK:
        current=read_sip_core()
        if expected_hash!=current['hash']:raise ValueError('Entwurf zwischenzeitlich verändert; neu laden')
        if current['content']:
            bd=DATA_DIR/'backups';bd.mkdir(exist_ok=True)
            fn=bd/('sip_core_draft_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.yaml')
            fn.write_text(current['content'],encoding='utf-8');os.chmod(fn,0o600)
            prune_backups(bd,'sip_core_draft_*.yaml');prune_backups(bd,'sip_core_[0-9]*.yaml')
        fd,tmp=tempfile.mkstemp(prefix='.sip-core-',dir=str(DATA_DIR))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(content);f.flush();os.fsync(f.fileno())
            os.chmod(tmp,0o600);os.replace(tmp,SIP_CORE_FILE)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    audit('sip_core_draft_saved','sip_core_draft.yaml')
    return {'saved':True,'hash':digest(content),'hint':reload_hint('sip_core_draft.yaml')}


# Camera routing is an independent, versioned draft. It never changes active SIP Core settings.
CAMERA_MAP_FILE = DATA_DIR / 'camera_mapping.json'
RE_CALLER = re.compile(r'^[0-9]{1,8}$')
RE_STREAM = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
RE_ENTITY = re.compile(r'^[a-z_]+\.[A-Za-z0-9_]+$')


def validate_camera_map(mapping):
    if not isinstance(mapping, dict) or len(mapping) > 80:
        raise ValueError('Ungültige Kamera-Zuordnung (maximal 80 Einträge)')
    normalized = {}
    for caller, entry in mapping.items():
        if not isinstance(caller, str) or not RE_CALLER.fullmatch(caller):
            raise ValueError('Ungültige SIP-Anrufernummer')
        if not isinstance(entry, dict):
            raise ValueError('Kameraeintrag muss ein Objekt sein')
        label, stream = entry.get('label', ''), entry.get('stream', '')
        mode = entry.get('mode', 'mse')
        camera_mode = entry.get('camera_mode', 'always')
        if not isinstance(label, str) or len(label) > 80 or any(c in label for c in '\r\n\x00'):
            raise ValueError('Ungültige Stationsbezeichnung')
        if not isinstance(stream, str) or not RE_STREAM.fullmatch(stream):
            raise ValueError('Ungültiger go2rtc-Streamname')
        if mode not in ('mse', 'webrtc') or camera_mode not in ('always', 'auto', 'hidden'):
            raise ValueError('Ungültiger Wiedergabe- oder Kameramodus')
        out = {'label': label, 'stream': stream, 'mode': mode, 'camera_mode': camera_mode}
        for field in ('door', 'light', 'bell'):
            val = entry.get(field, '')
            if not isinstance(val, str) or (val and not RE_ENTITY.fullmatch(val)):
                raise ValueError(f'Ungültige Entität in {caller}: {field}')
            out[field] = val
        normalized[caller] = out
    return normalized


def read_camera_map():
    if CAMERA_MAP_FILE.is_file():
        raw = CAMERA_MAP_FILE.read_text(encoding='utf-8')
        if len(raw) > MAX_SIZE:
            raise ValueError('Kamerakonfiguration zu groß')
        mapping = validate_camera_map(json.loads(raw))
        return {'mapping': mapping, 'hash': digest(raw), 'saved': True}
    return {'mapping': {}, 'hash': digest(''), 'saved': False}


def write_camera_map(mapping, expected_hash):
    with LOCK:
        current = read_camera_map()
        if expected_hash != current['hash']:
            raise ValueError('Kamerazuordnungen wurden inzwischen geändert. Neu laden.')
        normalized = validate_camera_map(mapping)
        content = json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
        if CAMERA_MAP_FILE.exists():
            backup_dir = DATA_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backup_dir / f'camera_mapping_{stamp}.json'
            backup.write_bytes(CAMERA_MAP_FILE.read_bytes())
            os.chmod(backup, 0o600)
            prune_backups(backup_dir, 'camera_mapping_*.json')
        fd, temp = tempfile.mkstemp(prefix='.smartify-cameras-', dir=str(DATA_DIR))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fp:
                fp.write(content)
                fp.flush()
                os.fsync(fp.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, CAMERA_MAP_FILE)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        audit('camera_mapping_saved', detail=f'entries={len(normalized)}')
        return {'saved': True, 'hash': digest(content), 'count': len(normalized),
                'note': 'Mapping gespeichert, noch NICHT in SIP Core aktiviert.'}


def log_tail():
    path=LOG_DIR/'smartify-manager.log'
    if not path.exists():return []
    with path.open(encoding='utf-8') as fp:
        return fp.readlines()[-160:]


def copy_default_to_custom(name, expected_hash):
    if not allowed_name(name):raise ValueError('Dateiname nicht erlaubt')
    with LOCK:
        source=DEFAULT/name
        target=file_path(name)
        if target.exists():raise ValueError('Custom-Datei existiert bereits. Stattdessen normal laden und bearbeiten.')
        if DEFAULT.is_symlink() or source.is_symlink() or not source.is_file():
            raise ValueError('Standarddatei nicht gefunden oder ist ein Symlink')
        if source.stat().st_size>MAX_SIZE:raise ValueError('Standarddatei zu groß')
        content=source.read_text(encoding='utf-8')
        if expected_hash!=digest(content):raise ValueError('Standarddatei hat sich geändert: erneut laden')
        if not ASTERISK_DIR.is_dir():raise ValueError('Asterisk-Verzeichnis fehlt')
        CUSTOM.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix='.smartify-copy-',dir=str(CUSTOM))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(content);f.flush();os.fsync(f.fileno())
            os.chmod(tmp,0o600)
            os.replace(tmp,target)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    audit('default_copied_to_custom',name)
    return {'saved':True,'hash':digest(content), 'hint':reload_hint(name), 'note':'Default-Vorlage als Custom-Kopie angelegt. Noch NICHT geladen!'}




def create_custom_file(name):
    """Create a missing, empty custom .conf only after an explicit user action.
    Never create/overwrite default configurations or synthesize #include lines.
    """
    with LOCK:
        target = file_path(name)
        if target.exists():
            raise ValueError('Custom-Datei existiert bereits: zuerst laden')
        reference = DEFAULT / name
        if reference.exists():
            raise ValueError('Eine Default-Datei existiert. Bitte ausdrücklich „Default → Custom kopieren“ verwenden.')
        if not ASTERISK_DIR.is_dir():
            raise ValueError('Asterisk-Verzeichnis fehlt; erst Mount und Add-on-Slug prüfen')
        CUSTOM.mkdir(parents=True, exist_ok=True)
        if CUSTOM.is_symlink() or target.is_symlink():
            raise ValueError('Unsicherer Symlink')
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
    audit('custom_file_created', name, detail='empty')
    return {'saved': True, 'hash': digest(''), 'hint': reload_hint(name),
            'note': 'Leere Custom-Datei angelegt. Noch keine wirksame Asterisk-Konfiguration; Einbindung prüfen.'}

def check_health():
    return {
        'asterisk_directory': ASTERISK_DIR.is_dir(),
        'custom_directory': CUSTOM.is_dir(),
        'default_directory': DEFAULT.is_dir(),
        'custom_files': len([p for p in CUSTOM.glob('*.conf') if p.is_file()]) if CUSTOM.is_dir() else 0,
        'writeable_custom': bool(CUSTOM.is_dir() and os.access(CUSTOM, os.W_OK)),
        'sip_core_mode': 'draft_only',
        'auto_reload': False,
        'homeassistant_api_token_present': bool(os.environ.get('SUPERVISOR_TOKEN')),
        'hint': ('Asterisk-Verzeichnis fehlt. Noch keine Dateien erzeugen: zuerst App-Mount und Add-on-Slug prüfen.'
                 if not ASTERISK_DIR.is_dir() else 'Asterisk-Verzeichnis gefunden. Dateiänderungen benötigen ggf. gezielten Reload.')
    }

AMI_OVERRIDE_FILE = DATA_DIR / 'ami_zugang.json'


def get_options():
    """App options; a manager-created AMI access (ami_zugang.json) wins for ami_username/ami_password."""
    try:
        opts = json.loads((DATA_DIR / 'options.json').read_text())
    except (OSError, ValueError, TypeError):
        opts = {}
    try:
        override = json.loads(AMI_OVERRIDE_FILE.read_text(encoding='utf-8'))
        if isinstance(override, dict) and override.get('ami_password'):
            opts = {**opts, 'ami_username': override.get('ami_username', 'smartify'),
                    'ami_password': override['ami_password']}
    except (OSError, ValueError, TypeError):
        pass
    return opts


def core_api(method, path, body=None, timeout=8):
    """Home Assistant Core REST API through the Supervisor proxy."""
    token = os.environ.get('SUPERVISOR_TOKEN')
    if not token:
        raise ValueError('Home Assistant API: SUPERVISOR_TOKEN fehlt im Add-on-Prozess. Smartify mit HA-Basisimage neu bauen (kein bloßer Neustart), danach unter SIP Core erneut laden.')
    data = None if body is None else json.dumps(body).encode('utf-8')
    request = urllib.request.Request('http://supervisor/core/api/' + path.lstrip('/'), data=data, method=method,
                                     headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(5_000_000)
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read(400).decode('utf-8', 'replace')
        raise ValueError(f'Home-Assistant-API {exc.code}: {detail}') from None
    except (OSError, ValueError) as exc:
        raise ValueError(f'Home-Assistant-API nicht erreichbar: {str(exc)[:160]}') from None


ENTITY_DOMAINS = {'media_player', 'camera', 'switch', 'light', 'button', 'lock', 'binary_sensor', 'sensor', 'select',
                  'event', 'script', 'input_boolean', 'input_button', 'cover'}


def ha_entity_index():
    try:
        data = core_api('GET', 'states')
    except ValueError as exc:
        return {'available': False, 'entities': [], 'message': str(exc)[:180]}
    entities = []
    for item in data or []:
        entity = item.get('entity_id', '')
        if entity.split('.')[0] in ENTITY_DOMAINS:
            attrs = item.get('attributes', {}) or {}
            entities.append({'entity_id': entity,
                             'name': str(attrs.get('friendly_name', ''))[:120],
                             'device_class': str(attrs.get('device_class', '') or '')[:40],
                             'state': str(item.get('state', ''))[:40]})
    entities.sort(key=lambda e: e['entity_id'])
    return {'available': True, 'entities': entities[:4000]}


def ha_persons():
    """Persons with linked HA users. SIP Core matches ha_username against user id or display name."""
    persons = []
    for item in core_api('GET', 'states') or []:
        if str(item.get('entity_id', '')).startswith('person.'):
            attrs = item.get('attributes', {}) or {}
            persons.append({'person': item['entity_id'], 'name': str(attrs.get('friendly_name', '')),
                            'user_id': str(attrs.get('user_id') or '')})
    return persons


def read_discovery():
    output=[]
    for name in ['pjsip_custom.conf','extensions.conf','extensions_custom.conf']:
        info=read_file(name)
        content=info['content']
        extensions=[]
        if name=='pjsip_custom.conf':
            for line in content.splitlines():
                if line.strip().startswith('[') and line.strip().endswith(']'):
                    extensions.append(line.strip())
        else:
            for line in content.splitlines():
                match=re.search(r'^\s*exten\s*=>\s*(\d{2,6}),1',line)
                if match: extensions.append(match.group(1))
        output.append({'file':name,'source':info['source'],'entries':extensions[:250]})
    return output

def scan_endpoints():
    """Read PJSIP endpoints without AMI or Asterisk-side effects.
    Only PJSIP configuration files define the endpoint objects being sought;
    unrelated Asterisk files (e.g. minivm.conf) must not cause false warnings.
    Duplicate object sections are reconciled by name + type, not by header alone.
    Templates are excluded. Auth secrets are never returned.
    """
    result = {}
    sources = []
    warnings = []
    if not ASTERISK_DIR.is_dir():
        return {'endpoints':[], 'warnings':['Asterisk-Konfigurationsordner fehlt: Mount/Slug prüfen'], 'sources':[]}
    for folder, origin in ((DEFAULT,'default'),(CUSTOM,'custom')):
        if not folder.is_dir():continue
        for path in sorted(folder.glob('*.conf')):
            if not allowed_name(path.name) or path.is_symlink():continue
            # Mini-Voicemail, manager.conf and other subsystems are not PJSIP.
            if not path.name.lower().startswith('pjsip'):continue
            try:
                if path.stat().st_size > MAX_SIZE:continue
                content = path.read_text(encoding='utf-8')
            except (OSError,UnicodeError) as exc:
                warnings.append(f'{origin}/{path.name}: nicht lesbar ({type(exc).__name__})')
                continue
            sources.append(f'{origin}/{path.name}')
            section=None; section_decl=''; attrs={}
            def store():
                if not section:return
                name=section.strip()
                if name.endswith(')') or name.startswith('!') or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,80}',name):return
                if attrs.get('type','').lower()!='endpoint' and not re.search(r'\]\s*\([^)]*endpoint[^)]*\)', section_decl, re.I):return
                obj=result.setdefault(name,{'extension':name,'display_name':'','transport':'','context':'', 'files':[],'origin':origin})
                obj['files'].append(f'{origin}/{path.name}')
                obj['origin']=origin
                for key in ('transport','context'):
                    if attrs.get(key):obj[key]=attrs[key][:120]
                raw=attrs.get('callerid','')
                if raw:
                    m=re.match(r'\s*"?([^"<]+)"?\s*(?:<[^>]*>)?',raw)
                    obj['display_name']=(m.group(1).strip() if m else raw.strip())[:100]
            for line in content.splitlines():
                clean=line.strip()
                if clean.startswith((';','#')) or not clean:continue
                if clean.startswith('[') and ']' in clean:
                    store();section=clean[1:clean.index(']')];section_decl=clean;attrs={}
                elif section and '=' in clean:
                    key,val=clean.split('=',1)
                    if key.strip().lower() in ('type','callerid','context','transport'):
                        attrs[key.strip().lower()]=val.strip().split(';',1)[0].strip()
            store()
    # SIP Core users may also be generated in users.conf with template-based sections.
    for item in result.values():
        item['status']='Nicht über AMI geprüft'
        item['editable']='custom' if any(f.startswith('custom/') for f in item['files']) else 'default – Referenz'
    return {'endpoints':sorted(result.values(),key=lambda x:(not x['extension'].isdigit(),int(x['extension']) if x['extension'].isdigit() else x['extension'])), 'warnings':warnings, 'sources':sources, 'note':'Konfigurationsscan (kein Live-Status). SIP-Core-Nebenstellen, die ausschließlich zur Laufzeit generiert werden, können fehlen.'}

# ---------------------------------------------------------------------------
# Number inventory: configured PJSIP endpoints, dialplan and SIP-Core accounts
# ---------------------------------------------------------------------------

def scan_number_plan():
    """Conservative, read-only inventory. No claim of effective/live availability.

    Asterisk dialplan can contain includes, patterns, realtime entries and AEL.
    We show simple numeric exten declarations seen in permitted config files,
    with source and context, and report the incompleteness clearly.
    """
    ep = scan_endpoints()
    endpoints = ep['endpoints']
    records = []
    warnings = list(ep.get('warnings') or [])
    for folder, origin in ((DEFAULT, 'default'), (CUSTOM, 'custom')):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.conf')):
            if not allowed_name(path.name) or path.is_symlink():
                continue
            if not ('extension' in path.stem.lower() or 'dialplan' in path.stem.lower()):
                continue
            try:
                if path.stat().st_size > MAX_SIZE:
                    warnings.append(f'{origin}/{path.name}: zu groß für Dialplan-Scan')
                    continue
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                warnings.append(f'{origin}/{path.name}: nicht lesbar')
                continue
            context = 'unbekannt'
            current = None
            def flush():
                if not current: return
                steps = []
                for line in current['lines']:
                    # Keep the actual dialplan commands visible. They can contain
                    # Goto, Dial, Playback, VoiceMail, Hangup etc.
                    cmd = re.sub(r'^\s*same\s*=>\s*(?:n|\d+)\s*,\s*', '', line, flags=re.I).strip()
                    steps.append(cmd[:600])
                body = ' '.join(steps)
                targets = list(dict.fromkeys(
                    re.findall(r'PJSIP_DIAL_CONTACTS\s*\(\s*(\d{2,6})\s*\)', body, re.I)
                    + re.findall(r'\bPJSIP/(\d{2,6})(?!\d)', body, re.I)))
                multi = ('&' in body and bool(re.search(r'\bDial\s*\(', body, re.I))) or len(targets) > 1
                labelled = bool(re.search(r'rufgruppe|ring\s*group|call\s*group', body, re.I))
                current['kind'] = 'Rufgruppe' if (multi or labelled) else 'Dialplan-Ziel'
                current['targets'] = targets
                current['steps'] = steps
                current['summary'] = ' → '.join(steps)[:1200]
                current['editable'] = (origin == 'custom' and
                    all(re.match(r'^(?:NoOp|Dial|Hangup)\s*\(', st, re.I) for st in steps)
                    and any(re.match(r'^Dial\s*\(', st, re.I) for st in steps))
                current.pop('lines', None)
                records.append(current)
            for line_no, raw in enumerate(text.splitlines(), 1):
                stripped = raw.strip()
                if not stripped or stripped.startswith((';', '#')):
                    continue
                head = re.match(r'^\s*\[([^]]+)\]', raw)
                if head:
                    flush(); current = None
                    context = head.group(1).strip()[:100]
                    continue
                definition = re.match(r'^\s*exten\s*=>\s*(\d{2,6})\s*,\s*(?:1|n(?:\([^)]*\))?)\s*,\s*(.*)$', raw, re.I)
                if definition:
                    flush()
                    current = {'number': definition.group(1), 'context': context,
                               'source': f'{origin}/{path.name}', 'line': line_no,
                               'lines': [definition.group(2).split(';', 1)[0].strip()]}
                    continue
                if current and re.match(r'^\s*same\s*=>', raw, re.I):
                    current['lines'].append(raw.split(';', 1)[0].strip())
                elif current and re.match(r'^\s*exten\s*=>', raw, re.I):
                    flush(); current = None
            flush()
    # SIP-Core may know numbers not represented in any readable pjsip*.conf.
    sip_numbers = []
    try:
        cfg = read_active_sip_core()
        for u in cfg.get('users') or []:
            if isinstance(u, dict):
                n = str(u.get('extension', '')).strip()
                if re.fullmatch(r'\d{2,6}', n):
                    sip_numbers.append({'number': n, 'name': str(u.get('display_name') or u.get('ha_username') or '')[:90]})
    except (ValueError, OSError, TypeError) as exc:
        warnings.append('SIP-Core-Nummern konnten nicht zusätzlich geprüft werden (' + type(exc).__name__ + ')')
    used = {}
    for item in endpoints:
        if re.fullmatch(r'\d{2,6}', item['extension']):
            used.setdefault(item['extension'], []).append('Asterisk-Nebenstelle')
    for item in records:
        used.setdefault(item['number'], []).append(item['kind'] + ' (' + item['context'] + ')')
    for item in sip_numbers:
        used.setdefault(item['number'], []).append('SIP-Core-Teilnehmer')
    # Auch unvollständige PJSIP-Definitionen sind belegt! Der reine Endpoint-Scan
    # übersieht etwa AOR/Auth ohne type=endpoint. Numeric sections in pjsip*.conf
    # or users.conf are therefore reserved independently of endpoint discovery.
    for folder, origin in ((DEFAULT, 'default'), (CUSTOM, 'custom')):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.conf')):
            if not allowed_name(path.name) or path.is_symlink():
                continue
            if not (path.name.lower().startswith('pjsip') or path.name.lower() == 'users.conf'):
                continue
            try:
                if path.stat().st_size > MAX_SIZE:
                    warnings.append(f'{origin}/{path.name}: zu groß für Nummernreservierung')
                    continue
                content = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                warnings.append(f'{origin}/{path.name}: für Nummernreservierung nicht lesbar')
                continue
            for section in pjsip_blocks(content):
                n = section['name']
                if re.fullmatch(r'\d{2,6}', n):
                    label = f'PJSIP-Konfiguration ({origin}/{path.name})'
                    used.setdefault(n, []).append(label)
    for row in records:
        route = group_simple_options(row)
        row['route_options'] = route
        row['editable'] = bool(route)
    return {'endpoints': endpoints, 'dialplan': records,
            'groups': [r for r in records if r['kind'] == 'Rufgruppe'],
            'sip_core_numbers': sip_numbers,
            'used': {n: list(dict.fromkeys(kinds)) for n, kinds in sorted(used.items())},
            'warnings': list(dict.fromkeys(warnings)),
            'complete': False,
            'note': ('Aus lesbaren Dateien und bei Erreichbarkeit SIP Core. Nicht erfasste Includes, '
                     'Realtime-Konfigurationen oder dynamische Dialplan-Einträge sind möglich. '
                     '„Nicht gefunden“ bedeutet NICHT garantiert frei.')}


# Structured editors are a conservative alternative to overwriting raw config.
# Only regular PJSIP triplets and simple dialplan blocks can be modified here.
PJSIP_FIELD_KEYS = {
    'aor': {'max_contacts','remove_existing','remove_unavailable','qualify_frequency',
            'minimum_expiration','default_expiration','maximum_expiration'},
    'auth': {'auth_type','username','password'},
    'endpoint': {'context','aors','auth','transport','disallow','allow','dtmf_mode',
                 'direct_media','force_rport','rewrite_contact','rtp_symmetric',
                 'ice_support','callerid'},
}


def pjsip_blocks(content):
    """Parse sections and preserve separators/comments belonging to the NEXT section.

    In particular, a comment banner between [106] and [linphone-cloud] must
    not make 106 uneditable, nor be erased when 106 is deleted.
    """
    heads = list(re.finditer(r'^[ \t]*\[([^]\r\n]+)\][^\r\n]*$', content, re.M))
    blocks = []
    for i, head in enumerate(heads):
        next_start = heads[i+1].start() if i + 1 < len(heads) else len(content)
        full_chunk = content[head.start():next_start]
        lines = full_chunk.splitlines(keepends=True)
        # Keep through the last nonempty, non-comment line; all trailing banners,
        # comments and spacing remain untouched outside this section's span.
        last = 0
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith(';'):
                last = index
        chunk = ''.join(lines[:last + 1])
        end = head.start() + len(chunk)
        attrs = {}
        for line in chunk.splitlines()[1:]:
            if not line.strip() or line.lstrip().startswith(';'):
                continue
            m = re.match(r'^\s*([a-z_]+)\s*=\s*([^;\r\n]*)', line, re.I)
            if m: attrs[m.group(1).lower()] = m.group(2).strip()
        blocks.append({'name':head.group(1).strip(), 'header':head.group(0).strip(), 'type': attrs.get('type',''),
                       'start':head.start(), 'end':end, 'attrs':attrs, 'raw':chunk})
    return blocks


def _custom_pjsip_sources():
    """Find custom conf files with recognized numeric AOR/Auth/Endpoint parts.

    These might be outside pjsip_custom.conf, e.g. custom/pjsip_extra.conf.
    Never write to the default directory.
    """
    if not CUSTOM.is_dir():
        return []
    found = []
    for path in sorted(CUSTOM.glob('*.conf')):
        if not allowed_name(path.name) or path.is_symlink():
            continue
        try:
            if path.stat().st_size > MAX_SIZE:
                continue
            info = read_file(path.name)
            blocks = pjsip_blocks(info['content'])
        except (ValueError, OSError, UnicodeError):
            continue
        if any(re.fullmatch(r'\d{2,6}', b['name']) and b['type'] in PJSIP_FIELD_KEYS for b in blocks):
            found.append((path.name, info, blocks))
    return found


def _pjsip_triplet_state(number, blocks):
    named = [b for b in blocks if b['name'] == number]
    complete = (len(named) == 3 and {b['type'] for b in named} == set(PJSIP_FIELD_KEYS)
                and all(b['header'] == '[' + number + ']' for b in named))
    plain = complete and all(
        set(b['attrs']) <= PJSIP_FIELD_KEYS[b['type']] | {'type'}
        and not any(';' in line for line in b['raw'].splitlines()[1:])
        for b in named)
    if plain:
        reason = ''
    elif not complete:
        reason = 'Keine vollständigen eindeutigen AOR/Auth/Endpoint-Dreiergruppen (z. B. Vorlagen, fehlender Abschnitt oder doppelte Definition). Über den Datei-Editor prüfen.'
    else:
        reason = 'Zusätzliche Parameter oder interne Kommentare: automatische Änderung nicht sicher. Datei-Editor verwenden.'
    return named, bool(plain), reason


def pjsip_table():
    primary = read_file('pjsip_custom.conf')
    primary_blocks = pjsip_blocks(primary['content']) if primary['source'] == 'custom' else []
    rows = []
    number_locations = {}
    sources = _custom_pjsip_sources()
    for filename, info, blocks in sources:
        by_number = {}
        for b in blocks:
            if re.fullmatch(r'\d{2,6}', b['name']) and b['type'] in PJSIP_FIELD_KEYS:
                by_number.setdefault(b['name'], []).append(b)
        for n in sorted(by_number, key=int):
            named, editable, reason = _pjsip_triplet_state(n, blocks)
            a = next((b['attrs'] for b in named if b['type'] == 'aor'), {})
            auth = next((b['attrs'] for b in named if b['type'] == 'auth'), {})
            ep = next((b['attrs'] for b in named if b['type'] == 'endpoint'), {})
            match = re.search(r'"?([^"<>]+)"?\s*<\s*' + re.escape(n) + r'\s*>', ep.get('callerid', ''))
            rows.append({'number': n, 'file': filename, 'hash': info['hash'],
                         'name': match.group(1).strip() if match else ep.get('callerid', '').strip('"'),
                         'max_contacts': a.get('max_contacts','1'), 'remove_existing': a.get('remove_existing','no'),
                         'remove_unavailable': a.get('remove_unavailable','no'),
                         'context': ep.get('context','default'), 'codecs': ep.get('allow','alaw,ulaw'),
                         'username': auth.get('username',n), 'has_password': bool(auth.get('password')),
                         'editable': editable, 'reason': reason,
                         'settings': {**a, **{k:v for k,v in ep.items() if k != 'callerid'}}})
            number_locations.setdefault(n, set()).add(filename)
    # Duplicates across different custom files are ambiguous, never modify them automatically.
    for row in rows:
        if len(number_locations[row['number']]) > 1:
            row['editable'] = False
            row['reason'] = 'Dieselbe Nebenstelle steht in mehreren Custom-Dateien: ' + ', '.join(sorted(number_locations[row['number']]))
    cloud = []
    for b in primary_blocks:
        if b['type'] != 'endpoint' or re.fullmatch(r'\d{2,6}', b['name']):
            continue
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', b['name']):
            continue
        duplicates = [x for x in primary_blocks if x['name'] == b['name']]
        allowed = {'type','transport','disallow','allow','direct_media','force_rport',
                   'rewrite_contact','rtp_symmetric','ice_support'}
        editable = (len(duplicates) == 1 and b['header'] == '['+b['name']+']'
                    and set(b['attrs']) <= allowed
                    and not any(';' in x for x in b['raw'].splitlines()[1:]))
        cloud.append({'name':b['name'], 'settings':{k:v for k,v in b['attrs'].items() if k != 'type'},
                      'editable':editable,
                      'reason':'' if editable else 'Weitere Endpoint-Optionen: nur im Rohdatei-Editor bearbeiten'})
    return {'file':'pjsip_custom.conf', 'source':primary['source'], 'hash':primary['hash'],
            'rows':sorted(rows, key=lambda r:(int(r['number']), r['file'])), 'cloud_endpoints':cloud,
            'note':'Einfache Custom-Definitionen aus allen lesbaren Custom-Dateien. Keine Passwörter werden ausgegeben.'}


def validate_pjsip_snippet(number, snippet):
    if not re.fullmatch(r'\d{2,6}', str(number)) or not isinstance(snippet,str) or len(snippet)>10000:
        raise ValueError('Ungültige Nebenstelle oder Snippet-Länge')
    blocks = pjsip_blocks(snippet)
    if len(blocks)!=3 or any(b['name'] != str(number) or b['header'] != '['+str(number)+']' for b in blocks) or {b['type'] for b in blocks} != set(PJSIP_FIELD_KEYS):
        raise ValueError('Erwartet genau drei Abschnitte [Nummer] mit type=aor/auth/endpoint')
    for b in blocks:
        if not set(b['attrs']) <= PJSIP_FIELD_KEYS[b['type']] | {'type'}:
            raise ValueError('Nicht unterstützte PJSIP-Option im Formular')
        for line in b['raw'].splitlines()[1:]:
            if line.strip() and not line.lstrip().startswith(';') and not re.match(r'^\s*[a-z_]+\s*=\s*[^\r\n]*$',line,re.I):
                raise ValueError('Ungültige Konfigurationszeile')
    attrs = {b['type']:b['attrs'] for b in blocks}
    if attrs['endpoint'].get('aors') != number or attrs['endpoint'].get('auth') != number:
        raise ValueError('AOR und Auth müssen auf dieselbe Nebenstelle zeigen')
    if attrs['auth'].get('auth_type')!='userpass':
        raise ValueError('Nur auth_type=userpass wird unterstützt')
    pwd = attrs['auth'].get('password','')
    if pwd and (len(pwd)>128 or re.search(r'[;#\s\x00-\x1f]',pwd)):
        raise ValueError('Passwort enthält ein ungültiges Zeichen')
    contacts = attrs['aor'].get('max_contacts', '1')
    if not contacts.isdigit() or not 1 <= int(contacts) <= 100:
        raise ValueError('max_contacts muss 1–100 sein')
    return blocks


def save_pjsip_row(data):
    n = str(data.get('number',''))
    op = data.get('operation')
    if op not in ('add','edit','delete'):
        raise ValueError('Ungültige Aktion')
    if op == 'delete':
        return delete_pjsip_row(data)
    snippet = data.get('snippet')
    blocks = validate_pjsip_snippet(n, snippet)
    filename = str(data.get('file') or 'pjsip_custom.conf')
    if not allowed_name(filename) or (op == 'add' and filename != 'pjsip_custom.conf'):
        raise ValueError('Ungültige Custom-PJSIP-Datei')
    with LOCK:
        file = read_file(filename)
        if file['source'] not in (('custom','missing') if op == 'add' else ('custom',)) or file['hash'] != data.get('hash'):
            raise ValueError('PJSIP-Datei ist nicht bearbeitbar oder hat sich geändert. Neu laden.')
        old = file['content']
        existing = [b for b in pjsip_blocks(old) if b['name']==n and b['type'] in PJSIP_FIELD_KEYS]
        if op == 'add':
            if existing or scan_number_plan()['used'].get(n):
                raise ValueError('Nummer bereits vergeben. Neu einlesen.')
            if not any(b['attrs'].get('password') for b in blocks if b['type']=='auth'):
                raise ValueError('Passwort für neue Nebenstelle erforderlich')
            updated = old.rstrip() + ('\n\n' if old.strip() else '') + '; Smartify Nebenstelle '+n+'\n' + snippet.strip() + '\n'
        else:
            all_named, editable, reason = _pjsip_triplet_state(n, pjsip_blocks(old))
            if not editable:
                raise ValueError(reason)
            if len(existing)!=3 or {b['type'] for b in existing}!=set(PJSIP_FIELD_KEYS) or any(b['header']!='['+n+']' for b in existing):
                raise ValueError('Bearbeitung nur bei vollständigen Custom-Dreiergruppen')
            if any(set(b['attrs']) - (PJSIP_FIELD_KEYS[b['type']]|{'type'})
                   or any(';' in line for line in b['raw'].splitlines()[1:]) for b in existing):
                raise ValueError('Nicht unterstützte Felder oder Kommentare gefunden. Den Rohdatei-Editor verwenden.')
            # Empty password means retain existing credentials, never clear them.
            oldpass = next(b['attrs'].get('password','') for b in existing if b['type']=='auth')
            if not next(b['attrs'].get('password','') for b in blocks if b['type']=='auth'):
                if not oldpass: raise ValueError('Bestehendes Passwort fehlt; neues angeben')
                snippet = re.sub(r'(?m)^(password=)\s*$', lambda m:m.group(1)+oldpass, snippet)
            replacement = {b['type']:b['raw'].strip()+ '\n\n' for b in pjsip_blocks(snippet)}
            updated = old
            for b in sorted(existing,key=lambda b:b['start'],reverse=True):
                updated=updated[:b['start']]+replacement[b['type']]+updated[b['end']:]
        report = lint_conf(filename, updated)
        if report['errors']:
            raise ValueError('PJSIP-Prüfung meldet Fehler: '+report['issues'][0]['message'])
        saved = write_file(filename,updated,file['hash'])
    return {'saved':True,'hash':saved['hash'],'note':'Nebenstelle '+n+' in custom/'+filename+' gespeichert (Backup bei Änderungen). Asterisk noch nicht neu geladen.', 'hint':saved['hint']}



def delete_pjsip_row(data):
    """Delete only a simple *custom* AOR/auth/endpoint triplet, with backup.

    Refuse deletion when the number is still referenced by a discovered dialplan
    or SIP Core account. This is intentionally not a general PJSIP section editor.
    """
    n = str(data.get('number', '')).strip()
    if not re.fullmatch(r'\d{2,6}', n):
        raise ValueError('Ungültige Nebenstellennummer')
    filename = str(data.get('file') or 'pjsip_custom.conf')
    if not allowed_name(filename):
        raise ValueError('Ungültige Custom-PJSIP-Datei')
    with LOCK:
        file = read_file(filename)
        if file['source'] != 'custom' or file['hash'] != data.get('hash'):
            raise ValueError('Die Custom-Datei hat sich geändert oder ist nicht bearbeitbar. Tabelle neu laden.')
        content = file['content']
        all_named, editable, reason = _pjsip_triplet_state(n, pjsip_blocks(content))
        if not editable:
            raise ValueError(reason)
        other_files = [f for f, _, blocks in _custom_pjsip_sources()
                       if f != filename and any(b['name'] == n and b['type'] in PJSIP_FIELD_KEYS for b in blocks)]
        if other_files:
            raise ValueError('Nebenstelle ist auch in Custom-Dateien definiert: ' + ', '.join(other_files))
        plan = scan_number_plan()
        refs = [f"{r['number']}@{r['context']} ({r['source']})"
                for r in plan['dialplan'] if n in r.get('targets', [])]
        accounts = [u for u in plan['sip_core_numbers'] if u['number'] == n]
        if refs or accounts:
            details = ', '.join(refs + [f"SIP Core: {u['name'] or n}" for u in accounts])
            raise ValueError('Nebenstelle '+n+' wird noch verwendet: '+details+'. Zuerst Referenzen entfernen.')
        # Remove just the validated definitions, preserving all other sections.
        updated = content
        for b in sorted(all_named, key=lambda b:b['start'], reverse=True):
            updated = updated[:b['start']] + updated[b['end']:]
        # An exact manager-generated comment may remain immediately above these
        # definitions; remove only that well-known standalone marker.
        updated = re.sub(r'(?m)^; Smartify Nebenstelle '+re.escape(n)+r'\n(?=\s*(?:\[|\Z))', '', updated)
        report = lint_conf(filename, updated)
        if report['errors']:
            raise ValueError('Löschen abgebrochen: '+report['issues'][0]['message'])
        saved = write_file(filename, updated, file['hash'])
    return {'saved': True, 'hash':saved['hash'],
            'note': 'Nebenstelle '+n+' aus custom/'+filename+' entfernt (Backup erstellt). Andere Dateien bleiben unverändert; Asterisk wurde NICHT neu geladen. SIP Core und Rufziele kontrollieren.',
            'hint':saved['hint']}


CLOUD_URI_RE = re.compile(r'sip:[A-Za-z0-9_.+%-]{1,80}@[A-Za-z0-9.-]{1,160}(?::\d{1,5})?\Z', re.I)
CLOUD_ENDPOINT_RE = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}\Z')


# Simple outgoing SIP/cloud endpoints are separate from numeric registered phones.
CLOUD_KEYS={'type','transport','disallow','allow','direct_media','force_rport',
            'rewrite_contact','rtp_symmetric','ice_support'}


def save_cloud_endpoint(data):
    name=str(data.get('name','')).strip()
    if not CLOUD_ENDPOINT_RE.fullmatch(name) or re.fullmatch(r'\d{2,6}',name):
        raise ValueError('Ungültiger Name des ausgehenden SIP-Endpoints')
    op=data.get('operation')
    if op not in ('add','edit'):
        raise ValueError('Ungültige Aktion')
    settings=data.get('settings')
    if not isinstance(settings,dict) or set(settings)-CLOUD_KEYS:
        raise ValueError('Nicht unterstützte Endpoint-Parameter')
    if settings.get('type','endpoint')!='endpoint':
        raise ValueError('Nur type=endpoint ist zulässig')
    if settings.get('disallow','all')!='all':
        raise ValueError('disallow=all ist erforderlich')
    tr=str(settings.get('transport','')).strip()
    if tr and not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',tr):
        raise ValueError('Transportname ungültig')
    codecs=str(settings.get('allow','alaw,ulaw')).strip()
    if not codecs or not re.fullmatch(r'(?:alaw|ulaw|g722|gsm|opus|g729)(?:,(?:alaw|ulaw|g722|gsm|opus|g729))*',codecs):
        raise ValueError('Codecs ungültig')
    if len(set(codecs.split(',')))!=len(codecs.split(',')):
        raise ValueError('Codecs doppelt')
    for key in ('direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support'):
        if key in settings and settings[key] not in ('yes','no'):
            raise ValueError(key+' muss yes oder no sein')
    options={'type':'endpoint', 'disallow':'all', 'allow':codecs}
    if tr: options['transport']=tr
    for key in ('direct_media','force_rport','rewrite_contact','rtp_symmetric','ice_support'):
        if key in settings:
            options[key]=settings[key]
    text='['+name+']\n'+'\n'.join(k+'='+v for k,v in options.items())+'\n'
    with LOCK:
        file=read_file('pjsip_custom.conf')
        if file['source']!='custom' or file['hash']!=data.get('hash'):
            raise ValueError('Custom-Datei wurde geändert oder fehlt. Bitte neu laden.')
        old=file['content']
        matching=[b for b in pjsip_blocks(old) if b['name']==name]
        if op=='add':
            if matching or any(e['extension']==name for e in scan_endpoints()['endpoints']):
                raise ValueError('Endpoint-Name bereits vergeben')
            updated=old.rstrip()+'\n\n'+text
        else:
            if len(matching)!=1 or matching[0]['type']!='endpoint':
                raise ValueError('Endpoint ist nicht eindeutig')
            entry=matching[0]
            if entry['header']!='['+name+']' or set(entry['attrs'])-CLOUD_KEYS or any(';' in line for line in entry['raw'].splitlines()[1:]):
                raise ValueError('Komplexer Endpoint: Rohdatei-Editor verwenden')
            updated=old[:entry['start']]+text+'\n'+old[entry['end']:]
        lint=lint_conf('pjsip_custom.conf',updated)
        if lint['errors']:
            raise ValueError('PJSIP-Prüfung: '+lint['issues'][0]['message'])
        saved=write_file('pjsip_custom.conf',updated,file['hash'])
    return {'saved':True,'hash':saved['hash'],
            'note':'Endpoint '+name+' in pjsip_custom.conf gespeichert (Backup). PJSIP-Reload noch erforderlich.',
            'hint':saved['hint']}


def group_simple_options(row):
    """Recognize only exact, losslessly understood NoOp/Dial/Hangup routes.

    Anything with macros, conditions, extra Dial arguments, or unsupported
    targets is read-only and remains available in the raw editor.
    """
    if not row.get('editable'):
        return None
    steps = row['steps']
    if len(steps) not in (2, 3) or steps[-1].strip().lower() != 'hangup()':
        return None
    if len(steps) == 3:
        header = re.fullmatch(r'NoOp\(([^\r\n();]*)\)', steps[0], re.I)
        if not header:
            return None
        description = header.group(1)
        dial = steps[1]
    else:
        description = ''
        dial = steps[0]
    match = re.fullmatch(r'Dial\((.+),(\d{1,3})\)', dial, re.I)
    if not match or not 5 <= int(match.group(2)) <= 120:
        return None
    locals_, externals = [], []
    for part in match.group(1).split('&'):
        part = part.strip()
        local = re.fullmatch(r'\$\{PJSIP_DIAL_CONTACTS\((\d{2,6})\)\}', part, re.I)
        external = re.fullmatch(r'PJSIP/([A-Za-z][A-Za-z0-9_.-]{0,63})/(sip:[A-Za-z0-9_.+%-]{1,80}@[A-Za-z0-9.-]{1,160}(?::\d{1,5})?)', part, re.I)
        if local:
            locals_.append(local.group(1))
        elif external:
            externals.append({'endpoint': external.group(1), 'uri': external.group(2)})
        else:
            return None
    if not (locals_ or externals) or len(externals) > 1 or len(locals_) > 20 or len(set(locals_)) != len(locals_):
        return None
    return {'targets': locals_, 'external_targets': externals,
            'timeout': int(match.group(2)), 'description': description, 'hangup': True}


def save_group_row(data):
    n = str(data.get('number','')).strip()
    context = str(data.get('context','default')).strip()
    name = data.get('file','extensions.conf')
    op = data.get('operation')
    if not re.fullmatch(r'\d{2,6}',n) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',context):
        raise ValueError('Ungültige Nummer oder Kontext')
    if name not in ('extensions.conf','extensions_custom.conf') or op not in ('add','edit'):
        raise ValueError('Nur vorhandene Custom-Dialplandateien erlaubt')
    targets=data.get('targets')
    if not isinstance(targets,list) or len(targets)>20 or any(not isinstance(x,str) or not re.fullmatch(r'\d{2,6}',x) for x in targets) or len(set(targets))!=len(targets):
        raise ValueError('Mindestens eine vorhandene, eindeutige SIP-Nebenstelle auswählen')
    external=data.get('external') or None
    # Frontend supports one external target; old API body remains compatible.
    if external:
        if not isinstance(external,dict) or not CLOUD_ENDPOINT_RE.fullmatch(str(external.get('endpoint',''))) or not CLOUD_URI_RE.fullmatch(str(external.get('uri',''))):
            raise ValueError('Externer PJSIP-Endpoint oder SIP-URI ungültig')
    if not targets and not external:
        raise ValueError('Mindestens ein lokales oder externes Ziel angeben')
    description=data.get('description')
    if description is None:
        description='Smartify Rufgruppe '+n
    if not isinstance(description,str) or len(description)>120 or re.search(r'[\r\n();]',description):
        raise ValueError('NoOp-Beschreibung enthält unzulässige Zeichen')
    seconds=data.get('timeout',30)
    if isinstance(seconds,bool) or not isinstance(seconds,int) or not 5<=seconds<=120:
        raise ValueError('Rufdauer 5–120 Sekunden erforderlich')
    with LOCK:
        file=read_file(name)
        if file['source']!='custom' or file['hash']!=data.get('hash'):
            raise ValueError('Nur bestehende Custom-Datei mit passender Versionskennung bearbeitbar')
        plan=scan_number_plan()
        known={x['extension'] for x in plan['endpoints']}
        if not set(targets) <= known: raise ValueError('Nicht vorhandene SIP-Nebenstelle in Zielen')
        rows=[r for r in plan['dialplan'] if r['number']==n and r['context']==context]
        if op=='add' and plan['used'].get(n): raise ValueError('Nummer bereits vergeben')
        source_rows=[r for r in rows if r['source']=='custom/'+name]
        if op=='edit' and (len(source_rows)!=1 or not group_simple_options(source_rows[0])):
            raise ValueError('Dialplan-Ziel ist in der gewählten Custom-Datei nicht eindeutig oder besitzt einen komplexen Ablauf. Rohdatei-Editor verwenden.')
        content=file['content']
        # Locate exact context boundaries and exact numeric extension stanza.
        heads=list(re.finditer(r'^[ \t]*\[([^]\r\n]+)\][^\r\n]*$',content,re.M))
        contexts=[(h, heads[i+1].start() if i+1<len(heads) else len(content)) for i,h in enumerate(heads) if h.group(1).strip()==context]
        if len(contexts)!=1: raise ValueError('Kontext ['+context+'] ist nicht genau einmal in custom/'+name+' vorhanden')
        h,end=contexts[0]
        seg=content[h.end():end]
        matches=list(re.finditer(r'^[ \t]*exten[ \t]*=>[ \t]*(\d{2,6})[ \t]*,[ \t]*1[ \t]*,[^\n]*$',seg,re.M|re.I))
        matched=[m for m in matches if m.group(1)==n]
        dialparts=['${PJSIP_DIAL_CONTACTS('+t+')}' for t in targets]
        if external:
            if external['endpoint'] not in {x['extension'] for x in plan['endpoints']}:
                raise ValueError('Externer PJSIP-Endpoint '+external['endpoint']+' nicht erkannt. Zuerst in Asterisk konfigurieren.')
            dialparts.append('PJSIP/'+external['endpoint']+'/'+external['uri'])
        block='; Smartify Dialplan '+n+'\n'+'exten => '+n+',1,NoOp('+description+')\n' + 'same => n,Dial('+'&'.join(dialparts)+','+str(seconds)+')\n'+'same => n,Hangup()\n'
        if op=='edit':
            if len(matched)!=1: raise ValueError('Dialplan-Definition in Quelldatei nicht eindeutig')
            m=matched[0]
            finish=next((other.start() for other in matches if other.start()>m.start()),len(seg))
            # Do not consume following blank/comment lines or arbitrary directives.
            stanza=seg[m.start():finish]
            lines=stanza.splitlines(keepends=True)
            count=1
            while count<len(lines) and re.match(r'^\s*same\s*=>\s*(?:n|\d+)\s*,',lines[count],re.I): count+=1
            if count < len(lines) and any(x.strip() and not x.lstrip().startswith(';') for x in lines[count:]):
                raise ValueError('Komplexer Dialplan-Block; nicht automatisch überschreiben')
            pos=h.end()+m.start()
            stop=pos+len(''.join(lines[:count]))
            updated=content[:pos]+block+content[stop:]
        else:
            updated=content[:end].rstrip('\n')+'\n'+block+'\n'+content[end:]
        lint=lint_conf(name,updated)
        if lint['errors']: raise ValueError('Dialplan-Prüfung: '+lint['issues'][0]['message'])
        saved=write_file(name,updated,file['hash'])
    return {'saved':True,'hash':saved['hash'],'note':'Rufgruppe '+n+' in custom/'+name+' gespeichert (Backup erstellt). Dialplan-Reload noch erforderlich.','hint':saved['hint']}



def wizard_password_targets():
    """Expose only identities and password presence, never secret values."""
    active = read_active_sip_core()
    rows = []
    for u in active.get('users') or []:
        if isinstance(u, dict) and re.fullmatch(r'\\d{2,6}', str(u.get('extension',''))):
            rows.append({'number': str(u['extension']), 'kind': 'sip_core',
                         'name': str(u.get('display_name') or u.get('ha_username') or '')[:100],
                         'configured': bool(u.get('password'))})
    for e in scan_endpoints().get('endpoints') or []:
        n = str(e.get('extension') or '')
        if re.fullmatch(r'\\d{2,6}', n) and not any(x['number']==n and x['kind']=='pjsip' for x in rows):
            rows.append({'number': n, 'kind': 'pjsip', 'name': str(e.get('display_name') or '')[:100],
                         'configured': bool(e.get('has_password'))})
    return {'targets': rows, 'sip_core_hash': canon_hash(active)}


def wizard_rotate_passwords(data):
    """Rotate only selected existing SIP Core credentials, using existing backup/flow mechanism."""
    selected = data.get('numbers')
    password = data.get('password')
    if data.get('confirm') != 'PASSWOERTER AENDERN':
        raise ValueError('Explizite Bestätigung fehlt')
    if not isinstance(selected, list) or not 1 <= len(selected) <= 100 or len(set(selected)) != len(selected):
        raise ValueError('1–100 eindeutige Nebenstellen auswählen')
    if not all(isinstance(n, str) and re.fullmatch(r'\\d{2,6}', n) for n in selected):
        raise ValueError('Ungültige Nebenstelle')
    if not isinstance(password, str) or not 12 <= len(password) <= 128 or re.search(r'[;#\\s\\x00-\\x1f]', password):
        raise ValueError('Passwort benötigt 12–128 Zeichen ohne Leerzeichen oder Steuerzeichen')
    cfg = read_active_sip_core()
    if canon_hash(cfg) != data.get('active_hash'):
        raise ValueError('SIP-Core-Konfiguration wurde geändert. Liste erneut laden.')
    copied = copy.deepcopy(cfg)
    users = {str(u.get('extension')): u for u in copied.get('users') or [] if isinstance(u, dict)}
    if any(n not in users for n in selected):
        raise ValueError('Mindestens ein Teilnehmer ist nicht in SIP Core vorhanden. Nicht geändert.')
    for number in selected:
        users[number]['password'] = password
    # apply_sip_core performs its own optimistic lock, secure backup and verification.
    result = apply_sip_core(dump_yaml(copied), data['active_hash'])
    return {'changed': len(selected), 'kind': 'sip_core', 'message': 'SIP-Core-Passwörter geändert. SIP-Clients müssen neu angemeldet werden.',
            'applied': bool(result)}


def stage_sip_core_user(content, extension, ha_username, display_name, password=''):
    """Stage only; do not change live SIP Core. Only existing Asterisk endpoints."""
    extension = str(extension).strip()
    ha_username = str(ha_username).strip() if isinstance(ha_username, str) else ''
    display_name = str(display_name).strip() if isinstance(display_name, str) else ''
    if not re.fullmatch(r'\d{2,6}', extension):
        raise ValueError('Ungültige Nebenstelle')
    if extension not in {e['extension'] for e in scan_endpoints()['endpoints']}:
        raise ValueError('Nebenstelle ' + extension + ' existiert nicht in den lesbaren Asterisk-Konfigurationsdateien. Zuerst dort anlegen.')
    if not ha_username or len(ha_username) > 100 or not display_name or len(display_name) > 100 or '\n' in ha_username + display_name:
        raise ValueError('HA-Benutzer und Anzeigename angeben (maximal 100 Zeichen)')
    cfg = parse_yaml(content)
    users = cfg.setdefault('users', [])
    if not isinstance(users, list):
        raise ValueError('users ist keine Liste')
    matches = [u for u in users if isinstance(u, dict) and str(u.get('extension', '')).strip() == extension]
    if len(matches) > 1:
        raise ValueError('Doppelte Nebenstelle in SIP-Core-Konfiguration. Zuerst manuell bereinigen.')
    if matches:
        if password:
            raise ValueError('Passwortfeld beim Bearbeiten bestehender Nutzer leer lassen. Passwortwechsel erfolgt separat.')
        entry = matches[0]
        entry['ha_username'] = ha_username
        entry['display_name'] = display_name
        created = False
    else:
        if not isinstance(password, str) or len(password) < 1 or len(password) > 128 or any(ch in password for ch in '\r\n\x00'):
            raise ValueError('Für einen neuen SIP-Core-Teilnehmer ein eigenes Passwort mit 1–128 Zeichen angeben')
        entry = {'extension': extension, 'ha_username': ha_username, 'display_name': display_name, 'password': password}
        users.append(entry)
        created = True
    return {'content': dump_yaml(cfg), 'created': created,
            'message': ('Teilnehmer zum Entwurf hinzugefügt' if created else 'Vorhandener Teilnehmer im Entwurf aktualisiert') + ' – NICHT aktiv übernommen'}


# ---------------------------------------------------------------------------
# YAML helpers, SIP Core (active config, merge, diff, apply)
# ---------------------------------------------------------------------------
PROTECTED_KEYS = ('users', 'backup_user')   # never taken over from generated snippets
REPLACE_KEYS = {'camera_by_caller'}          # replaced as a whole, so removed callers disappear
RE_PASSWORD_LINE = re.compile(r'^([+\- ]?\s*(?:-\s+)?password:\s*).+$', re.M)


def need_yaml():
    if yaml is None:
        raise ValueError('PyYAML fehlt im Image. Add-on neu bauen (Aktualisieren / Neu erstellen).')


def parse_yaml(text):
    need_yaml()
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_SIZE:
        raise ValueError('Ungültiger oder zu langer YAML-Inhalt')
    try:
        data = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, 'problem_mark', None)
        where = f' (Zeile {mark.line + 1}, Spalte {mark.column + 1})' if mark else ''
        raise ValueError('YAML-Fehler' + where + ': ' + str(getattr(exc, 'problem', exc))[:120]) from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError('Die SIP-Core-Konfiguration muss aus Schlüssel-Wert-Paaren bestehen')
    return data


def dump_yaml(obj):
    need_yaml()
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000) if obj else ''


def mask_secrets(text):
    return RE_PASSWORD_LINE.sub(lambda m: m.group(1) + '••••••', text)


def text_diff(old, new, old_name='vorher', new_name='nachher'):
    lines = difflib.unified_diff(old.splitlines(True), new.splitlines(True), old_name, new_name, n=2)
    return mask_secrets(''.join(lines))


def canon_hash(obj):
    return digest(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def deep_merge(base, extra):
    out = dict(base)
    for key, val in extra.items():
        if key not in REPLACE_KEYS and isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def merge_sip_core(base_text, snippet_text):
    base, snippet = parse_yaml(base_text), parse_yaml(snippet_text)
    skipped = [k for k in PROTECTED_KEYS if k in snippet]
    for key in skipped:
        snippet.pop(key)
    merged = deep_merge(base, snippet)
    new = dump_yaml(merged)
    return {'content': new, 'diff': text_diff(dump_yaml(base), new), 'protected_skipped': skipped,
            'note': 'Kommentare aus dem Entwurf gehen beim Zusammenführen verloren.' if '#' in base_text else ''}


def read_active_sip_core():
    cfg = core_api('GET', 'sip-core/config')
    if not isinstance(cfg, dict):
        raise ValueError('SIP Core hat keine Konfiguration geliefert')
    return cfg



# Read-only Supervisor metadata; never return the Asterisk secret to the browser.
def asterisk_auto_secret():
    """Resolve the shared password from Asterisk's generated default PJSIP auth.

    Supervisor /addons/<slug>/info omits options on recent HA versions.
    Never expose the password via a response, log or exception.
    """
    path = DEFAULT / 'pjsip_default.conf'
    if path.is_symlink() or DEFAULT.is_symlink() or not path.is_file():
        raise ValueError('Asterisk pjsip_default.conf fehlt oder ist nicht lesbar')
    if path.stat().st_size > MAX_SIZE:
        raise ValueError('Asterisk-Standardkonfiguration ist zu groß')
    blocks = pjsip_blocks(path.read_text(encoding='utf-8'))
    auth = [b for b in blocks if b.get('type') == 'auth' and
            b.get('attrs', {}).get('auth_type', 'userpass') == 'userpass']
    secrets_found = {b['attrs'].get('password', '') for b in auth if b['attrs'].get('password')}
    if len(secrets_found) != 1:
        raise ValueError('Kein eindeutiges gemeinsames Asterisk-Auth-Passwort gefunden')
    secret = next(iter(secrets_found))
    if not secret or secret in ('*', '********', 'REDACTED'):
        raise ValueError('Asterisk-Passwort ist nicht verfügbar')
    # This is evidence of a common generated auth credential, not proof that
    # the auto_add switch is active: that option is not visible here.
    return True, secret


def auto_secret_preview():
    enabled, secret = asterisk_auto_secret()
    cfg = read_active_sip_core()
    users = cfg.get('users') or []
    if not isinstance(users, list):
        raise ValueError('SIP Core users ist keine Liste')
    rows = []
    seen = set()
    for user in users:
        if not isinstance(user, dict):
            raise ValueError('Ungültiger SIP-Core-Teilnehmer')
        ext = str(user.get('extension') or '')
        if ext in seen or not re.fullmatch(r'\d{2,8}', ext):
            raise ValueError('Doppelte/ungültige SIP-Core-Nebenstellen; keine Synchronisierung')
        seen.add(ext)
        rows.append({'extension': ext, 'display_name': str(user.get('display_name') or '')[:100],
                     'change': user.get('password') != secret if secret else False})
    return {'auto_add_enabled': enabled, 'secret_present': bool(secret),
            'active_hash': canon_hash(cfg), 'users': rows,
            'count_changed': sum(u['change'] for u in rows),
            'note': 'Passwörter werden nur nach ausdrücklicher Bestätigung überschrieben. Manuelle Asterisk-Nebenstellen können eigene Passwörter haben.'}


def auto_secret_sync(expected_hash, confirm):
    if confirm != 'ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN':
        raise ValueError('Explizite Bestätigung fehlt')
    enabled, secret = asterisk_auto_secret()
    if not enabled or not secret:
        raise ValueError('Asterisk Auto Add Extensions/Secret nicht aktiv oder nicht gesetzt')
    if not isinstance(secret, str) or not secret.strip():
        raise ValueError('Auto Add Secret ist leer')
    active = read_active_sip_core()
    if canon_hash(active) != expected_hash:
        raise ValueError('SIP-Core-Konfiguration wurde verändert; zuerst Vorschau aktualisieren')
    cfg = copy.deepcopy(active)
    users = cfg.get('users')
    if not isinstance(users, list) or not users:
        raise ValueError('Keine SIP-Core-Benutzer vorhanden')
    seen = set()
    changed = 0
    for user in users:
        if not isinstance(user, dict):
            raise ValueError('Ungültiger SIP-Core-Benutzer')
        ext = str(user.get('extension') or '')
        if not re.fullmatch(r'\d{2,8}', ext) or ext in seen:
            raise ValueError('Doppelte oder ungültige SIP-Core-Nebenstelle')
        seen.add(ext)
        if user.get('password') != secret:
            user['password'] = secret
            changed += 1
    if not changed:
        return {'applied': False, 'changed': 0, 'verified': True, 'note': 'Alle SIP-Core-Passwörter stimmen bereits überein.'}
    result = apply_sip_core(dump_yaml(cfg), expected_hash)
    return {'applied': result['applied'], 'verified': result['verified'], 'changed': changed,
            'backup': result.get('backup'), 'note': result['note']}

def stage_auto_answer_allowlist(content, extension, enabled, allowed):
    """Modify a SIP-Core YAML draft only; preserve users, credentials and other settings."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError('Zuerst die aktive SIP-Core-Konfiguration als Entwurf laden')
    extension = str(extension).strip()
    if not re.fullmatch(r'\d{2,6}', extension):
        raise ValueError('Ungültige SIP-Core-Nebenstelle')
    if not isinstance(enabled, bool) or not isinstance(allowed, list):
        raise ValueError('Auto Answer und Anruferliste müssen gültig sein')
    if len(allowed) > 100 or any(not re.fullmatch(r'\d{2,6}', str(n)) for n in allowed):
        raise ValueError('Nur numerische SIP-Nebenstellen als erlaubte Anrufer')
    cfg = parse_yaml(content)
    if not isinstance(cfg, dict):
        raise ValueError('Ungültige SIP-Core-Konfiguration')
    users = cfg.get('users') or []
    if extension not in {str(u.get('extension')) for u in users if isinstance(u, dict)}:
        raise ValueError('Zielnebenstelle ist nicht als SIP-Core-Benutzer konfiguriert')
    popup = cfg.setdefault('popup_config', {})
    if not isinstance(popup, dict):
        raise ValueError('popup_config muss ein Objekt sein')
    smartify = popup.setdefault('smartify', {})
    if not isinstance(smartify, dict):
        raise ValueError('popup_config.smartify muss ein Objekt sein')
    mapping = smartify.setdefault('auto_answer_by_extension', {})
    if not isinstance(mapping, dict):
        raise ValueError('auto_answer_by_extension muss eine Zuordnung sein')
    if enabled:
        selected = sorted(set(map(str, allowed)), key=int)
        if not selected:
            raise ValueError('Mindestens einen erlaubten Anrufer auswählen')
        if extension in selected:
            raise ValueError('Eigene Nebenstelle darf nicht als Anrufer freigegeben werden')
        mapping[extension] = selected
    else:
        mapping.pop(extension, None)
    # Upstream's global auto_answer accepts EVERY caller, so always disable it.
    cfg['auto_answer'] = False
    return {'content': dump_yaml(cfg), 'extension': extension,
            'enabled': enabled, 'allowed': mapping.get(extension, []),
            'note': 'Nur Entwurf geändert; SIP Core noch nicht aktualisiert. Unterschiede prüfen und bewusst übernehmen.'}


def active_sip_core_view():
    cfg = read_active_sip_core()
    users = [{'extension': str(u.get('extension', '')), 'ha_username': str(u.get('ha_username', '')),
              'display_name': str(u.get('display_name', ''))} for u in cfg.get('users') or [] if isinstance(u, dict)]
    smartify = (cfg.get('popup_config') or {}).get('smartify') or {}
    rules = smartify.get('auto_answer_by_extension') or {}
    return {'content': dump_yaml(cfg), 'hash': canon_hash(cfg), 'users': users,
            'auto_answer_by_extension': rules if isinstance(rules, dict) else {},
            'global_auto_answer': cfg.get('auto_answer', False)}


def validate_sip_core_cfg(cfg):
    users = cfg.get('users')
    if not isinstance(users, list) or not users:
        raise ValueError('users fehlt oder ist leer – SIP Core würde ohne Teilnehmer starten')
    for user in users:
        if not isinstance(user, dict) or not str(user.get('extension', '')).strip() or not str(user.get('ha_username', '')).strip():
            raise ValueError('Jeder Eintrag unter users braucht extension und ha_username')
        if 'HIER_BESTEHENDES' in str(user.get('password', '')):
            raise ValueError(f'Platzhalter-Passwort bei Nebenstelle {user.get("extension")} – echtes Passwort eintragen')
    popup = cfg.get('popup_config')
    if popup is not None and not isinstance(popup, dict):
        raise ValueError('popup_config muss ein Objekt sein')


def is_subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and is_subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(is_subset(a, b) for a, b in zip(expected, actual))
    return expected == actual or str(expected) == str(actual)


def diff_against_active(content):
    new_cfg = parse_yaml(content)
    active = read_active_sip_core()
    warnings = []
    old_users = {str(u.get('extension')) for u in active.get('users', []) if isinstance(u, dict)}
    new_users = {str(u.get('extension')) for u in new_cfg.get('users', []) if isinstance(u, dict)}
    if old_users - new_users:
        warnings.append('Folgende Teilnehmer würden entfernt: ' + ', '.join(sorted(old_users - new_users)))
    try:
        validate_sip_core_cfg(new_cfg)
    except ValueError as exc:
        warnings.append(str(exc))
    return {'diff': text_diff(dump_yaml(active), dump_yaml(new_cfg), 'aktiv in SIP Core', 'Entwurf'),
            'active_hash': canon_hash(active), 'warnings': warnings,
            'changed': canon_hash(active) != canon_hash(new_cfg)}


def apply_sip_core(content, expected_active_hash):
    """Write a validated configuration into the SIP Core integration via its options flow.
    Aborts on any unexpected form, keeps a backup of the active configuration and verifies afterwards."""
    new_cfg = parse_yaml(content)
    validate_sip_core_cfg(new_cfg)
    with LOCK:
        active = read_active_sip_core()
        if canon_hash(active) != expected_active_hash:
            raise ValueError('Die aktive SIP-Core-Konfiguration wurde inzwischen geändert. Unterschiede neu laden.')
        entries = core_api('GET', 'config/config_entries/entry?domain=sip_core') or []
        if len(entries) != 1:
            raise ValueError(f'Erwartet genau eine SIP-Core-Integration, gefunden: {len(entries)}')
        flow = core_api('POST', 'config/config_entries/options/flow', {'handler': entries[0]['entry_id']})
        flow_id = flow.get('flow_id') if isinstance(flow, dict) else None
        try:
            if not flow_id or flow.get('type') != 'form':
                raise ValueError('SIP Core bietet keinen Konfigurationsdialog an')
            schema = flow.get('data_schema') or []
            if len(schema) != 1:
                raise ValueError('Unerwarteter SIP-Core-Dialog (Felder: ' + ', '.join(str(f.get('name')) for f in schema)
                                 + '). Nichts geändert – bitte manuell übernehmen.')
            field = schema[0]
            current = (field.get('description') or {}).get('suggested_value', field.get('default'))
            selector = field.get('selector') or {}
            if 'object' in selector or isinstance(current, dict):
                value = new_cfg
            elif isinstance(current, str) and current.lstrip().startswith('{'):
                value = json.dumps(new_cfg, ensure_ascii=False, indent=2)
            elif isinstance(current, str) or 'text' in selector or 'code' in selector:
                value = dump_yaml(new_cfg)
            else:
                raise ValueError(f'Unbekannter Feldtyp im SIP-Core-Dialog ({field.get("name")}). Nichts geändert.')
            backup_dir = DATA_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backup_dir / f'sip_core_active_{stamp}.json'
            backup.write_text(json.dumps(active, ensure_ascii=False, indent=2), encoding='utf-8')
            os.chmod(backup, 0o600)
            prune_backups(backup_dir, 'sip_core_active_*.json')
            result = core_api('POST', f'config/config_entries/options/flow/{flow_id}', {field['name']: value}) or {}
            if result.get('type') == 'create_entry':
                flow_id = None
            else:
                raise ValueError('SIP Core hat die Konfiguration abgelehnt: ' + json.dumps(result.get('errors') or result)[:200])
        finally:
            if flow_id:
                try:
                    core_api('DELETE', f'config/config_entries/options/flow/{flow_id}')
                except ValueError:
                    pass
        time.sleep(1.0)
        verified = False
        try:
            verified = is_subset(new_cfg, read_active_sip_core())
        except ValueError:
            pass
    audit('sip_core_applied', detail=f'verified={verified};backup={backup.name}')
    return {'applied': True, 'verified': verified, 'backup': backup.name,
            'note': ('Übernommen und geprüft.' if verified else 'Übernommen, Prüfung nicht eindeutig – Konfiguration in SIP Core kontrollieren.')
                    + ' Frontend auf allen Geräten neu laden.'}


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------
WEAK_PASSWORDS = {'1234', '12345', '123456', '1234567', '12345678', 'test', 'test123', 'test1234', 'password', 'passwort', 'admin', 'sip'}


def check_users(source='auto', content=None):
    issues = []
    add = lambda level, msg: issues.append({'level': level, 'message': msg})
    if source == 'content':
        cfg, origin = parse_yaml(content or ''), 'übergebener Entwurf'
    else:
        try:
            cfg, origin = read_active_sip_core(), 'aktive SIP-Core-Konfiguration'
        except ValueError as exc:
            draft = read_sip_core()['content']
            if not draft.strip():
                raise ValueError('Weder aktive SIP-Core-Konfiguration erreichbar noch Entwurf vorhanden: ' + str(exc)) from None
            cfg, origin = parse_yaml(draft), 'Manager-Entwurf (SIP Core nicht erreichbar)'
    endpoints = {e['extension'] for e in scan_endpoints().get('endpoints', [])}
    if not endpoints:
        add('info', 'Keine Asterisk-Nebenstellen gefunden – Abgleich mit Asterisk übersprungen.')
    try:
        persons = ha_persons()
    except ValueError as exc:
        persons = []
        add('info', 'HA-Personen nicht abrufbar, Benutzerabgleich übersprungen: ' + str(exc)[:100])
    ids = {p['user_id'] for p in persons if p['user_id']}
    names = {p['name'] for p in persons if p['name']}
    users = [u for u in cfg.get('users') or [] if isinstance(u, dict)]
    if not users:
        add('error', 'users ist leer – SIP Core kann niemanden anmelden.')
    seen_ext, seen_ha = {}, {}
    for user in users:
        ext, ha, pw = str(user.get('extension', '')).strip(), str(user.get('ha_username', '')).strip(), str(user.get('password', ''))
        label = f'Nebenstelle {ext or "?"} ({ha or "ohne ha_username"})'
        if not ext or not ha:
            add('error', label + ': extension und ha_username sind Pflicht.')
        if ext in seen_ext:
            add('error', f'{label}: Nebenstelle mehrfach vergeben (auch bei {seen_ext[ext]}).')
        if ha and ha in seen_ha:
            add('error', f'{label}: ha_username mehrfach vergeben.')
        seen_ext[ext], seen_ha[ha] = ha, ext
        if endpoints and ext and ext not in endpoints:
            add('error', f'{label}: In Asterisk gibt es keine Nebenstelle {ext}. Anmeldung schlägt mit „No matching endpoint“ fehl.')
        if persons and ha and ha not in ids and ha not in names:
            close = [n for n in names if n.lower() == ha.lower()]
            add('error', f'{label}: passt zu keinem HA-Benutzer. SIP Core vergleicht mit Benutzer-ID oder Anzeigenamen'
                + (f' – gemeint ist vermutlich „{close[0]}“ (Groß-/Kleinschreibung).' if close else '.'))
        if not pw:
            add('warn', f'{label}: kein Passwort gesetzt.')
        elif len(pw) < 10 or pw.lower() in WEAK_PASSWORDS:
            add('warn', f'{label}: schwaches Passwort – mindestens 10 Zeichen, keine Standardwerte.')
    backup = cfg.get('backup_user')
    if not isinstance(backup, dict) or not backup.get('extension'):
        add('warn', 'Kein backup_user gesetzt. Meldet sich ein nicht eingetragener HA-Benutzer an, startet SIP Core nicht und Karten verschwinden.')
    else:
        b_ext = str(backup.get('extension'))
        if endpoints and b_ext not in endpoints:
            add('error', f'backup_user {b_ext}: In Asterisk gibt es diese Nebenstelle nicht.')
        bpw = str(backup.get('password', ''))
        if bpw and (len(bpw) < 10 or bpw.lower() in WEAK_PASSWORDS):
            add('warn', f'backup_user {b_ext}: schwaches Passwort.')
    covered = set(seen_ha)
    for person in persons:
        if person['user_id'] and person['user_id'] not in covered and person['name'] not in covered:
            add('info' if isinstance(backup, dict) else 'warn',
                f'{person["name"]}: kein eigener SIP-Eintrag' + (' – nutzt backup_user.' if isinstance(backup, dict) else ' und kein backup_user.'))
    popup = cfg.get('popup_config') if isinstance(cfg.get('popup_config'), dict) else {}
    if popup and not isinstance(popup.get('extensions'), dict):
        add('warn', 'popup_config.extensions fehlt. Das Original-Popup erwartet den Schlüssel – mindestens „extensions: {}“ setzen.')
    for key in list((popup.get('extensions') or {}).keys()) + list(((popup.get('smartify') or {}).get('camera_by_caller') or {}).keys()):
        if endpoints and str(key) not in endpoints:
            add('info', f'Popup-Eintrag für {key}: keine gleichnamige Asterisk-Nebenstelle (bei externen Anrufern normal).')
    if not any(i['level'] in ('error', 'warn') for i in issues):
        add('ok', 'Keine Probleme gefunden.')
    return {'source': origin, 'issues': issues, 'users': len(users), 'endpoints': len(endpoints), 'persons': len(persons)}


RE_INCLUDE = re.compile(r'^#\s*(include|tryinclude|exec)\b', re.I)


def defined_pjsip_objects(exclude_custom=None):
    """(name, type) of all pjsip objects in mounted files; templates resolved by their name."""
    objects = set()
    for folder in (DEFAULT, CUSTOM):
        if not folder.is_dir():
            continue
        for path in folder.glob('pjsip*.conf'):
            if folder == CUSTOM and path.name == exclude_custom or path.is_symlink() or path.stat().st_size > MAX_SIZE:
                continue
            try:
                objects |= _pjsip_objects(path.read_text(encoding='utf-8'))
            except (OSError, UnicodeError):
                pass
    return objects


def _pjsip_objects(content):
    objects, section, decl, otype = set(), None, '', None
    def close():
        if section and not decl.rstrip().endswith('!)') and '(!' not in decl:
            t = otype or next((k for k in ('endpoint', 'aor', 'auth', 'transport', 'registration', 'identify')
                               if k in decl.split(']', 1)[1].lower()), None)
            if t:
                objects.add((section, t))
    for line in content.splitlines():
        clean = line.split(';', 1)[0].strip()
        if clean.startswith('[') and ']' in clean:
            close()
            section, decl, otype = clean[1:clean.index(']')], clean, None
        elif section and '=' in clean and clean.split('=', 1)[0].strip().lower() == 'type':
            otype = clean.split('=', 1)[1].strip().lower()
    close()
    return objects


def lint_conf(name, content):
    if not allowed_name(name):
        raise ValueError('Datei nicht zugelassen')
    if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_SIZE:
        raise ValueError('Ungültiger Inhalt')
    issues = []
    add = lambda line, level, msg, fix=None: issues.append({'line': line, 'level': level, 'message': msg, **({'fix': fix} if fix else {})})
    is_pjsip, is_ext = name.startswith('pjsip'), name.startswith('extensions')
    section, decl, otype, seen, refs = None, '', None, {}, []
    started_context = False

    def close(line_no):
        if is_pjsip and section and '(!' not in decl:
            t = otype or next((k for k in ('endpoint', 'aor', 'auth', 'transport') if k in decl.split(']', 1)[1].lower()), None)
            if t:
                key = (section, t)
                if key in seen:
                    add(line_no, 'error', f'[{section}] vom Typ {t} doppelt definiert (zuerst Zeile {seen[key]}).')
                seen.setdefault(key, line_no)

    start_line = 0
    for no, raw in enumerate(content.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(';'):
            continue
        if stripped.startswith('#'):
            if not RE_INCLUDE.match(stripped):
                add(no, 'error', 'Kommentare beginnen in Asterisk mit „;“, nicht mit „#“ (erzeugt „Unknown directive“).', 'hash_comment')
            continue
        clean = stripped.split(';', 1)[0].strip()
        if clean.startswith('['):
            if ']' not in clean:
                add(no, 'error', 'Abschnitt ohne schließende Klammer „]“.')
                continue
            close(start_line)
            section, decl, otype, start_line = clean[1:clean.index(']')], clean, None, no
            if not section:
                add(no, 'error', 'Leerer Abschnittsname.')
            started_context = False
            continue
        if '=' not in clean:
            add(no, 'warn', 'Zeile ohne „=“ wird von Asterisk ignoriert.')
            continue
        key, val = (x.strip() for x in clean.split('=', 1))
        val = val.lstrip('>').strip()
        if section is None and not (is_ext and key.lower() in ('static', 'writeprotect', 'autofallthrough', 'clearglobalvars')):
            add(no, 'warn', 'Einstellung steht vor dem ersten [Abschnitt].')
        lk = key.lower()
        if is_pjsip:
            if lk == 'type':
                otype = val.lower()
            elif lk in ('aors', 'auth', 'outbound_auth'):
                refs.extend((no, 'aor' if lk == 'aors' else 'auth', r.strip()) for r in val.split(',') if r.strip())
            elif lk == 'password' and (len(val) < 10 or val.lower() in WEAK_PASSWORDS):
                add(no, 'warn', f'Schwaches Passwort in [{section}].')
        if is_ext:
            if lk == 'exten':
                started_context = True
                if not re.match(r'^[^,]+,\s*(\d+|n|hint)\s*(\(\w+\))?\s*,', val):
                    add(no, 'warn', 'exten-Zeile: erwartet „Nummer,Priorität,Anwendung(...)“.')
            elif lk == 'same' and not started_context:
                add(no, 'error', '„same =>“ ohne vorhergehende exten-Zeile in diesem Abschnitt.')
            if val.count('(') != val.count(')'):
                add(no, 'warn', 'Klammern ( ) nicht ausgeglichen.')
    close(start_line)
    if is_pjsip and refs:
        known = defined_pjsip_objects(exclude_custom=name) | {k for k in seen}
        for line_no, kind, ref in refs:
            if (ref, kind) not in known:
                add(line_no, 'warn', f'Verweis auf {kind} „{ref}“, die nirgends definiert ist.')
    issues.sort(key=lambda i: (i['line'], i['level']))
    return {'issues': issues, 'errors': sum(i['level'] == 'error' for i in issues),
            'warnings': sum(i['level'] == 'warn' for i in issues)}


# ---------------------------------------------------------------------------
# AMI (read-only status + whitelisted commands)
# ---------------------------------------------------------------------------
AMI_SAFE_COMMANDS = {'pjsip show contacts', 'pjsip show endpoints', 'pjsip show transports', 'pjsip show registrations',
                     'pjsip show aors', 'core show version', 'core show channels', 'dialplan show'}
AMI_RELOAD_COMMANDS = {'pjsip reload', 'dialplan reload'}
RE_AMI_PARAM_COMMANDS = [re.compile(r'^pjsip show (endpoint|aor|auth|contact) [A-Za-z0-9_.+@-]{1,60}$'),
                         re.compile(r'^dialplan show [A-Za-z0-9_.+-]{0,40}@?[A-Za-z0-9_-]{1,40}$')]


def ami_command_allowed(command):
    command = re.sub(r'\s+', ' ', str(command or '')).strip().lower()
    if command in AMI_SAFE_COMMANDS or command in AMI_RELOAD_COMMANDS or any(r.fullmatch(command) for r in RE_AMI_PARAM_COMMANDS):
        return command
    raise ValueError('Befehl nicht freigegeben')


def ami_host_effective(opt):
    """AMI-Host aus dem Asterisk-Slug ableiten, falls kein eigener Host gesetzt ist."""
    configured = str(opt.get('ami_host') or '').strip()
    if configured and configured.lower() not in ('auto', '127.0.0.1', 'localhost', '::1'):
        return configured
    addon_slug = str(opt.get('asterisk_slug') or slug).strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}', addon_slug):
        raise ValueError('AMI-Host automatisch: ungültiger Asterisk-Add-on-Slug')
    return addon_slug.replace('_', '-')


class AmiSession:
    """Minimal AMI client. Every action carries its own ActionID and only the matching
    response is accepted, so unsolicited events (e.g. FullyBooted after login) are skipped."""

    def __init__(self):
        opt = get_options()
        self.password = opt.get('ami_password', '')
        if not self.password:
            raise ValueError('AMI nicht eingerichtet. Benutzer und Passwort in den Optionen dieser App eintragen.')
        self.host, self.port = ami_host_effective(opt), int(opt.get('ami_port', 5038))
        self.user = str(opt.get('ami_username', 'admin'))
        self.buf, self.seq, self.sock, self.banner = b'', 0, None, ''

    def __enter__(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=4)
        except socket.timeout:
            raise ValueError(f'Keine Antwort von {self.host}:{self.port} (Zeitüberschreitung beim Verbinden)') from None
        except OSError as exc:
            raise ValueError(f'Verbindung zu {self.host}:{self.port} fehlgeschlagen: {exc}') from None
        self.sock.settimeout(5)
        try:
            self.banner = self._read_line()
            if 'Call Manager' not in self.banner:
                raise ValueError(f'An {self.host}:{self.port} antwortet kein Asterisk-AMI ({self.banner[:60]!r})')
            reply = self.action({'Action': 'Login', 'Username': self.user, 'Secret': self.password, 'Events': 'off'})
            if reply.get('Response', '').lower() != 'success':
                raise ValueError('AMI-Anmeldung verweigert: ' + reply.get('Message', 'Benutzer/Passwort prüfen'))
        except Exception:
            self.sock.close()
            raise
        return self

    def __exit__(self, *exc):
        try:
            self.sock.sendall(b'Action: Logoff\r\n\r\n')
        except OSError:
            pass
        self.sock.close()

    def _fill(self):
        try:
            chunk = self.sock.recv(8192)
        except socket.timeout:
            raise ValueError('Asterisk antwortet nicht (Zeitüberschreitung)') from None
        if not chunk:
            raise ValueError('Asterisk hat die AMI-Verbindung geschlossen')
        self.buf += chunk
        if len(self.buf) > 2_000_000:
            raise ValueError('AMI-Antwort zu groß')

    def _read_line(self):
        while b'\r\n' not in self.buf:
            self._fill()
        line, _, self.buf = self.buf.partition(b'\r\n')
        return line.decode('utf-8', 'replace')

    def _read_block(self):
        while b'\r\n\r\n' not in self.buf:
            self._fill()
        block, _, self.buf = self.buf.partition(b'\r\n\r\n')
        return block.decode('utf-8', 'replace')

    @staticmethod
    def parse(block):
        fields, output, raw = {}, [], []
        for line in block.replace('\r\n', '\n').split('\n'):
            key, sep, val = line.partition(': ')
            if sep and key == 'Output':
                output.append(val)
            elif sep and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,40}', key) and key not in fields:
                fields[key] = val
            elif line.strip() and line.strip() != '--END COMMAND--':
                raw.append(line)
        fields['_output'], fields['_raw'] = output, raw
        return fields

    def _send(self, fields):
        self.seq += 1
        action_id = f'smartify-{self.seq}'
        payload = {**fields, 'ActionID': action_id}
        self.sock.sendall((''.join(f'{k}: {v}\r\n' for k, v in payload.items()) + '\r\n').encode('utf-8'))
        return action_id

    def _matches(self, fields, action_id):
        return fields.get('ActionID') == action_id or ('ActionID' not in fields and 'Response' in fields)

    def action(self, fields):
        action_id = self._send(fields)
        for _ in range(500):                      # skip unrelated events
            reply = self.parse(self._read_block())
            if 'Response' in reply and self._matches(reply, action_id):
                return reply
        raise ValueError('Keine passende AMI-Antwort erhalten')

    def command(self, command):
        reply = self.action({'Action': 'Command', 'Command': command})
        if reply.get('Response', '').lower() == 'error':
            raise ValueError('Asterisk: ' + reply.get('Message', 'Fehler')[:160]
                             + ' (der AMI-Benutzer braucht das Recht „command“)')
        lines = reply['_output'] or [l for l in reply['_raw'] if not l.startswith(('Response', 'Privilege', 'ActionID', 'Message'))]
        return '\n'.join(lines)

    def list_events(self, fields, end_event, limit=2000):
        action_id = self._send(fields)
        events, started = [], False
        for _ in range(limit + 50):
            block = self.parse(self._read_block())
            if not self._matches(block, action_id) and block.get('ActionID') != action_id:
                continue
            if 'Response' in block:
                if block['Response'].lower() == 'error':
                    if 'no ' in block.get('Message', '').lower() and 'found' in block.get('Message', '').lower():
                        return []          # e.g. "No endpoints found"
                    raise ValueError('Asterisk: ' + block.get('Message', 'Fehler')[:160])
                started = True
                continue
            if block.get('Event') == end_event:
                return events
            if started or block.get('ActionID') == action_id:
                events.append(block)
        return events


def ami_readonly():
    try:
        with AmiSession() as ami:
            records = ami.list_events({'Action': 'PJSIPShowEndpoints'}, 'EndpointListComplete')
    except (OSError, ValueError) as exc:
        return {'available': False, 'message': str(exc)[:220]}
    entries = [{k: r[k] for k in ('ObjectName', 'DeviceState', 'ActiveChannels', 'Contacts') if k in r}
               for r in records if r.get('Event') == 'EndpointList']
    return {'available': True, 'endpoints': entries[:150], 'message': 'AMI erreichbar; nur lesender Zugriff'}


def ami_diagnose():
    """Step-by-step AMI check for the UI: shows exactly which step fails."""
    steps = []
    add = lambda level, text: steps.append({'level': level, 'message': text})
    opt = get_options()
    host, port, user = ami_host_effective(opt), opt.get('ami_port', 5038), opt.get('ami_username', 'admin')
    configured = str(opt.get('ami_host') or '').strip()
    source = ('automatisch aus Add-on-Slug' if configured.lower() in ('', 'auto', '127.0.0.1', 'localhost', '::1') else 'manuell')
    add('info', f'AMI: Host {host} ({source}), Port {port}, Benutzer {user}, Passwort ' + ('gesetzt' if opt.get('ami_password') else 'FEHLT'))
    try:
        with AmiSession() as ami:
            add('ok', f'Verbunden, Asterisk meldet sich: {ami.banner[:60]}')
            add('ok', 'Anmeldung erfolgreich')
            try:
                count = len([r for r in ami.list_events({'Action': 'PJSIPShowEndpoints'}, 'EndpointListComplete')
                             if r.get('Event') == 'EndpointList'])
                add('ok', f'Nebenstellen abrufbar: {count}')
            except ValueError as exc:
                add('error', f'Nebenstellen nicht abrufbar: {exc}')
            try:
                version = ami.command('core show version').splitlines()
                add('ok', 'Befehle erlaubt: ' + (version[0][:80] if version else 'ok'))
            except ValueError as exc:
                add('warn', f'Befehle nicht möglich: {exc}')
    except (OSError, ValueError) as exc:
        add('error', str(exc)[:220])
    return {'steps': steps}


def ami_run(command):
    command = ami_command_allowed(command)
    with AmiSession() as ami:
        output = ami.command(command)
    audit('ami_command', detail=command)
    return {'command': command, 'output': output[:60_000] or '(keine Ausgabe)'}


# ---------------------------------------------------------------------------
# go2rtc
# ---------------------------------------------------------------------------
GO2RTC_CANDIDATES = ['http://a889bffc-go2rtc:1984', 'http://172.30.32.1:1984', 'http://homeassistant:1984']
_go2rtc_cache = {'base': None, 'time': 0.0}


def _go2rtc_probe(base):
    with urllib.request.urlopen(base + '/api/streams', timeout=2.5) as response:
        json.load(response)


def go2rtc_base():
    """Find go2rtc: configured URL, then LAN-IP from the model, then known add-on addresses.
    The first address that answers is cached for 5 minutes. Errors name every address tried."""
    age = time.time() - _go2rtc_cache['time']
    if _go2rtc_cache['base'] and age < 300:
        return _go2rtc_cache['base']
    configured = str(get_options().get('go2rtc_url') or '').strip().rstrip('/')
    if configured and not re.fullmatch(r'https?://[A-Za-z0-9.\-]+(:\d{1,5})?', configured):
        raise ValueError('go2rtc_url in den App-Optionen ungültig (Beispiel: http://192.168.2.65:1984)')
    candidates = []
    if configured:
        candidates.append(configured)
    try:
        lan = read_anlage()['model']['anlage'].get('lan_ip')
        if lan:
            candidates.append(f'http://{lan}:1984')
    except (OSError, ValueError):
        pass
    candidates += GO2RTC_CANDIDATES
    tried = []
    for base in dict.fromkeys(candidates):
        try:
            _go2rtc_probe(base)
            _go2rtc_cache.update(base=base, time=time.time())
            return base
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, 'reason', exc))
            tried.append(f'{base} ({"Name nicht auflösbar" if "resolve" in reason or "Name or service" in reason else reason[:60]})')
        except (OSError, ValueError) as exc:
            tried.append(f'{base} ({str(exc)[:60]})')
    _go2rtc_cache.update(base=None, time=0.0)
    raise ValueError('go2rtc nicht erreichbar. Versucht: ' + '; '.join(tried)
                     + '. In den App-Optionen go2rtc_url mit IP setzen, z. B. http://192.168.2.65:1984 – kein Hostname.')


def go2rtc_streams():
    try:
        base = go2rtc_base()
        with urllib.request.urlopen(base + '/api/streams', timeout=4) as response:
            data = json.load(response)
    except (OSError, ValueError) as exc:
        return {'available': False, 'streams': [], 'message': str(exc)[:200]}
    names = sorted(k for k in (data or {}) if isinstance(k, str) and RE_STREAM.fullmatch(k))
    return {'available': True, 'streams': names, 'source': base}


def go2rtc_frame(name):
    if not RE_STREAM.fullmatch(name or ''):
        raise ValueError('Ungültiger Streamname')
    base = go2rtc_base()
    try:
        with urllib.request.urlopen(base + '/api/frame.jpeg?src=' + quote(name), timeout=12) as response:
            data = response.read(4_000_000)
            ctype = response.headers.get('Content-Type', 'image/jpeg')
    except urllib.error.HTTPError as exc:
        raise ValueError(f'go2rtc liefert kein Bild für „{name}“ (HTTP {exc.code})') from None
    except OSError as exc:
        raise ValueError(f'go2rtc nicht erreichbar: {str(exc)[:120]}') from None
    if not data or not ctype.startswith('image/'):
        raise ValueError(f'Stream „{name}“ liefert kein Bild')
    return data, ctype


# ---------------------------------------------------------------------------
# Export / import of manager data (per installation)
# ---------------------------------------------------------------------------
EXPORT_FORMAT = 'smartify-sip-manager-export'


def export_data():
    return {'format': EXPORT_FORMAT, 'format_version': 1, 'addon_version': ADDON_VERSION,
            'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'camera_mapping': read_camera_map()['mapping'], 'sip_core_draft': read_sip_core()['content'],
            'anlage': read_anlage()['model']}


def import_data(data):
    if not isinstance(data, dict) or data.get('format') != EXPORT_FORMAT:
        raise ValueError('Keine Smartify-Exportdatei')
    if int(data.get('format_version', 0)) > 1:
        raise ValueError('Exportdatei stammt aus einer neueren Manager-Version')
    mapping = validate_camera_map(data.get('camera_mapping') or {})
    draft = data.get('sip_core_draft') or ''
    if not isinstance(draft, str) or len(draft.encode('utf-8')) > MAX_SIZE or '\x00' in draft:
        raise ValueError('SIP-Core-Entwurf in der Exportdatei ungültig')
    model = anlage_model.validate(data['anlage']) if data.get('anlage') else None
    with LOCK:
        write_camera_map(mapping, read_camera_map()['hash'])
        write_sip_core(draft, read_sip_core()['hash'])
        if model:
            write_anlage(model, read_anlage()['hash'])
    audit('import', detail=f'cameras={len(mapping)};draft={bool(draft)};anlage={bool(model)}')
    return {'imported': True, 'cameras': len(mapping), 'draft': bool(draft),
            'note': 'Importiert. Vorherige Stände liegen als Backup unter /data/backups.'}



# ---------------------------------------------------------------------------
# Anlagen-Modell (v1.4): eine Beschreibung der Anlage + Prüfbericht über alle Schichten
# ---------------------------------------------------------------------------
ANLAGE_FILE = DATA_DIR / 'anlage.json'


def read_anlage():
    if ANLAGE_FILE.is_file():
        raw = ANLAGE_FILE.read_text(encoding='utf-8')
        if len(raw) > MAX_SIZE:
            raise ValueError('Anlagenmodell zu groß')
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        model, hinweise = anlage_model.validate_lenient(data)
        out = {'model': model, 'hash': digest(raw), 'saved': True}
        if hinweise:
            out['hinweise'] = hinweise
        return out
    return {'model': anlage_model.leer(), 'hash': digest(''), 'saved': False}


def write_anlage(model, expected_hash):
    with LOCK:
        current = read_anlage()
        if expected_hash != current['hash']:
            raise ValueError('Das Anlagenmodell wurde inzwischen geändert. Neu laden.')
        normalized = anlage_model.validate(model)
        content = json.dumps(normalized, ensure_ascii=False, indent=2) + '\n'
        if ANLAGE_FILE.exists():
            backup_dir = DATA_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backup_dir / f'anlage_{stamp}.json'
            backup.write_bytes(ANLAGE_FILE.read_bytes())
            os.chmod(backup, 0o600)
            prune_backups(backup_dir, 'anlage_*.json')
        fd, temp = tempfile.mkstemp(prefix='.smartify-anlage-', dir=str(DATA_DIR))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fp:
                fp.write(content)
                fp.flush()
                os.fsync(fp.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, ANLAGE_FILE)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        audit('anlage_saved', detail=f'teilnehmer={len(normalized["teilnehmer"])};wege={len(normalized["wege"])}')
        return {'saved': True, 'hash': digest(content), 'model': normalized,
                'note': 'Modell gespeichert. Es wurden keine Asterisk-, SIP-Core- oder go2rtc-Dateien geändert.'}


def conf_files_for_model():
    """All permitted .conf files, default first, then custom (custom wins)."""
    files = []
    for folder, origin in ((DEFAULT, 'default'), (CUSTOM, 'custom')):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.conf')):
            if not allowed_name(path.name) or path.is_symlink():
                continue
            try:
                if path.stat().st_size > MAX_SIZE:
                    continue
                files.append((f'{origin}/{path.name}', path.read_text(encoding='utf-8')))
            except (OSError, UnicodeError):
                continue
    return files


def go2rtc_streams_full():
    base = go2rtc_base()
    with urllib.request.urlopen(base + '/api/streams', timeout=4) as response:
        data = json.load(response) or {}
    out = {}
    for name, info in data.items():
        if not isinstance(name, str) or not RE_STREAM.fullmatch(name):
            continue
        info = info if isinstance(info, dict) else {}
        producers = []
        for p in info.get('producers') or []:
            if isinstance(p, dict):
                producers.append({'format': str(p.get('format_name') or '')[:40],
                                  'bytes_recv': int(p.get('bytes_recv') or 0),
                                  'receivers': len(p.get('receivers') or []),
                                  'medias': len(p.get('medias') or []),
                                  'user_agent': str(p.get('user_agent') or '')[:160]})
        consumers = [{'format': str(c.get('format_name') or '')[:40], 'user_agent': str(c.get('user_agent') or '')[:160]}
                     for c in info.get('consumers') or [] if isinstance(c, dict)]
        out[name] = {'producers': producers, 'consumers': consumers}
    return out, base


def go2rtc_cors(base):
    request = urllib.request.Request(base + '/api/webrtc?dst=smartify_cors_check', method='OPTIONS',
                                     headers={'Origin': 'https://smartify.check', 'Access-Control-Request-Method': 'POST'})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return bool(response.headers.get('Access-Control-Allow-Origin'))
    except urllib.error.HTTPError as exc:
        return bool(exc.headers.get('Access-Control-Allow-Origin'))
    except OSError:
        return None


def asterisk_addon_options():
    """Options of the Asterisk add-on via Supervisor (read only, secrets removed). {} if unavailable."""
    token = os.environ.get('SUPERVISOR_TOKEN')
    if not token:
        return {}
    try:
        req = urllib.request.Request(f'http://supervisor/addons/{slug}/info', headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = (json.load(response) or {}).get('data') or {}
    except (OSError, ValueError):
        return {}
    opts = data.get('options') or {}
    return {k: v for k, v in opts.items() if isinstance(v, (bool, int, str))
            and not re.search(r'pass|secret|token|key|cert', k, re.I)}


def dialplan_text_all(exclude_main=False):
    """Dialplan from extensions.conf (custom or default) plus every other custom .conf with exten lines."""
    parts = [] if exclude_main else [read_file('extensions.conf')['content']]
    if CUSTOM.is_dir():
        for path in sorted(CUSTOM.glob('*.conf')):
            if path.name in ('extensions.conf', 'manager.conf') or path.name.startswith('pjsip') or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                continue
            if re.search(r'^\s*exten\s*=>', text, re.M):
                parts.append(text)
    return '\n'.join(parts)


def collect_context(model):
    try:
        dialplan = generator.dialplan_numbers(dialplan_text_all())
    except (OSError, ValueError):
        dialplan = None
    ctx = {'asterisk_dir': ASTERISK_DIR.is_dir(), 'rtsp_passwords': set(read_secrets().get('rtsp', {})), 'dialplan': dialplan,
           'asterisk_addon': asterisk_addon_options()}
    try:
        ctx['endpoints'] = anlage_model.endpoints_from_conf(conf_files_for_model())
    except (OSError, ValueError) as exc:
        ctx['endpoints'] = {}
        ctx['endpoint_error'] = str(exc)[:160]
    try:
        ctx['sip_core'] = read_active_sip_core()
    except ValueError as exc:
        ctx['sip_core'] = None
        ctx['sip_core_error'] = str(exc)[:200]
    try:
        ctx['streams'], base = go2rtc_streams_full()
        ctx['cors'] = go2rtc_cors(base)
    except (OSError, ValueError) as exc:
        ctx['streams'] = None
        ctx['go2rtc_error'] = str(exc)[:200]
    if get_options().get('ami_password'):
        wanted = sorted({t['nummer'] or t['endpoint'] for t in model.get('teilnehmer', [])
                         if t['faehigkeiten'].get('video_im_anruf') and (t['nummer'] or t['endpoint'])})[:40]
        try:
            with AmiSession() as ami:
                records = ami.list_events({'Action': 'PJSIPShowEndpoints'}, 'EndpointListComplete')
                ctx['registered'] = {}
                for r in records:
                    if r.get('Event') == 'EndpointList':
                        contacts = [c for c in str(r.get('Contacts') or '').split(',') if c.strip()]
                        ctx['registered'][r.get('ObjectName', '')] = len(contacts)
                codecs = {}
                for name in wanted:
                    try:
                        found = anlage_model.parse_ami_allow(ami.command(ami_command_allowed(f'pjsip show endpoint {name}')))
                    except ValueError:
                        found = None
                    if found is not None:
                        codecs[name] = found
                ctx['ami_codecs'] = codecs
        except (OSError, ValueError) as exc:
            ctx['ami_error'] = str(exc)[:200]
    else:
        ctx['ami_error'] = 'AMI-Passwort nicht gesetzt.'
    return ctx


def anlage_vorschlag():
    current = read_anlage()['model']
    ctx = collect_context(current)
    rtsp_sources, hinweise = {}, []
    try:
        _, g2cfg, _ = go2rtc_config_read()
        rtsp_sources, passwords = generator.rtsp_from_go2rtc(g2cfg)
        if passwords:
            data = read_secrets()
            store = data.setdefault('rtsp', {})
            for stream, pw in passwords.items():
                if pw and not store.get(stream):
                    store[stream] = pw
            write_secrets(data)
        if rtsp_sources:
            hinweise.append(f'{len(rtsp_sources)} RTSP-Kamera(s) aus der go2rtc-Konfiguration erkannt; Passwörter sicher im Manager abgelegt.')
    except ValueError as exc:
        hinweise.append('go2rtc-Konfiguration nicht lesbar: ' + str(exc)[:120])
    try:
        extern_ziele = generator.dialplan_extern_targets(dialplan_text_all())
        gruppen = generator.dialplan_groups(read_file('extensions.conf')['content'])
    except (OSError, ValueError):
        extern_ziele, gruppen = [], []
    if gruppen:
        hinweise.append('Rufgruppen erkannt: ' + ', '.join(f'{g["nummer"]} {g["name"]}' for g in gruppen)
                        + '. Sie erscheinen im Rufgruppen-Manager; beim Übernehmen ersetzt der Manager den bisherigen Eintrag (mit Backup).')
    if extern_ziele:
        hinweise.append('Externe Ziele aus dem Dialplan erkannt: ' + ', '.join(f'{z["nummer"]} → {z["sip_adresse"]}' for z in extern_ziele)
                        + '. Der eigene Eintrag bleibt bestehen; zum Verwalten durch den Manager den eigenen Eintrag entfernen.')
    proposal = anlage_model.import_from(ctx.get('sip_core') or {}, ctx.get('endpoints') or {},
                                        ctx.get('streams') or {}, read_camera_map()['mapping'], current['anlage'], rtsp_sources,
                                        extern_ziele, ctx.get('dialplan'), gruppen)
    if ctx.get('sip_core') is None:
        hinweise.append('SIP Core nicht lesbar: ' + ctx.get('sip_core_error', ''))
    if ctx.get('streams') is None:
        hinweise.append('go2rtc nicht erreichbar – Kameras ohne SIP fehlen im Vorschlag.')
    hinweise.append('Typ, Fähigkeiten (v. a. „iOS-Gerät“) und Namen bitte prüfen; der Import kann das nicht sicher erkennen.')
    return {'model': proposal, 'hinweise': hinweise, 'rtsp_passwoerter': sorted(read_secrets().get('rtsp', {})),
            'sip_passwoerter': sorted(read_secrets().get('sip', {}))}


def pruefbericht():
    data = read_anlage()
    model = data['model']
    report = anlage_model.pruefbericht(model, collect_context(model))
    for h in data.get('hinweise', []):
        report['zeilen'].insert(0, {'level': 'warn', 'bereich': 'Modell', 'titel': 'Gespeichertes Modell wurde beim Laden korrigiert',
                                    'detail': h, 'beheben': 'Unter „Anlage & Teilnehmer“ prüfen und speichern.', 'bezug': '', 'aktion': ''})
        report['zusammenfassung']['warn'] += 1
    report['erstellt'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    return report


def anlage_export():
    model = read_anlage()['model']
    return {**model, 'exportiert': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'addon_version': ADDON_VERSION}


def anlage_import_datei(data):
    if not isinstance(data, dict):
        raise ValueError('Keine Anlagen-Datei')
    data = {k: v for k, v in data.items() if k not in ('exportiert', 'addon_version')}
    with LOCK:
        return write_anlage(data, read_anlage()['hash'])


# ---------------------------------------------------------------------------
# v1.5: Geheimnisse, go2rtc-Konfiguration, Erzeugen und Übernehmen
# ---------------------------------------------------------------------------
SECRETS_FILE = DATA_DIR / 'secrets.json'


def read_secrets():
    try:
        data = json.loads(SECRETS_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_secrets(data):
    with LOCK:
        fd, temp = tempfile.mkstemp(prefix='.smartify-secrets-', dir=str(DATA_DIR))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fp:
                json.dump(data, fp, ensure_ascii=False, indent=1)
                fp.flush()
                os.fsync(fp.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, SECRETS_FILE)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def go2rtc_config_read():
    base = go2rtc_base()
    try:
        with urllib.request.urlopen(base + '/api/config', timeout=4) as response:
            text = response.read(MAX_SIZE).decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        raise ValueError(f'go2rtc-Konfiguration nicht lesbar (HTTP {exc.code}). go2rtc braucht eine Konfigurationsdatei.') from None
    except OSError as exc:
        raise ValueError(f'go2rtc nicht erreichbar: {str(exc)[:120]}') from None
    need_yaml()
    try:
        cfg = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError:
        raise ValueError('go2rtc-Konfiguration ist kein gültiges YAML') from None
    return text, (cfg if isinstance(cfg, dict) else {}), base


def go2rtc_config_write(text, restart=True):
    base = go2rtc_base()
    old, _, _ = go2rtc_config_read()
    backup_dir = DATA_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = backup_dir / f'go2rtc_{stamp}.yaml'
    backup.write_text(old, encoding='utf-8')
    os.chmod(backup, 0o600)
    prune_backups(backup_dir, 'go2rtc_*.yaml')
    try:
        req = urllib.request.Request(base + '/api/config', data=text.encode('utf-8'), method='POST',
                                     headers={'Content-Type': 'application/yaml'})
        with urllib.request.urlopen(req, timeout=6):
            pass
    except urllib.error.HTTPError as exc:
        raise ValueError(f'go2rtc hat die Konfiguration abgelehnt (HTTP {exc.code}): {exc.read(200).decode("utf-8", "replace")}') from None
    restarted = False
    if restart:
        try:
            with urllib.request.urlopen(urllib.request.Request(base + '/api/restart', data=b'', method='POST'), timeout=6):
                restarted = True
        except OSError:
            restarted = False
    _go2rtc_cache.update(base=None, time=0.0)
    return {'backup': backup.name, 'restarted': restarted}


def _yaml_text(obj):
    need_yaml()
    return yaml.safe_dump(obj or {}, sort_keys=False, allow_unicode=True, default_flow_style=False, width=1000)


def erzeugen_vorschau():
    model = read_anlage()['model']
    secrets = read_secrets()
    before = json.dumps(secrets, sort_keys=True)
    out, hinweise = {}, []
    # Asterisk
    info = read_file('pjsip_custom.conf')
    custom_text = info['content'] if info['source'] == 'custom' else ''
    try:
        users = (read_active_sip_core() or {}).get('users') or []
    except ValueError:
        users = []
    pj = generator.gen_pjsip(model, custom_text, conf_files_for_model(), secrets, users)
    lint = lint_conf('pjsip_custom.conf', pj['content']) if pj['content'] != custom_text else {'errors': 0, 'issues': []}
    out['asterisk'] = {'titel': 'Asterisk · custom/pjsip_custom.conf', 'changed': pj['content'] != custom_text,
                       'diff': text_diff(custom_text, pj['content'], 'aktuell', 'neu'), 'aktionen': pj['aktionen'],
                       'token': digest(custom_text), 'lint_fehler': lint.get('errors', 0),
                       'lint': [i for i in lint.get('issues', []) if i['level'] == 'error'][:10]}
    # Dialplan
    eps_all = anlage_model.endpoints_from_conf(conf_files_for_model())
    einfo = read_file('extensions.conf')
    e_custom = einfo['content'] if einfo['source'] == 'custom' else ''
    dp = migration.generate_migrated_dialplan(model, einfo['content'], eps_all, dialplan_text_all(exclude_main=True))
    e_changed = dp['content'] != einfo['content']
    elint = lint_conf('extensions.conf', dp['content']) if e_changed else {'errors': 0, 'issues': []}
    out['dialplan'] = {'titel': 'Dialplan · custom/extensions.conf', 'changed': e_changed,
                       'diff': text_diff(einfo['content'], dp['content'], 'aktuell', 'neu'), 'aktionen': dp['aktionen'],
                       'token': digest(e_custom), 'lint_fehler': elint.get('errors', 0),
                       'lint': [i for i in elint.get('issues', []) if i['level'] == 'error'][:10],
                       'hinweis': '' if einfo['source'] == 'custom' else 'extensions.conf wird neu im custom-Ordner angelegt (Inhalt der Standarddatei bleibt erhalten).'}
    # SIP Core
    try:
        active = read_active_sip_core()
        sc = generator.gen_sip_core(model, active)
        out['sip_core'] = {'titel': 'SIP Core · Konfiguration', 'changed': canon_hash(sc['config']) != canon_hash(active),
                           'diff': text_diff(dump_yaml(active), dump_yaml(sc['config']), 'aktiv', 'neu'),
                           'aktionen': sc['aktionen'], 'token': canon_hash(active)}
    except ValueError as exc:
        out['sip_core'] = {'titel': 'SIP Core', 'changed': False, 'fehler': str(exc)[:200], 'aktionen': [], 'token': ''}
    # go2rtc
    try:
        text, cfg, base = go2rtc_config_read()
        go = generator.gen_go2rtc(model, cfg, secrets)
        new_text = _yaml_text(go['config'])
        old_norm = _yaml_text(cfg)
        out['go2rtc'] = {'titel': f'go2rtc · {base}/api/config', 'changed': new_text != old_norm,
                         'diff': generator.mask_go2rtc_text(text_diff(old_norm, new_text, 'aktuell', 'neu')),
                         'aktionen': go['aktionen'], 'token': digest(text),
                         'hinweis': 'Kommentare in der go2rtc-Datei gehen beim Übernehmen verloren (Backup wird angelegt).' if '#' in text.split('rtsp')[0] else ''}
    except ValueError as exc:
        out['go2rtc'] = {'titel': 'go2rtc', 'changed': False, 'fehler': str(exc)[:200], 'aktionen': [], 'token': ''}
    if json.dumps(secrets, sort_keys=True) != before:
        write_secrets(secrets)
    return {'ziele': out, 'hinweise': hinweise}


def erzeugen_uebernehmen(body):
    if body.get('confirm') is not True:
        raise ValueError('Bestätigung fehlt')
    wanted = [z for z in body.get('ziele') or [] if z in ('asterisk', 'dialplan', 'go2rtc', 'sip_core')]
    if not wanted:
        raise ValueError('Nichts ausgewählt')
    tokens = body.get('tokens') or {}
    model = read_anlage()['model']
    results = {}
    with LOCK:
        preview = erzeugen_vorschau()['ziele']
        for ziel in wanted:
            if preview[ziel].get('token') != tokens.get(ziel):
                raise ValueError(f'{preview[ziel]["titel"]}: hat sich seit der Vorschau geändert – Vorschau neu erzeugen.')
            if preview[ziel].get('fehler'):
                raise ValueError(f'{preview[ziel]["titel"]}: {preview[ziel]["fehler"]}')
        for z in ('asterisk', 'dialplan'):
            if z in wanted and preview[z]['lint_fehler']:
                raise ValueError(f'{preview[z]["titel"]}: Die erzeugte Datei hat Fehler – nichts geschrieben.')
        secrets = read_secrets()
        if 'asterisk' in wanted and preview['asterisk']['changed']:
            info = read_file('pjsip_custom.conf')
            current = info['content'] if info['source'] == 'custom' else ''
            users = []
            try:
                users = (read_active_sip_core() or {}).get('users') or []
            except ValueError:
                pass
            pj = generator.gen_pjsip(model, current, conf_files_for_model(), secrets, users)
            write_file('pjsip_custom.conf', pj['content'], digest(current))
            res = {'geschrieben': True, 'reload': None}
            if body.get('reload'):
                try:
                    ami_run('pjsip reload')
                    res['reload'] = 'pjsip reload ausgeführt'
                except (OSError, ValueError) as exc:
                    res['reload'] = f'Reload nicht möglich ({str(exc)[:120]}) – im Asterisk-Terminal „pjsip reload“ ausführen.'
            results['asterisk'] = res
        if 'dialplan' in wanted and preview['dialplan']['changed']:
            einfo = read_file('extensions.conf')
            e_custom = einfo['content'] if einfo['source'] == 'custom' else ''
            dp = migration.generate_migrated_dialplan(model, einfo['content'], anlage_model.endpoints_from_conf(conf_files_for_model()), dialplan_text_all(exclude_main=True))
            write_file('extensions.conf', dp['content'], digest(e_custom))
            res = {'geschrieben': True, 'reload': None}
            if body.get('reload'):
                try:
                    ami_run('dialplan reload')
                    res['reload'] = 'dialplan reload ausgeführt'
                except (OSError, ValueError) as exc:
                    res['reload'] = f'Reload nicht möglich ({str(exc)[:120]}) – im Asterisk-Terminal „dialplan reload“ ausführen.'
            results['dialplan'] = res
        if 'go2rtc' in wanted and preview['go2rtc']['changed']:
            _, cfg, _ = go2rtc_config_read()
            go = generator.gen_go2rtc(model, cfg, secrets)
            results['go2rtc'] = go2rtc_config_write(_yaml_text(go['config']), restart=True)
        if 'sip_core' in wanted and preview['sip_core']['changed']:
            active = read_active_sip_core()
            sc = generator.gen_sip_core(model, active)
            results['sip_core'] = apply_sip_core(dump_yaml(sc['config']), canon_hash(active))
            if sc.get('camera_map') is not None:
                try:
                    write_camera_map(sc['camera_map'], read_camera_map()['hash'])
                except ValueError:
                    pass
        write_secrets(secrets)
    audit('erzeugt', detail=','.join(f'{k}=ok' for k in results))
    return {'ergebnisse': results, 'note': 'Übernommen: ' + (', '.join(results) or 'keine Änderungen nötig')
            + '. Danach Prüfbericht neu laden und die App auf den Geräten neu laden.'}


def zugangsdaten(nummer):
    if not anlage_model.RE_NUMMER.fullmatch(str(nummer or '')):
        raise ValueError('Ungültige Nummer')
    pw = read_secrets().get('sip', {}).get(str(nummer))
    if not pw:
        raise ValueError('Für diese Nummer ist kein Passwort im Manager gespeichert.')
    audit('zugangsdaten_angezeigt', str(nummer))
    model = read_anlage()['model']
    t = next((x for x in model['teilnehmer'] if x['nummer'] == str(nummer)), {})
    realm = t.get('realm') or ''
    return {'nummer': str(nummer), 'benutzer': str(nummer), 'passwort': pw,
            'server': realm or model['anlage'].get('lan_ip') or '',
            'hinweis': 'SIP-Server/Domain = ' + (f'{realm} (wie Realm), ' if realm else 'IP von Home Assistant, ') + 'Port 5060 (UDP).'}


def kamera_suche(body):
    lan = str(body.get('lan_ip') or read_anlage()['model']['anlage'].get('lan_ip') or '').strip()
    if not lan:
        raise ValueError('Zuerst die LAN-IP von Home Assistant unter „Anlage“ eintragen.')
    try:
        found = rtsp_mod.discover(lan)
    except ValueError as exc:
        raise ValueError(str(exc)) from None
    known = {(t['rtsp']['host'], t['rtsp']['port']): t['stream'] for t in read_anlage()['model']['teilnehmer'] if t.get('rtsp')}
    for item in found:
        item['im_modell'] = known.get((item['host'], item['port']), '')
    audit('kamerasuche', detail=f'netz={lan}/24;gefunden={len(found)}')
    return {'netz': lan + '/24', 'kameras': found, 'hersteller': [{'hersteller': k, 'bezeichnung': l, 'pfad': m, 'nebenstream': n}
                                                                  for k, l, m, n in rtsp_mod.VENDORS]}


def kamera_test(body):
    cam = {'host': str(body.get('host') or ''), 'port': int(body.get('port') or 554), 'pfad': str(body.get('pfad') or '/'),
           'benutzer': str(body.get('benutzer') or ''), 'passwort': str(body.get('passwort') or '')}
    if not anlage_model.RE_HOST.fullmatch(cam['host']) or not cam['host']:
        raise ValueError('Ungültige Adresse')
    if not cam['passwort'] and body.get('stream'):
        cam['passwort'] = read_secrets().get('rtsp', {}).get(str(body['stream']), '')
    return rtsp_mod.describe(cam)


def kamera_passwort(body):
    stream = str(body.get('stream') or '')
    if not RE_STREAM.fullmatch(stream):
        raise ValueError('Ungültiger Streamname')
    pw = body.get('passwort')
    if not isinstance(pw, str) or len(pw) > 128 or any(c in pw for c in '\r\n\x00'):
        raise ValueError('Ungültiges Passwort')
    data = read_secrets()
    data.setdefault('rtsp', {})[stream] = pw
    write_secrets(data)
    audit('kamera_passwort', stream)
    return {'gespeichert': True}


# ---------------------------------------------------------------------------
# v1.6: Auswahllisten für die Oberfläche (jede Quelle einzeln fehlertolerant)
# ---------------------------------------------------------------------------
DOOR_HINT = re.compile(r't[üu]r|door|öffn|oeffn|tor\b|gate|lock|schloss|summer|haust', re.I)
BELL_HINT = re.compile(r'klingel|bell|ring|doorbell|taster|button|press', re.I)
LIGHT_HINT = re.compile(r'licht|light|lampe|leuchte|eingang|haust|au[sß]en', re.I)


def supervisor_get(path):
    token = os.environ.get('SUPERVISOR_TOKEN')
    if not token:
        raise ValueError('Supervisor nicht erreichbar')
    req = urllib.request.Request('http://supervisor/' + path.lstrip('/'), headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=4) as response:
        return (json.load(response) or {}).get('data') or {}


def netz_erkennen():
    out = {'lan_ip': '', 'tailscale_name': '', 'tailscale_ip': '', 'go2rtc_https_url': '', 'quellen': []}
    try:
        info = supervisor_get('network/info')
        ifaces = info.get('interfaces') or []
        ifaces.sort(key=lambda i: not i.get('primary'))
        for iface in ifaces:                 # Tailscale-IP nur sichtbar, wenn das Add-on ohne Userspace-Networking läuft
            for addr in ((iface.get('ipv4') or {}).get('address') or []):
                ip = str(addr).split('/')[0]
                if anlage_model.RE_TS_IP.fullmatch(ip) and not out['tailscale_ip']:
                    out['tailscale_ip'] = ip
                    out['quellen'].append(f'Tailscale-IP aus Supervisor ({iface.get("interface", "?")})')
        for iface in ifaces:
            for addr in ((iface.get('ipv4') or {}).get('address') or []):
                ip = str(addr).split('/')[0]
                if ip and not ip.startswith(('127.', '172.30.', '100.')):
                    out['lan_ip'] = ip
                    out['quellen'].append(f'LAN-IP aus Supervisor ({iface.get("interface", "?")})')
                    break
            if out['lan_ip']:
                break
    except (OSError, ValueError):
        pass
    try:
        cfg = core_api('GET', 'config') or {}
        for key in ('external_url', 'internal_url'):
            host = urlsplit(str(cfg.get(key) or '')).hostname or ''
            if host.endswith('.ts.net'):
                out['tailscale_name'] = host
                out['quellen'].append(f'Tailscale-Name aus HA ({key})')
                break
    except ValueError:
        pass
    if out['tailscale_name']:
        out['go2rtc_https_url'] = f'https://{out["tailscale_name"]}:8443'
    return out


def _entity_choices(entities, domains, hint):
    rows = [e for e in entities if e['entity_id'].split('.')[0] in domains]
    rows.sort(key=lambda e: (not hint.search(e['entity_id'] + ' ' + e['name']), e['entity_id']))
    return [{'value': e['entity_id'], 'label': e['name'] or e['entity_id']} for e in rows[:600]]


def anlage_auswahl():
    model = read_anlage()['model']
    out = {'sip_users': [], 'endpoints_extern': [], 'endpoints_nummern': [], 'streams': [], 'entities': {},
           'frei': [], 'meldungen': []}
    try:
        cfg = read_active_sip_core()
        out['sip_users'] = [{'nummer': str(u.get('extension', '')), 'name': str(u.get('display_name') or u.get('ha_username') or ''),
                             'ha_benutzer': str(u.get('ha_username', '')), 'backup': bool(u.get('_backup'))}
                            for u in anlage_model.sip_core_users(cfg) if u.get('extension')]
    except ValueError as exc:
        out['meldungen'].append('SIP Core: ' + str(exc)[:120])
    # HA-Benutzer: alle Personen mit HA-Konto plus alle in SIP Core verwendeten Namen
    in_use = {}
    for u in out['sip_users']:
        if u['ha_benutzer']:
            in_use.setdefault(u['ha_benutzer'], []).append(u['nummer'])
    names = {}
    try:
        for person in ha_persons():
            if person.get('user_id') and person.get('name'):
                names[person['name']] = 'HA-Benutzer'
    except ValueError as exc:
        out['meldungen'].append('HA-Benutzer: ' + str(exc)[:120])
    for n in in_use:
        if n != anlage_model.BACKUP:
            names.setdefault(n, 'aus SIP Core')
    out['ha_users'] = [{'value': n, 'label': n + (f' (jetzt bei {", ".join(in_use[n])})' if n in in_use else ''), 'quelle': q}
                       for n, q in sorted(names.items(), key=lambda kv: kv[0].lower())]
    if anlage_model.BACKUP in in_use:
        out['ha_users'].insert(0, {'value': anlage_model.BACKUP, 'quelle': 'backup_user',
                                   'label': f'alle übrigen HA-Benutzer (backup_user, jetzt bei {", ".join(in_use[anlage_model.BACKUP])})'})
    eps = anlage_model.endpoints_from_conf(conf_files_for_model())
    used = set()
    for name, ep in sorted(eps.items()):
        if anlage_model.RE_NUMMER.fullmatch(name):
            used.add(int(name))
            out['endpoints_nummern'].append({'value': name, 'label': f'{name} {ep.get("display_name") or ""}'.strip()})
        elif not ep.get('aors') and not ep.get('webrtc'):
            rolle, grund = anlage_model.anschluss_rolle(name, ep)
            out['endpoints_extern'].append({'value': name, 'rolle': rolle, 'grund': grund,
                                            'label': name + (f' · {ep.get("transport")}' if ep.get('transport') else '')})
    try:
        streams, _ = go2rtc_streams_full()
        try:
            _, g2cfg, _ = go2rtc_config_read()
            rtsp_names = set(generator.rtsp_from_go2rtc(g2cfg)[0])
        except ValueError:
            rtsp_names = set()
        for name, info in sorted(streams.items()):
            active = any(p.get('bytes_recv') or p.get('receivers') or p.get('medias') for p in info.get('producers') or [])
            kind = 'RTSP' if name in rtsp_names else ('Gerät sendet' if active else ('leer – wartet auf Gerät' if not info.get('producers') else 'Quelle'))
            out['streams'].append({'value': name, 'label': f'{name} · {kind}'})
    except (OSError, ValueError) as exc:
        out['meldungen'].append('go2rtc: ' + str(exc)[:120])
    ent = ha_entity_index()
    if ent.get('available'):
        e = ent['entities']
        out['entities'] = {'tuer': _entity_choices(e, {'switch', 'lock', 'button', 'input_button', 'script', 'cover'}, DOOR_HINT),
                           'licht': _entity_choices(e, {'light', 'switch'}, LIGHT_HINT),
                           'klingel': _entity_choices(e, {'binary_sensor', 'event', 'input_boolean', 'sensor'}, BELL_HINT)}
    else:
        out['meldungen'].append('HA-Entitäten: ' + ent.get('message', 'nicht verfügbar'))
    used |= {int(t['nummer']) for t in model['teilnehmer'] if t['nummer']}
    used |= {int(u['nummer']) for u in out['sip_users'] if anlage_model.RE_NUMMER.fullmatch(u['nummer'])}
    lo = int(model['anlage'].get('nummer_von') or 100)
    hi = int(model['anlage'].get('nummer_bis') or 199)
    out['frei'] = [str(n) for n in range(lo, hi + 1) if n not in used][:40]
    try:   # eigene Dialplan-Einträge (außerhalb des verwalteten Blocks) sind ebenfalls belegt
        own = generator.split_managed(read_file('extensions.conf')['content'])[0] + '\n' + dialplan_text_all(exclude_main=True)
        used |= {int(n) for n in generator.dialplan_numbers(own)}
    except (OSError, ValueError):
        pass
    out['belegt'] = sorted(str(n) for n in used)
    return out


# ---------------------------------------------------------------------------
# v1.7: AMI-Zugang für den Manager einrichten (eigener Benutzer, nur Add-on-Netz)
# ---------------------------------------------------------------------------
AMI_USER = 'smartify'
AMI_BEGIN = '; >>> SMARTIFY-AMI – vom Smartify SIP Manager angelegt'
AMI_END = '; <<< SMARTIFY-AMI'
HASSIO_NET = ('172.30.32.0', '255.255.254.0')


def _own_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('172.30.32.1', 9))
            return sock.getsockname()[0]
    except OSError:
        return ''


def ami_block(password):
    return '\n'.join([AMI_BEGIN, f'[{AMI_USER}]', f'secret = {password}', 'deny = 0.0.0.0/0.0.0.0',
                      f'permit = {HASSIO_NET[0]}/{HASSIO_NET[1]}',
                      'read = system,call,log,verbose,agent,user,config,dtmf,reporting,cdr,dialplan',
                      'write = system,call,command,reporting,originate', 'writetimeout = 5000', AMI_END]) + '\n'


def manager_conf_with_user(content, password):
    """Insert or replace the managed [smartify] block. Refuses if a foreign [smartify] section exists."""
    if AMI_BEGIN in content:
        before, _, rest = content.partition(AMI_BEGIN)
        _, _, after = rest.partition(AMI_END)
        content = before.rstrip('\n') + ('\n' if before.strip() else '') + after.lstrip('\n')
    if re.search(r'^\s*\[' + AMI_USER + r'\]', content, re.M):
        raise ValueError(f'In manager_custom.conf gibt es schon einen eigenen Abschnitt [{AMI_USER}] – bitte von Hand prüfen.')
    content = content.rstrip('\n')
    return (content + '\n\n' if content else '') + ami_block(password)


def manager_include_state():
    """Does Asterisk include manager_custom.conf? True/False/None (unknown)."""
    for name in ('manager.conf',):
        for folder in (CUSTOM, DEFAULT):
            path = folder / name
            if path.is_file() and not path.is_symlink():
                try:
                    text = path.read_text(encoding='utf-8')
                except (OSError, UnicodeError):
                    continue
                return bool(re.search(r'^\s*#(try)?include\s+"?[^"\n]*manager_custom\.conf', text, re.M))
    return None


def self_options_update(changes):
    """Persist options of THIS add-on through the Supervisor. Returns True on success."""
    token = os.environ.get('SUPERVISOR_TOKEN')
    if not token:
        return False
    try:
        info = supervisor_get('addons/self/info')
        options = {**(info.get('options') or {}), **changes}
        req = urllib.request.Request('http://supervisor/addons/self/options', method='POST',
                                     data=json.dumps({'options': options}).encode('utf-8'),
                                     headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=6):
            return True
    except (OSError, ValueError):
        return False


MANAGER_HEADER = ('; Von Smartify SIP Manager erzeugt: ersetzt die vom Asterisk-Add-on erzeugte manager.conf,\n'
                  '; damit manager_custom.conf eingebunden wird. [admin] bleibt unverändert.\n')


def asterisk_addon_raw_option(key):
    try:
        return (supervisor_get(f'addons/{slug}/info').get('options') or {}).get(key)
    except (OSError, ValueError):
        return None


def manager_conf_base():
    """Current generated manager.conf: default/ copy if present, else rebuilt from the add-on options."""
    path = DEFAULT / 'manager.conf'
    if path.is_file() and not path.is_symlink():
        text = path.read_text(encoding='utf-8')
        if '[admin]' in text or '[general]' in text:
            return text, 'default/manager.conf'
    secret = asterisk_addon_raw_option('ami_password')
    if not secret:
        # Fallback: das in DIESER App eingetragene admin-Passwort (stimmt laut Asterisk-Log, nur die ACL sperrt)
        try:
            own = json.loads((DATA_DIR / 'options.json').read_text())
            if str(own.get('ami_username') or 'admin') == 'admin':
                secret = own.get('ami_password') or ''
        except (OSError, ValueError, TypeError):
            pass
    if not secret:
        raise ValueError('manager.conf des Asterisk-Add-ons nicht lesbar und ami_password nicht ermittelbar – '
                         'bitte die Ausgabe von „cat /etc/asterisk/manager.conf“ prüfen.')
    return ('[general]\nenabled = yes\nport = 5038\nbindaddr = 0.0.0.0\ndisplayconnects = yes\n\n[admin]\n'
            f'secret = {secret}\ndeny = 0.0.0.0/0.0.0.0\npermit = 127.0.0.1/255.255.255.0\n'
            'read = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message\n'
            'write = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message\n'
            'writetimeout = 5000\n'), 'aus Add-on-Optionen nachgebaut'


def manager_conf_with_include(base):
    text = base
    if text.startswith(MANAGER_HEADER):
        text = text[len(MANAGER_HEADER):]
    text = re.sub(r'^\s*#(try)?include\s+"?manager_custom\.conf"?\s*$\n?', '', text, flags=re.M).rstrip('\n')
    return MANAGER_HEADER + text + '\n\n#tryinclude manager_custom.conf\n'


def write_manager_conf(content, expected_hash):
    """Only for ami_einrichten: custom/manager.conf is blocked for the file editor (AMI secrets)."""
    with LOCK:
        if not ASTERISK_DIR.is_dir():
            raise ValueError('Asterisk-Verzeichnis nicht gefunden')
        CUSTOM.mkdir(parents=True, exist_ok=True)
        target = CUSTOM / 'manager.conf'
        if target.is_symlink() or CUSTOM.is_symlink():
            raise ValueError('Symlinks sind nicht erlaubt')
        old = target.read_text(encoding='utf-8') if target.exists() else ''
        if digest(old) != expected_hash:
            raise ValueError('manager.conf wurde zwischenzeitlich geändert: erneut versuchen')
        if old:
            backup_dir = CUSTOM / '.smartify-backups'
            backup_dir.mkdir(exist_ok=True)
            backup = backup_dir / f'manager.conf.{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}.bak'
            backup.write_text(old, encoding='utf-8')
            os.chmod(backup, 0o600)
            prune_backups(backup_dir, 'manager.conf.*.bak')
        fd, temp = tempfile.mkstemp(prefix='.smartify-', dir=str(CUSTOM))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(content)
                fp.flush()
                os.fsync(fp.fileno())
            os.chmod(temp, 0o640)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        audit('file_saved', 'manager.conf', detail='ami_einrichten')


def ami_einrichten(body):
    if body.get('confirm') is not True:
        raise ValueError('Bestätigung fehlt')
    password = secrets.token_urlsafe(24)
    info = read_file('manager_custom.conf')
    current = info['content'] if info['source'] == 'custom' else ''
    new = manager_conf_with_user(current, password)
    include = manager_include_state()
    manager_written, quelle = False, ''
    if include is not True:
        main = CUSTOM / 'manager.conf'
        if main.is_file():
            old_main = main.read_text(encoding='utf-8')
            base, quelle = old_main, 'custom/manager.conf'
        else:
            old_main = ''
            base, quelle = manager_conf_base()
        write_manager_conf(manager_conf_with_include(base), digest(old_main))
        manager_written = True
    write_file('manager_custom.conf', new, digest(current))
    data = {'ami_username': AMI_USER, 'ami_password': password,
            'angelegt': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    fd, temp = tempfile.mkstemp(prefix='.smartify-ami-', dir=str(DATA_DIR))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fp:
            json.dump(data, fp)
        os.chmod(temp, 0o600)
        os.replace(temp, AMI_OVERRIDE_FILE)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    stored = self_options_update({'ami_username': AMI_USER, 'ami_password': password})
    audit('ami_eingerichtet', AMI_USER, detail=f'optionen={stored};manager_conf={manager_written};quelle={quelle}')
    restart = manager_written
    return {'eingerichtet': True, 'benutzer': AMI_USER, 'optionen_gespeichert': stored, 'include': include,
            'manager_conf': manager_written, 'quelle': quelle, 'neustart_noetig': restart, 'eigene_ip': _own_ip(),
            'befehl': ('Asterisk-Add-on neu starten (Einstellungen → Add-ons/Apps → Asterisk → Neu starten)' if restart else
                       "docker exec $(docker ps --format '{{.Names}}' | grep -m1 " + slug + ') asterisk -rx "manager reload"'),
            'pruefen': ("docker exec $(docker ps --format '{{.Names}}' | grep -m1 " + slug + ') asterisk -rx "manager show users"'),
            'note': ('Benutzer „smartify“ in manager_custom.conf angelegt'
                     + (' und custom/manager.conf mit Einbindung erzeugt ([admin] unverändert, Quelle: ' + quelle + ')' if manager_written else '')
                     + '. Backups wurden erstellt. '
                     + ('Auch in den App-Optionen gespeichert. ' if stored else 'App-Optionen konnten nicht gesetzt werden – der Manager nutzt den Zugang trotzdem. ')
                     + ('Jetzt das Asterisk-Add-on einmal NEU STARTEN (laufende Anrufe brechen ab), dann „Verbindung prüfen“.' if restart
                        else 'Jetzt einmal „manager reload“ ausführen, dann „Verbindung prüfen“.'))}


# Trusted inbound SIP over Tailnet: scoped PJSIP identify and dialplan rules.
def inbound_workspace():
    return inbound_routes.workspace(read_file, CUSTOM, DEFAULT, pjsip_blocks, scan_endpoints)


def inbound_prepare(data):
    return inbound_routes.prepare(data, read_file, CUSTOM, DEFAULT, pjsip_blocks, scan_endpoints)


def inbound_preview(data):
    with LOCK:
        output = inbound_prepare(data)
        for filename, content in ((output['pjsip_file'],output['pjsip_content']),
                                  (output['extensions_file'],output['extensions_content'])):
            checked = lint_conf(filename, content)
            if checked['errors']:
                raise ValueError(filename+': '+ checked['issues'][0]['message'])
        return {'pjsip':output['pjsip_preview'], 'extensions':output['extensions_preview'],
                'updated':output['updated'], 'warning':'Vorschau, noch nicht gespeichert. IP-basiert ohne Passwort; nur bestätigte Tailscale-Geräte erlauben.'}


def inbound_save(data):
    if data.get('confirm') is not True:
        raise ValueError('Speichern muss ausdrücklich bestätigt werden')
    with LOCK:
        output = inbound_prepare(data)
        p_name, e_name = output['pjsip_file'], output['extensions_file']
        for filename, content in ((p_name,output['pjsip_content']), (e_name,output['extensions_content'])):
            checked = lint_conf(filename,content)
            if checked['errors']:
                raise ValueError(filename+': '+checked['issues'][0]['message'])
        first = write_file(p_name, output['pjsip_content'], output['original_pjsip']['hash'])
        try:
            second = write_file(e_name, output['extensions_content'], output['original_extensions']['hash'])
        except (OSError, ValueError) as exc:
            try:
                # Bring the first file back to its original contents (another
                # versioned backup will be created). Never reload automatically.
                write_file(p_name, output['original_pjsip']['content'],first['hash'])
            except (OSError, ValueError) as undo:
                raise ValueError('ACHTUNG: '+e_name+' fehlgeschlagen, '+p_name+' konnte nicht automatisch zurückgesetzt werden: '+str(undo)) from exc
            raise ValueError('Speichern der zweiten Datei fehlgeschlagen; erste Datei zurückgesetzt: '+str(exc)) from exc
        audit('inbound_saved', p_name, detail='route='+output['name']+';ips='+str(len(output['ips']))+';targets='+str(len(output['targets'])))
        return {'saved':True, 'note':'Eingang '+output['name']+' in custom/'+p_name+' und custom/'+e_name+
                ' gespeichert. Backups vorhanden. Asterisk noch nicht neu geladen.',
                'pjsip_hash':first['hash'], 'extensions_hash':second['hash']}


STATIC_FILES = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'),
                '/pjsip-builder.js': ('pjsip-builder.js', 'text/javascript; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/anlage-ui.js': ('anlage-ui.js', 'text/javascript; charset=utf-8'), '/setup-wizard.js': ('setup-wizard.js', 'text/javascript; charset=utf-8'), '/verbindungen-ui.js': ('verbindungen-ui.js', 'text/javascript; charset=utf-8'), '/app.css': ('app.css', 'text/css; charset=utf-8')}
PAGE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")


class Handler(BaseHTTPRequestHandler):
    def allowed_client(self):
        return self.client_address[0] in {'172.30.32.2', '127.0.0.1', '::1'}

    def reject_non_ingress(self):
        if self.allowed_client():
            return False
        self.reply(403, {'error': 'Nur über Home Assistant Ingress erreichbar'})
        return True

    def log_message(self, format, *args):
        # Requests may contain sensitive details; no access log. Changes and errors go to the audit log.
        return

    def send_bytes(self, status, data, ctype, csp="default-src 'none'; frame-ancestors 'self'", extra=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', csp)
        for key, val in (extra or {}).items():
            self.send_header(key, val)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def reply(self, status, obj, extra=None):
        self.send_bytes(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8', extra=extra)

    def guarded(self, func, *args):
        try:
            self.reply(200, func(*args))
        except (ValueError, OSError, TypeError, UnicodeError, KeyError) as exc:
            self.reply(400, {'error': str(exc)})

    def do_GET(self):
        self._safe(self._do_get)

    def do_POST(self):
        self._safe(self._do_post)

    def _safe(self, func):
        try:
            func()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # never leave the browser with an empty response
            audit('internal_error', urlsplit(self.path).path, 'error', f'{type(exc).__name__}: {str(exc)[:120]}')
            try:
                self.reply(500, {'error': f'Interner Fehler ({type(exc).__name__}): {str(exc)[:200]}'})
            except OSError:
                pass

    def _do_get(self):
        if self.reject_non_ingress(): return
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        if path in STATIC_FILES:
            name, ctype = STATIC_FILES[path]
            self.send_bytes(200, (APP_DIR / name).read_bytes(), ctype, csp=PAGE_CSP)
        elif path == '/api/status':
            self.reply(200, {'version': ADDON_VERSION, 'frontend': FRONTEND_VERSIONS,
                             'slug': slug, 'container': 'addon_' + slug, 'asterisk_config_found': ASTERISK_DIR.is_dir(),
                             'custom': str(CUSTOM), 'files': available_files(), 'yaml': yaml is not None,
                             'mode': 'file-editor / no automatic reload'})
        elif path == '/api/health':
            self.reply(200, check_health())
        elif path == '/api/changes':
            self.reply(200, {'logs': log_tail(), 'note': 'Rotierende Logs unter /data/logs/smartify-manager.log; keine Passwörter oder Datei-Inhalte.'})
        elif path == '/api/sip-core-draft':
            self.reply(200, read_sip_core())
        elif path == '/api/wizard/password-targets':
            self.reply(200, wizard_password_targets())
        elif path == '/api/sip-core/active':
            self.guarded(active_sip_core_view)
        elif path == '/api/sip-core/auto-secret':
            self.guarded(auto_secret_preview)
        elif path == '/api/wizard/password-rotate':
                out = wizard_rotate_passwords(body)
            elif path == '/api/check/users':
            self.guarded(check_users)
        elif path == '/api/hints':
            self.reply(200, {'hints': {n: reload_hint(n) for n in available_files()}, 'sip_core': reload_hint('sip_core_draft.yaml')})
        elif path == '/api/camera-mapping':
            self.guarded(read_camera_map)
        elif path == '/api/endpoints':
            self.reply(200, scan_endpoints())
        elif path == '/api/structured/pjsip':
            self.guarded(pjsip_table)
        elif path == '/api/number-plan':
            self.reply(200, scan_number_plan())
        elif path == '/api/inbound':
            self.guarded(inbound_workspace)
        elif path == '/api/live':
            self.reply(200, ami_readonly())
        elif path == '/api/ami/diagnose':
            self.reply(200, ami_diagnose())
        elif path == '/api/entities':
            self.reply(200, ha_entity_index())
        elif path == '/api/go2rtc/streams':
            self.reply(200, go2rtc_streams())
        elif path == '/api/go2rtc/frame':
            try:
                data, ctype = go2rtc_frame((query.get('src') or [''])[0])
                self.send_bytes(200, data, ctype)
            except ValueError as exc:
                self.reply(400, {'error': str(exc)})
        elif path == '/api/export':
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')
            self.reply(200, export_data(), extra={'Content-Disposition': f'attachment; filename="smartify-export-{stamp}.json"'})
        elif path == '/api/anlage':
            self.guarded(lambda: {**read_anlage(), 'typen': anlage_model.TYPEN, 'faehigkeiten': anlage_model.FAEHIGKEITEN,
                                  'tailscale': anlage_model.tailscale_serve_anleitung(),
                                  'hersteller': [{'hersteller': k, 'bezeichnung': l, 'pfad': m, 'nebenstream': n} for k, l, m, n in rtsp_mod.VENDORS],
                                  'rtsp_passwoerter': sorted(read_secrets().get('rtsp', {})),
                                  'sip_passwoerter': sorted(read_secrets().get('sip', {}))})
        elif path == '/api/anlage/vorschlag':
            self.guarded(anlage_vorschlag)
        elif path == '/api/erzeugen/vorschau':
            self.guarded(erzeugen_vorschau)
        elif path == '/api/anlage/zugang':
            self.guarded(zugangsdaten, (query.get('nummer') or [''])[0])
        elif path == '/api/anlage/auswahl':
            self.guarded(anlage_auswahl)
        elif path == '/api/anlage/netz':
            self.guarded(netz_erkennen)
        elif path == '/api/verbindungen':
            self.guarded(lambda: verbindungen_mod.graph(read_anlage()['model'],
                                                        anlage_model.endpoints_from_conf(conf_files_for_model()), dialplan_text_all()))
        elif path == '/api/pruefbericht':
            self.guarded(pruefbericht)
        elif path == '/api/anlage/export':
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')
            try:
                data = anlage_export()
                kunde = re.sub(r'[^A-Za-z0-9_-]+', '-', data['anlage'].get('kunde') or data['anlage'].get('name') or 'anlage').strip('-')[:40] or 'anlage'
                self.reply(200, data, extra={'Content-Disposition': f'attachment; filename="smartify-anlage-{kunde}-{stamp}.json"'})
            except (ValueError, OSError) as exc:
                self.reply(400, {'error': str(exc)})
        elif path == '/api/discovery':
            self.guarded(lambda: {'files': read_discovery()})
        elif path.startswith('/api/file/'):
            self.guarded(read_file, path.rsplit('/', 1)[-1])
        else:
            self.reply(404, {'error': 'Nicht gefunden'})

    POST_ROUTES = ('/api/camera-mapping', '/api/sip-core-draft', '/api/lint', '/api/sip-core/merge', '/api/sip-core/auto-answer/stage', '/api/sip-core/diff',
                   '/api/sip-core/apply', '/api/sip-core/auto-secret/apply', '/api/sip-core/stage-user', '/api/wizard/password-rotate', '/api/check/users', '/api/ami/command', '/api/import',
                   '/api/structured/pjsip/save', '/api/structured/group/save', '/api/structured/cloud/save',
                   '/api/inbound/preview', '/api/inbound/save', '/api/anlage', '/api/anlage/import', '/api/erzeugen/uebernehmen', '/api/kameras/suche', '/api/kameras/test', '/api/kameras/passwort', '/api/ami/einrichten')

    def _do_post(self):
        if self.reject_non_ingress(): return
        path = urlsplit(self.path).path
        if path not in self.POST_ROUTES and not path.startswith(('/api/file/', '/api/copy-default/', '/api/create-custom/')):
            self.reply(404, {'error': 'Nicht gefunden'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 1 <= size <= MAX_SIZE * 3:
                raise ValueError('Ungültige Länge')
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError('Ungültige Anfrage')
            if path == '/api/camera-mapping':
                out = write_camera_map(body.get('mapping'), body.get('hash'))
            elif path == '/api/sip-core-draft':
                out = write_sip_core(body.get('content'), body.get('hash'))
            elif path == '/api/lint':
                out = lint_conf(body.get('name'), body.get('content'))
            elif path == '/api/sip-core/merge':
                out = merge_sip_core(body.get('base') or '', body.get('snippet') or '')
            elif path == '/api/sip-core/auto-answer/stage':
                out = stage_auto_answer_allowlist(body.get('content') or '', body.get('extension'),
                                                   body.get('enabled'), body.get('allowed'))
            elif path == '/api/sip-core/diff':
                out = diff_against_active(body.get('content') or '')
            elif path == '/api/sip-core/apply':
                if body.get('confirm') is not True:
                    raise ValueError('Bestätigung fehlt')
                out = apply_sip_core(body.get('content') or '', body.get('active_hash'))
            elif path == '/api/sip-core/auto-secret/apply':
                out = auto_secret_sync(body.get('active_hash'), body.get('confirm'))
            elif path == '/api/sip-core/stage-user':
                out = stage_sip_core_user(body.get('content') or '', body.get('extension'),
                                          body.get('ha_username'), body.get('display_name'), body.get('password') or '')
            elif path == '/api/check/users':
                out = check_users('content', body.get('content'))
            elif path == '/api/structured/pjsip/save':
                out = save_pjsip_row(body)
            elif path == '/api/structured/group/save':
                out = save_group_row(body)
            elif path == '/api/structured/cloud/save':
                out = save_cloud_endpoint(body)
            elif path == '/api/inbound/preview':
                out = inbound_preview(body)
            elif path == '/api/inbound/save':
                out = inbound_save(body)
            elif path == '/api/ami/command':
                command = ami_command_allowed(body.get('command'))
                if command in AMI_RELOAD_COMMANDS and body.get('confirm') is not True:
                    raise ValueError('Reload nur mit Bestätigung')
                out = ami_run(command)
            elif path == '/api/import':
                if body.get('confirm') is not True:
                    raise ValueError('Bestätigung fehlt')
                out = import_data(body.get('data'))
            elif path == '/api/anlage':
                out = write_anlage(body.get('model'), body.get('hash'))
            elif path == '/api/erzeugen/uebernehmen':
                out = erzeugen_uebernehmen(body)
            elif path == '/api/ami/einrichten':
                out = ami_einrichten(body)
            elif path == '/api/kameras/suche':
                out = kamera_suche(body)
            elif path == '/api/kameras/test':
                out = kamera_test(body)
            elif path == '/api/kameras/passwort':
                out = kamera_passwort(body)
            elif path == '/api/anlage/import':
                if body.get('confirm') is not True:
                    raise ValueError('Bestätigung fehlt')
                out = anlage_import_datei(body.get('data'))
            elif path.startswith('/api/create-custom/'):
                out = create_custom_file(path.rsplit('/', 1)[-1])
            elif path.startswith('/api/copy-default/'):
                out = copy_default_to_custom(path.rsplit('/', 1)[-1], body.get('hash'))
            else:
                out = write_file(path.rsplit('/', 1)[-1], body.get('content'), body.get('hash'))
            self.reply(200, out)
        except (ValueError, OSError, TypeError, UnicodeError, KeyError, json.JSONDecodeError) as exc:
            audit('request_rejected', path, 'rejected', type(exc).__name__)
            self.reply(400, {'error': str(exc)})


if __name__ == '__main__':
    if not ASTERISK_DIR.is_dir():
        print(f'ACHTUNG: Asterisk-Verzeichnis {ASTERISK_DIR} nicht gefunden', flush=True)
    # Supervisor ingress binds port internally; no public ports are exposed in addon config.
    audit('startup',detail=f'version={ADDON_VERSION};port={PORT};asterisk_found={ASTERISK_DIR.is_dir()}')
    sip_status_worker.start(AmiSession, core_api, LOGGER, read_anlage)
    ring_router.start(AmiSession, read_anlage, core_api, LOGGER)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
