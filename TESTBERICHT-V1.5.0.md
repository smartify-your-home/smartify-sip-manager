# Smartify SIP Manager 1.5.0 – Testbericht

| Prüfung | Ergebnis |
| --- | --- |
| `release-check.sh` (Versionen, Syntax, alle Unit-Tests, JS) | bestanden |
| `test_generator_150.py`: Übernahme bestehender Nebenstelle mit Passwort, neue Nebenstelle, keine Doppelung von Add-on-Endpoints, externe allow-Zeile, Idempotenz, SIP-Core-Patch, go2rtc-Streams, Maskierung | bestanden |
| RTSP gegen simulierte Kamera: Digest-Anmeldung, falsches Passwort (401), falscher Pfad (404), H.265-Erkennung, Netzsuche mit Herstellererkennung, Ablehnung öffentlicher Netze | bestanden |
| `test_erzeugen_app_150.py`: Vorschlag mit RTSP aus go2rtc, Vorschau, Bestätigungs- und Versionsschutz, Übernahme aller drei Ziele, Zugangsdaten, zweiter Lauf ohne Änderungen | bestanden |
| Chromium mit echtem Manager-Server, simuliertem SIP Core/go2rtc und simulierter Kamera: Übernehmen, Kamerasuche, Testen, Übernehmen, Speichern, Vorschau, Übernahme, Prüfbericht, zweite Vorschau „aktuell“ | ohne Skriptfehler |

**Nicht geprüft:** echte Asterisk-, SIP-Core- und go2rtc-Instanz (insbesondere `POST /api/config` der go2rtc-Version aus WebRTC Camera), echte Kameras im LAN.
