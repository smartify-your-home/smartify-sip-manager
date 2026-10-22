"""Inventory and guarded reconciliation planning for Asterisk dialplan.

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
    """Remove recognized routes in owned contexts; reject ambiguous entries.

    Does not modify files. Caller must persist with atomic backup/rollback.
    """
    managed_contexts = set(managed_contexts)
    desired_routes = set(desired_routes)
    inventory = inventory_dialplan(text)
    eligible = [r for r in inventory if r['context'] in managed_contexts]
    blocked = [r for r in eligible if not safe_legacy_route(r)]
    if blocked:
        raise ValueError('Komplexe manuelle Routen verhindern Migration: '
                         + ', '.join(f"{r['number']}@{r['context']}" for r in blocked))
    # Never remove a route when multiple declarations share the same key.
    keys = [(r['context'], r['number']) for r in eligible]
    if len(keys) != len(set(keys)):
        raise ValueError('Doppelte Legacy-Routen verhindern automatische Migration')
    # Preserve managed block while removing only exact line ranges.
    outside, inside = split_managed(text or '')
    lines = outside.splitlines(keepends=True)
    remove_lines = set()
    for record in eligible:
        start = record['line'] - 1
        # The inventory's source line must still match the expected header.
        if start >= len(lines) or lines[start].split(';', 1)[0].strip() != record['steps'][0]:
            raise ValueError('Dialplan hat sich während der Migration verändert')
        for offset, step in enumerate(record['steps']):
            idx = start + offset
            if idx >= len(lines) or lines[idx].split(';', 1)[0].strip() != step:
                raise ValueError('Nicht zusammenhängende Legacy-Route; manuelle Prüfung erforderlich')
            remove_lines.add(idx)
    new_outside = ''.join(line for i, line in enumerate(lines) if i not in remove_lines)
    from .generator import BEGIN, END
    new_text = new_outside
    if inside or BEGIN in (text or ''):
        new_text = new_outside.rstrip('\n') + '\n\n' + BEGIN + inside + END + '\n'
    return {
        'content': new_text,
        'removed': keys,
        'recreated': sorted(desired_routes),
        'backup_required': bool(eligible),
    }


def generate_migrated_dialplan(model, text, endpoints, other_text=''):
    """Pure end-to-end planning: reconcile known legacy routes then regenerate.

    No Asterisk file is written. Persist through the existing transactional
    manager workflow, with backup and validation before reload.
    """
    from .generator import gen_dialplan, eingaenge_effektiv
    participants = model.get('teilnehmer', [])
    contexts = {
        (endpoints.get(t['eingang']) or {}).get('context') or t['eingang']
        for t in participants if t.get('typ') == 'extern_ziel' and t.get('eingang')
    }
    contexts.update(
        (endpoints.get(e['name']) or {}).get('context') or e['name']
        for e in eingaenge_effektiv(model)
    )
    desired = {
        ((endpoints.get(t['eingang']) or {}).get('context') or t['eingang'], str(n))
        for t in participants if t.get('typ') == 'extern_ziel' and t.get('eingang')
        for n in t.get('darf_anrufen') or []
    }
    migration = reconcile_legacy_routes(text, contexts, desired)
    generated = gen_dialplan(model, migration['content'], endpoints, other_text)
    generated['migration'] = {
        'removed': migration['removed'],
        'recreated': migration['recreated'],
        'backup_required': migration['backup_required'],
    }
    return generated
