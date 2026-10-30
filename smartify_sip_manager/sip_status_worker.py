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
    """Use documented AMI ContactList.Endpoint and EndpointList.Aor fields.

    Older Asterisk versions may omit Endpoint. In that case associate the
    contact through its AoR or the prefix of ObjectName ('104/sip:...').
    A registered but non-qualified contact is not labelled unreachable.
    """
    with ami_class() as ami:
        eps = ami.list_events({"Action": "PJSIPShowEndpoints"}, "EndpointListComplete")
        contacts = ami.list_events({"Action": "PJSIPShowContacts"}, "ContactListComplete")
    by_endpoint, by_aor = {}, {}
    for c in contacts:
        if c.get("Event") != "ContactList":
            continue
        endpoint = str(c.get("Endpoint") or c.get("EndpointName") or "").strip()
        aor = _aor_name(c)
        if endpoint:
            by_endpoint.setdefault(endpoint, []).append(c)
        if aor:
            by_aor.setdefault(aor, []).append(c)
    result = []
    for ep in eps:
        if ep.get("Event") != "EndpointList":
            continue
        name = str(ep.get("ObjectName") or "").strip()
        if not name:
            continue
        # 'Aor' singular and 'Contacts' are the officially documented fields.
        aors = str(ep.get("Aor") or ep.get("Aors") or ep.get("AORs") or ep.get("AOR") or "")
        keys = [name] + [aor.strip() for aor in aors.split(",") if aor.strip()]
        linked, seen = [], set()
        for contact in by_endpoint.get(name, []) + [c for key in keys for c in by_aor.get(key, [])]:
            identity = str(contact.get("ObjectName") or contact.get("ID") or contact.get("Uri") or id(contact))
            if identity not in seen:
                seen.add(identity)
                linked.append(contact)
        states = [_contact_status(contact) for contact in linked]
        registered = bool(linked)
        reachable = "reachable" in states
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
                rules = {}
                browsers = {}
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
                        # Publish only extension-level authorization rules, not HA usernames
                        # or any SIP credentials. None means unrestricted; [] means nobody.
                        rules = {}
                        browsers = {}
                        for p in participants:
                            if not isinstance(p, dict):
                                continue
                            number = str(p.get("nummer") or "").strip()
                            if not number:
                                continue
                            if p.get("browser_mod_entity"):
                                browsers[number] = str(p["browser_mod_entity"])
                            rules[number] = {
                                "can_call": p.get("anruf_ziele"),
                                "called_by": p.get("angerufen_von"),
                            }
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
                        "call_rules": rules,
                        "browser_mod_entities": browsers,
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
