"""Manueller UI-Test: Manager mit simuliertem SIP Core und go2rtc auf Port 8099."""
import importlib.util, os, tempfile, sys
from pathlib import Path
from http.server import ThreadingHTTPServer
TMP = Path(tempfile.mkdtemp(prefix='ui-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP/'data'); os.environ['ADDON_CONFIGS_ROOT'] = str(TMP/'configs')
AST = TMP/'configs'/'3e533915_asterisk'/'asterisk'; (AST/'custom').mkdir(parents=True); (AST/'default').mkdir(parents=True)
(AST/'default'/'pjsip_default.conf').write_text('[sipjs-phone-endpoint](!)\ntype=endpoint\nwebrtc=yes\ndisallow=all\nallow=opus,ulaw,alaw\n[104](sipjs-phone-endpoint)\naors=104\ncallerid="iPad" <104>\n[105](sipjs-phone-endpoint)\naors=105\ncallerid="Browser" <105>\n')
(AST/'custom'/'pjsip_custom.conf').write_text('[linphone-cloud]\ntype=endpoint\ndisallow=all\nallow=alaw,ulaw,opus,vp8,h264\n[110]\ntype=endpoint\naors=110\nallow=alaw\ncallerid="Haustür" <110>\n')
spec = importlib.util.spec_from_file_location('app', str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py'))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
SIP = {'users':[{'extension':'104','ha_username':'ipad','display_name':'iPad Gang'},{'extension':'105','ha_username':'browser','display_name':'Browser'}],
 'sip_video':False,'popup_override_component':'smartify-doorstation-popup',
 'popup_config':{'auto_open':True,'extensions':{'104':{'stream':'ipad_gang','stream_mode':'mse','camera_mode':'auto'}}}}
app.read_active_sip_core = lambda: SIP
app.go2rtc_streams_full = lambda: ({'ipad_gang':{'producers':[{'bytes_recv':21000000,'receivers':1,'medias':2}],'consumers':[]},'cam_pt2':{'producers':[{'bytes_recv':0,'receivers':0,'medias':0}],'consumers':[]}}, 'http://x:1984')
app.go2rtc_cors = lambda base: True
app.Handler.allowed_client = lambda self: True
ThreadingHTTPServer(('127.0.0.1', 8099), app.Handler).serve_forever()
