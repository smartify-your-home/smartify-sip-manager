"""Regression tests for participant-specific video codec policies."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "smartify_sip_manager"))
import anlage
import generator


class VideoCodecPolicyTests(unittest.TestCase):
    def test_policy_validation(self):
        self.assertEqual(anlage._video_codec_choice("vp8"), "vp8")
        self.assertEqual(anlage._video_codec_choice(None), "auto")
        with self.assertRaises(ValueError):
            anlage._video_codec_choice("vp8\nallow=all")

    def test_vp8_preserves_audio(self):
        t = {"typ": "ha_geraet", "video_codecs": "vp8",
             "faehigkeiten": {"video_im_anruf": True}}
        self.assertEqual(generator._codecs_for(t, ["opus", "ulaw", "h264"]), ["opus", "ulaw", "vp8"])

    def test_auto_preserves_legacy(self):
        t = {"typ": "ha_geraet", "faehigkeiten": {"video_im_anruf": True}}
        self.assertEqual(generator._codecs_for(t, ["opus"]), ["opus", "vp8", "h264"])

    def test_video_disabled(self):
        t = {"typ": "ha_geraet", "video_codecs": "vp8",
             "faehigkeiten": {"video_im_anruf": False}}
        self.assertEqual(generator._codecs_for(t, ["opus", "h264"]), ["opus"])


if __name__ == "__main__":
    unittest.main()
