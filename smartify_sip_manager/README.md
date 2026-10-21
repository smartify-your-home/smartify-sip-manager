# Smartify SIP Manager 1.18.0

Der Manager ist nach dem tatsächlichen Einrichtungsablauf gegliedert:

1. **Asterisk:** Nebenstellen und unter „Externe SIP-Eingänge“ konfigurierbare IP-basierte Direktanrufe (ein oder mehrere externe Geräte → auswählbare vorhandene interne Nebenstellen). Gemeinsame Nummern-/Endpunktübersicht inklusive Rufgruppen sehen. Einfache Custom-AOR/Auth/Endpoint-Einträge in deren tatsächlicher Custom-Quelldatei bearbeiten oder nach Referenzprüfung mit Backup löschen.
2. **SIP Core:** Aktive SIP-Core-Konfiguration lesen, bestehende Teilnehmer anzeigen, neue Teilnehmer **nur aus Asterisk-Nebenstellen** auswählen und im YAML-Entwurf bearbeiten. Untermenüs für Anrufer-Kameras, RTSP/go2rtc, Popup und Doorstation Card.
3. **Rufgruppen:** Dialplan-Einträge aus `extensions.conf` und `extensions_custom.conf` anzeigen, die wirklichen Dialplan-Schritte anzeigen, einfache Rufgruppen als Tabellenzeile bearbeiten und in eine vorhandene Custom-Datei speichern.
4. **Werkzeuge:** Datei-Editor, Live-Status/AMI, Diagnose, Sicherung, Logs und Anleitungen.

## PJSIP-Nebenstellen konfigurieren

Unter **Asterisk → Vorhandene & neue Nebenstellen** können AOR-Parameter (z. B. `max_contacts`, `remove_existing`, `remove_unavailable`, `qualify_frequency` und Registrierungszeiten), Login, Kontext, Transport, Codecs, DTMF sowie NAT-/RTP-Werte eingestellt werden. „1 Gerät“ und „mehrere Geräte“ sind wählbare Ausgangswerte, keine unveränderlichen Festlegungen.

Tabellarisches Speichern ändert ausschließlich die geprüfte Custom-Datei, mit Konflikterkennung und Backup. Unbekannte/komplexe Abschnitte werden nicht automatisch überschrieben. Jede Änderung an einem Eingabefeld der Expertenmaske verwirft die bisherige Vorschau. Vor Übernahme in den Datei-Editor wird die Nummernbelegung erneut eingelesen. Die Konfiguration wird erst nach explizitem Speichern und einem manuellen Reload wirksam. Für Codec- und Transportoptionen muss Asterisk entsprechend vorbereitet sein.

## Datenquellen und Grenzen

Die Belegungsanzeige verwendet die zugänglichen Asterisk-`.conf`-Dateien und, falls erreichbar, die aktive SIP-Core-Konfiguration. Nicht erkannte Nummern sind **nicht garantiert frei**: Asterisk kann über Includes, Muster, dynamische Konfigurationen und andere Kontexte weitere Ziele besitzen. Gruppen werden heuristisch aus Dialplan-Zielen mit parallelen `Dial`-Zielen oder einer Gruppenbezeichnung erkannt; andere numerische Ziele bleiben sichtbar.

## Sicherheit

In der Tabellenansicht können Änderungen mit Bestätigung direkt in Custom-Dateien geschrieben werden. Ein Reload erfolgt nur nach zusätzlicher Bestätigung über AMI. Keine automatische Änderung an Asterisk beim Generieren. „In Datei vorbereiten“ füllt nur den Editor; gespeichert wird erst nach ausdrücklicher Bestätigung und Backup. Änderungen werden erst nach einem bewusst ausgeführten passenden Reload wirksam. Der SIP-Core-Entwurf verändert die laufende Integration erst nach Validierung, Diff und ausdrücklicher Bestätigung mit Backup. Ein neues SIP-Core-Passwort muss zur PJSIP-Anmeldung passen. Es wird keine Mindestlänge von 12 Zeichen erzwungen; kurze Passwörter werden weiterhin als schwach gewarnt. In Listen erscheinen keine Passwörter; im vollständigen YAML-Editor sind sie potenziell sichtbar.

## Kompatibilität

Basis ist Smartify SIP Manager 1.2.1. Mitgeliefert werden die unveränderten Frontend-Komponenten Popup 3.3.1 und Card 2.7.0. Vorhandene Kamera-Zuordnungen, SIP-Core-Entwürfe und Asterisk-Dateien werden nicht beim Start überschrieben. Mehr unter `CHANGELOG.md` und der [Repository-README](../README.md).

## Neues in 1.3.3

Einfach strukturierte Linphone-Cloud-Ziele und gemischte Parallelrufe (z. B. 109 und 600) sind direkt in Tabellenzellen änderbar. NoOp-Beschreibung, lokale und externe Ziele sowie Zeitlimit werden getrennt dargestellt. Für AOR/Auth/Endpoint gibt es erweiterte Parameterzellen, außerdem eine gesonderte Tabelle für ausgehende PJSIP-Endpoints ohne AOR/Auth (z. B. `linphone-cloud`). Nicht unterstützte komplexe Abschnitte bleiben im Rohdatei-Editor.


### Manager-Theme und API

Ab 1.3.4 ist Hell die Standardeinstellung (Calibri, schwarzer Text auf hellgrauem Hintergrund). Im Kopfbereich kann Dunkel gewählt werden; die Auswahl wird nur im lokalen Browser gespeichert. Die separate SIP-Core-Popup-Theme-Einstellung ist davon unabhängig.

Für SIP Core benötigt der Manager einen vom Supervisor bereitgestellten `SUPERVISOR_TOKEN`. Das neue Docker-Basisimage und `/run.sh` mit `with-contenv` benötigen einen **vollständigen Add-on-Neubau**. Wird der Token nach dem Neubau weiterhin vermisst, unter Werkzeuge die API-Verfügbarkeit prüfen und die Home-Assistant-Add-on-Logs kontrollieren, keine Tokens manuell in Felder eintragen.

## Neu 1.5.0: Erzeugen & Übernehmen, Kameras finden

Aus dem Anlagen-Modell erzeugt der Manager Asterisk (verwalteter Block), SIP Core und go2rtc – erst Vorschau, dann Übernahme mit Backup. RTSP-Kameras werden aus go2rtc übernommen oder per Netzsuche gefunden, getestet und ins Modell gelegt.

## Neu 1.4.0: Prüfbericht und Anlagen-Modell

Die Startseite zeigt einen **Prüfbericht**, der Asterisk, SIP Core, go2rtc und das Popup gegeneinander prüft. Grundlage ist das **Anlagen-Modell** unter *Start → Anlage & Teilnehmer*: einmal „Aus bestehender Konfiguration übernehmen“, Typ und Fähigkeiten prüfen (vor allem „iOS-Gerät“ und „Video im Anruf“), speichern. In 1.4.0 wird nur das Modell gespeichert, keine anderen Dateien. Export/Import je Kunde über dieselbe Seite.

## Neu 1.3.7: Eingehende Linphone-/Tailscale-Anrufe

Unter **Asterisk → Externe SIP-Eingänge** werden beispielsweise die bereits vorhandenen Abschnitte `[linphone-in]` und `[linphone-in-identify]` aus Custom-PJSIP und der Kontext `[linphone-in]` aus `extensions.conf` eingelesen. Du kannst dort die Quell-IP-Adressen der externen Linphone-Geräte und eine oder mehrere erlaubte Asterisk-Nebenstellen auswählen. Für jede ausgewählte Durchwahl wird eine eigene `exten => …`-Regel erzeugt. Das Ziel ist `sip:NUMMER@TAILSCALE-IP-DEINES-ASTERISK`.

Achtung: Die IP-Identifikation authentifiziert kein Linphone-Cloud-Passwort; Zugriff nur für bestätigte Tailnet-Geräte freigeben, Tailnet-ACLs einschränken und nicht pauschal das gesamte Tailnet/IP-Netz zulassen. Es werden ausschließlich einzelne Quell-IPs akzeptiert, keine CIDR-Subnetze. Der ausgehende `[linphone-cloud]`-Endpoint bleibt separat und wird nicht verändert.

Beide Custom-Dateien müssen bereits angelegt und für Asterisk eingebunden sein. Die Speicherung erstellt Backups und prüft Versionskennungen; sie führt **keinen** automatischen Asterisk-Reload aus. Nach Änderungen Asterisk über den im Add-on verfügbaren vorgesehenen Weg kontrolliert neu laden oder das TECH7Fox-Add-on in Home Assistant neu starten (aktive Gespräche werden dabei unterbrochen).
