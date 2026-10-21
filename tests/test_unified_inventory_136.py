"""Regression for unified inventory / deletion from multiple custom sources."""
from pathlib import Path
import unittest
from unittest import mock
import test_app

app=test_app.app
AST=test_app.AST
ROOT=AST/'custom'

SOURCE='''; phone 106
[106]
type=aor
max_contacts=2
remove_existing=yes
qualify_frequency=30

[106]
type=auth
auth_type=userpass
username=106
password=short

[106]
type=endpoint
context=default
aors=106
auth=106
disallow=all
allow=alaw,ulaw
callerid="Raphael" <106>

; ==================================
; Linphone Cloud: DO NOT DELETE
; ==================================

[linphone-cloud]
type=endpoint
transport=transport-udp
allow=alaw,ulaw
'''

class UnifiedInventoryTests(unittest.TestCase):
    def setUp(self):
        self.extra=ROOT/'pjsip_devices.conf'
        self.primary=ROOT/'pjsip_custom.conf'
        self.default=ROOT/'extensions.conf'
        self.primary.write_text('',encoding='utf-8')
        self.extra.write_text(SOURCE,encoding='utf-8')
        self.default.unlink(missing_ok=True)

    def tearDown(self):
        self.extra.unlink(missing_ok=True)
        self.primary.unlink(missing_ok=True)
        self.default.unlink(missing_ok=True)

    def test_extra_custom_file_appears_in_editor(self):
        data=app.pjsip_table()
        row=next(r for r in data['rows'] if r['number']=='106')
        self.assertEqual(row['file'],'pjsip_devices.conf')
        self.assertTrue(row['editable'],row['reason'])
        self.assertEqual(row['max_contacts'],'2')

    def test_delete_from_original_custom_file_preserves_cloud_banner(self):
        row=next(r for r in app.pjsip_table()['rows'] if r['number']=='106')
        with mock.patch.object(app,'read_active_sip_core',return_value={'users':[]}):
            result=app.save_pjsip_row({'operation':'delete','number':'106','file':row['file'],'hash':row['hash']})
        self.assertTrue(result['saved'])
        text=self.extra.read_text(encoding='utf-8')
        self.assertNotIn('[106]',text)
        self.assertIn('Linphone Cloud: DO NOT DELETE',text)
        self.assertIn('[linphone-cloud]',text)
        self.assertEqual(self.primary.read_text(encoding='utf-8'),'')
        self.assertTrue(list((ROOT/'.smartify-backups').glob('pjsip_devices.conf.*.bak')))

    def test_edit_non_primary_file(self):
        row=next(r for r in app.pjsip_table()['rows'] if r['number']=='106')
        snippet=SOURCE.split('; ==================================')[0].replace('max_contacts=2','max_contacts=4').replace('password=short','password=')
        data=app.save_pjsip_row({'operation':'edit','number':'106','file':row['file'],'snippet':snippet,'hash':row['hash']})
        self.assertTrue(data['saved'])
        self.assertIn('max_contacts=4',self.extra.read_text())
        self.assertIn('password=short',self.extra.read_text())
        self.assertIn('Linphone Cloud: DO NOT DELETE',self.extra.read_text())

    def test_duplicate_custom_sources_not_editable_and_no_delete(self):
        self.primary.write_text(SOURCE.replace('106','106'),encoding='utf-8')
        data=app.pjsip_table()
        rows=[r for r in data['rows'] if r['number']=='106']
        self.assertEqual(len(rows),2)
        self.assertTrue(all(not r['editable'] for r in rows))
        with self.assertRaisesRegex(ValueError,'auch in Custom-Dateien'):
            app.save_pjsip_row({'operation':'delete','number':'106','file':'pjsip_devices.conf','hash':app.digest(self.extra.read_text())})

    def test_referenced_endpoint_deletion_still_blocked(self):
        self.default.write_text('[default]\nexten => 600,1,Dial(${PJSIP_DIAL_CONTACTS(106)},30)\n',encoding='utf-8')
        with mock.patch.object(app,'read_active_sip_core',return_value={'users':[]}):
            with self.assertRaisesRegex(ValueError,'wird noch verwendet'):
                app.save_pjsip_row({'operation':'delete','number':'106','file':'pjsip_devices.conf','hash':app.digest(self.extra.read_text())})

if __name__=='__main__':unittest.main()
