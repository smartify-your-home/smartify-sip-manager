"""Backend-Tests für Anlagen-Modell, Vorschlag, Prüfbericht und Export (v1.4)."""
import importlib.util, json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix='smartify-anlage-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP / 'data')
os.environ['ADDON_CONFIGS_ROOT'] = str(TMP / 'configs')
AST = TMP / 'configs' / '3e533915_asterisk' / 'asterisk'
(AST / 'custom').mkdir(parents=True)
(AST / 'default').mkdir(parents=True)
(AST / 'default' / 'pjsip_default.conf').write_text(
    '[sipjs-phone-endpoint](!)\ntype=endpoint\nwebrtc=yes\ndisallow=all\nallow=opus,ulaw\n'
    '[104](sipjs-phone-endpoint)\naors=104\ncallerid="iPad" <104>\n')
(AST / 'custom' / 'pjsip_custom.conf').write_text(
    '[linphone-cloud]\ntype=endpoint\ndisallow=all\nallow=alaw,ulaw,opus,vp8,h264\n')

spec = importlib.util.spec_from_file_location('app140', Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

SIP = {'users': [{'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad Gang'}], 'sip_video': False,
       'popup_override_component': 'smartify-doorstation-popup',
       'popup_config': {'extensions': {'104': {'stream': 'ipad_gang', 'stream_mode': 'webrtc'}}}}
STREAMS = {'ipad_gang': {'producers': [], 'consumers': []}}


def patched():
    return [mock.patch.object(app, 'read_active_sip_core', return_value=SIP),
            mock.patch.object(app, 'go2rtc_streams_full', return_value=(STREAMS, 'http://go2rtc:1984')),
            mock.patch.object(app, 'go2rtc_cors', return_value=True)]


class AnlageAppTests(unittest.TestCase):
    def setUp(self):
        self.patches = patched()
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        if app.ANLAGE_FILE.exists():
            app.ANLAGE_FILE.unlink()

    def test_empty_model(self):
        data = app.read_anlage()
        self.assertFalse(data['saved'])
        self.assertEqual(data['model']['teilnehmer'], [])

    def test_vorschlag_save_report(self):
        proposal = app.anlage_vorschlag()['model']
        names = {t['nummer'] or t['endpoint']: t for t in proposal['teilnehmer']}
        self.assertEqual(names['104']['typ'], 'ha_geraet')
        self.assertTrue(names['104']['faehigkeiten']['ios'])
        self.assertNotIn('linphone-cloud', names)
        self.assertFalse(app.read_anlage()['saved'], 'Vorschlag darf nichts speichern')
        names['104']['faehigkeiten']['video_im_anruf'] = True
        saved = app.write_anlage(proposal, app.read_anlage()['hash'])
        self.assertTrue(saved['saved'])
        with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
            app.write_anlage(proposal, 'falsch')
        report = app.pruefbericht()
        errors = [r['titel'] for r in report['zeilen'] if r['level'] == 'error']
        self.assertTrue(any('nur Audio' in e for e in errors), errors)
        self.assertTrue(any('sip_video' in e for e in errors), errors)

    def test_export_import_roundtrip(self):
        proposal = app.anlage_vorschlag()['model']
        proposal['anlage']['kunde'] = 'Muster'
        app.write_anlage(proposal, app.read_anlage()['hash'])
        exported = json.loads(json.dumps(app.anlage_export()))
        self.assertEqual(exported['anlage']['kunde'], 'Muster')
        app.ANLAGE_FILE.unlink()
        result = app.anlage_import_datei(exported)
        self.assertTrue(result['saved'])
        self.assertEqual(app.read_anlage()['model']['anlage']['kunde'], 'Muster')

    def test_full_export_contains_model(self):
        self.assertIn('anlage', app.export_data())


if __name__ == '__main__':
    unittest.main()


class LadenTests(unittest.TestCase):
    def test_broken_saved_model_still_loads(self):
        bad = {'format': 'smartify-anlage', 'format_version': 1, 'anlage': {},
               'teilnehmer': [{'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'ha_benutzer': 'ipadvisu'},
                              {'nummer': '105', 'typ': 'ha_geraet', 'name': 'Raph PC', 'ha_benutzer': 'ipadvisu'},
                              {'nummer': 'x1', 'typ': 'sip_telefon', 'name': 'kaputt'}],
               'wege': [{'name': 'W', 'nummer': '600', 'von': ['104'], 'ziele': ['999'], 'klingelzeit': 20}]}
        app.ANLAGE_FILE.write_text(json.dumps(bad))
        try:
            data = app.read_anlage()
            names = [(t['nummer'], t['ha_benutzer']) for t in data['model']['teilnehmer']]
            self.assertEqual(names, [('104', 'ipadvisu'), ('105', '')])
            self.assertEqual(data['model']['wege'], [])
            self.assertEqual(len(data['hinweise']), 3)
        finally:
            app.ANLAGE_FILE.unlink()
