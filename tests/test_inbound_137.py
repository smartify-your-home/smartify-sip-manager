"""Incoming Linphone/Tailscale path: safe edits of both PJSIP and dialplan."""
import unittest
from unittest import mock
import test_app

app=test_app.app
CUSTOM=test_app.AST/'custom'
DEFAULT=test_app.AST/'default'

PJSIP='''; cloud registration is not part of inbound
[linphone-in]
type=endpoint
transport=transport-udp
context=linphone-in
disallow=all
allow=alaw,ulaw
direct_media=no
force_rport=yes
rewrite_contact=yes
rtp_symmetric=yes

[linphone-in-identify]
type=identify
endpoint=linphone-in
match=100.64.10.20/32

; outward cloud MUST STAY
[linphone-cloud]
type=endpoint
disallow=all
allow=alaw,ulaw
transport=transport-udp
direct_media=no
force_rport=yes
rtp_symmetric=yes
'''
EXT='''[default]
exten => 600,1,NoOp(Parallelruf)
 same => n,Dial(${PJSIP_DIAL_CONTACTS(104)},30)
 same => n,Hangup()

[linphone-in]
exten => 104,1,NoOp(Linphone Cloud zu iPad 104)
 same => n,Dial(${PJSIP_DIAL_CONTACTS(104)},30)
 same => n,Hangup()

[parkedcallstimeout]
exten => s,1,Hangup()
'''

class InboundTests(unittest.TestCase):
    def setUp(self):
        self.p=CUSTOM/'pjsip_custom.conf'
        self.e=CUSTOM/'extensions.conf'
        self.p.write_text(PJSIP,encoding='utf-8')
        self.e.write_text(EXT,encoding='utf-8')
    def tearDown(self):
        self.p.unlink(missing_ok=True)
        self.e.unlink(missing_ok=True)
        for fn in ('pjsip_other.conf','extensions_custom.conf','pjsip_extra.conf'):
            (CUSTOM/fn).unlink(missing_ok=True)
    def body(self,**changes):
        b={'name':'linphone-in','ips':['100.64.10.20/32','100.64.10.22/32'],
           'targets':['104','100'],'timeout':30,
           'pjsip_file':'pjsip_custom.conf','extensions_file':'extensions.conf',
           'hashes':{'pjsip':app.read_file('pjsip_custom.conf')['hash'],
                     'extensions':app.read_file('extensions.conf')['hash']}}
        b.update(changes)
        return b
    def test_existing_recognized(self):
        result=app.inbound_workspace()
        row=next(x for x in result['profiles'] if x['name']=='linphone-in')
        self.assertEqual(row['targets'],['104'])
        self.assertEqual(row['ips'],['100.64.10.20/32'])
        self.assertIn('104',result['available_extensions'])
    def test_multiple_ips_multiple_destinations_write_exact(self):
        b=self.body();out=app.inbound_preview(b)
        self.assertIn('match=100.64.10.20/32,100.64.10.22/32',out['pjsip'])
        self.assertIn('exten => 100,1',out['extensions'])
        b['confirm']=True;r=app.inbound_save(b)
        self.assertTrue(r['saved'])
        text=self.p.read_text();ext=self.e.read_text()
        self.assertEqual(text.count('[linphone-in]'),1)
        self.assertEqual(text.count('[linphone-in-identify]'),1)
        self.assertIn('match=100.64.10.20/32,100.64.10.22/32',text)
        self.assertIn('outward cloud MUST STAY',text)
        self.assertIn('linphone-cloud',text)
        self.assertIn('exten => 100,1,NoOp',ext)
        self.assertIn('exten => 104,1,NoOp',ext)
        self.assertIn('[parkedcallstimeout]',ext)
        self.assertIn('[default]',ext)
        self.assertEqual(ext.count('[linphone-in]'),1)
        self.assertTrue(list((CUSTOM/'.smartify-backups').glob('pjsip_custom.conf.*.bak')))
        self.assertTrue(list((CUSTOM/'.smartify-backups').glob('extensions.conf.*.bak')))
        self.assertEqual(next(x for x in app.inbound_workspace()['profiles'] if x['name']=='linphone-in')['targets'],['104','100'])
    def test_reject_broad_range_and_bad_ip(self):
        for ips in (['100.64.10.0/24'],['0.0.0.0/0'],['not-an-ip'],[], ['100.64.10.20','100.64.10.20/32']):
            with self.subTest(ips=ips),self.assertRaises(ValueError):
                app.inbound_preview(self.body(ips=ips))
    def test_reject_unregistered_and_duplicate_target(self):
        for dests in (['999'],['104','104'],[],[';exec']):
            with self.subTest(dests=dests),self.assertRaises(ValueError):
                app.inbound_preview(self.body(targets=dests))
    def test_reject_stale_hashes(self):
        with self.assertRaisesRegex(ValueError,'geändert'):
            app.inbound_save(self.body(hashes={'pjsip':'old','extensions':'old'},confirm=True))
        self.assertEqual(self.p.read_text(),PJSIP)
    def test_other_profile_identify_conflict(self):
        (CUSTOM/'pjsip_other.conf').write_text('[another-identify]\ntype=identify\nendpoint=another\nmatch=100.64.10.22/32\n')
        with self.assertRaisesRegex(ValueError,'überschneidet'):
            app.inbound_preview(self.body())
    def test_unknown_dialplan_preserved_and_refuses_modification(self):
        self.e.write_text(EXT.replace(' same => n,Hangup()\n\n[parkedcallstimeout]', ' same => n,Playback(hello-world)\n\n[parkedcallstimeout]'))
        with self.assertRaisesRegex(ValueError,'nicht unterstützte|andere Dial'):
            app.inbound_save(self.body(hashes={'pjsip':app.digest(PJSIP),'extensions':app.digest(self.e.read_text())},confirm=True))
        self.assertEqual(self.p.read_text(),PJSIP)
    def test_save_requires_confirmation(self):
        with self.assertRaisesRegex(ValueError,'bestätigt'):
            app.inbound_save(self.body())
    def test_new_profile_add_does_not_modify_existing(self):
        b=self.body(name='linphone-guest',ips=['100.64.10.22/32'],targets=['104'])
        b['confirm']=True
        app.inbound_save(b)
        self.assertIn('[linphone-guest-identify]',self.p.read_text())
        self.assertIn('[linphone-in-identify]',self.p.read_text())
        self.assertIn('[linphone-guest]',self.e.read_text())
        self.assertIn('[linphone-in]',self.e.read_text())
    def test_rollback_first_write_when_second_fails(self):
        original=app.write_file
        def fails(name,*args):
            if name=='extensions.conf':raise OSError('simulated disk error')
            return original(name,*args)
        with mock.patch.object(app,'write_file',side_effect=fails):
            with self.assertRaisesRegex(ValueError,'zurückgesetzt'):
                app.inbound_save(self.body(confirm=True))
        self.assertEqual(self.p.read_text(),PJSIP)
        self.assertEqual(self.e.read_text(),EXT)

if __name__ == '__main__':unittest.main()
