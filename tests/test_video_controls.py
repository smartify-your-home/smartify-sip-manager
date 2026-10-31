"""Static safety checks for Smartify received-video controls."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = (ROOT / "frontend/smartify-doorstation-card.js").read_text(encoding="utf-8")
POPUP = (ROOT / "frontend/smartify-doorstation-popup.js").read_text(encoding="utf-8")
BUNDLE = (ROOT / "dist/smartify-sip-manager.js").read_text(encoding="utf-8")


class ReceivedVideoControlsTests(unittest.TestCase):
    def test_both_components_offer_hide_and_show(self):
        for content in (CARD, POPUP):
            with self.subTest(component=content[:60]):
                self.assertIn("Video ausblenden", content)
                self.assertIn("Video anzeigen", content)

    def test_card_unmounts_player_when_hidden(self):
        self.assertIn("!shouldShow || !this._videoShown", CARD)
        self.assertIn("this._cameraHost.replaceChildren()", CARD)

    def test_popup_unmounts_player_when_hidden(self):
        self.assertIn("this._smartifyDropCamera()", POPUP)
        self.assertIn("this._smartifyVideoShown=false", POPUP)
        self.assertIn("this._smartifyVideoShown = true;", POPUP)

    def test_native_sip_controls_remain_embedded(self):
        self.assertIn("type:'custom:sip-call-card'", CARD)
        self.assertIn("super.render()", POPUP)
        self.assertIn("super.closePopup()", POPUP)

    def test_bundle_contains_updated_components(self):
        self.assertIn(CARD, BUNDLE)
        self.assertIn(POPUP, BUNDLE)


if __name__ == "__main__":
    unittest.main()
