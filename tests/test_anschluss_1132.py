"""Ausgang/Eingang eines externen Anschlusses erkennen (v1.13.2)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager'))
import anlage

CONF = """
[linphone-auth]
type=auth
auth_type=userpass
username=raphael
password=x

[linphone-cloud]
type=endpoint
context=default
outbound_auth=linphone-auth
from_domain=sip.linphone.org

[linphone-in]
type=endpoint
context=linphone-in

[linphone-in-ident]
type=identify
endpoint=linphone-in
match=sip.linphone.org

[provider]
type=endpoint
context=from-provider
outbound_auth=prov-auth

[sonstwas]
type=endpoint
"""


class RolleTests(unittest.TestCase):
    def setUp(self):
        self.eps = anlage.endpoints_from_conf([('custom/pjsip_custom.conf', CONF)])

    def test_roles(self):
        r = {n: anlage.anschluss_rolle(n, self.eps[n])[0] for n in ('linphone-cloud', 'linphone-in', 'provider', 'sonstwas')}
        self.assertEqual(r, {'linphone-cloud': 'ausgang', 'linphone-in': 'eingang', 'provider': 'beide', 'sonstwas': ''})
        self.assertIn('identify', anlage.anschluss_rolle('linphone-in', self.eps['linphone-in'])[1])

    def test_name_only(self):
        self.assertEqual(anlage.anschluss_rolle('linphone-in', {})[0], 'eingang')
        self.assertEqual(anlage.anschluss_rolle('my-trunk', {})[0], 'ausgang')

    def test_report_warns_on_swapped(self):
        model = anlage.validate({'format': 'smartify-anlage', 'format_version': 1, 'anlage': {}, 'wege': [],
                                 'teilnehmer': [{'nummer': '', 'typ': 'extern_ziel', 'name': 'Handy', 'endpoint': 'linphone-in',
                                                 'eingang': 'linphone-cloud', 'sip_adresse': 'a@sip.linphone.org', 'faehigkeiten': {}}]})
        rows = anlage.pruefbericht(model, {'endpoints': self.eps})['zeilen']
        titles = [z['titel'] for z in rows if z['level'] == 'warn']
        self.assertTrue(any('„linphone-in“ ist eher ein Eingang als ein Ausgang' in t for t in titles), titles)
        self.assertTrue(any('„linphone-cloud“ ist eher ein Ausgang als ein Eingang' in t for t in titles), titles)
        model['teilnehmer'][0].update(endpoint='linphone-cloud', eingang='linphone-in')
        rows = anlage.pruefbericht(model, {'endpoints': self.eps})['zeilen']
        self.assertFalse(any('ist eher ein' in z['titel'] for z in rows))


if __name__ == '__main__':
    unittest.main()
