"""Asterisk AMI incoming-call events -> Home Assistant media player ringing.

Only external HA media_player audio is handled here; Asterisk ringback and SIP
signalling remain untouched. The native SIP Core sound must be disabled separately.
"""
import re
import threading
import time

RE_CHANNEL = re.compile(r"(?:^|/)PJSIP/([A-Za-z0-9_.+-]+)-[A-Fa-f0-9]+")
RE_DIAL = re.compile(r"(?:^|/)PJSIP/([A-Za-z0-9_.+-]+)(?:/|$)", re.I)


def destination(event):
    channel = str(event.get("DestChannel") or event.get("Destination") or "")
    m = RE_CHANNEL.search(channel)
    if m:
        return m.group(1)
    dial = str(event.get("DialString") or "")
    m = RE_DIAL.search(dial)
    return m.group(1) if m else ""


class RingRouter:
    def __init__(self, read_model, ha_call, logger):
        self.read_model, self.ha_call, self.logger = read_model, ha_call, logger
        self.calls = {}
        self.groups = {}
        self.active_players = {}
        self.lock = threading.RLock()

    def service(self, name, entity_id, media=None):
        payload = {"entity_id": entity_id}
        if media:
            payload.update(media_content_id=media, media_content_type="music")
        self.ha_call("POST", "services/media_player/" + name, payload, timeout=4)

    def start(self, event):
        number = destination(event)
        unique = str(event.get("DestUniqueid") or event.get("DestUniqueID") or event.get("Uniqueid") or "")
        linked = str(event.get("Linkedid") or event.get("LinkedID") or unique)
        if not (number and unique):
            return
        try:
            model = self.read_model().get("model") or {}
            participant = next((p for p in model.get("teilnehmer", []) if
                number in (str(p.get("nummer") or ""), str(p.get("endpoint") or ""))), None)
        except (OSError, ValueError):
            return
        if not participant or participant.get("ring_output") != "media_player":
            return
        player = str(participant.get("ring_player") or "")
        media = str(participant.get("ring_media") or "")
        if not player.startswith("media_player.") or not media.startswith("/local/"):
            return
        with self.lock:
            if unique in self.calls:
                return
            self.calls[unique] = (player, linked, time.monotonic())
            self.groups.setdefault(linked, set()).add(unique)
            users = self.active_players.setdefault(player, set())
            first = not users
            users.add(unique)
        if first:
            try:
                self.service("play_media", player, media)
            except (OSError, ValueError) as exc:
                self.logger.warning("ring_router_play: %s", type(exc).__name__)
                self.stop(unique)

    def stop(self, unique):
        with self.lock:
            old = self.calls.pop(unique, None)
            if not old:
                return
            player, linked, _ = old
            users = self.active_players.get(player, set())
            users.discard(unique)
            if not users:
                self.active_players.pop(player, None)
            group = self.groups.get(linked, set())
            group.discard(unique)
            if not group:
                self.groups.pop(linked, None)
            should_stop = not users
        if should_stop:
            try:
                self.service("media_stop", player)
            except (OSError, ValueError) as exc:
                self.logger.warning("ring_router_stop: %s", type(exc).__name__)

    def stop_group(self, linked):
        with self.lock:
            keys = tuple(self.groups.get(linked, ()))
        for key in keys:
            self.stop(key)

    def process(self, event):
        kind = event.get("Event", "")
        if kind == "DialBegin":
            self.start(event)
        elif kind == "DialEnd":
            self.stop(str(event.get("DestUniqueid") or event.get("DestUniqueID") or ""))
            if str(event.get("DialStatus") or "").upper() == "ANSWER":
                self.stop_group(str(event.get("Linkedid") or event.get("LinkedID") or ""))
        elif kind in ("BridgeEnter", "BridgeCreate"):
            linked = str(event.get("Linkedid") or event.get("LinkedID") or "")
            if linked:
                self.stop_group(linked)
        elif kind == "Hangup":
            unique = str(event.get("Uniqueid") or "")
            self.stop(unique)
            linked = str(event.get("Linkedid") or "")
            if unique == linked:
                self.stop_group(linked)

    def expire(self):
        now = time.monotonic()
        with self.lock:
            expired = [key for key, (_, _, started) in self.calls.items() if now - started > 45]
        for key in expired:
            self.stop(key)

    def shutdown(self):
        with self.lock:
            keys = tuple(self.calls)
        for key in keys:
            self.stop(key)


def start(ami_class, read_model, ha_call, logger):
    router = RingRouter(read_model, ha_call, logger)
    def loop():
        while True:
            try:
                with ami_class() as ami:
                    reply = ami.action({"Action": "Events", "EventMask": "call"})
                    if reply.get("Response", "").lower() != "success":
                        raise ValueError("AMI call event subscription denied")
                    ami.sock.settimeout(2)
                    while True:
                        try:
                            event = ami.parse(ami._read_block())
                        except ValueError as exc:
                            if "Zeitüberschreitung" in str(exc):
                                router.expire()
                                continue
                            raise
                        router.process(event)
                        router.expire()
            except (OSError, ValueError) as exc:
                logger.warning("ring_router_AMI: %s", type(exc).__name__)
            finally:
                router.shutdown()
            time.sleep(5)
    threading.Thread(target=loop, daemon=True, name="smartify-ring-router").start()
