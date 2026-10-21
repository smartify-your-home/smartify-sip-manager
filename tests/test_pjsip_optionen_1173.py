"""1.17.3: Jede Option, die der Manager in einen Endpoint schreibt, muss Asterisk kennen.
Liste aus Asterisk res_pjsip (ast_sorcery_object_field_register … "endpoint", …) in asterisk_pjsip_options.txt.
Hintergrund: 1.17.2 schrieb „use_received_transport“ statt „media_use_received_transport“ – Asterisk lud den Endpoint nicht."""
import sys, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'smartify_sip_manager'))
import anlage as A, generator as G

KNOWN = {l.split()[1] for l in (HERE / 'asterisk_pjsip_options.txt').read_text().splitlines() if l.startswith('endpoint ')}
KNOWN |= {'type', 'disallow'}   # disallow ist in Asterisk mehrzeilig registriert


class OptionTests(unittest.TestCase):
    def test_endpoint_keys_known(self):
        pj = '[linphone-cloud]\ntype=endpoint\nallow=alaw\n\n[linphone-in]\ntype=endpoint\ncontext=linphone-in\nallow=ulaw\n'
        m = A.validate({'format': 'smartify-anlage', 'format_version': 1, 'wege': [],
            'anlage': {'lan_ip': '192.168.2.65', 'tailscale_ip': '100.64.10.10'},
            'eingaenge': [{'name': 'tailscale-in', 'quell_ips': ['100.64.1.1']}],
            'teilnehmer': [{'nummer': '120', 'typ': 'sip_telefon', 'name': 'Büro', 'faehigkeiten': {'video_im_anruf': True}},
                           {'nummer': '110', 'typ': 'tuerstation', 'name': 'Tür', 'faehigkeiten': {}},
                           {'nummer': '104', 'typ': 'ha_geraet', 'name': 'iPad', 'faehigkeiten': {'video_im_anruf': True}},
                           {'nummer': '906', 'typ': 'extern_ziel', 'name': 'R', 'endpoint': 'linphone-cloud', 'eingang': 'linphone-in',
                            'sip_adresse': 'r@sip.linphone.org', 'faehigkeiten': {'video_im_anruf': True}, 'quell_ips': '100.64.2.2'}]})
        content = G.gen_pjsip(m, pj, [('custom/pjsip_custom.conf', pj)], {'sip': {}})['content']
        bad = []
        for sec in content.split('\n['):
            lines = [l for l in sec.splitlines()[1:] if '=' in l and not l.lstrip().startswith(';')]
            if 'type=endpoint' not in lines:
                continue
            bad += [l.split('=', 1)[0].strip() for l in lines if l.split('=', 1)[0].strip() not in KNOWN]
        self.assertEqual(bad, [], 'Asterisk kennt diese Endpoint-Optionen nicht')


if __name__ == '__main__':
    unittest.main()
