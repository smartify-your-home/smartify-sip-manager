# Smartify SIP Manager – Add-on-Dokumentation (1.19.40)

Der **Smartify SIP Manager** ist die Home-Assistant-App für Asterisk/PJSIP, SIP Core, Rufgruppen, Türstationen und RTSP/go2rtc. Installation und Updates der App erfolgen im **Home-Assistant-App-Store**, nicht über HACS. HACS installiert ausschließlich die optionalen Dashboard-Karten.

## Schnellstart und Konfigurationsübernahme

1. Asterisk-/Home-Assistant-Backup erstellen; App installieren, starten und über die Seitenleiste öffnen.
2. Unter **Teilnehmer** Nebenstellen, Berechtigungen, Video-Codecs, Klingeltöne, Browser Mod und OPTIONS pflegen.
3. **Speichern** sichert das Anlagenmodell. Asterisk-relevante Änderungen anschließend über **Änderungen laden / Erzeugen & Übernehmen** in der Vorschau prüfen und übernehmen; Asterisk bei Bedarf neu laden.
4. Bei Problemen unter **System & Expertenwerkzeuge → Live-Status (AMI)** die Verbindung und Kontaktliste prüfen.

## Teilnehmer: OPTIONS und Browser Mod

**OPTIONS (s)** im Teilnehmerbereich steuert `qualify_frequency` pro Nebenstelle: **leer** = bestehenden AoR-Wert beibehalten; **0** = deaktivieren; **30** = alle 30 Sekunden prüfen (zulässig 0–3600). Diese Einstellung braucht die Übernahme nach Asterisk. Der Generator ergänzt erforderlichenfalls auch einen Default-AoR per `(+type=aor)`.

Die **Browser-Mod-Visibility-Entity** (z. B. `sensor.ipad_gang_browser_visibility`) wird dagegen **einmal zentral im Manager** gespeichert. Sie gilt dadurch auf allen Endgeräten; ein Asterisk-Reload ist dafür nicht nötig. Im HA-Sensor `sensor.smartify_sip_teilnehmer` werden `browser_mod_entities`, `participants`, `call_rules` und `updated` veröffentlicht.

## SIP Calling Card

Die Dashboard-Karte zeigt erreichbare und ungeprüfte Kontakte sowie Browser-Mod-Status. **Eigene Nebenstelle** wird unter ⚙ ausgewählt, oben als grün/rot/gelber Punkt angezeigt und aus der Kontaktliste ausgeblendet. Grün bedeutet von Asterisk bestätigt erreichbar, rot ausdrücklich nicht erreichbar, gelb ungeprüft oder veraltete Statusdaten. Die Meldung „AMI verbunden“ wurde aus dem Kopf entfernt; bei Störungen bleibt „Daten veraltet“ sichtbar.

Im Bearbeitungsmodus gibt es Drag & Drop, Anzeige-/Entfernen-Schaltflächen, Schriftgröße **11–24 px** und Hörergröße **24–50 px**. Die Zeilenhöhe passt sich an. Der Anrufknopf setzt die installierte SIP-Core-Komponente `custom:sip-call-button` voraus. Für laut Manager-Anrufregeln gesperrte Kontakte erscheint **⛔** statt eines Hörers. Regeln werden in beide Richtungen (`anruf_ziele`, `angerufen_von`) geprüft.

**Zentral:** Browser-Mod-Zuordnungen und Anrufregeln. **Nur im jeweiligen Browser gespeichert:** eigene Nebenstelle, Reihenfolge, Größen, lokale Anzeigenamen. Eine native YAML-Variante ohne eigene Smartify-JS-Ressource wurde diskutiert, aber **noch nicht ausgeliefert**.

## Kontakte und Asterisk-Status

`Reachable` = OPTIONS bestätigt erreichbar; `Unreachable` = ausdrücklich unerreichbar; `NonQualified`/`Unknown` = **gelb, nicht automatisch offline**. Bei `qualify_frequency=0` erfolgt keine regelmäßige OPTIONS-Abfrage. Werden in der Karte **0 Kontakte** angezeigt, PJSIP in Asterisk mit `pjsip show contacts` prüfen und mit der AMI-Diagnose vergleichen. Ein grüner Status garantiert nicht, dass Video/Audio/NAT oder Rufgruppen funktionieren.

## Installation des Frontends und Cache

Es gibt zwei Installationswege für das Frontend: **HACS-Dashboard** mit `smartify-sip-manager.js` oder manuelle Ressource `/local/smartify/smartify-sip-manager.js?v=1.19.40`. **Nie beide gleichzeitig registrieren**, sonst drohen doppelte Custom-Elemente und Versionskonflikte. App und HACS getrennt aktualisieren. Nach einem Update Dashboard/Companion-WebView vollständig neu laden; ggf. Ressourcen-URL mit neuer Versionskennung versehen.

## Sicherheit und Grenzen

Vor Änderungen an PJSIP und Dialplan Vorschau und Backup prüfen. SIP-/AMI-Passwörter nicht in die Dashboard-Konfiguration eintragen. Eine AMI-Verbindung ist nur ein Verwaltungsstatus, kein garantierter Audio-/Videoerfolg. Der zentrale Klingelton-Router über AMI/HA-Mediaplayer muss je Installation geprüft werden; der SIP-Core-Rufton wird nicht automatisch unterdrückt.

Weitere Hinweise: [Calling Card](../docs/SIP-CALLING-CARD.md), [Repository-Übersicht](../README.md).


## Geführter Einrichtungsassistent (Entwicklungsstand)

Über **Einrichtungsassistent** in der oberen Aktionsleiste können vier Abläufe gestartet werden:
Home Assistant/System, Teilnehmer, Cloud-/externe SIP-Konten und Rufgruppen.
Jeder Ablauf führt schrittweise in die **bestehenden, voll funktionsfähigen Editoren**.
Dadurch werden vorhandene Einstellungen nicht durch einen zweiten Datenbestand ersetzt.

**Wichtig:** Diese erste Implementierung ist ein geführter Navigationsassistent, noch
kein vollständig integrierter Formularassistent. Die Teilnehmer- oder Gruppenauswahl
und die eigentlichen Änderungen erfolgen weiterhin in den bestehenden Editoren.
Der Assistent speichert und überschreibt nichts automatisch. Vorschau, Backup,
Speichern, Übernahme und Reload bleiben explizite Aktionen.

Für die vollständige Integration sind noch erforderlich: vorbefüllte gezielte
Teilnehmer-/Gruppenbearbeitung innerhalb eines einheitlichen Formulars, Validierung
über alle Editoren hinweg, gruppen- und teilnehmerbezogene Änderungsvorschau,
durchgängige Cloud-Account-Tests sowie automatisierte End-to-End-Tests.
