"""Tests für das Anlagen-Modell und den Prüfbericht (v1.4). Fälle aus dem Praxistest vom 16.10.2026."""
import importlib.util, unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('anlage', Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'anlage.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

DEFAULT = """
[sipjs-phone-endpoint](!)
type=endpoint
webrtc=yes
disallow=all
allow=opus,ulaw,alaw,speex,gsm,g726,g723,g722
[104](sipjs-phone-endpoint)
aors=104
auth=104
callerid="iPad" <104>
"""
CUSTOM = """
[linphone-cloud]
type=endpoint
disallow=all
allow=alaw,ulaw,vp8,h264 ; video
transport=transport-udp
[110]
type=aor
max_contacts=1
[110]
type=endpoint
aors=110
auth=110
disallow=all
allow=alaw,ulaw
callerid="Haustür Akuvox" <110>
"""

SIP_CORE = {
    'users': [{'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad Gang'},
              {'extension': '105', 'ha_username': 'browser', 'display_name': 'Browser'}],
    'sip_video': False,
    'popup_override_component': 'smartify-doorstation-popup',
    'popup_config': {'auto_open': True, 'extensions': {'104': {'stream': 'ipad_gang', 'stream_mode': 'mse',
                                                              'camera_mode': 'hidden'}}},
}
STREAMS = {'ipad_gang': {'producers': [], 'consumers': []},
           'cam_pt2': {'producers': [{'format': 'rtsp', 'bytes_recv': 0, 'receivers': 0, 'medias': 0}], 'consumers': []}}


def endpoints():
    return A.endpoints_from_conf([('default/pjsip_default.conf', DEFAULT), ('custom/pjsip_custom.conf', CUSTOM)])


class CodecTests(unittest.TestCase):
    def test_template_codecs_resolved(self):
        eps = endpoints()
        self.assertEqual(eps['104']['codecs'][:3], ['opus', 'ulaw', 'alaw'])
        self.assertFalse(A.has_video(eps['104']['codecs']))
        self.assertTrue(eps['104']['webrtc'])

    def test_comment_and_video(self):
        eps = endpoints()
        self.assertEqual(eps['linphone-cloud']['codecs'], ['alaw', 'ulaw', 'vp8', 'h264'])
        self.assertNotIn('110', [k for k, v in eps.items() if v.get('type') == 'aor'])

    def test_ami_allow(self):
        text = ' allow                              : (opus|ulaw|alaw|speex)\n allow_overlap : true'
        self.assertEqual(A.parse_ami_allow(text), ['opus', 'ulaw', 'alaw', 'speex'])
        self.assertIsNone(A.parse_ami_allow('nothing'))


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.model = A.import_from(SIP_CORE, endpoints(), STREAMS)
        self.by = {t['nummer'] or t['name']: t for t in self.model['teilnehmer']}

    def test_types(self):
        self.assertEqual(self.by['104']['typ'], 'ha_geraet')
        self.assertEqual(self.by['104']['stream'], 'ipad_gang')
        self.assertTrue(self.by['104']['faehigkeiten']['kamerabild'])
        self.assertEqual(self.by['110']['typ'], 'tuerstation')
        self.assertNotIn('linphone-cloud', self.by, 'Anschlüsse sind keine Teilnehmer')
        self.assertEqual(self.by['cam_pt2']['typ'], 'kamera')

    def test_validate_roundtrip(self):
        self.assertEqual(A.validate(self.model), self.model)

    def test_duplicate_number(self):
        bad = dict(self.model, teilnehmer=self.model['teilnehmer'] + [dict(self.by['104'])])
        with self.assertRaisesRegex(ValueError, 'doppelt'):
            A.validate(bad)

    def test_stream_required_for_camera(self):
        t = dict(self.by['105'], faehigkeiten={'kamerabild': True})
        with self.assertRaisesRegex(ValueError, 'Streamnamen'):
            A.validate(dict(self.model, teilnehmer=[t]))

    def test_weg_must_reference_participant(self):
        with self.assertRaisesRegex(ValueError, 'kein Teilnehmer'):
            A.validate(dict(self.model, wege=[{'name': 'Klingel', 'von': ['110'], 'ziele': ['999']}]))


class PruefberichtTests(unittest.TestCase):
    def report(self, **changes):
        model = A.import_from(SIP_CORE, endpoints(), STREAMS)
        for t in model['teilnehmer']:
            if t['nummer'] == '104':
                t['faehigkeiten'].update(video_im_anruf=True, ios=True)
        model.update(changes)
        ctx = {'asterisk_dir': True, 'endpoints': endpoints(), 'sip_core': SIP_CORE, 'streams': STREAMS,
               'cors': False, 'ami_error': 'AMI-Passwort nicht gesetzt.'}
        return A.pruefbericht(A.validate(model), ctx)

    def titles(self, report, level):
        return [r['titel'] for r in report['zeilen'] if r['level'] == level]

    def test_finds_all_issues_from_field_test(self):
        report = self.report()
        errors = ' | '.join(self.titles(report, 'error'))
        warns = ' | '.join(self.titles(report, 'warn'))
        self.assertIn('104 iPad Gang: Video SIP gewünscht, Endpoint erlaubt nur Audio', errors)
        self.assertIn('sip_video: false', errors)
        self.assertIn('CORS', errors)
        self.assertIn('Keine HTTPS-Adresse', errors)
        self.assertIn('keinen Sender', warns)
        self.assertIn('hidden', warns)
        self.assertIn('Wiedergabe „mse“', warns)

    def test_fixed_setup_is_clean(self):
        sip = dict(SIP_CORE, sip_video=True, popup_config={'auto_open': True, 'smartify': {'camera_by_caller': {
            '104': {'stream': 'ipad_gang', 'mode': 'webrtc', 'camera_mode': 'always'}}}})
        streams = dict(STREAMS, ipad_gang={'producers': [{'bytes_recv': 2000, 'receivers': 1, 'medias': 2}], 'consumers': []})
        model = A.import_from(sip, endpoints(), streams)
        for t in model['teilnehmer']:
            if t['nummer'] == '104':
                t['faehigkeiten'].update(video_im_anruf=True, ios=True)
        model['anlage']['go2rtc_https_url'] = 'https://homeassistant.example-tailnet.ts.net:8443'
        ctx = {'asterisk_dir': True, 'endpoints': endpoints(), 'sip_core': sip, 'streams': streams, 'cors': True,
               'ami_codecs': {'104': ['opus', 'ulaw', 'vp8', 'h264']}}
        report = A.pruefbericht(A.validate(model), ctx)
        self.assertEqual(self.titles(report, 'error'), [])
        self.assertIn('104 iPad Gang: Video-Codecs vorhanden (vp8, h264)', self.titles(report, 'ok'))

    def test_empty_model_hint(self):
        report = A.pruefbericht(A.leer(), {'asterisk_dir': True, 'sip_core': SIP_CORE, 'streams': STREAMS})
        self.assertIn('Noch keine Teilnehmer im Modell', self.titles(report, 'warn'))

    def test_no_secrets_in_report(self):
        report = self.report()
        self.assertNotIn('rtsp://', str(report))


if __name__ == '__main__':
    unittest.main()
