# Smartify SIP Manager 1.4.0 – Testbericht

**Geprüft:** Manager 1.4.0, Popup 3.3.1 und Card 2.7.0 (unverändert).

| Prüfung | Ergebnis |
| --- | --- |
| `release-check.sh` (Versionen, Python-Syntax, alle Unit-Tests, JS-Syntax, Generator-Tests) | bestanden |
| Neue Unit-Tests `test_anlage_140.py` (Codecs mit Vorlagen, Import, Validierung, Prüfbericht mit den Fehlern vom 16.10., bereinigter Aufbau ohne Rot) | 12/12 |
| Neue Backend-Tests `test_anlage_app_140.py` (Vorschlag speichert nichts, Speichern mit Versionsschutz, Prüfbericht, Export/Import) | 4/4 |
| Bestehende Tests 1.3.x | unverändert grün |
| Chromium mit echtem Manager-Server, simuliertem SIP Core und go2rtc: Prüfbericht, Übernehmen, Bearbeiten, Wege, Speichern | ohne Skriptfehler |

**Nicht geprüft:** echte Asterisk-, SIP-Core- und go2rtc-Instanz; AMI-Live-Codecs nur per Unit-Test des Parsers.
