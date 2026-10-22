import unittest
from smartify_sip_manager.inbound_routes import normal_ips, render_pjsip, inspect_context, prepare


class FakePjsipTests(unittest.TestCase):
    def test_fake_linphone_endpoint_and_identify(self):
        ip = normal_ips(['100.101.102.103'])
        config = render_pjsip('linphone-in', ip)
        self.assertIn('context=linphone-in', config)
        self.assertIn('match=100.101.102.103/32', config)
        self.assertIn('direct_media=no', config)

    def test_fake_route_104(self):
        conf = ('[linphone-in]\n'
                'exten => 104,1,NoOp(Test)\n'
                ' same => n,Dial($' + '{PJSIP_DIAL_CONTACTS(104)},30)\n'
                ' same => n,Hangup()\n')
        result = inspect_context(conf, 'linphone-in')
        self.assertEqual(result['targets'], ['104'])

    def test_fake_route_with_unknown_action_rejected(self):
        conf = '[linphone-in]\nexten => 104,1,System(echo test)\n'
        with self.assertRaises(ValueError):
            inspect_context(conf, 'linphone-in')

    def test_subnet_is_rejected(self):
        with self.assertRaises(ValueError):
            normal_ips(['100.101.102.0/24'])


if __name__ == '__main__':
    unittest.main()
