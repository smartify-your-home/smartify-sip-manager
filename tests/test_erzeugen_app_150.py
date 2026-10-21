"""Backend-Test: Vorschau und Übernehmen (v1.5) mit simuliertem SIP Core und go2rtc."""
import importlib.util, json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix='smartify-erz-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP / 'data')
os.environ['ADDON_CONFIGS_ROOT'] = str(TMP / 'configs')
AST = TMP / 'configs' / '3e533915_asterisk' / 'asterisk'
(AST / 'custom').mkdir(parents=True)
(AST / 'default').mkdir(parents=True)
(AST / 'default' / 'pjsip_default.conf').write_text(
    '[transport-udp]\ntype=transport\nprotocol=udp\n[sipjs-phone-endpoint](!)\ntype=endpoint\nwebrtc=yes\ndisallow=all\nallow=opus,ulaw\n'
    '[104](sipjs-phone-endpoint)\naors=104\ncallerid="iPad" <104>\n')
(AST / 'custom' / 'pjsip_custom.conf').write_text('[linphone-cloud]\ntype=endpoint\ndisallow=all\nallow=alaw,ulaw\n')

spec = importlib.util.spec_from_file_location('app150', Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

SIP = {'users': [{'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad Gang', 'password': 'pw104'}], 'sip_video': False,
       'popup_config': {'extensions': {'104': {'stream': 'ipad_gang', 'stream_mode': 'mse'}}}}
G2 = "streams:\n  cam_pt2:\n    - rtsp://sonoff:geheim@192.168.2.175:554/av_stream/ch0#video=h264&audio=pcma\n  ipad_gang:\n"


class ErzeugenTests(unittest.TestCase):
    def setUp(self):
        self.g2 = {'text': G2}
        self.applied = []

        def g2_read():
            import yaml
            return self.g2['text'], yaml.safe_load(self.g2['text']), 'http://go2rtc:1984'

        def g2_write(text, restart=True):
            self.g2['text'] = text
            return {'backup': 'x', 'restarted': restart}

        self.patches = [mock.patch.object(app, 'read_active_sip_core', return_value=SIP),
                        mock.patch.object(app, 'go2rtc_streams_full', return_value=({'ipad_gang': {'producers': [], 'consumers': []},
                                                                                      'cam_pt2': {'producers': [{'bytes_recv': 1}], 'consumers': []}}, 'http://go2rtc:1984')),
                        mock.patch.object(app, 'go2rtc_cors', return_value=False),
                        mock.patch.object(app, 'go2rtc_config_read', side_effect=g2_read),
                        mock.patch.object(app, 'go2rtc_config_write', side_effect=g2_write),
                        mock.patch.object(app, 'apply_sip_core', side_effect=lambda c, h: self.applied.append(c) or {'applied': True})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_full_flow(self):
        vorschlag = app.anlage_vorschlag()
        model = vorschlag['model']
        self.assertTrue(any('RTSP' in h for h in vorschlag['hinweise']))
        cam = next(t for t in model['teilnehmer'] if t['stream'] == 'cam_pt2')
        self.assertEqual(cam['typ'], 'kamera')
        self.assertEqual(cam['rtsp']['pfad'], '/av_stream/ch0')
        self.assertNotIn('geheim', json.dumps(model))
        self.assertEqual(app.read_secrets()['rtsp']['cam_pt2'], 'geheim')
        ipad = next(t for t in model['teilnehmer'] if t['nummer'] == '104')
        ipad['faehigkeiten'].update(ios=True, video_im_anruf=True)
        model['anlage']['lan_ip'] = '192.168.2.65'
        model['teilnehmer'].append({'nummer': '120', 'typ': 'sip_telefon', 'name': 'Büro', 'faehigkeiten': {}})
        model['teilnehmer'].append({'nummer': '', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-cloud',
                                    'sip_adresse': 'test-benutzer-r@sip.linphone.org', 'faehigkeiten': {'video_im_anruf': True}})
        app.write_anlage(model, app.read_anlage()['hash'])

        preview = app.erzeugen_vorschau()['ziele']
        self.assertTrue(preview['asterisk']['changed'])
        self.assertEqual(preview['asterisk']['lint_fehler'], 0, preview['asterisk'].get('lint'))
        self.assertNotIn('geheim', preview['go2rtc']['diff'])
        self.assertIn('origin', preview['go2rtc']['diff'])
        self.assertIn('webrtc', preview['sip_core']['diff'])
        tokens = {k: v['token'] for k, v in preview.items()}

        with self.assertRaisesRegex(ValueError, 'Bestätigung'):
            app.erzeugen_uebernehmen({'ziele': ['asterisk'], 'tokens': tokens})
        bad = dict(tokens, asterisk='alt')
        with self.assertRaisesRegex(ValueError, 'seit der Vorschau'):
            app.erzeugen_uebernehmen({'ziele': ['asterisk'], 'tokens': bad, 'confirm': True})

        result = app.erzeugen_uebernehmen({'ziele': ['asterisk', 'go2rtc', 'sip_core'], 'tokens': tokens, 'confirm': True})
        self.assertEqual(set(result['ergebnisse']), {'asterisk', 'go2rtc', 'sip_core'})
        conf = (AST / 'custom' / 'pjsip_custom.conf').read_text()
        self.assertIn('[120]', conf)
        self.assertIn('allow=alaw,ulaw,opus,vp8,h264', conf)
        self.assertIn('geheim@192.168.2.175', self.g2['text'])
        self.assertIn("origin: '*'", self.g2['text'])
        self.assertIn('sip_video: true', self.applied[0])
        self.assertEqual(app.read_camera_map()['mapping']['104']['mode'], 'webrtc')
        z = app.zugangsdaten('120')
        self.assertEqual(len(z['passwort']), 20)

        second = app.erzeugen_vorschau()['ziele']
        self.assertFalse(second['asterisk']['changed'], 'zweiter Lauf muss stabil sein')
        self.assertFalse(second['go2rtc']['changed'])


if __name__ == '__main__':
    unittest.main()
