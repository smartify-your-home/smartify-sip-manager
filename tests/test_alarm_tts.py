import struct
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "smartify_sip_manager"))
from alarm_tts import repair_wav


class AlarmTtsTests(unittest.TestCase):
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
