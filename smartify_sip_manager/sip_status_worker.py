"""Read-only SIP contact monitor publishing a 10-second HA status snapshot.

Asterisk OPTIONS qualification is configured separately on the AoR; polling does
not perform SIP traffic by itself. This worker never edits Asterisk configuration.
"""
import threading
import time
from datetime import datetime, timezone

ENTITY = "sensor.smartify_sip_teilnehmer"
INTERVAL = 10


def _aor_name(contact):
    """AMI variants: AOR, Aor, or ObjectName '104/sip:...' / '104@@hash'."""
    name = str(contact.get("AOR") or contact.get("Aor") or contact.get("AorName") or "").strip()
    if name:
        return name
    obj = str(contact.get("ObjectName") or contact.get("ID") or "")
    return obj.split("/", 1)[0].split("@@", 1)[0].strip()


def _contact_status(contact):
    status = str(contact.get("Status") or contact.get("ContactStatus") or "").strip().lower()
    # PJSIP AMI calls the positive state "Reachable".
    if status in ("reachable", "avail", "available", "ok"):
        return "reachable"
    if status in ("unreachable", "unavail", "unavailable", "removed"):
        return "unreachable"
    return "unknown"


def snapshot(ami_class):
    with ami_class() as ami:
        eps = ami.list_events({"Action": "PJSIPShowEndpoints"}, "EndpointListComplete")
        contacts = ami.list_events({"Action": "PJSIPShowContacts"}, "ContactListComplete")
    by_aor = {}
    for c in contacts:
        if c.get("Event") != "ContactList":
            continue
        name = _aor_name(c)
        if name:
            by_aor.setdefault(name, []).append(c)
    result = []
    for ep in eps:
        if ep.get("Event") != "EndpointList":
            continue
        name = str(ep.get("ObjectName") or "").strip()
        if not name:
            continue
        # Only use known AOR mapping. Never falsely mark an endpoint offline
        # because AMI does not expose a mapping in EndpointList.
        aors = str(ep.get("Aors") or ep.get("AORs") or ep.get("AOR") or "")
        keys = [name] + [key.strip() for key in aors.split(",") if key.strip()]
        linked = []
        for key in keys:
            for contact in by_aor.get(key, []):
                if contact not in linked:
                    linked.append(contact)
        states = [_contact_status(contact) for contact in linked]
        registered = bool(linked)
        reachable = "reachable" in states
        # Missing/unmapped contact is UNKNOWN, not an authoritative "unregistered".
        status = ("reachable" if reachable else
                  "unreachable" if states and all(v == "unreachable" for v in states) else
                  "unknown")
        result.append({
            "extension": name,
            "name": name,
            "registered": registered,
            "reachable": reachable,
            "status": status,
            "contacts": len(linked),
            "device_state": str(ep.get("DeviceState") or "")[:48],
        })
    return sorted(result, key=lambda x: x["extension"])


def start(ami_class, core_api, logger, model_reader=None):
    """Start one daemon after the HTTP service has initialized."""
    def loop():
        while True:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                people = snapshot(ami_class)
                if model_reader:
                    try:
                        participants = (model_reader().get("model") or {}).get("teilnehmer") or []
                        names = {}
                        for p in participants:
                            if not isinstance(p, dict):
                                continue
                            label = str(p.get("name") or "").strip()
                            for key in ("nummer", "endpoint"):
                                identifier = str(p.get(key) or "").strip()
                                if identifier and label:
                                    names[identifier] = label[:100]
                        for person in people:
                            person["name"] = names.get(person["extension"], person["extension"])
                    except (ValueError, KeyError, OSError, TypeError):
                        pass
                state = str(sum(p["reachable"] for p in people))
                payload = {
                    "state": state,
                    "attributes": {
                        "friendly_name": "Smartify SIP Teilnehmer",
                        "icon": "mdi:phone-check",
                        "participants": people[:150],
                        "total": len(people),
                        "reachable": int(state),
                        "updated": now,
                        "source": "Asterisk AMI PJSIPShowContacts",
                    },
                }
                core_api("POST", "states/" + ENTITY, payload, timeout=6)
            except Exception as exc:
                # Never keep a previous green snapshot on AMI or API failure.
                try:
                    core_api("POST", "states/" + ENTITY, {
                        "state": "unavailable",
                        "attributes": {"friendly_name": "Smartify SIP Teilnehmer",
                                       "icon": "mdi:phone-alert",
                                       "participants": [], "updated": now,
                                       "error": type(exc).__name__},
                    }, timeout=6)
                except Exception:
                    pass
                logger.warning("sip_status_monitor: %s", type(exc).__name__)
            time.sleep(INTERVAL)

    threading.Thread(target=loop, name="smartify-sip-status", daemon=True).start()
