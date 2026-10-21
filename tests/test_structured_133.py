"""New tests for structured PJSIP and mixed Linphone-cloud dialplan rows."""
import unittest
from pathlib import Path
from unittest import mock
import test_app
app = test_app.app
AST = test_app.AST


class DialplanStructuredTests(unittest.TestCase):
    def setUp(self):
        self.path=AST/'custom'/'extensions.conf'
        self.pjsip=AST/'custom'/'pjsip_custom.conf'
        self.pjsip.write_text('[linphone-cloud]\ntype=endpoint\ntransport=transport-udp\ndisallow=all\nallow=alaw,ulaw\ndirect_media=no\nforce_rport=yes\nrtp_symmetric=yes\n',encoding='utf-8')
        self.path.write_text('''[default]
; Linphone 109 ueber Cloud
exten => 109,1,NoOp(Linphone Push 106)
 same => n,Dial(PJSIP/linphone-cloud/sip:test-benutzer-v@sip.linphone.org,30)
 same => n,Hangup()

; Akuvox Parallelruf
exten => 600,1,NoOp(Akuvox Klingel iPad + iPhone)
 same => n,Dial(${PJSIP_DIAL_CONTACTS(104)}&PJSIP/linphone-cloud/sip:beispielkonto@sip.linphone.org,30)
 same => n,Hangup()

[parkedcallstimeout]
exten => s,1,Hangup()
''',encoding='utf-8')
    def tearDown(self):
        self.path.unlink(missing_ok=True)
        self.pjsip.unlink(missing_ok=True)

    def test_read_109_600_cloud_in_separate_fields(self):
        plan=app.scan_number_plan()
        by={r['number']:r for r in plan['dialplan'] if r['source']=='custom/extensions.conf'}
        self.assertEqual(by['109']['route_options']['description'],'Linphone Push 106')
        self.assertEqual(by['109']['route_options']['targets'],[])
        self.assertEqual(by['109']['route_options']['external_targets'][0]['uri'],'sip:test-benutzer-v@sip.linphone.org')
        self.assertTrue(by['109']['editable'])
        self.assertEqual(by['600']['route_options']['targets'],['104'])
        self.assertEqual(by['600']['route_options']['external_targets'][0]['endpoint'],'linphone-cloud')
        self.assertTrue(by['600']['editable'])

    def test_edit_parallel_route_preserves_neighbor_and_context(self):
        text=self.path.read_text()
        out=app.save_group_row({'operation':'edit','number':'600','context':'default','file':'extensions.conf',
          'hash':app.digest(text),'targets':['104'], 'external':{'endpoint':'linphone-cloud','uri':'sip:newuser@sip.linphone.org'},
          'timeout':45, 'description':'Akuvox Klingel Neues Ziel'})
        self.assertTrue(out['saved'])
        text=self.path.read_text()
        self.assertIn('Dial(PJSIP/linphone-cloud/sip:test-benutzer-v@sip.linphone.org,30)',text)
        self.assertIn('Dial(${PJSIP_DIAL_CONTACTS(104)}&PJSIP/linphone-cloud/sip:newuser@sip.linphone.org,45)',text)
        self.assertIn('[parkedcallstimeout]\nexten => s,1,Hangup()',text)

    def test_edit_cloud_only_109(self):
        out=app.save_group_row({'operation':'edit','number':'109','context':'default','file':'extensions.conf',
          'hash':app.digest(self.path.read_text()),'targets':[], 'external':{'endpoint':'linphone-cloud','uri':'sip:test@sip.linphone.org'},
          'timeout':30, 'description':'Linphone Push Test'})
        self.assertTrue(out['saved'])
        self.assertIn('NoOp(Linphone Push Test)',self.path.read_text())
        self.assertIn('PJSIP/linphone-cloud/sip:test@sip.linphone.org',self.path.read_text())

    def test_rejects_unsupported_dialplan_without_losing_data(self):
        text=self.path.read_text().replace('same => n,Dial(${PJSIP_DIAL_CONTACTS(104)}&', 'same => n,Set(X=1)\n same => n,Dial(${PJSIP_DIAL_CONTACTS(104)}&')
        self.path.write_text(text)
        plan=app.scan_number_plan()
        self.assertFalse(next(r for r in plan['dialplan'] if r['number']=='600' and r['source']=='custom/extensions.conf')['editable'])
        with self.assertRaisesRegex(ValueError,'komplexen'):
            app.save_group_row({'operation':'edit','number':'600','context':'default','file':'extensions.conf',
              'hash':app.digest(text),'targets':['104'],'timeout':30})
        self.assertEqual(text,self.path.read_text())

    def test_cloud_endpoint_edit_and_preserve_other_blocks(self):
        self.assertEqual(app.pjsip_table()['cloud_endpoints'][0]['name'],'linphone-cloud')
        data=app.save_cloud_endpoint({'operation':'edit','name':'linphone-cloud',
          'hash':app.digest(self.pjsip.read_text()),'settings':{'transport':'transport-udp','allow':'alaw,ulaw',
          'direct_media':'no','force_rport':'yes','rewrite_contact':'yes','rtp_symmetric':'yes','ice_support':'no'}})
        self.assertTrue(data['saved'])
        self.assertIn('rewrite_contact=yes',self.pjsip.read_text())

    def test_cloud_save_does_not_inject_unspecified_nat_flags(self):
        self.pjsip.write_text('[linphone-cloud]\ntype=endpoint\nallow=alaw,ulaw\n',encoding='utf-8')
        app.save_cloud_endpoint({'operation':'edit','name':'linphone-cloud',
          'hash':app.digest(self.pjsip.read_text()),'settings':{'transport':'','allow':'alaw,ulaw'}})
        result=self.pjsip.read_text()
        self.assertNotIn('rewrite_contact=',result)
        self.assertNotIn('rtp_symmetric=',result)
        self.assertNotIn('direct_media=',result)

    def test_new_cloud_endpoint_reject_duplicate_and_nonsafe_payload(self):
        base=self.pjsip.read_text()
        with self.assertRaisesRegex(ValueError,'vergeben'):
            app.save_cloud_endpoint({'operation':'add','name':'linphone-cloud','hash':app.digest(base),'settings':{'allow':'alaw'}})
        with self.assertRaisesRegex(ValueError,'Ungültiger'):
            app.save_cloud_endpoint({'operation':'add','name':'evil;foo','hash':app.digest(base),'settings':{'allow':'alaw'}})
        with self.assertRaisesRegex(ValueError,'Codecs'):
            app.save_cloud_endpoint({'operation':'add','name':'other-cloud','hash':app.digest(base),'settings':{'allow':'alaw;foo'}})
        self.assertEqual(self.pjsip.read_text(),base)

if __name__=='__main__':unittest.main()
