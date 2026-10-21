"""Manueller UI-Test 1.5: Manager mit simuliertem SIP Core, go2rtc und Kamera (Port 554, root nötig) auf Port 8099."""
import importlib.util, os, sys, tempfile, socket
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_generator_150 import FakeCamera
TMP = Path(tempfile.mkdtemp(prefix='ui15-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP/'data'); os.environ['ADDON_CONFIGS_ROOT'] = str(TMP/'configs')
AST = TMP/'configs'/'3e533915_asterisk'/'asterisk'; (AST/'custom').mkdir(parents=True); (AST/'default').mkdir(parents=True)
(AST/'default'/'pjsip_default.conf').write_text('[transport-udp]\ntype=transport\nprotocol=udp\n[sipjs-phone-endpoint](!)\ntype=endpoint\nwebrtc=yes\ndisallow=all\nallow=opus,ulaw,alaw\n[104](sipjs-phone-endpoint)\naors=104\ncallerid="iPad" <104>\n[105](sipjs-phone-endpoint)\naors=105\ncallerid="Browser" <105>\n')
(AST/'custom'/'pjsip_custom.conf').write_text('[110]\ntype=aor\nmax_contacts=1\n\n[110]\ntype=auth\nauth_type=userpass\nusername=110\npassword=tuer110geheim\n\n[110]\ntype=endpoint\naors=110\nauth=110\ndisallow=all\nallow=alaw\ncallerid="Haustür" <110>\n\n; Linphone Cloud\n[linphone-cloud]\ntype=endpoint\ndisallow=all\nallow=alaw,ulaw\n')
spec = importlib.util.spec_from_file_location('app', str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py'))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
import yaml
STATE = {'g2': "streams:\n  cam_pt2:\n    - rtsp://sonoff:test-sample-123@192.168.2.175:554/av_stream/ch0#video=h264&audio=pcma\n  ipad_gang:\nwebrtc:\n  listen: ':8555'\n", 'sip': {'users':[{'extension':'104','ha_username':'ipad','display_name':'iPad Gang','password':'x'},{'extension':'105','ha_username':'browser','display_name':'Browser','password':'y'}],
 'sip_video':False,'popup_override_component':'smartify-doorstation-popup','popup_config':{'auto_open':True,'extensions':{'104':{'name':'iPad','stream':'ipad_gang','stream_mode':'mse','camera_mode':'hidden'}}}}}
app.read_active_sip_core = lambda: STATE['sip']
def apply(content, h):
    STATE['sip'] = yaml.safe_load(content); return {'applied': True, 'note': 'Übernommen und geprüft (Test).'}
app.apply_sip_core = apply
app.go2rtc_config_read = lambda: (STATE['g2'], yaml.safe_load(STATE['g2']), 'http://go2rtc:1984')
def g2w(text, restart=True):
    STATE['g2'] = text; return {'backup': 'go2rtc_test.yaml', 'restarted': True}
app.go2rtc_config_write = g2w
app.go2rtc_streams_full = lambda: ({k: {'producers': ([{'bytes_recv': 5}] if k != 'ipad_gang' else []), 'consumers': []} for k in (yaml.safe_load(STATE['g2']).get('streams') or {})}, 'http://go2rtc:1984')
app.go2rtc_cors = lambda base: "origin" in STATE['g2']
app.Handler.allowed_client = lambda self: True
cam = FakeCamera.__new__(FakeCamera); import threading; threading.Thread.__init__(cam, daemon=True)
cam.sock = socket.socket(); cam.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); cam.sock.bind(('127.0.0.1', 554)); cam.sock.listen(8); cam.port = 554; cam.start()
ThreadingHTTPServer(('127.0.0.1', 8099), app.Handler).serve_forever()
