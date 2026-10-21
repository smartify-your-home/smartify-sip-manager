# Smartify SIP Manager 1.3.7 – Testbericht

**Geprüfte Komponenten:** Manager 1.3.7, Popup 3.3.1 und Card 2.7.0 (letztere beiden unverändert).

- **69 Python-Unit-/Regressionstests bestanden**, darunter 10 gezielte Eingangsroute-Tests.
- **5 JavaScript-Generator-Tests bestanden**, JavaScript-Syntax geprüft.
- **7 Chromium-UI-Tests bestanden**, einschließlich neuem Linphone-Eingang mit zwei Quell-IPs, zwei erlaubten Zielen und dem Speichern-Dialog.
- Beispielkonfiguration: bestehender `linphone-in` mit `match=100.64.10.20/32`, Dialplan-Ziel 104, zusätzliche IP/Ziel 100. Die Tests zeigen, dass der bestehende `[linphone-cloud]`-Ausgang, `[default]` und `[parkedcallstimeout]` unverändert bleiben.
- Schutztests: ungültige/weite CIDR-Netze, unbekannte Ziele, doppelte Nummern/IPs, veraltete Datei-Hashes, Überschneidungen mit anderen `identify`-Regeln, unbekannte Dialplan-Schritte, Bestätigung und Rollback bei Fehler der zweiten Datei.
- **Dockerfile kontrolliert:** `inbound_routes.py` wird durch COPY eingebaut. Docker-Image wurde nicht tatsächlich gebaut.

**Grenzen:** Kein Zugriff auf deine laufende Asterisk-/SIP-Core-/Tailscale-Installation und keine Bestätigung realer Audio-/SIP-Anrufe. Der Parser ersetzt nur einfache, eindeutig erkannte Einträge. Die Speicherung schreibt zwei einzelne Dateien mit Backup und Rücksetzversuch im Fehlerfall; sie ist keine vollständig transaktionale Dateisystem-Operation. Asterisk wird nicht automatisch neu geladen.
