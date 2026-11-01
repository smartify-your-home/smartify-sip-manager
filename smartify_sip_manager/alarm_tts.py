"""Prepare Piper TTS audio for Asterisk and originate an external SIP alarm call."""
import os
import re
import struct
import uuid
import urllib.request
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


def prepare_and_call(message, options, core_api, ami_session, media_dir=MEDIA_DIR):
    """Text is trusted only as speech; SIP endpoint and target come from add-on options."""
    if not isinstance(message, str) or not 1 <= len(message) <= 500:
        raise ValueError("Alarmtext muss 1 bis 500 Zeichen enthalten")
    endpoint = str(options.get("alarm_endpoint") or "").strip()
    destination = str(options.get("alarm_destination") or "").strip()
    engine = str(options.get("alarm_tts_engine") or "tts.piper").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", endpoint):
        raise ValueError("Alarm-Endpoint fehlt oder ist ungültig")
    if not re.fullmatch(r"sip:[A-Za-z0-9_.+%-]{1,100}@[A-Za-z0-9.-]{1,150}", destination):
        raise ValueError("Alarm-SIP-Adresse fehlt oder ist ungültig")
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
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(MAX_WAV_BYTES + 1)
    audio = repair_wav(raw)

    media_dir.mkdir(parents=True, exist_ok=True)
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
    channel = f"PJSIP/{endpoint}/{destination}"
    with ami_session() as ami:
        result = ami.action({"Action": "Originate", "Channel": channel,
                             "Application": "Playback", "Data": str(path.with_suffix("")),
                             "CallerID": '"RAUCHALARM" <999>',
                             "Timeout": "30000", "Async": "true"})
    if result.get("Response", "").lower() != "success":
        path.unlink(missing_ok=True)
        raise ValueError("Asterisk Originate fehlgeschlagen: " + str(result.get("Message", "Unbekannt"))[:100])
    return {"queued": True, "file": path.name, "note": "AMI akzeptierte den Anrufauftrag; Zustellung nicht bestätigt"}
