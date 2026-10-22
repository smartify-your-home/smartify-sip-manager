import unittest
from smartify_sip_manager.migration import reconcile_legacy_routes


class MigrationTests(unittest.TestCase):
    def test_remove_simple_route_only(self):
        text = ('[linphone-in]\n'
                'exten => 104,1,NoOp(legacy)\n'
                ' same => n,Dial($' + '{PJSIP_DIAL_CONTACTS(104)},30)\n'
                ' same => n,Hangup()\n'
                '[doorbell]\n'
                'exten => 200,1,NoOp(door)\n')
        result = reconcile_legacy_routes(text, {'linphone-in'}, {('linphone-in', '104')})
        self.assertNotIn('exten => 104', result['content'])
        self.assertIn('exten => 200', result['content'])

    def test_unknown_route_blocks_migration(self):
        with self.assertRaises(ValueError):
            reconcile_legacy_routes('[linphone-in]\nexten => 104,1,System(echo bad)\n', {'linphone-in'}, set())

    def test_duplicate_route_blocks_migration(self):
        route = ('exten => 104,1,NoOp(legacy)\n'
                 ' same => n,Dial($' + '{PJSIP_DIAL_CONTACTS(104)},30)\n'
                 ' same => n,Hangup()\n')
        with self.assertRaises(ValueError):
            reconcile_legacy_routes('[linphone-in]\n' + route + route, {'linphone-in'}, set())


if __name__ == '__main__':
    unittest.main()
