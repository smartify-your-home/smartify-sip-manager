"""Regression checks for Calling Card button integration and layout."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CallingCardButtonTest(unittest.TestCase):
    def test_button_is_native_centered_and_not_clipped_sip_card(self):
        js = (ROOT / "frontend/smartify-sip-calling-card.js").read_text(encoding="utf-8")
        self.assertIn('icon="mdi:phone-outline"', js)
        self.assertIn('display:flex;align-items:center;justify-content:center', js)
        self.assertIn('this._phoneSize*0.70', js)
        self.assertIn('window.sipCore', js)
        self.assertIn('sip.startCall(extension)', js)
        self.assertIn('sip.answerCall()', js)
        self.assertIn('sip.endCall()', js)
        self.assertNotIn('custom:sip-call-button', js)
        self.assertNotIn('scale(${(this._phoneSize/65)', js)

    def test_standalone_and_addon_copies_match(self):
        source = (ROOT / "frontend/smartify-sip-calling-card.js").read_bytes()
        packaged = (ROOT / "smartify_sip_manager/frontend/smartify-sip-calling-card.js").read_bytes()
        self.assertEqual(source, packaged)


if __name__ == "__main__":
    unittest.main()
