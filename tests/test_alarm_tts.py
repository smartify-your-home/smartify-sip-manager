import struct
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "smartify_sip_manager"))
from alarm_tts import repair_wav, alarm_targets, alarm_caller_id


class AlarmTtsTests(unittest.TestCase):
    def test_configurable_caller_id(self):
        self.assertEqual(alarm_caller_id({}), '"RAUCHALARM" <999>')
        self.assertEqual(alarm_caller_id({"alarm_caller_name": "Hausalarm", "alarm_caller_number": "998"}), '"Hausalarm" <998>')

    def test_caller_id_rejects_injection(self):
        with self.assertRaises(ValueError):
            alarm_caller_id({"alarm_caller_name": "Alarm\\r\\nAction: Hangup"})
        with self.assertRaises(ValueError):
            alarm_caller_id({"alarm_caller_number": "9\\n9"})

    def test_multiple_destinations_and_deduplication(self):
        opts = {"alarm_destinations": "sip:a@sip.linphone.org,sip:b@sip.linphone.org\nsip:a@sip.linphone.org"}
        self.assertEqual(alarm_targets(opts), ["sip:a@sip.linphone.org", "sip:b@sip.linphone.org"])

    def test_legacy_destination(self):
        self.assertEqual(alarm_targets({"alarm_destination": "sip:old@sip.linphone.org"}),
                         ["sip:old@sip.linphone.org"])

    def test_invalid_destination_rejected(self):
        with self.assertRaisesRegex(ValueError, "Ungültige"):
            alarm_targets({"alarm_destinations": "PJSIP/100"})

    def test_streaming_header_is_repaired(self):
        payload = b"\x00\x00" * 32
        wav = (b"RIFF" + b"\xff" * 4 + b"WAVEfmt " +
               struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16) +
               b"data" + b"\xff" * 4 + payload)
        fixed = repair_wav(wav)
        self.assertEqual(struct.unpack_from("<I", fixed, 4)[0], len(fixed) - 8)
        self.assertEqual(struct.unpack_from("<I", fixed, 40)[0], len(fixed) - 44)
        self.assertEqual(fixed[44:], payload)

    def test_incompatible_rate_is_rejected(self):
        wav = (b"RIFF" + b"\xff" * 4 + b"WAVEfmt " +
               struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16) +
               b"data" + b"\xff" * 4 + b"\x00\x00")
        with self.assertRaisesRegex(ValueError, "8000"):
            repair_wav(wav)
