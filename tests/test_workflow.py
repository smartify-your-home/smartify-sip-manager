"""v1.3.0 number inventory and SIP-Core endpoint workflow regression tests."""
import unittest
from unittest import mock
import test_app

app = test_app.app
AST = test_app.AST


class NumberInventoryTests(unittest.TestCase):
    def setUp(self):
        self.file = AST / 'default' / 'extensions.conf'
        self.file.write_text('''[default]
; dummy
exten => 600,1,NoOp(Smartify Rufgruppe 600)
 same => n,Dial(${PJSIP_DIAL_CONTACTS(100)}&${PJSIP_DIAL_CONTACTS(104)},30)
 same => n,Hangup()
exten => 906,1,NoOp(Einzelziel)
 same => n,Dial(${PJSIP_DIAL_CONTACTS(100)},30)
[internal]
exten => 700,1,NoOp(Other target)
 same => n,Hangup()
''', encoding='utf-8')

    def tearDown(self):
        self.file.unlink(missing_ok=True)

    def test_read_groups_and_other_reserved_numbers(self):
        with mock.patch.object(app, 'read_active_sip_core', return_value={
            'users': [{'extension':'100','ha_username':'Max'}, {'extension':'222','ha_username':'Tab'}]}):
            d = app.scan_number_plan()
        self.assertEqual([x['number'] for x in d['groups']], ['600'])
        self.assertEqual(d['groups'][0]['targets'], ['100', '104'])
        self.assertEqual(d['groups'][0]['context'], 'default')
        self.assertEqual(d['groups'][0]['source'], 'default/extensions.conf')
        self.assertIn('906', d['used'])
        self.assertIn('700', d['used'])
        self.assertIn('222', d['used'])
        self.assertIn('100', d['used'])
        self.assertFalse(d['complete'])

    def test_no_false_free_claim_when_sip_core_unreachable(self):
        with mock.patch.object(app, 'read_active_sip_core', side_effect=ValueError('unavailable')):
            d=app.scan_number_plan()
        self.assertFalse(d['complete'])
        self.assertTrue(any('SIP-Core' in w for w in d['warnings']))
        self.assertIn('600', d['used'])


class StageSipUserTests(unittest.TestCase):
    def test_reject_nonexistent_asterisk_extension(self):
        with self.assertRaisesRegex(ValueError, 'existiert nicht'):
            app.stage_sip_core_user('users: []\n', '888', 'Test', 'Test', 'superSecret12345')

    def test_add_known_endpoint_requires_password(self):
        with self.assertRaisesRegex(ValueError, 'Passwort'):
            app.stage_sip_core_user('users: []\n', '100', 'Max', 'Telefon')
        d=app.stage_sip_core_user('users: []\n', '100', 'Max', 'Telefon', 'superSecret12345')
        self.assertTrue(d['created'])
        cfg=app.parse_yaml(d['content'])
        self.assertEqual(cfg['users'][0]['extension'], '100')
        self.assertEqual(cfg['users'][0]['password'], 'superSecret12345')

    def test_update_preserves_existing_credentials(self):
        existing='users:\n  - extension: "100"\n    ha_username: Max\n    display_name: alt\n    password: bestandsPasswort999\nother_option: abc\n'
        d=app.stage_sip_core_user(existing, '100', 'MaxNEU', 'iPad')
        self.assertFalse(d['created'])
        cfg=app.parse_yaml(d['content'])
        self.assertEqual(cfg['users'][0]['password'], 'bestandsPasswort999')
        self.assertEqual(cfg['users'][0]['display_name'], 'iPad')
        self.assertEqual(cfg['other_option'], 'abc')
        with self.assertRaisesRegex(ValueError, 'Passwortfeld'):
            app.stage_sip_core_user(existing, '100', 'Max', 'iPad', 'someChangedPassword')

    def test_reject_duplicate_user(self):
        existing='users:\n  - {extension: "100", ha_username: Max}\n  - {extension: "100", ha_username: Max}\n'
        with self.assertRaisesRegex(ValueError, 'Doppelte'):
            app.stage_sip_core_user(existing, '100', 'Max', 'iPad')


if __name__=='__main__':
    unittest.main()
