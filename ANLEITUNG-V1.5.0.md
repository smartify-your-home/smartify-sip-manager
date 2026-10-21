# Smartify SIP Manager 1.5.0 – Erzeugen & Übernehmen, Kameras finden

## Installation
1. Ordner `smartify_sip_manager` ersetzen, Add-on **neu erstellen** (neue Dateien und `hassio_api`).
2. Empfohlen: AMI-Zugang in den App-Optionen eintragen (Live-Codecs, `pjsip reload`).

## Ablauf
1. **Start → Anlage & Teilnehmer → Aus bestehender Konfiguration übernehmen.** RTSP-Kameras aus go2rtc kommen automatisch mit (Passwort sicher im Manager).
2. Fähigkeiten setzen: **iOS** bei iPhone/iPad, **Video** bei Teilnehmern, die Video im SIP-Anruf senden.
3. Weitere Kameras: **Kameras finden → Netzwerk durchsuchen**, Benutzer/Passwort eintragen, **Testen**, **Übernehmen**.
4. **Speichern**.
5. **Erzeugen & Übernehmen → Vorschau erzeugen**, Aktionen und Unterschiede ansehen, Ziele auswählen, **Übernehmen**.
6. **Prüfbericht → Neu prüfen**, App auf den Geräten neu laden.

## Wichtig zu HA-Geräten (z. B. iPad 104)
Endpoints der SIP-Core-Benutzer erzeugt das Asterisk-Add-on selbst. Der Manager legt sie nicht doppelt an. Für Video:
- im Asterisk-Add-on Video aktivieren (falls die Option angeboten wird; der Prüfbericht zeigt die Add-on-Optionen), **oder**
- die automatische Erzeugung im Asterisk-Add-on abschalten und erneut „Erzeugen & Übernehmen“ – dann legt der Manager den Endpoint mit Video-Codecs an.

## Sicherheit
- Asterisk schreibt nur in `custom/pjsip_custom.conf`, Backup unter `custom/.smartify-backups`.
- go2rtc: Backup unter `/data/backups/go2rtc_*.yaml`; Kommentare in der go2rtc-Datei gehen verloren.
- SIP Core: Backup wie bisher, Übernahme über den Options-Flow.
- Netzsuche nur in privaten Netzen, nur auf Knopfdruck.
