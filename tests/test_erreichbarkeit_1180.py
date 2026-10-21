"""Tests für die Erreichbarkeit interner Teilnehmer (v1.18): wer darf wen anrufen."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'smartify_sip_manager'
sys.path.insert(0, str(ROOT))
import anlage as A  # noqa: E402
import generator as G  # noqa: E402
import verbindungen as V  # noqa: E402

F = lambda **k: {'kamerabild': False, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False, **k}
EPS = {n: {'context': 'default'} for n in ('101', '102', '103', '200')}


def model(**per):
    m = A.leer()
    m['teilnehmer'] = [
        {'nummer': '101', 'typ': 'sip_telefon', 'name': 'Raphael', 'faehigkeiten': F(), **per.get('101', {})},
        {'nummer': '102', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': F(), **per.get('102', {})},
        {'nummer': '103', 'typ': 'sip_telefon', 'name': 'Beate', 'faehigkeiten': F(), **per.get('103', {})},
        {'nummer': '200', 'typ': 'tuerstation', 'name': 'Tür', 'faehigkeiten': F(), **per.get('200', {})},
    ]
    m['wege'] = [{'name': 'Smartify', 'nummer': '601', 'von': [], 'ziele': ['101', '102'], 'klingelzeit': 20}]
    return A.validate(m)


def exten(text, nr):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(f'exten => {nr},1,'))
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith(' same')), len(lines))
    return '\n'.join(lines[start:end])


class ModelTests(unittest.TestCase):
    def test_default_is_unrestricted(self):
        for t in model()['teilnehmer']:
            self.assertIsNone(t['anruf_ziele'])
            self.assertIsNone(t['angerufen_von'])

    def test_unknown_numbers_dropped_empty_list_kept(self):
        m = model(**{'103': {'anruf_ziele': ['101', '999', '601'], 'angerufen_von': []}})
        t = next(x for x in m['teilnehmer'] if x['nummer'] == '103')
        self.assertEqual(t['anruf_ziele'], ['101', '601'])
        self.assertEqual(t['angerufen_von'], [])


class DialplanTests(unittest.TestCase):
    def test_nothing_generated_without_restriction(self):
        text = G.gen_dialplan(model(), '', EPS)['content']
        self.assertNotIn('exten => 101,1,', text)
        self.assertNotIn('gesperrt', text)

    def test_outbound_limit_blocks_other_numbers(self):
        text = G.gen_dialplan(model(**{'103': {'anruf_ziele': ['101']}}), '', EPS)['content']
        for nr in ('102', '200', '601'):
            self.assertIn('GotoIf($["${SM_EP}" = "103"]?gesperrt)', exten(text, nr), nr)
        self.assertNotIn('exten => 101,1,', text)       # 101 bleibt erlaubt: kein eigener Eintrag nötig

    def test_inbound_limit_allows_only_listed(self):
        text = G.gen_dialplan(model(**{'200': {'angerufen_von': ['101']}}), '', EPS)['content']
        e = exten(text, '200')
        self.assertIn('GotoIf($["${SM_EP}" = "101"]?erlaubt)', e)
        self.assertNotIn('"102"', e)
        self.assertIn('Hangup(21)', e)

    def test_inbound_nobody(self):
        e = exten(G.gen_dialplan(model(**{'200': {'angerufen_von': []}}), '', EPS)['content'], '200')
        self.assertIn('$[1 = 0]', e)

    def test_both_directions_combine(self):
        m = model(**{'200': {'angerufen_von': ['101', '103']}, '103': {'anruf_ziele': ['101']}})
        e = exten(G.gen_dialplan(m, '', EPS)['content'], '200')
        self.assertIn('GotoIf($["${SM_EP}" = "103"]?gesperrt)', e)       # 103 darf 200 nicht wählen, auch wenn 200 sie zulässt
        self.assertNotIn('= "103"]?erlaubt', e)

    def test_existing_manual_entry_is_reported_not_overwritten(self):
        ext = '[default]\nexten => 200,1,Dial(PJSIP/200)\n'
        out = G.gen_dialplan(model(**{'200': {'angerufen_von': ['101']}}), ext, EPS)
        self.assertEqual(G.split_managed(out['content'])[1].count('exten => 200,1,'), 0)
        self.assertTrue(any(r['level'] == 'warn' and '200' in r['text'] for r in out['aktionen']))


class VerbindungenTests(unittest.TestCase):
    def test_blocked_pairs_have_no_direct_edge(self):
        m = model(**{'103': {'anruf_ziele': ['101']}, '200': {'angerufen_von': ['101']}})
        edges = {(e['von'], e['nach']) for e in V.graph(m, EPS, '[default]\nexten => _XXX,1,NoOp()\n')['kanten'] if e['art'] == 'direkt'}
        self.assertNotIn(('tn:103', 'tn:200'), edges)      # 103 darf nur 101
        self.assertNotIn(('tn:102', 'tn:200'), edges)      # 200 nimmt nur 101 an
        self.assertIn(('tn:101', 'tn:200'), edges)
        self.assertIn(('tn:103', 'tn:101'), edges)


if __name__ == '__main__':
    unittest.main()
