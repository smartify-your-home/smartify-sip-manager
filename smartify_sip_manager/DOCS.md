# Smartify SIP Manager v1.19.18

Die Home-Assistant-App für **Asterisk/PJSIP, SIP Core, Rufgruppen, RTSP-Kameras und go2rtc**. Die Oberfläche ist per Home-Assistant-Ingress erreichbar.

## Frontend automatisch mitinstallieren

Bei Start und nach jedem Update der Smartify-App werden diese Dateien nach `/homeassistant/www/smartify/` kopiert: `smartify-doorstation-card.js`, `smartify-doorstation-popup.js` und das gemeinsame Bundle `smartify-sip-manager.js`.

**Einmalige Registrierung:** Home Assistant → Einstellungen → Dashboards → Ressourcen → Ressource hinzufügen:
- URL: `/local/smartify/smartify-sip-manager.js?v=1.19.4`
- Typ: **JavaScript-Modul**

Nur das gemeinsame Bundle registrieren, **nicht** alle drei Dateien. Wenn die HACS-Ressource `/hacsfiles/Smartify-SIP-Manager/smartify-sip-manager.js` bereits eingetragen ist, diese vor der manuellen Registrierung deaktivieren/entfernen – sonst würden identische Custom Elements doppelt geladen.

Bei Updates wird die Datei automatisch ersetzt. Der Browser kann sie zwischenspeichern: Bei Bedarf die Versionskennung `?v=...` in der Ressourcen-URL aktualisieren und den Frontend-Cache neu laden. Der Installer bearbeitet keine `.storage`-Dateien und registriert Ressourcen aus Sicherheitsgründen nicht eigenmächtig.

## Erstinstallation

1. Backup deiner bestehenden Asterisk-/SIP-Core-Dateien sowie Smartify-Daten anlegen.
2. App installieren und die Optionen prüfen: `asterisk_slug`, `ami_host` (standardmäßig `auto`), `ami_port`, `ami_username`, `ami_password`, `go2rtc_url`.
3. Sicherstellen, dass der Asterisk-Konfigurationsordner über `/addon_configs` im Container sichtbar und der AMI-Dienst vom Manager erreichbar ist.
4. App starten und in der Seitenleiste **Smartify SIP** öffnen.
5. Die Status- und Diagnoseanzeigen verwenden, dann bei Bedarf Anlagen-Modell und Zuordnungen übernehmen.

**AMI-Hinweis:** `ami_host: auto` verwendet den aus `asterisk_slug` abgeleiteten HA-internen Add-on-Hostnamen (Unterstriche werden Bindestriche). Auch alte `127.0.0.1`-Werte werden automatisch so aufgelöst. Ein ausdrücklich eingetragener anderer Host überschreibt die Automatik. AMI nur intern freigeben.

**Umstieg vom lokalen Add-on:** Ein Repository-Add-on hat meist eine andere vollständige Add-on-ID. Private Daten unter `/data` werden nicht automatisch migriert. Vorher exportieren/sichern, nachher importieren bzw. Konfiguration kontrollieren.

## Bedienen und Aktualisieren

- Unter **Asterisk** Nebenstellen, externe Eingänge, PJSIP-Dateien und Rufgruppen bearbeiten.
- Unter **SIP Core** Teilnehmer, Popup- und Kamera-Konfiguration im Entwurf vorbereiten.
- Unter **Werkzeuge** Vorschau, Diagnose, Sicherungen und Logs verwenden.
- Vor jeder Änderung Backup, Diff und Bestätigung prüfen. Änderungen erst mit explizitem Speichern und danach nötigen Reloads aktivieren.
- Updates der **App** erfolgen über den Home-Assistant-App-Store, nicht über HACS.

## Erreichbarkeit einschränken

Unter **Anlage → Teilnehmer** lässt sich pro Teilnehmer (aufklappbar in der Spalte „HA-Benutzer / Endpoint“) festlegen, wer wen anrufen darf:

- **darf nur anrufen** (SIP-Telefon, HA-Gerät, Türstation): nur die angehakten Nummern sind wählbar.
- **darf nur angerufen werden von** bzw. **direkt über Asterisk anrufbar nur von**: nur die angehakten lokalen Teilnehmer dürfen die Nummer direkt wählen.

Ohne Haken gilt keine Einschränkung; ein Haken ohne Auswahl sperrt komplett. Der Manager erzeugt dafür Dialplan-Einträge mit Prüfung (abgewiesen: `Hangup(21)`). **Grenzen:** Es werden nur dem Manager bekannte Nummern geprüft (Teilnehmer, Rufgruppen, Cloud-Direktwahl). Eigene Dialplan-Einträge und Muster, Rufgruppen-Zustellung an Mitglieder und Cloud-zu-Cloud-Gespräche zwischen Linphone-Konten bleiben unberührt; vorhandene eigene Einträge derselben Nummer werden nicht überschrieben, sondern gemeldet.

Für Card/Popup sind separate Frontend-Ressourcen nötig. Installationsweg über HACS (Dashboard) siehe [Repository-README](https://github.com/smartify-your-home/Smartify-SIP-Manager#installation-von-doorstation-card--popup-mit-hacs).

**Achtung:** Das Add-on hat Schreibzugriff auf `/addon_configs` (Konfigurationsordner aller Apps). Nur in vertrauenswürdigen Installationen verwenden. Die App ist für administrative Benutzer bestimmt.

## Individuelle Video-Codecs (Version 1.19.18)

Unter **Teilnehmer → Teilnehmer** lässt sich direkt neben **Video SIP** pro Nebenstelle `Automatisch`, `Nur VP8`, `Nur H.264`, `Nur VP9`, `VP8 + H.264` oder `Kein Video` wählen. Für Samsung S10 (103) `Nur VP8` auswählen und **Video SIP** aktivieren. Audio-Codecs bleiben erhalten. Einstellungen werden im Anlagenmodell gespeichert und beim Generieren verwalteter PJSIP-Endpoints als `disallow=all` / `allow=...` ausgegeben.

**Grenze:** Wird die Nebenstelle vom Asterisk-Add-on selbst in `default/` erzeugt (z. B. aus `sipjs-phone-endpoint`), verändert der Manager sie bewusst nicht. Die Vorschau zeigt dann eine Warnung; die Codec-Auswahl wird für diese Nebenstelle **nicht wirksam**. Erst die Default-Endpoint-Erzeugung bzw. eine unterstützte Override-Methode muss angepasst werden. Kein stillschweigendes Überschreiben von `pjsip_default.conf`.
