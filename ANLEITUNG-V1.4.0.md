# Smartify SIP Manager 1.4.0 – Prüfbericht und Anlagen-Modell

## Installation
1. Ordner `smartify_sip_manager` in dein lokales Add-on-Repository kopieren (ersetzt 1.3.7).
2. In Home Assistant: **Add-on aktualisieren / neu erstellen** (nicht nur neu starten – neue Dateien im Image).
3. Popup und Card bleiben unverändert (3.3.1 / 2.7.0).

## Erste Schritte
1. **Start → Anlage & Teilnehmer** öffnen.
2. **Aus bestehender Konfiguration übernehmen** klicken. Der Manager liest SIP Core, Asterisk, Popup und go2rtc.
3. Tabelle prüfen:
   - **Typ** jeder Zeile (HA-Gerät, SIP-Telefon, Türstation, Kamera ohne SIP, externer Anschluss).
   - **iOS** bei iPhone/iPad ankreuzen (der Import erkennt das nur, wenn bereits WebRTC eingestellt ist).
   - **Video** bei Teilnehmern, die Video im SIP-Anruf senden sollen (z. B. iPad → Linphone).
4. Anlagendaten ergänzen, besonders die **go2rtc-HTTPS-Adresse** (z. B. `https://homeassistant.example-tailnet.ts.net:8443`).
5. **Speichern**, dann **Start → Prüfbericht → Neu prüfen**.

## Was der Prüfbericht bei der Anlage vom 16.10. gezeigt hätte
- Rot: 104 soll Video senden, Endpoint erlaubt nur Audio → Video-Option im Asterisk-Add-on.
- Rot: `sip_video: false` in SIP Core.
- Rot: keine HTTPS-Adresse für go2rtc / CORS fehlt.
- Gelb: Stream `ipad_gang` hat keinen Sender (Browser-ID „iPad Gang“ statt `ipad_gang`).
- Gelb: Wiedergabe MSE, obwohl iOS-Geräte vorhanden sind.

## Hinweise
- AMI in den App-Optionen eintragen, dann prüft der Bericht Codecs live und meldet nicht angemeldete Geräte.
- Export je Kunde: **Exportieren (je Kunde)**; Import ersetzt das Modell (Backup in `/data/backups`).
- Nichts in 1.4.0 schreibt Asterisk, SIP Core oder go2rtc – das kommt mit 1.5.
