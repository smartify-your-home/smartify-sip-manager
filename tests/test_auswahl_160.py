"""Tests für Auswahllisten und Netzwerkerkennung (v1.6)."""
import importlib.util, os, tempfile, unittest
from pathlib import Path
from unittest import mock

TMP = Path(tempfile.mkdtemp(prefix='smartify-160-'))
os.environ['SMARTIFY_DATA_DIR'] = str(TMP / 'data')
os.environ['ADDON_CONFIGS_ROOT'] = str(TMP / 'configs')
AST = TMP / 'configs' / '3e533915_asterisk' / 'asterisk'
(AST / 'custom').mkdir(parents=True)
(AST / 'default').mkdir(parents=True)
(AST / 'default' / 'pjsip_default.conf').write_text('[sipjs-phone-endpoint](!)\ntype=endpoint\nwebrtc=yes\n[104](sipjs-phone-endpoint)\naors=104\n')
(AST / 'custom' / 'pjsip_custom.conf').write_text('[110]\ntype=endpoint\naors=110\ncallerid="Tür" <110>\n[linphone-cloud]\ntype=endpoint\ntransport=transport-udp\n')
spec = importlib.util.spec_from_file_location('app160', Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

ENT = {'available': True, 'entities': [
    {'entity_id': 'switch.pumpe', 'name': 'Poolpumpe'}, {'entity_id': 'switch.haustuer_oeffner', 'name': 'Haustür'},
    {'entity_id': 'light.eingang', 'name': 'Eingang'}, {'entity_id': 'binary_sensor.klingel', 'name': 'Klingel'},
    {'entity_id': 'sensor.temp', 'name': 'Temperatur'}]}


class AuswahlTests(unittest.TestCase):
    def test_lists(self):
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users': [{'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad'}]}), \
             mock.patch.object(app, 'go2rtc_streams_full', return_value=({'cam': {'producers': [{'bytes_recv': 1}]}, 'ipad_gang': {'producers': []}}, 'x')), \
             mock.patch.object(app, 'go2rtc_config_read', return_value=('', {'streams': {'cam': ['rtsp://a:b@1.2.3.4/x']}}, 'x')), \
             mock.patch.object(app, 'ha_entity_index', return_value=ENT):
            a = app.anlage_auswahl()
        self.assertEqual(a['sip_users'][0]['ha_benutzer'], 'ipad')
        self.assertEqual([e['value'] for e in a['endpoints_extern']], ['linphone-cloud'])
        self.assertIn({'value': 'cam', 'label': 'cam · RTSP'}, a['streams'])
        self.assertIn('leer', next(s['label'] for s in a['streams'] if s['value'] == 'ipad_gang'))
        self.assertEqual(a['entities']['tuer'][0]['value'], 'switch.haustuer_oeffner', 'Türöffner zuerst')
        self.assertEqual(a['entities']['licht'][0]['value'], 'light.eingang')
        self.assertEqual(a['entities']['klingel'][0]['value'], 'binary_sensor.klingel')
        self.assertNotIn('104', a['frei'])
        self.assertNotIn('110', a['frei'])
        self.assertEqual(a['frei'][0], '100')

    def test_ha_users_and_switch(self):
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users': [
                    {'extension': '104', 'ha_username': 'Raph PC'}, {'extension': '105', 'ha_username': 'Raph PC'}]}), \
             mock.patch.object(app, 'ha_persons', return_value=[{'name': 'ipadvisu', 'user_id': 'u2'}, {'name': 'Raph PC', 'user_id': 'u1'}]), \
             mock.patch.object(app, 'go2rtc_streams_full', side_effect=ValueError('x')), \
             mock.patch.object(app, 'ha_entity_index', return_value={'available': False, 'message': 'x'}):
            a = app.anlage_auswahl()
        self.assertEqual([u['value'] for u in a['ha_users']], ['ipadvisu', 'Raph PC'])
        self.assertIn('jetzt bei 104, 105', a['ha_users'][1]['label'])
        m = app.anlage_model.import_from({'users': [{'extension': '104', 'ha_username': 'Raph PC'}, {'extension': '105', 'ha_username': 'Raph PC'}]}, {}, {})
        self.assertEqual([t['ha_benutzer'] for t in m['teilnehmer']], ['Raph PC', ''])
        m['teilnehmer'][0]['ha_benutzer'] = 'ipadvisu'
        m['teilnehmer'][1]['ha_benutzer'] = 'Raph PC'
        cfg = {'users': [{'extension': '104', 'ha_username': 'Raph PC'}, {'extension': '105', 'ha_username': 'Raph PC'}]}
        out = app.generator.gen_sip_core(app.anlage_model.validate(m), cfg)
        self.assertEqual([u['ha_username'] for u in out['config']['users']], ['ipadvisu', 'Raph PC'])
        dup = dict(m, teilnehmer=[dict(m['teilnehmer'][0]), dict(m['teilnehmer'][1], ha_benutzer='ipadvisu')])
        with self.assertRaisesRegex(ValueError, 'nur ein HA-Gerät'):
            app.anlage_model.validate(dup)

    def test_lists_without_services(self):
        with mock.patch.object(app, 'read_active_sip_core', side_effect=ValueError('weg')), \
             mock.patch.object(app, 'go2rtc_streams_full', side_effect=ValueError('weg')), \
             mock.patch.object(app, 'ha_entity_index', return_value={'available': False, 'message': 'kein Token'}):
            a = app.anlage_auswahl()
        self.assertGreaterEqual(len(a['meldungen']), 3)
        self.assertTrue(a['frei'])

    def test_netz(self):
        net = {'interfaces': [{'interface': 'hassio', 'primary': False, 'ipv4': {'address': ['172.30.32.1/23']}},
                              {'interface': 'enp0s18', 'primary': True, 'ipv4': {'address': ['192.168.2.65/24']}}]}
        with mock.patch.object(app, 'supervisor_get', return_value=net), \
             mock.patch.object(app, 'core_api', return_value={'external_url': 'https://homeassistant.example-tailnet.ts.net'}):
            n = app.netz_erkennen()
        self.assertEqual(n['lan_ip'], '192.168.2.65')
        self.assertEqual(n['go2rtc_https_url'], 'https://homeassistant.example-tailnet.ts.net:8443')


if __name__ == '__main__':
    unittest.main()


class BackupUserTests(unittest.TestCase):
    def test_backup_user_imported_and_kept(self):
        cfg = {'users': [{'extension': '104', 'ha_username': 'ipadvisu', 'display_name': 'iPad'}],
               'backup_user': {'extension': '105', 'display_name': 'SmartifyService', 'password': 'x'}}
        m = app.anlage_model.import_from(cfg, {}, {})
        b = next(t for t in m['teilnehmer'] if t['nummer'] == '105')
        self.assertEqual((b['typ'], b['ha_benutzer'], b['name']), ('ha_geraet', '*', 'SmartifyService'))
        out = app.generator.gen_sip_core(m, cfg)
        self.assertEqual([r for r in out['aktionen'] if r['level'] == 'warn'], [])
        self.assertNotIn('ha_username', out['config']['backup_user'])
        rep = app.anlage_model.pruefbericht(m, {'asterisk_dir': True, 'sip_core': cfg, 'streams': {}})
        self.assertFalse(any('kein SIP-Core-Benutzer' in r['titel'] for r in rep['zeilen']))
