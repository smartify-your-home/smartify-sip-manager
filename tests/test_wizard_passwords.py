"""Regression tests for password rotation (no live SIP Core or Asterisk)."""
import unittest
from unittest.mock import patch
from test_app import app


class WizardPasswordTests(unittest.TestCase):
    def test_rejects_without_confirmation_or_weak_password(self):
        with self.assertRaisesRegex(ValueError, 'Bestätigung'):
            app.wizard_rotate_passwords({'kind': 'sip_core', 'numbers': ['100'], 'password': 'ValidPassword123!'})
        with self.assertRaisesRegex(ValueError, '12–128'):
            app.wizard_rotate_passwords({'kind': 'sip_core', 'numbers': ['100'], 'password': 'short', 'confirm': 'PASSWOERTER AENDERN'})

    def test_no_duplicate_or_invalid_targets(self):
        for numbers in ([], ['100','100'], ['1'], ['100','x']):
            with self.subTest(numbers=numbers), self.assertRaises(ValueError):
                app.wizard_rotate_passwords({'kind': 'sip_core', 'numbers': numbers, 'password': 'LongSecurePassword123!', 'confirm':'PASSWOERTER AENDERN'})

    def test_sip_core_rotates_selected_only(self):
        current={'users':[{'extension':'100','ha_username':'a','password':'old100'},
                          {'extension':'103','ha_username':'b','password':'old103'}]}
        captured={}
        def apply(content, expected):
            captured['cfg']=app.parse_yaml(content)
            captured['hash']=expected
            return {'saved':True}
        with patch.object(app, 'read_active_sip_core', return_value=current), patch.object(app, 'apply_sip_core', side_effect=apply):
            outcome=app.wizard_rotate_passwords({'kind':'sip_core','numbers':['100'],'password':'SecurePassword123!', 'active_hash':app.canon_hash(current),'confirm':'PASSWOERTER AENDERN'})
        self.assertEqual(outcome['changed'],1)
        self.assertEqual(captured['cfg']['users'][0]['password'],'SecurePassword123!')
        self.assertEqual(captured['cfg']['users'][1]['password'],'old103')
        self.assertNotIn('SecurePassword123!',str(outcome))

    def test_sip_core_detects_concurrent_modification(self):
        current={'users':[{'extension':'100','ha_username':'a','password':'old'}]}
        with patch.object(app, 'read_active_sip_core', return_value=current), patch.object(app, 'apply_sip_core') as apply:
            with self.assertRaisesRegex(ValueError,'geändert'):
                app.wizard_rotate_passwords({'kind':'sip_core','numbers':['100'],'password':'SecurePassword123!','active_hash':'stale','confirm':'PASSWOERTER AENDERN'})
            apply.assert_not_called()

    def test_target_metadata_has_no_password_values(self):
        current={'users':[{'extension':'100','display_name':'Test','password':'SecretMustNotLeak'}]}
        with patch.object(app,'read_active_sip_core',return_value=current), patch.object(app,'pjsip_table',return_value={'rows':[]}):
            result=app.wizard_password_targets()
        self.assertEqual(result['targets'][0]['configured'],True)
        self.assertNotIn('SecretMustNotLeak',str(result))


    def test_pjsip_rotates_selected_auth_only(self):
        original = (
            '[100]\ntype=aor\nmax_contacts=1\n\n'
            '[100]\ntype=auth\nauth_type=userpass\nusername=100\npassword=old100\n\n'
            '[100]\ntype=endpoint\naors=100\nauth=100\n\n'
            '[103]\ntype=aor\nmax_contacts=1\n\n'
            '[103]\ntype=auth\nauth_type=userpass\nusername=103\npassword=old103\n\n'
            '[103]\ntype=endpoint\naors=103\nauth=103\n'
        )
        info = {'source':'custom','hash':'goodhash','content':original}
        rows = {'rows':[{'number':n,'file':'pjsip_custom.conf','editable':True} for n in ('100','103')]}
        saved = {}
        def write(name, content, expected):
            saved.update(name=name, content=content, expected=expected)
            return {'hash':'changed'}
        with patch.object(app,'read_file',return_value=info), \
             patch.object(app,'pjsip_table',return_value=rows), \
             patch.object(app,'lint_conf',return_value={'errors':False}), \
             patch.object(app,'write_file',side_effect=write):
            result=app.wizard_rotate_passwords({'kind':'pjsip','numbers':['100'],
                'password':'SecurePassword123!','file':'pjsip_custom.conf','file_hash':'goodhash',
                'confirm':'PASSWOERTER AENDERN'})
        self.assertEqual(result['changed'],1)
        self.assertIn('password=SecurePassword123!',saved['content'])
        self.assertIn('password=old103',saved['content'])
        self.assertEqual(saved['expected'],'goodhash')
        self.assertNotIn('SecurePassword123!',str(result))

    def test_pjsip_rejects_stale_file(self):
        with patch.object(app,'read_file',return_value={'source':'custom','hash':'new','content':''}), \
             patch.object(app,'write_file') as write:
            with self.assertRaisesRegex(ValueError,'verändert'):
                app.wizard_rotate_passwords({'kind':'pjsip','numbers':['100'],'password':'SecurePassword123!',
                    'file':'pjsip_custom.conf','file_hash':'old','confirm':'PASSWOERTER AENDERN'})
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
