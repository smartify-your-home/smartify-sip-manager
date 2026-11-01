"""Prepare Piper TTS audio for Asterisk and originate an external SIP alarm call."""
import os
import re
import struct
import uuid
import urllib.request
import urllib.error
import time
import threading
import logging
from pathlib import Path
from urllib.parse import urlsplit

MAX_WAV_BYTES = 5_000_000
MEDIA_DIR = Path("/media/smartify-sip-alarms")


def repair_wav(raw):
    wav = bytearray(raw)
    if len(wav) < 45 or wav[:4] != b"RIFF" or wav[8:16] != b"WAVEfmt " or wav[36:40] != b"data":
        raise ValueError("Piper hat kein erwartetes PCM-WAV geliefert")
    audio_format, channels, rate = struct.unpack_from("<HHI", wav, 20)
    bits = struct.unpack_from("<H", wav, 34)[0]
    if (audio_format, channels, rate, bits) != (1, 1, 8000, 16):
        raise ValueError("Piper-WAV muss PCM, Mono, 8000 Hz, 16 Bit sein")
    if len(wav) > MAX_WAV_BYTES:
        raise ValueError("Piper-WAV ist zu groß")
    struct.pack_into("<I", wav, 4, len(wav) - 8)
    struct.pack_into("<I", wav, 40, len(wav) - 44)
    return bytes(wav)



def alarm_targets(options):
    """Comma-/newline-separated SIP URIs; old single destination remains compatible."""
    raw = str(options.get("alarm_destinations") or "").strip()
    configured = [part for line in raw.splitlines() for part in re.split("[,;]+", line)] if raw else [str(options.get("alarm_destination") or "")]
    targets = []
    for item in configured:
        item = item.strip()
        if not item:
            continue
        if not re.fullmatch(r"sip:[A-Za-z0-9_.+%-]{1,100}@[A-Za-z0-9.-]{1,150}", item):
            raise ValueError("Ungültige SIP-Alarmdestination: " + item[:80])
        if item not in targets:
            targets.append(item)
    if not targets or len(targets) > 12:
        raise ValueError("Bitte 1 bis 12 SIP-Alarmziele konfigurieren")
    return targets


def alarm_caller_id(options):
    """Build a caller ID without accepting AMI line breaks or SIP header injection."""
    name = str(options.get("alarm_caller_name") or "RAUCHALARM").strip()
    number = str(options.get("alarm_caller_number") or "999").strip()
    if not re.fullmatch(r"[A-Za-z0-9ÄÖÜäöüß ._-]{1,48}", name):
        raise ValueError("Alarm-Anrufername ungültig")
    if not re.fullmatch(r"[0-9]{1,15}", number):
        raise ValueError("Alarm-Anrufernummer ungültig")
    return f'"{name}" <{number}>'


LOG = logging.getLogger("smartify.alarm")


def retry_settings(options):
    attempts = int(options.get("alarm_call_attempts", 3))
    timeout = int(options.get("alarm_ring_seconds", 30))
    pause = int(options.get("alarm_retry_pause_seconds", 30))
    if not 1 <= attempts <= 5 or not 10 <= timeout <= 90 or not 0 <= pause <= 300:
        raise ValueError("Wahlwiederholung: Versuche 1–5, Klingeldauer 10–90 s, Pause 0–300 s")
    return attempts, timeout, pause


def _redial_target(destination, endpoint, audio_path, caller_id, ami_session,
                   attempts, timeout, pause, sleep=time.sleep):
    """Synchronous AMI Originate: Success indicates answered, unlike async queue acceptance."""
    for attempt in range(1, attempts + 1):
        try:
            with ami_session() as ami:
                # AmiSession normally uses 5 seconds for routine actions;
                # synchronous Originate must wait for the whole ringing period.
                if hasattr(ami, "sock") and ami.sock is not None:
                    ami.sock.settimeout(timeout + 12)
                result = ami.action({
                    "Action": "Originate",
                    "Channel": f"PJSIP/{endpoint}/{destination}",
                    "Application": "Playback",
                    "Data": str(audio_path.with_suffix("")),
                    "CallerID": caller_id,
                    "Timeout": str(timeout * 1000),
                    "Async": "false",
                })
            if str(result.get("Response", "")).lower() == "success":
                LOG.info("Alarmanruf angenommen: %s, Versuch %s", destination, attempt)
                return
            LOG.warning("Alarmanruf nicht angenommen: %s, Versuch %s/%s: %s",
                        destination, attempt, attempts, result.get("Message", "AMI Error"))
        except Exception:
            # An unknown result must not trigger another call: the first call
            # may already have been answered while AMI disconnected.
            LOG.exception("Alarmanrufstatus unklar für %s; keine automatische Wiederholung", destination)
            return
        if attempt < attempts:
            sleep(pause)
    LOG.error("Alarmanruf ohne Annahme nach %s Versuchen: %s", attempts, destination)


def prepare_and_call(message, options, core_api, ami_session, media_dir=MEDIA_DIR):
    """Text is trusted only as speech; SIP endpoint and target come from add-on options."""
    if not isinstance(message, str) or not 1 <= len(message) <= 500:
        raise ValueError("Alarmtext muss 1 bis 500 Zeichen enthalten")
    endpoint = str(options.get("alarm_endpoint") or "").strip()
    destinations = alarm_targets(options)
    caller_id = alarm_caller_id(options)
    attempts, ring_seconds, retry_pause = retry_settings(options)
    engine = str(options.get("alarm_tts_engine") or "tts.piper").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", endpoint):
        raise ValueError("Alarm-Endpoint fehlt oder ist ungültig")
    if not re.fullmatch(r"tts\.[A-Za-z0-9_]{1,100}", engine):
        raise ValueError("TTS-Engine ungültig")

    response = core_api("POST", "tts_get_url", {
        "engine_id": engine,
        "message": message,
        "cache": False,
        "options": {"preferred_format": "wav", "preferred_sample_rate": 8000,
                    "preferred_sample_channels": 1, "preferred_sample_bytes": 2}
    }, timeout=30)
    url = response.get("url", "") if isinstance(response, dict) else ""
    parsed = urlsplit(url)
    if not (parsed.path.startswith("/api/tts_proxy/") and parsed.path.endswith(".wav")
            and not parsed.query and not parsed.fragment):
        raise ValueError("Home Assistant lieferte keine gültige TTS-WAV-URL")

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise ValueError("Supervisor-Token fehlt")
    # Use the authenticated Supervisor proxy, not arbitrary URLs supplied by the client.
    req = urllib.request.Request("http://supervisor/core" + parsed.path,
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read(MAX_WAV_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"TTS-Datei HTTP {exc.code}; Supervisor-Zugriff prüfen") from None
    except (OSError, TimeoutError) as exc:
        raise ValueError(f"TTS-Datei nicht erreichbar: {str(exc)[:100]}") from None
    audio = repair_wav(raw)

    media_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 24 * 3600
    for old in media_dir.glob("alarm_*.wav"):
        try:
            if old.is_file() and not old.is_symlink() and old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass
    ident = uuid.uuid4().hex
    path = media_dir / ("alarm_" + ident + ".wav")
    tmp = media_dir / ("alarm_" + ident + ".tmp")
    try:
        tmp.write_bytes(audio)
        tmp.chmod(0o644)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    # The shared /media mount must also be present at the same path in Asterisk.
    # One background worker per recipient; calls ring concurrently.
    # Blocking Originate lets Asterisk distinguish answered from not answered.
    workers = []
    for destination in destinations:
        thread = threading.Thread(
            target=_redial_target,
            args=(destination, endpoint, path, caller_id, ami_session,
                  attempts, ring_seconds, retry_pause),
            name="alarm-redial-" + uuid.uuid4().hex[:8],
            daemon=True,
        )
        workers.append(thread)
    for worker in workers:
        worker.start()
    return {
        "queued": True,
        "queued_count": len(workers),
        "destinations": destinations,
        "file": path.name,
        "attempts": attempts,
        "note": "Wahlwiederholung läuft pro Empfänger im Hintergrund; API-Antwort ist keine Zustellbestätigung",
    }
