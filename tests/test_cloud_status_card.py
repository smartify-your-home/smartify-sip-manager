"""Cloud-registration snapshot and Calling Card transparency regressions."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "smartify_sip_manager"))
import sip_status_worker


class TestCloudRegistration(unittest.TestCase):
    def test_registration_does_not_mean_endpoint_reachable(self):
        class Ami:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def list_events(self, action, end):
                action = action["Action"]
                if action == "PJSIPShowEndpoints":
                    return [{"Event": "EndpointList", "ObjectName": "linphone-cloud", "Aor": ""}]
                if action == "PJSIPShowContacts":
                    return []
                if action == "PJSIPShowRegistrationsOutbound":
                    return [{"Event": "OutboundRegistrationDetail", "ObjectName": "linphone-cloud",
                             "Status": "Registered"}]
                raise AssertionError(action)
        people = sip_status_worker.snapshot(Ami)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["registration_status"], "registered")
        self.assertFalse(people[0]["reachable"])
        self.assertEqual(people[0]["status"], "unknown")

    def test_optional_registration_query_failure_keeps_other_status(self):
        class Ami:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def list_events(self, action, end):
                action = action["Action"]
                if action == "PJSIPShowEndpoints":
                    return [{"Event": "EndpointList", "ObjectName": "100", "Aor": "100"}]
                if action == "PJSIPShowContacts":
                    return [{"Event": "ContactList", "Aor": "100", "Status": "Reachable"}]
                raise ValueError("not supported")
        people = sip_status_worker.snapshot(Ami)
        self.assertTrue(people[0]["reachable"])
        self.assertIsNone(people[0]["registration_status"])

    def test_card_hides_only_unknown_cloud_status(self):
        src = (ROOT / "frontend/smartify-sip-calling-card.js").read_text(encoding="utf-8")
        self.assertIn('p.status==="unknown" && cloudAccount(p) ? ["",""]', src)
        self.assertIn('p.status==="unknown" && !cloudAccount(p)', src)
        self.assertIn('!desc ? "" : desc==="?"', src)

    def test_transparency_does_not_fade_labels_or_buttons(self):
        src = (ROOT / "frontend/smartify-sip-calling-card.js").read_text(encoding="utf-8")
        self.assertIn('id="card-transparency"', src)
        self.assertIn('min="0" max="100" step="5"', src)
        self.assertIn('this._prefs._cardTransparency', src)
        self.assertIn('background:color-mix(in srgb,', src)
        self.assertNotIn('ha-card{opacity:', src)


if __name__ == "__main__":
    unittest.main()
