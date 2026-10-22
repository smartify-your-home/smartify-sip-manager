"""Read-only inventory and conservative migration planning for Asterisk dialplan.

The migration plan never deletes or edits foreign configuration. Only exact,
simple extension definitions are eligible for an explicit later takeover.
"""
import re
from .generator import split_managed

HEADER = re.compile(r'^\s*\[([^\]]+)\]')
EXTEN = re.compile(r'^\s*exten\s*=>\s*(\d{2,8})\s*,\s*1\s*,', re.I)
SAME = re.compile(r'^\s*same\s*=>', re.I)


def inventory_dialplan(text):
    """Return legacy extension records outside Smartify's managed block."""
    outside, _ = split_managed(text or '')
    records, context, active = [], None, None
    for lineno, raw in enumerate(outside.splitlines(), 1):
        line = raw.split(';', 1)[0].strip()
        header = HEADER.match(line)
        if header:
            context, active = header.group(1), None
            continue
        ext = EXTEN.match(line)
        if ext and context:
            active = {'context': context, 'number': ext.group(1),
                      'line': lineno, 'steps': [line]}
            records.append(active)
        elif active and SAME.match(line):
            active['steps'].append(line)
        elif line and not line.startswith('#'):
            active = None
    return records


def plan_dialplan_migration(text, desired_routes):
    """Compare existing manual routes to desired {(context, number)}.

    All legacy routes require explicit review: their bodies can contain
    conditions, authentication or side effects that must not be discarded.
    """
    desired = set(desired_routes)
    inventory = inventory_dialplan(text)
    found = {(r['context'], r['number']) for r in inventory}
    duplicates = {key for key in found
                  if sum((r['context'], r['number']) == key for r in inventory) > 1}
    return {
        'manual_routes': inventory,
        'conflicts': [r for r in inventory
                      if (r['context'], r['number']) in desired],
        'stale_candidates': [r for r in inventory
                             if (r['context'], r['number']) not in desired],
        'duplicate_keys': sorted(duplicates),
        'missing_routes': sorted(desired - found),
        'requires_approval': bool(inventory),
        'automatic_deletion_allowed': False,
    }


# Strictly supported legacy route: NoOp -> Dial(PJSIP_DIAL_CONTACTS(N))
# -> Hangup. Arbitrary applications and expressions must never be removed.
NOOP = re.compile(r'^exten\s*=>\s*(\d{2,8})\s*,\s*1\s*,\s*NoOp\([^;]*\)$', re.I)
DIAL = re.compile(r'^same\s*=>\s*n\s*,\s*Dial\(\$\{PJSIP_DIAL_CONTACTS\((\d{2,8})\)\},\s*(\d{1,3})\)$', re.I)
HANGUP = re.compile(r'^same\s*=>\s*n\s*,\s*Hangup\(\)$', re.I)


def safe_legacy_route(record):
    """True only for an exact three-step route with matching destination."""
    steps = record['steps']
    if len(steps) != 3:
        return False
    a, b = NOOP.fullmatch(steps[0]), DIAL.fullmatch(steps[1])
    return bool(a and b and HANGUP.fullmatch(steps[2])
                and a.group(1) == b.group(1) == record['number']
                and 5 <= int(b.group(2)) <= 120)


def reconcile_legacy_routes(text, managed_contexts, desired_routes):
    """Remove only recognized simple routes from explicitly managed contexts.

    The caller must regenerate the managed block from desired_routes using
    gen_dialplan; this function does not create routing permissions.
    Unknown routes block automatic migration rather than being discarded.
    """
    managed_contexts = set(managed_contexts)
    desired_routes = set(desired_routes)
    inventory = inventory_dialplan(text)
    eligible = [r for r in inventory if r['context'] in managed_contexts]
    blocked = [r for r in eligible if not safe_legacy_route(r)]
    if blocked:
        raise ValueError('Manuelle komplexe Dialplan-Routen verhindern automatische Migration: '
                         + ', '.join(f"{r['number']}@{r['context']}" for r in blocked))
    from .generator import remove_manual_exten
    result = text
    for r in eligible:
        result = remove_manual_exten(result, r['number'], [r['context']])
    return {
        'content': result,
        'removed': [(r['context'], r['number']) for r in eligible],
        'recreated': sorted(desired_routes),
        'backup_required': bool(eligible),
    }
