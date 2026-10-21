"""v1.3.5 – reserve numbers before creation and safely delete custom triplets."""
import unittest
from unittest import mock
import test_app

app = test_app.app
AST = test_app.AST

SNIPPET='''[107]
type=aor
max_contacts=1
remove_existing=yes

[107]
type=auth
auth_type=userpass
username=107
password=short

[107]
type=endpoint
context=default
aors=107
auth=107
disallow=all
allow=alaw,ulaw
callerid="Beate" <107>
'''

class NumberGuardTests(unittest.TestCase):
    def setUp(self):
        self.path = AST/'custom'/'pjsip_custom.conf'
        self.dp = AST/'custom'/'extensions.conf'
        self.path.write_text('', encoding='utf-8')
        self.dp.unlink(missing_ok=True)

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        self.dp.unlink(missing_ok=True)

    def add(self):
        self.path.write_text(SNIPPET, encoding='utf-8')

    def test_partial_auth_and_aor_number_still_reserved(self):
        self.path.write_text('[109]\ntype=aor\nmax_contacts=1\n', encoding='utf-8')
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[]}):
            plan=app.scan_number_plan()
            self.assertIn('109', plan['used'])
            duplicate=SNIPPET.replace('107','109')
            with self.assertRaisesRegex(ValueError, 'bereits vergeben'):
                app.save_pjsip_row({'operation':'add','number':'109','snippet':duplicate,
                                    'hash':app.digest(self.path.read_text())})

    def test_occupied_existing_cannot_be_added_again(self):
        self.add()
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[]}):
            with self.assertRaisesRegex(ValueError, 'bereits vergeben'):
                app.save_pjsip_row({'operation':'add','number':'107','snippet':SNIPPET,
                                    'hash':app.digest(self.path.read_text())})

    def test_delete_simple_custom_triplet_preserves_unrelated(self):
        self.path.write_text('[transport-udp]\ntype=transport\nprotocol=udp\n\n'+SNIPPET, encoding='utf-8')
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[]}):
            result=app.save_pjsip_row({'operation':'delete','number':'107',
                                       'hash':app.digest(self.path.read_text())})
        self.assertTrue(result['saved'])
        self.assertNotIn('[107]', self.path.read_text())
        self.assertIn('[transport-udp]', self.path.read_text())

    def test_delete_refuses_dialplan_reference(self):
        self.add()
        self.dp.write_text('[default]\nexten => 600,1,Dial(${PJSIP_DIAL_CONTACTS(107)},30)\n', encoding='utf-8')
        before=self.path.read_text()
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[]}):
            with self.assertRaisesRegex(ValueError, 'wird noch verwendet'):
                app.save_pjsip_row({'operation':'delete','number':'107',
                                    'hash':app.digest(before)})
        self.assertEqual(self.path.read_text(), before)

    def test_delete_refuses_sip_core_account(self):
        self.add()
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[{'extension':'107','ha_username':'Beate'}]}):
            with self.assertRaisesRegex(ValueError, 'wird noch verwendet'):
                app.save_pjsip_row({'operation':'delete','number':'107',
                                    'hash':app.digest(self.path.read_text())})

    def test_delete_refuses_stale_hash(self):
        self.add()
        with self.assertRaisesRegex(ValueError, 'geändert'):
            app.save_pjsip_row({'operation':'delete','number':'107', 'hash':'stale'})

    def test_delete_keeps_trailing_comments(self):
        self.path.write_text(SNIPPET+'; comment belongs to next section\n',encoding='utf-8')
        with mock.patch.object(app, 'read_active_sip_core', return_value={'users':[]}):
            app.save_pjsip_row({'operation':'delete','number':'107',
                                'hash':app.digest(self.path.read_text())})
        self.assertNotIn('[107]',self.path.read_text())
        self.assertIn('; comment belongs to next section',self.path.read_text())

if __name__=='__main__':unittest.main()
