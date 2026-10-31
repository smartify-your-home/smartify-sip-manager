"""Unit tests for the Smartify SIP Manager backend. Run: python3 -m unittest discover -s tests"""
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix='smartify-test-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP / 'data')
os.environ['ADDON_CONFIGS_ROOT'] = str(TMP / 'configs')
AST = TMP / 'configs' / '3e533915_asterisk' / 'asterisk'
(AST / 'custom').mkdir(parents=True)
(AST / 'default').mkdir(parents=True)
(AST / 'default' / 'pjsip_default.conf').write_text(
    '[100](sipjs-phone-aor)\n[100](sipjs-phone-auth)\n[100](sipjs-phone-endpoint)\naors=100\nauth=100\ncallerid="Max" <100>\n'
    '[104](sipjs-phone-aor)\n[104](sipjs-phone-auth)\n[104](sipjs-phone-endpoint)\naors=104\nauth=104\ncallerid="ipadvisu" <104>\n')

spec = importlib.util.spec_from_file_location('app', Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

PERSONS = [{'person': 'person.max', 'name': 'Max', 'user_id': 'u1'}, {'person': 'person.ipad', 'name': 'ipadvisu', 'user_id': 'u2'},
           {'person': 'person.service', 'name': 'Fernwartung', 'user_id': 'u3'}]


class VersionTests(unittest.TestCase):
    def test_version_from_config(self):
        self.assertRegex(app.ADDON_VERSION, r'^\d+\.\d+\.\d+$')


class BackupTests(unittest.TestCase):
    def test_prune_keeps_newest(self):
        folder = TMP / 'prune'
        folder.mkdir()
        for i in range(40):
            (folder / f'x.2026{i:04d}.bak').write_text('a')
        app.prune_backups(folder, 'x.*.bak', keep=30)
        names = sorted(p.name for p in folder.iterdir())
        self.assertEqual(len(names), 30)
        self.assertEqual(names[0], 'x.20260010.bak')


class LintTests(unittest.TestCase):
    def test_hash_comment_is_error_but_include_ok(self):
        r = app.lint_conf('pjsip_custom.conf', '# Kommentar\n#include extra.conf\n[105]\ntype=aor\n')
        self.assertEqual([i['line'] for i in r['issues'] if i['level'] == 'error'], [1])

    def test_duplicate_and_missing_reference(self):
        text = '[105]\ntype=endpoint\naors=105\nauth=999\n[105]\ntype=aor\n[105]\ntype=aor\n'
        r = app.lint_conf('pjsip_custom.conf', text)
        msgs = ' '.join(i['message'] for i in r['issues'])
        self.assertIn('doppelt', msgs)
        self.assertIn('„999“', msgs)
        self.assertNotIn('„105“', msgs)

    def test_template_references_from_default_are_known(self):
        r = app.lint_conf('pjsip_custom.conf', '[200]\ntype=endpoint\naors=100\n')
        self.assertFalse([i for i in r['issues'] if 'aor' in i['message']])

    def test_dialplan_same_without_exten(self):
        r = app.lint_conf('extensions_custom.conf', '[default]\nsame => n,Hangup()\nexten => 600,1,Dial(PJSIP/104,30)\n')
        self.assertEqual(r['errors'], 1)


class MergeTests(unittest.TestCase):
    BASE = ('users:\n- extension: "100"\n  ha_username: Max\n  password: geheim12345\npopup_config:\n'
            '  smartify:\n    camera_by_caller:\n      "200": {stream: alt}\n      "201": {stream: weg}\n')

    def test_users_protected_and_mapping_replaced(self):
        snippet = 'users: []\npopup_config:\n  smartify:\n    camera_by_caller:\n      "200": {stream: neu}\n'
        r = app.merge_sip_core(self.BASE, snippet)
        merged = app.parse_yaml(r['content'])
        self.assertEqual(merged['users'][0]['extension'], '100')
        self.assertEqual(merged['popup_config']['smartify']['camera_by_caller'], {'200': {'stream': 'neu'}})
        self.assertEqual(r['protected_skipped'], ['users'])

    def test_diff_masks_passwords(self):
        r = app.merge_sip_core(self.BASE.replace('geheim12345', 'alt12345678'), self.BASE)
        self.assertNotIn('alt12345678', app.text_diff(self.BASE.replace('geheim12345', 'alt12345678'), self.BASE))
        self.assertIsInstance(r['diff'], str)

    def test_yaml_error_has_line(self):
        with self.assertRaisesRegex(ValueError, 'Zeile'):
            app.parse_yaml('users:\n  - a: [\n')


class UserCheckTests(unittest.TestCase):
    def run_check(self, text):
        with mock.patch.object(app, 'ha_persons', return_value=PERSONS):
            return app.check_users('content', text)

    def test_detects_typical_problems(self):
        text = ('users:\n- {extension: "100", ha_username: max, password: test1234}\n'
                '- {extension: "104", ha_username: ipadvisu, password: langesPasswort123}\n'
                '- {extension: "103", ha_username: Amelie, password: langesPasswort123}\n'
                'popup_config: {auto_open: true}\n')
        msgs = [i['level'] + ':' + i['message'] for i in self.run_check(text)['issues']]
        joined = '\n'.join(msgs)
        self.assertIn('„Max“ (Groß-/Kleinschreibung)', joined)
        self.assertIn('keine Nebenstelle 103', joined)
        self.assertIn('schwaches Passwort', joined)
        self.assertIn('Kein backup_user', joined)
        self.assertIn('extensions fehlt', joined)
        self.assertIn('Fernwartung', joined)

    def test_clean_config(self):
        text = ('users:\n- {extension: "100", ha_username: Max, password: langesPasswort123}\n'
                '- {extension: "104", ha_username: u2, password: langesPasswort123}\n'
                'backup_user: {extension: "100", password: langesPasswort123}\npopup_config: {extensions: {}}\n')
        levels = {i['level'] for i in self.run_check(text)['issues']}
        self.assertNotIn('error', levels)
        self.assertNotIn('warn', levels)


class AmiTests(unittest.TestCase):
    def test_whitelist(self):
        self.assertEqual(app.ami_command_allowed('PJSIP  show contacts'), 'pjsip show contacts')
        self.assertEqual(app.ami_command_allowed('dialplan show 600@default'), 'dialplan show 600@default')
        for bad in ('core restart now', 'pjsip show endpoint 104; core stop', 'originate PJSIP/104', ''):
            with self.assertRaises(ValueError):
                app.ami_command_allowed(bad)


class ApplyTests(unittest.TestCase):
    ACTIVE = {'users': [{'extension': '100', 'ha_username': 'Max', 'password': 'x' * 12}]}
    NEW = 'users:\n- {extension: "100", ha_username: Max, password: xxxxxxxxxxxx}\npopup_config: {extensions: {}}\n'

    def fake_api(self, schema, result_type='create_entry'):
        calls = []
        state = {'cfg': dict(self.ACTIVE)}

        def core_api(method, path, body=None, timeout=8):
            calls.append((method, path))
            if path == 'sip-core/config':
                return state['cfg']
            if path.startswith('config/config_entries/entry'):
                return [{'entry_id': 'abc'}]
            if path == 'config/config_entries/options/flow':
                return {'type': 'form', 'flow_id': 'f1', 'data_schema': schema}
            if method == 'POST' and path.endswith('/f1'):
                state['cfg'] = list(body.values())[0] if isinstance(list(body.values())[0], dict) else app.parse_yaml(list(body.values())[0])
                return {'type': result_type}
            return None
        return core_api, calls

    def test_apply_object_field(self):
        api, calls = self.fake_api([{'name': 'config', 'selector': {'object': {}}}])
        with mock.patch.object(app, 'core_api', api), mock.patch.object(app.time, 'sleep'):
            r = app.apply_sip_core(self.NEW, app.canon_hash(self.ACTIVE))
        self.assertTrue(r['applied'])
        self.assertTrue(r['verified'])
        self.assertTrue((app.DATA_DIR / 'backups' / r['backup']).exists())

    def test_unexpected_form_aborts_without_change(self):
        api, calls = self.fake_api([{'name': 'a'}, {'name': 'b'}])
        with mock.patch.object(app, 'core_api', api):
            with self.assertRaisesRegex(ValueError, 'Unerwarteter'):
                app.apply_sip_core(self.NEW, app.canon_hash(self.ACTIVE))
        self.assertIn(('DELETE', 'config/config_entries/options/flow/f1'), calls)
        self.assertFalse([c for c in calls if c[0] == 'POST' and c[1].endswith('/f1')])

    def test_concurrent_change_detected(self):
        api, _ = self.fake_api([{'name': 'config'}])
        with mock.patch.object(app, 'core_api', api):
            with self.assertRaisesRegex(ValueError, 'inzwischen geändert'):
                app.apply_sip_core(self.NEW, 'falsch')

    def test_placeholder_password_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Platzhalter'):
            app.validate_sip_core_cfg(app.parse_yaml('users:\n- {extension: "1", ha_username: a, password: HIER_BESTEHENDES_PASSWORT_EINSETZEN}\n'))


class ExportImportTests(unittest.TestCase):
    def test_roundtrip(self):
        app.write_camera_map({'200': {'label': 'Tür', 'stream': 'cam', 'mode': 'mse', 'camera_mode': 'auto'}}, app.read_camera_map()['hash'])
        app.write_sip_core('users: []\n', app.read_sip_core()['hash'])
        exported = json.loads(json.dumps(app.export_data()))
        app.write_camera_map({}, app.read_camera_map()['hash'])
        result = app.import_data(exported)
        self.assertEqual(result['cameras'], 1)
        self.assertEqual(app.read_camera_map()['mapping']['200']['stream'], 'cam')

    def test_rejects_foreign_file(self):
        with self.assertRaises(ValueError):
            app.import_data({'format': 'anderes'})


class Go2rtcTests(unittest.TestCase):
    def test_frame_rejects_bad_names(self):
        with self.assertRaises(ValueError):
            app.go2rtc_frame('../etc/passwd')


import socketserver, threading
from contextlib import contextmanager


class FakeAmi(socketserver.StreamRequestHandler):
    """Behaves like Asterisk: banner, FullyBooted event right after login, ActionID echo."""
    legacy = False

    def handle(self):
        send = lambda text: self.wfile.write(text.replace('\n', '\r\n').encode())
        send('Asterisk Call Manager/9.0.0\n')
        buf = ''
        while True:
            line = self.rfile.readline().decode()
            if not line:
                return
            buf += line
            if line.strip():
                continue
            req, buf = buf, ''
            aid = next((l.split(': ', 1)[1].strip() for l in req.splitlines() if l.startswith('ActionID: ')), '')
            if 'Action: Login' in req:
                ok = 'Secret: richtig' in req
                send(f'Response: {"Success" if ok else "Error"}\nActionID: {aid}\nMessage: {"Authentication accepted" if ok else "Authentication failed"}\n\n')
                if ok:
                    send('Event: FullyBooted\nPrivilege: system,all\nStatus: Fully Booted\n\n')
            elif 'PJSIPShowEndpoints' in req:
                send(f'Response: Success\nActionID: {aid}\nEventList: start\nMessage: follows\n\n')
                send('Event: PeerStatus\nPeer: PJSIP/104\n\n')
                for n in ('100', '104'):
                    send(f'Event: EndpointList\nActionID: {aid}\nObjectName: {n}\nDeviceState: Not in use\nContacts: {n}/sip:x,\n\n')
                send(f'Event: EndpointListComplete\nActionID: {aid}\nEventList: Complete\n\n')
            elif 'Action: Command' in req:
                if self.legacy:
                    send(f'Response: Follows\nPrivilege: Command\nActionID: {aid}\nAsterisk 13.0\nZeile zwei\n--END COMMAND--\n\n')
                else:
                    send(f'Response: Success\nActionID: {aid}\nMessage: Command output follows\nOutput: Asterisk 22.8.2\nOutput: Zeile zwei\n\n')
            elif 'Logoff' in req:
                send(f'Response: Goodbye\nActionID: {aid}\n\n')
                return


class AmiSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        cls.server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), FakeAmi)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    @contextmanager
    def options(self, password='richtig'):
        with mock.patch.object(app, 'get_options', return_value={'ami_host': '127.0.0.1', 'ami_port': self.port,
                                                                 'ami_username': 'admin', 'ami_password': password}), \
             mock.patch.object(app, 'ami_host_effective', return_value='127.0.0.1'):
            yield

    def test_status_skips_fullybooted_and_foreign_events(self):
        with self.options():
            r = app.ami_readonly()
        self.assertTrue(r['available'], r)
        self.assertEqual([e['ObjectName'] for e in r['endpoints']], ['100', '104'])

    def test_command_after_login_returns_its_own_output(self):
        with self.options():
            r = app.ami_run('core show version')
        self.assertEqual(r['output'], 'Asterisk 22.8.2\nZeile zwei')

    def test_legacy_follows_response(self):
        FakeAmi.legacy = True
        try:
            with self.options():
                r = app.ami_run('core show version')
        finally:
            FakeAmi.legacy = False
        self.assertEqual(r['output'], 'Asterisk 13.0\nZeile zwei')

    def test_wrong_password_is_reported(self):
        with self.options('falsch'):
            r = app.ami_readonly()
        self.assertFalse(r['available'])
        self.assertIn('Anmeldung verweigert', r['message'])

    def test_diagnose_lists_steps(self):
        with self.options():
            steps = app.ami_diagnose()['steps']
        self.assertEqual([s['level'] for s in steps], ['info', 'warn', 'ok', 'ok', 'ok', 'ok'])

    def test_unreachable_host(self):
        with mock.patch.object(app, 'get_options', return_value={'ami_host': '127.0.0.1', 'ami_port': 1, 'ami_password': 'x'}), \
             mock.patch.object(app, 'ami_host_effective', return_value='127.0.0.1'):
            r = app.ami_readonly()
        self.assertFalse(r['available'])
        self.assertIn('fehlgeschlagen', r['message'])


if __name__ == '__main__':
    unittest.main()
