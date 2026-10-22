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
