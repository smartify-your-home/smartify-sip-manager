"""Tests für die Verbindungsgrafik (v1.12)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager'))
import anlage as A  # noqa: E402
import verbindungen as V  # noqa: E402

F = lambda **k: {'kamerabild': False, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False, **k}
DP = """
[default]
exten => _1XX,1,Dial(PJSIP/${EXTEN},30)
exten => 906,1,Dial(PJSIP/linphone-cloud/sip:test-benutzer-r@sip.linphone.org,30)
[tuer]
include => wege
[wege]
exten => 600,1,NoOp()
[linphone-in]
exten => 104,1,Dial(PJSIP/104,30)
[vorlage](!)
exten => 999,1,NoOp()
"""
EPS = {'100': {'context': 'default'}, '104': {'context': 'default'}, '110': {'context': 'tuer'}, 'linphone-in': {'context': 'linphone-in'}}


def model():
    m = A.leer()
    m['teilnehmer'] = [
        {'nummer': '100', 'typ': 'ha_geraet', 'name': 'iPhone', 'faehigkeiten': F()},
        {'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'stream': 'ipad_gang', 'faehigkeiten': F(kamerabild=True)},
        {'nummer': '110', 'typ': 'tuerstation', 'name': 'Haustür', 'stream': 'cam_pt2', 'faehigkeiten': F(kamerabild=True)},
        {'nummer': '906', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
         'sip_adresse': 'test-benutzer-r@sip.linphone.org', 'darf_anrufen': ['104', '100'], 'faehigkeiten': F()},
        {'nummer': '', 'typ': 'extern_ziel', 'name': 'Amelie', 'endpoint': 'linphone-cloud', 'sip_adresse': 'test-benutzer-a@sip.linphone.org', 'faehigkeiten': F()},
        {'nummer': '', 'typ': 'kamera', 'name': 'Sonoff', 'stream': 'cam_pt2', 'faehigkeiten': F(kamerabild=True)},
    ]
    m['wege'] = [{'name': 'Klingel', 'nummer': '600', 'von': ['110'], 'ziele': ['104', '906'], 'klingelzeit': 20}]
    return A.validate(m)


class PatternTests(unittest.TestCase):
    def test_patterns(self):
        self.assertTrue(V.pattern_matches('_1XX', '104'))
        self.assertFalse(V.pattern_matches('_1XX', '1040'))
        self.assertTrue(V.pattern_matches('_X.', '600'))
        self.assertTrue(V.pattern_matches('_[1-3]0Z', '205'))
        self.assertFalse(V.pattern_matches('_N0X', '104'))
        self.assertTrue(V.pattern_matches('104', '104'))

    def test_include_and_template(self):
        dp = V.parse_dialplan(DP)
        self.assertNotIn('vorlage', dp)
        ok, why = V.reachable(dp, 'tuer', '600')
        self.assertTrue(ok)
        self.assertIn('include', why)


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.g = V.graph(model(), EPS, DP)
        self.e = {(e['von'], e['nach'], e['art']): e for e in self.g['kanten']}

    def test_direct(self):
        self.assertEqual(self.e[('tn:100', 'tn:104', 'direkt')]['grund'], 'Muster _1XX@default')
        self.assertNotIn(('tn:110', 'tn:104', 'direkt'), self.e, 'Türstation-Kontext „tuer“ kennt 104 nicht')

    def test_weg(self):
        self.assertEqual(self.e[('tn:110', 'weg:600', 'weg')]['status'], 'aktiv')
        self.assertIn(('weg:600', 'tn:906', 'weg'), self.e)

    def test_cloud(self):
        self.assertEqual(self.e[('tn:100', 'tn:906', 'cloud_aus')]['status'], 'aktiv')
        self.assertEqual(self.e[('tn:906', 'tn:104', 'cloud_ein')]['status'], 'aktiv')
        self.assertEqual(self.e[('tn:906', 'tn:100', 'cloud_ein')]['status'], 'geplant')
        self.assertIn(('tn:906', 'tn:sip:test-benutzer-a@sip.linphone.org', 'cloud_direkt'), self.e)

    def test_camera(self):
        self.assertIn(('cam:cam_pt2', 'tn:110', 'kamera'), self.e)
        self.assertEqual({n['id'] for n in self.g['knoten'] if n['gruppe'] == 'anschluss'}, {'an:linphone-cloud', 'an:linphone-in'})


if __name__ == '__main__':
    unittest.main()


class RufgruppenSperreTests(unittest.TestCase):
    def test_cloud_not_member_not_shown(self):
        import anlage, verbindungen
        m = anlage.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
            'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {}},
                           {'nummer': '908', 'typ': 'extern_ziel', 'name': 'Lisi', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'l@sip.linphone.org', 'faehigkeiten': {}, 'darf_anrufen': ['104']}],
            'wege': [{'name': 'MaPa', 'nummer': '600', 'von': ['104'], 'ziele': ['906'], 'klingelzeit': 20, 'mitglieder_rufen': True}]})
        dp = '[default]\nexten => 600,1,NoOp()\n[linphone-in]\nexten => 600,1,NoOp()\nexten => 104,1,NoOp()\n'
        g = verbindungen.graph(m, {'linphone-in': {'context': 'linphone-in'}}, dp)
        ein = {(e['von'], e['nach']) for e in g['kanten'] if e['art'] == 'cloud_ein'}
        self.assertIn(('tn:906', 'weg:600'), ein)
        self.assertNotIn(('tn:908', 'weg:600'), ein)
        self.assertIn(('tn:908', 'tn:104'), ein)
