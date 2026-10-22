import copy
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TEST_DATA = tempfile.TemporaryDirectory()
os.environ['SMARTIFY_DATA_DIR'] = TEST_DATA.name
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'smartify_sip_manager'))
app = importlib.import_module('app')


class AutoSecretTests(unittest.TestCase):
    def setUp(self):
        self.config = {'users': [
            {'extension': '104', 'ha_username': 'ipad', 'display_name': 'iPad', 'password': 'old'},
            {'extension': '100', 'ha_username': 'iphone', 'display_name': 'iPhone', 'password': 'shared'}],
            'popup_config': {'auto_open': True}}

    def test_preview_redacts_secret_and_counts_changes(self):
        with patch.object(app, 'asterisk_auto_secret', return_value=(True, 'shared')), \
             patch.object(app, 'read_active_sip_core', return_value=copy.deepcopy(self.config)):
            d = app.auto_secret_preview()
        self.assertEqual(d['count_changed'], 1)
        self.assertNotIn('shared', repr(d))
        self.assertTrue(d['secret_present'])

    def test_sync_overwrites_only_passwords_and_preserves_other_settings(self):
        before = copy.deepcopy(self.config)
        received = {}
        def fake_apply(content, expected):
            received['cfg'] = app.parse_yaml(content)
            received['hash'] = expected
            return {'applied': True, 'verified': True, 'backup': 'backup.json', 'note': 'OK'}
        with patch.object(app, 'asterisk_auto_secret', return_value=(True, 'shared')), \
             patch.object(app, 'read_active_sip_core', return_value=copy.deepcopy(before)), \
             patch.object(app, 'apply_sip_core', side_effect=fake_apply):
            r = app.auto_secret_sync(app.canon_hash(before), 'ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN')
        self.assertEqual(r['changed'], 1)
        self.assertEqual([u['password'] for u in received['cfg']['users']], ['shared', 'shared'])
        self.assertEqual(received['cfg']['popup_config'], before['popup_config'])
        self.assertEqual([u['ha_username'] for u in received['cfg']['users']], ['ipad', 'iphone'])

    def test_stale_revision_does_not_write(self):
        with patch.object(app, 'asterisk_auto_secret', return_value=(True, 'shared')), \
             patch.object(app, 'read_active_sip_core', return_value=copy.deepcopy(self.config)), \
             patch.object(app, 'apply_sip_core') as write:
            with self.assertRaises(ValueError):
                app.auto_secret_sync('stale', 'ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN')
            write.assert_not_called()

    def test_requires_confirm_and_enabled_autogeneration(self):
        with patch.object(app, 'asterisk_auto_secret', return_value=(False, 'shared')), \
             patch.object(app, 'read_active_sip_core', return_value=copy.deepcopy(self.config)), \
             patch.object(app, 'apply_sip_core') as write:
            with self.assertRaises(ValueError):
                app.auto_secret_sync(app.canon_hash(self.config), 'ALLE SIP CORE PASSWOERTER UEBERSCHREIBEN')
            with self.assertRaises(ValueError):
                app.auto_secret_sync(app.canon_hash(self.config), None)
            write.assert_not_called()

    def test_invalid_duplicate_extension_rejected(self):
        cfg = copy.deepcopy(self.config)
        cfg['users'][1]['extension'] = '104'
        with patch.object(app, 'asterisk_auto_secret', return_value=(True, 'shared')), \
             patch.object(app, 'read_active_sip_core', return_value=cfg):
            with self.assertRaises(ValueError):
                app.auto_secret_preview()


if __name__ == '__main__':
    unittest.main()
