"""AMI-Hostauflösung: Automatik, Legacy-Loopback und manueller Override."""
import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'smartify_sip_manager' / 'app.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ami_host_effective')
scope = {'re': __import__('re'), 'slug': '3e533915_asterisk'}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), 'exec'), scope)
resolve = scope['ami_host_effective']


class TestAmiHost(unittest.TestCase):
    def test_auto_from_slug(self):
        self.assertEqual(resolve({'ami_host': 'auto', 'asterisk_slug': '3e533915_asterisk'}), '3e533915-asterisk')

    def test_legacy_localhost(self):
        self.assertEqual(resolve({'ami_host': '127.0.0.1'}), '3e533915-asterisk')

    def test_manual_override(self):
        self.assertEqual(resolve({'ami_host': '192.168.1.14', 'asterisk_slug': '3e533915_asterisk'}), '192.168.1.14')

    def test_another_slug(self):
        self.assertEqual(resolve({'ami_host': '', 'asterisk_slug': 'a0d7b954_asterisk'}), 'a0d7b954-asterisk')


if __name__ == '__main__':
    unittest.main()
