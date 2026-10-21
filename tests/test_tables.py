"""Structured PJSIP and dialplan regression cases (1.3.3)."""
import unittest
from pathlib import Path
from unittest import mock
import test_app

app=test_app.app
AST=test_app.AST


class PjsipTablesTests(unittest.TestCase):
    def setUp(self):
        self.path=AST/'custom'/'pjsip_custom.conf'
        self.path.write_text('; Existing unrelated settings\n[transport-udp]\ntype=transport\nprotocol=udp\n',encoding='utf-8')
    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def snippet(self,pwd='short',maxcontacts=2):
        return f'''[107]
type=aor
max_contacts={maxcontacts}
remove_existing=no
remove_unavailable=yes

[107]
type=auth
auth_type=userpass
username=107
password={pwd}

[107]
type=endpoint
context=default
aors=107
auth=107
disallow=all
allow=alaw,ulaw
callerid="Beate Linphone" <107>
'''

    def test_add_short_password_and_preserve_unrelated(self):
        d=app.save_pjsip_row({'operation':'add','number':'107','snippet':self.snippet(), 'hash':app.digest(self.path.read_text())})
        self.assertTrue(d['saved'])
        text=self.path.read_text()
        self.assertIn('[transport-udp]',text)
        self.assertIn('password=short',text)
        table=app.pjsip_table()
        self.assertEqual(table['rows'][0]['max_contacts'],'2')
        self.assertTrue(table['rows'][0]['has_password'])
        self.assertNotIn('short',str(table))
        self.assertTrue((AST/'custom'/'.smartify-backups').is_dir())

    def test_edit_empty_password_retains_original(self):
        self.path.write_text(self.snippet('existingPass'),encoding='utf-8')
        data=app.save_pjsip_row({'operation':'edit','number':'107','snippet':self.snippet('',3),'hash':app.digest(self.path.read_text())})
        self.assertIn('max_contacts=3',self.path.read_text())
        self.assertIn('password=existingPass',self.path.read_text())
        self.assertTrue(data['saved'])

    def test_concurrency_collision_and_injection(self):
        with self.assertRaisesRegex(ValueError,'geändert'):
            app.save_pjsip_row({'operation':'add','number':'107','snippet':self.snippet(),'hash':'old'})
        with self.assertRaisesRegex(ValueError,'Zeile|Abschnitte|Option'):
            app.save_pjsip_row({'operation':'add','number':'107','snippet':self.snippet()+'\n[evil]\ntype=endpoint\n','hash':app.digest(self.path.read_text())})
        self.path.write_text(self.snippet('old'),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'vergeben'):
            app.save_pjsip_row({'operation':'add','number':'107','snippet':self.snippet(),'hash':app.digest(self.path.read_text())})

    def test_existing_complex_section_not_overwritten(self):
        self.path.write_text(self.snippet('old')+'\n[107]\ntype=endpoint\nmailboxes=foo\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'vollständigen'):
            app.save_pjsip_row({'operation':'edit','number':'107','snippet':self.snippet(''),'hash':app.digest(self.path.read_text())})


class DialplanTablesTests(unittest.TestCase):
    def setUp(self):
        self.path=AST/'custom'/'extensions.conf'
        self.path.write_text('''[default]
exten => 444,1,Playback(hello-world)
 same => n,Hangup()
; End of first
exten => 555,1,Goto(internal,600,1)
 same => n,Hangup()
[internal]
exten => 777,1,NoOp(keep)
''',encoding='utf-8')
    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_display_real_steps(self):
        with mock.patch.object(app,'read_active_sip_core',return_value={'users':[]}):
            rows=app.scan_number_plan()['dialplan']
        self.assertEqual(next(x for x in rows if x['number']=='444')['steps'],['Playback(hello-world)','Hangup()'])
        self.assertIn('Goto(internal,600,1)',next(x for x in rows if x['number']=='555')['summary'])

    def test_add_group_and_edit_preserve_other_routes(self):
        old=self.path.read_text()
        with mock.patch.object(app, 'scan_number_plan', wraps=app.scan_number_plan):
            d=app.save_group_row({'operation':'add','file':'extensions.conf','hash':app.digest(old),
                 'number':'600','context':'default','targets':['100','104'],'timeout':35})
        self.assertTrue(d['saved'])
        self.assertIn('Goto(internal,600,1)',self.path.read_text())
        self.assertIn('PJSIP_DIAL_CONTACTS(104)',self.path.read_text())
        nxt=app.save_group_row({'operation':'edit','file':'extensions.conf','hash':app.digest(self.path.read_text()),
             'number':'600','context':'default','targets':['104'],'timeout':40})
        self.assertTrue(nxt['saved'])
        self.assertIn('Dial(${PJSIP_DIAL_CONTACTS(104)},40)',self.path.read_text())
        self.assertIn('Playback(hello-world)',self.path.read_text())

    def test_collision_and_unknown_endpoint_rejected(self):
        base=self.path.read_text()
        with self.assertRaisesRegex(ValueError,'vergeben'):
            app.save_group_row({'operation':'add','file':'extensions.conf','hash':app.digest(base),
                 'number':'444','context':'default','targets':['100'],'timeout':30})
        with self.assertRaisesRegex(ValueError,'Nicht vorhandene'):
            app.save_group_row({'operation':'add','file':'extensions.conf','hash':app.digest(base),
                 'number':'601','context':'default','targets':['888'],'timeout':30})

    def test_external_target_preset(self):
        trunk=AST/'default'/'pjsip_linphone.conf'
        trunk.write_text('[linphone-cloud]\ntype=endpoint\n',encoding='utf-8')
        self.addCleanup(lambda:trunk.unlink(missing_ok=True))
        d=app.save_group_row({'operation':'add','file':'extensions.conf','hash':app.digest(self.path.read_text()),
                 'number':'906','context':'default','targets':[],'timeout':30,
                 'external':{'endpoint':'linphone-cloud','uri':'sip:user@sip.linphone.org'}})
        self.assertTrue(d['saved'])
        self.assertIn('PJSIP/linphone-cloud/sip:user@sip.linphone.org',self.path.read_text())
        # 1.3.3: external-only routes are now editable in structured form.
        out=app.save_group_row({'operation':'edit','file':'extensions.conf','hash':app.digest(self.path.read_text()),
             'number':'906','context':'default','targets':['100'],'timeout':30,
             'description':'Lokale Testgruppe'})
        self.assertTrue(out['saved'])
        self.assertIn('Dial(${PJSIP_DIAL_CONTACTS(100)},30)',self.path.read_text())

if __name__=='__main__':unittest.main()

class ShortSipCorePasswordTests(unittest.TestCase):
    def test_short_sip_core_password_allowed_for_new_account(self):
        text='users: []\n'
        d=app.stage_sip_core_user(text, '100', 'Max', 'iPad', 'abc123')
        self.assertTrue(d['created'])
        self.assertEqual(app.parse_yaml(d['content'])['users'][0]['password'], 'abc123')
