"""Tests für Generator (Asterisk, SIP Core, go2rtc) und RTSP-Erkennung (v1.5)."""
import hashlib, importlib.util, re, socket, sys, threading, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'smartify_sip_manager'
sys.path.insert(0, str(ROOT))
import anlage as A  # noqa: E402
import generator as G  # noqa: E402
import rtsp as R  # noqa: E402

DEFAULT = ('default/pjsip_default.conf', """
[transport-udp]
type=transport
protocol=udp
[sipjs-phone-endpoint](!)
type=endpoint
webrtc=yes
disallow=all
allow=opus,ulaw
[104](sipjs-phone-endpoint)
aors=104
callerid="iPad" <104>
""")
CUSTOM = """; Meine Datei
[110]
type=aor
max_contacts=1

[110]
type=auth
auth_type=userpass
username=110
password=geheim110

[110]
type=endpoint
context=tuer
aors=110
auth=110
disallow=all
allow=alaw,ulaw
callerid="Alt" <110>

; ==== Linphone Cloud ====
[linphone-cloud]
type=endpoint
transport=transport-udp
disallow=all
allow=alaw,ulaw
"""


def model():
    m = A.leer()
    m['anlage']['lan_ip'] = '192.168.2.65'
    f = lambda **k: {'kamerabild': False, 'video_im_anruf': False, 'ios': False, 'tuer_oeffnen': False, **k}
    m['teilnehmer'] = [
        {'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad Gang', 'stream': 'ipad_gang', 'faehigkeiten': f(kamerabild=True, video_im_anruf=True, ios=True)},
        {'nummer': '110', 'typ': 'tuerstation', 'name': 'Haustür', 'stream': 'akuvox', 'faehigkeiten': f(kamerabild=True, video_im_anruf=True),
         'rtsp': {'host': '192.168.2.50', 'port': 554, 'pfad': '/live/ch00_0', 'benutzer': 'admin'}},
        {'nummer': '120', 'typ': 'sip_telefon', 'name': 'Linphone Büro', 'faehigkeiten': f()},
        {'nummer': '', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-cloud', 'sip_adresse': 'test-benutzer-r@sip.linphone.org',
         'faehigkeiten': f(video_im_anruf=True)},
        {'nummer': '', 'typ': 'kamera', 'name': 'Garten', 'stream': 'cam_pt2', 'faehigkeiten': f(kamerabild=True),
         'rtsp': {'host': '192.168.2.175', 'port': 554, 'pfad': '/av_stream/ch0', 'benutzer': 'sonoff', 'zusatz': 'video=h264&audio=pcma'}},
    ]
    return A.validate(m)


class PjsipTests(unittest.TestCase):
    def setUp(self):
        self.secrets = {}
        self.files = [DEFAULT, ('custom/pjsip_custom.conf', CUSTOM)]
        self.out = G.gen_pjsip(model(), CUSTOM, self.files, self.secrets)
        self.text = self.out['content']

    def test_takeover_keeps_password_and_settings(self):
        outside, inside = G.split_managed(self.text)
        self.assertNotIn('[110]', outside)
        self.assertIn('password=geheim110', inside)
        self.assertIn('context=tuer', inside)
        self.assertRegex(inside, r'allow=alaw,ulaw,h264,vp8')
        self.assertIn('callerid="Haustür" <110>', inside)

    def test_new_phone_gets_password(self):
        self.assertIn('120', self.out['neu'])
        self.assertIn('password=' + self.secrets['sip']['120'], self.text)
        self.assertIn('transport=transport-udp', G.split_managed(self.text)[1])

    def test_addon_endpoint_not_duplicated(self):
        self.assertNotIn('[104]', self.text)

    def test_extern_patched_in_place(self):
        outside, _ = G.split_managed(self.text)
        self.assertIn('; ==== Linphone Cloud ====', outside)
        self.assertRegex(outside, r'\[linphone-cloud\][^\[]*allow=alaw,ulaw,opus,vp8,h264')

    def test_idempotent(self):
        again = G.gen_pjsip(model(), self.text, [DEFAULT, ('custom/pjsip_custom.conf', self.text)], self.secrets)
        self.assertEqual(again['content'], self.text)
        self.assertEqual(again['neu'], [])

    def test_removed_participant_is_reported(self):
        m = model()
        m['teilnehmer'] = [t for t in m['teilnehmer'] if t['nummer'] != '120']
        out = G.gen_pjsip(m, self.text, [DEFAULT, ('custom/pjsip_custom.conf', self.text)], self.secrets)
        self.assertNotIn('[120]', out['content'])
        self.assertTrue(any(r['level'] == 'warn' and r['text'].startswith('120:') and 'ENTFERNT' in r['text'] for r in out['aktionen']))
        self.assertNotIn('120', self.secrets['sip'])

    def test_result_parses_with_codecs(self):
        eps = A.endpoints_from_conf([DEFAULT, ('custom/pjsip_custom.conf', self.text)])
        self.assertIn('h264', eps['110']['codecs'])
        self.assertIn('vp8', eps['linphone-cloud']['codecs'])


class SipCoreTests(unittest.TestCase):
    def test_patch(self):
        cfg = {'users': [{'extension': '104', 'ha_username': 'ipad', 'password': 'x'}], 'sip_video': False,
               'popup_config': {'extensions': {'104': {'name': 'iPad', 'override_icon': 'mdi:tablet', 'stream': 'ipad_gang', 'stream_mode': 'mse'}}}}
        out = G.gen_sip_core(model(), cfg)
        new = out['config']
        self.assertTrue(new['sip_video'])
        self.assertEqual(new['popup_override_component'], 'smartify-doorstation-popup')
        cams = new['popup_config']['smartify']['camera_by_caller']
        self.assertEqual(cams['104'], {'label': 'iPad Gang', 'stream': 'ipad_gang', 'mode': 'webrtc', 'camera_mode': 'always'})
        self.assertEqual(cams['110']['stream'], 'akuvox')
        self.assertEqual(new['popup_config']['extensions']['104'], {'name': 'iPad', 'override_icon': 'mdi:tablet'})
        self.assertFalse(cfg['sip_video'], 'Eingabe darf nicht verändert werden')
        self.assertEqual([r for r in out['aktionen'] if r['level'] == 'warn'], [])
        cfg2 = dict(cfg, users=[])
        self.assertTrue(any('104' in r['text'] for r in G.gen_sip_core(model(), cfg2)['aktionen'] if r['level'] == 'warn'))


class Go2rtcTests(unittest.TestCase):
    def test_streams(self):
        cfg = {'streams': {'cam_pt2': ['rtsp://sonoff:alt@192.168.2.175:554/av_stream/ch0#video=h264&audio=pcma'], 'fremd': ['rtsp://x/y']}}
        sources, pws = G.rtsp_from_go2rtc(cfg)
        self.assertEqual(sources['cam_pt2']['pfad'], '/av_stream/ch0')
        self.assertEqual(pws['cam_pt2'], 'alt')
        secrets = {'rtsp': {'cam_pt2': 'neu', 'akuvox': 'tür'}}
        out = G.gen_go2rtc(model(), cfg, secrets)['config']
        self.assertEqual(out['streams']['cam_pt2'], ['rtsp://sonoff:neu@192.168.2.175/av_stream/ch0#video=h264&audio=pcma'])
        self.assertEqual(out['streams']['akuvox'], ['rtsp://admin:t%C3%BCr@192.168.2.50/live/ch00_0'])
        self.assertEqual(out['streams']['ipad_gang'], [])
        self.assertEqual(out['streams']['fremd'], ['rtsp://x/y'])
        self.assertEqual(out['api']['origin'], '*')
        self.assertIn('192.168.2.65:8555', out['webrtc']['candidates'])

    def test_equivalent_sources_unchanged(self):
        cfg = {'streams': {'cam_pt2': ['rtsp://sonoff:neu@192.168.2.175:554/av_stream/ch0#video=h264&audio=pcma'], 'ipad_gang': None,
                           'akuvox': ['rtsp://admin:t%C3%BCr@192.168.2.50/live/ch00_0']},
               'api': {'origin': '*'}, 'webrtc': {'listen': ':8555', 'candidates': ['192.168.2.65:8555']}}
        out = G.gen_go2rtc(model(), cfg, {'rtsp': {'cam_pt2': 'neu', 'akuvox': 'tür'}})
        self.assertEqual(out['config'], cfg)
        self.assertEqual(out['aktionen'], [])

    def test_missing_password_keeps_stream(self):
        cfg = {'streams': {'akuvox': ['rtsp://admin:a@192.168.2.50/x']}}
        out = G.gen_go2rtc(model(), cfg, {})
        self.assertEqual(out['config']['streams']['akuvox'], ['rtsp://admin:a@192.168.2.50/x'])
        self.assertTrue(any('Passwort' in r['text'] for r in out['aktionen']))

    def test_mask(self):
        self.assertEqual(G.mask_go2rtc_text('- rtsp://sonoff:n1lu9@1.2.3.4/x'), '- rtsp://sonoff:•••@1.2.3.4/x')


class RtspUrlTests(unittest.TestCase):
    def test_roundtrip(self):
        url = 'rtsp://us%40er:p%3Aw@192.168.2.175:8554/cam/realmonitor?channel=1&subtype=0#video=h264'
        cam = R.parse_url(url)
        self.assertEqual((cam['benutzer'], cam['passwort'], cam['port']), ('us@er', 'p:w', 8554))
        self.assertEqual(R.build_url(cam), url)
        self.assertNotIn('p%3Aw', R.mask_url(url))

    def test_sdp(self):
        sdp = 'v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\nm=audio 0 RTP/AVP 8\r\n'
        self.assertEqual(R.parse_sdp(sdp), {'video': ['H264'], 'audio': ['PCMA']})

    def test_vendor(self):
        self.assertEqual(R.guess_vendor('Hikvision-Webs'), 'hikvision')
        self.assertEqual(R.vendor_info('sonoff')['pfad'], '/av_stream/ch0')


class FakeCamera(threading.Thread):
    """Minimal RTSP server with Digest auth, like many IP cameras."""
    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]

    def run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                data = b''
                while b'\r\n\r\n' not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                text = data.decode()
                if not text.strip():
                    continue
                method, uri = text.split(' ')[:2]
                cseq = re.search(r'CSeq: (\d+)', text).group(1)
                if method == 'OPTIONS':
                    conn.sendall(f'RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nServer: Hikvision-Webs\r\nPublic: DESCRIBE\r\n\r\n'.encode())
                    continue
                auth = re.search(r'Authorization: Digest (.*)\r\n', text)
                if not auth:
                    conn.sendall(f'RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\nWWW-Authenticate: Digest realm="cam", nonce="abc123"\r\n\r\n'.encode())
                    continue
                f = dict(re.findall(r'(\w+)="?([^",]*)"?', auth.group(1)))
                ha1 = hashlib.md5(b'admin:cam:richtig').hexdigest()
                ha2 = hashlib.md5(f'DESCRIBE:{f["uri"]}'.encode()).hexdigest()
                if f['response'] != hashlib.md5(f'{ha1}:abc123:{ha2}'.encode()).hexdigest():
                    conn.sendall(f'RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\nWWW-Authenticate: Digest realm="cam", nonce="abc123"\r\n\r\n'.encode())
                    continue
                if not uri.endswith('/Streaming/Channels/101'):
                    conn.sendall(f'RTSP/1.0 404 Not Found\r\nCSeq: {cseq}\r\n\r\n'.encode())
                    continue
                sdp = 'v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H265/90000\r\nm=audio 0 RTP/AVP 8\r\na=rtpmap:8 PCMA/8000\r\n'
                conn.sendall(f'RTSP/1.0 200 OK\r\nCSeq: {cseq}\r\nContent-Type: application/sdp\r\nContent-Length: {len(sdp)}\r\n\r\n{sdp}'.encode())


class RtspNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cam = FakeCamera()
        cls.cam.start()

    def base(self, **k):
        return {'host': '127.0.0.1', 'port': self.cam.port, 'pfad': '/Streaming/Channels/101', 'benutzer': 'admin', 'passwort': 'richtig', **k}

    def test_describe_digest(self):
        r = R.describe(self.base())
        self.assertTrue(r['ok'], r)
        self.assertEqual(r['video'], ['H265'])
        self.assertIn('H.265', r['meldung'])

    def test_wrong_password_and_path(self):
        self.assertEqual(R.describe(self.base(passwort='falsch'))['status'], 401)
        self.assertEqual(R.describe(self.base(pfad='/x'))['status'], 404)

    def test_discover(self):
        found = R.discover('127.0.0.1', ports=(self.cam.port,), timeout=0.2)
        self.assertEqual([(f['host'], f['hersteller']) for f in found], [('127.0.0.1', 'hikvision')])
        self.assertEqual(found[0]['pfad'], '/Streaming/Channels/101')

    def test_public_network_refused(self):
        with self.assertRaises(ValueError):
            R.discover('8.8.8.8')


if __name__ == '__main__':
    unittest.main()
