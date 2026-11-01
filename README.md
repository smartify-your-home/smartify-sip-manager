# Smartify SIP Manager

**SIP-Core-Passwort anzeigen (Feature-Branch):** Im Assistenten unter „Passwörter verwalten“ kann das vorhandene Passwort einer einzelnen SIP-Core-Nebenstelle über das Augensymbol nach ausdrücklicher Bestätigung kurz angezeigt und wieder verborgen werden, auch wenn es ursprünglich manuell konfiguriert wurde. Der normale Teilnehmerlistenabruf enthält weiterhin keine Passwörter; das Reveal erfolgt gezielt über eine nur im Add-on-Ingress erreichbare POST-Aktion. Auf gemeinsam genutzten Geräten nur bei geschütztem Bildschirm verwenden. Nicht lesbare oder fehlende Zugangsdaten können weiterhin nur neu gesetzt werden.


**Assistent-Farben & Passwortimport (noch nicht veröffentlicht):** Der Assistent verwendet jetzt die lokalen Hell-/Dunkel-Theme-Farbvariablen des Managers, einschließlich Eingaben, Buttons, Hinweisen und Fehlern. Die Passwortverwaltung übernimmt eindeutige vorhandene Asterisk-PJSIP-Auth-Datensätze auch dann zur **Passwortrotation**, wenn der ganze Teilnehmer wegen zusätzlicher AOR-/Endpoint-Optionen nicht im Standardformular bearbeitbar ist. Die bestehende Passwortzeile wird nur nach Bestätigung und Backup in ihrer Datei geändert; übrige Optionen bleiben erhalten. Mehrdeutige, duplizierte oder vorlagenbasierte Auth-Datensätze bleiben gesperrt. Vorhandene Passwörter werden weder angezeigt noch entschlüsselt. Nach Änderungen PJSIP bewusst neu laden und Clients aktualisieren.


**Einheitliche Übernahme im Assistenten:** In den letzten Schritten von Home Assistant & System, SIP-Teilnehmer, Cloud-Konto und Türstation gibt es jetzt „Erzeugen & Übernehmen …“. Der Knopf validiert und speichert zuerst das Anlagenmodell, danach wird der unveränderte Originalbereich „Erzeugen & Übernehmen“ im selben Dialog angezeigt. Dort müssen die betroffenen Ziele anhand der Vorschau ausgewählt und die Übernahme separat bestätigt werden. SIP-Core-Auto-Answer und Passwortverwaltung nutzen ihre eigenen gesicherten Übernahmewege; kein automatischer Reload ohne bewusste Entscheidung.


Im grafischen Rufgruppen-Manager **innerhalb des Einrichtungsassistenten** steht jetzt „Erzeugen & Übernehmen …“. Der Knopf speichert zunächst eventuelle Modelländerungen und zeigt danach direkt darunter die bestehende vollständige Vorschau mit auswählbaren Konfigurationszielen. Die Übernahme selbst erfordert weiterhin die separate Bestätigung und erstellt Backups; es findet keine automatische, ungeprüfte Übernahme statt. Beim Schließen kehren beide originalen Manager-Oberflächen an ihre Stelle zurück.


**Auto Answer direkt im Assistenten (ab 1.19.48):** Bei einem vorhandenen SIP-Core-Teilnehmer (`HA-Gerät`) erscheint im zweiten Schritt eine Auto-Answer-Checkbox mit auswählbaren erlaubten SIP-Core-Anrufern. „Änderung prüfen“ nutzt die vorhandene SIP-Core-Stage-/Diff-API; „Geprüfte Regel in SIP Core übernehmen“ verlangt eine ausdrückliche Bestätigung und nutzt Backup, Versionsprüfung und Verifikation des vorhandenen SIP-Core-Übernahmemechanismus. Unbekannte Rufnummern oder die eigene Nebenstelle werden nicht freigegeben; globales Auto Answer wird deaktiviert. SIP-Telefon, Türstation und Cloud sehen dieses Feld nicht. Für neue Teilnehmer muss zuerst ein SIP-Core-Benutzer eingerichtet sein.


**Rufgruppen im Assistenten:** Der Assistent zeigt jetzt den **originalen grafischen Rufgruppen-Manager direkt im Assistentenfenster**. Drag-and-drop und Antippen auf Mobilgeräten, neue Gruppen, Teilnehmerzuordnungen und Speichern sind dieselben Funktionen wie im Hauptmanager; die Originaloberfläche wird beim Schließen zurück an ihre vorherige Stelle gesetzt. Es ist **keine Weiterleitung** und keine zweite, abweichende Implementierung. Die eigentliche Asterisk-Übernahme bleibt ein separater bestätigter Schritt.


**Kontextabhängige Felder (ab 1.19.48):** Bei Cloud-Zielen erscheinen nur SIP-Adresse/Provider, eingehender und ausgehender Anschluss, Video-Codecs und optionale Quell-IPs. Browser Mod, lokaler Klingelton, HA-Stream, lokale OPTIONS-Erreichbarkeitsprüfung und Türöffner werden nicht angeboten. Bei SIP-Telefonen bleiben Endpoint, Codecs und OPTIONS; bei HA/SIP-Core-Teilnehmern zusätzlich Browser Mod und lokale Klingeltonausgabe; bei Türstationen Tür/Licht/Klingel und Kamerabild. Bereits gespeicherte, ausgeblendete Felder werden beim Bearbeiten nicht gelöscht.


**Linphone-Cloud-Vorlage (noch nicht veröffentlicht):** Im Assistenten unter „Cloud-Konto“ den Anbieter **Linphone** auswählen und nur den vorhandenen Linphone-Benutzernamen eingeben. Daraus wird die SIP-Adresse `benutzername@sip.linphone.org` gebildet. Für neue Einträge werden `linphone-cloud` (ausgehender Endpoint) und `linphone-in` (eingehender Anschluss) vorausgefüllt, bleiben aber im nächsten Schritt bearbeitbar. Andere Anbieter können mit „Manuell“ eingerichtet werden. Die Vorlage erstellt kein Konto beim Anbieter, hinterlegt kein Anbieter-Passwort und ersetzt nicht die gesonderte Einrichtung der Asterisk-Verbindungen.


**Version 1.19.48:** Im Einrichtungsassistenten bietet „Passwörter verwalten“ die Auswahl einzelner oder mehrerer SIP-Core- und bearbeitbarer PJSIP-Teilnehmer. Sichere Passworterzeugung, Bestätigung, Backup und Versionsprüfung sind eingebaut. SIP Core und PJSIP werden getrennt übernommen; der PJSIP-Reload erfolgt bewusst danach. Cloud-Passwörter können nicht beim externen SIP-Anbieter geändert werden. Bestehende SIP-Clients müssen neu konfiguriert werden.


Der Einrichtungsassistent verlinkt jetzt kontextabhängig zu den bestehenden Editoren für SIP Core (Benutzer und Auto Answer), PJSIP (AOR, Authentifizierung, Codecs und weitere Expertenoptionen), Cloud-SIP-Eingänge, Türstation, Anrufrechte, Live-Status sowie Vorschau und Übernahme. Diese Werkzeuge öffnen sich im jeweiligen Manager-Bereich; Änderungen werden nicht automatisch übernommen. Passwortwechsel und insbesondere ein gemeinsamer Passwortwechsel für mehrere Teilnehmer sind **noch nicht im Assistenten umgesetzt**. Die Konfigurationsbearbeitung bleibt auf die bewährten bestehenden Manager-Funktionen verteilt.


Im Einrichtungsassistenten bieten **HA-Benutzer, Stream, Browser-Mod-Status, Türöffner, Licht, Klingel und Klingelton-Mediaplayer** kontextabhängige Vorschläge aus der vorhandenen Home-Assistant-/Anlagen-Auswahl. Die Entitätslisten sind nach passender Domain bzw. Funktion gefiltert; Freitexteingabe bleibt möglich, falls eine HA-Entität noch nicht erfasst wurde. Bei nicht verfügbarer HA-API werden keine erfundenen Vorschläge angezeigt.


**OPTIONS – Erreichbarkeitsprüfung:** Neue Teilnehmer erhalten standardmäßig **30 s**. **0 s = deaktiviert**. Bei bestehenden Teilnehmern bleiben gespeicherte Werte erhalten; leer bedeutet, dass Asterisk seinen bisherigen Wert behält.


## Einrichtungsassistent (PR #27 – Beta-Testversion 1.19.48)

Der Button **✨ Einrichtungsassistent** im Manager öffnet vier Bereiche: Home Assistant & System, SIP-Teilnehmer, Cloud-Konto / externes SIP-Ziel und Rufgruppe. Im Assistenten kann ein **bestehender Teilnehmer oder eine vorhandene Rufgruppe ausgewählt und gezielt bearbeitet** oder ein neuer Eintrag erstellt werden. Der Assistent verwendet dasselbe Anlagenmodell wie die bisherigen Editoren, keine zusätzliche Konfigurationsdatei.

Teilnehmer: Nummer, Name, Typ, HA-Benutzer, Endpoint, Stream, Codec-Auswahl, SIP-OPTIONS-Frequenz, zentrale Browser-Mod-Statusentität, Realm und Anrufberechtigungen. Cloud-Teilnehmer: SIP-Adresse, Ausgangs-/Eingangsanschluss, Quell-IPs und Freigaben. Rufgruppen: Nummer, Name, Klingelzeit, Anrufer und Klingelziele. System: LAN-/Tailscale-/go2rtc-Parameter. Angaben werden schrittweise bearbeitet und **erst durch „Validieren & speichern“** an die vorhandene Servervalidierung übergeben.

**Sicherheitsgrenzen:** Das Modell wird vor dem Speichern erneut geladen und der Versions-Hash geprüft; fremde Änderungen werden nicht überschrieben. Ein vorhandener Teilnehmer behält nicht bearbeitete Felder. Weder SIP-Passwörter noch Asterisk-Dateien werden durch den Assistenten direkt geändert. **Nach Änderungen an Gruppen, SIP-Zugängen, Codecs oder Rechten im Bereich „Erzeugen & Übernehmen“ die Vorschau prüfen, Backup anlegen und separat übernehmen.** Schon geöffnete Editoren nach dem Speichern neu laden, damit sie keine veralteten Werte anzeigen.

**Noch offen vor produktiver Freigabe:** echte Cloud-Registrierungs- und Verbindungstests, automatisierte Browser-/End-to-End-Tests und Prüfung an einer realen Asterisk-/Home-Assistant-Installation. Die Beta dient dem Praxistest; die fehlenden Funktionen werden vor einer stabilen Freigabe ergänzt.


**Version 1.19.48** – Verwaltung von Asterisk/PJSIP, SIP Core, go2rtc und Türstations-Kameras in Home Assistant.

Dieses Repository enthält **zwei getrennt installierbare Teile**:

- **Home-Assistant-App (früher: Add-on)** `smartify_sip_manager/` – der eigentliche Smartify SIP Manager mit eigenem Python-Webserver und Ingress. **Installation und Aktualisierung über den Home-Assistant-App-Store**, nicht HACS.
- **HACS-Dashboard-Frontend** `dist/smartify-sip-manager.js` – stellt **Smartify Doorstation Card** und **Smartify Doorstation Popup** sowie die **Smartify SIP Calling Card** bereit. **Installation und Updates optional über HACS** (Typ *Dashboard*). Der Manager ist davon unabhängig.

> **Wichtig:** HACS kann keine Apps/Add-ons installieren. Das Dashboard-Bundle enthält ausschließlich die Frontend-Komponenten, nicht den Python-/Asterisk-Manager. Für den kompletten Funktionsumfang benötigt man die App und bei Verwendung der Doorstation-Oberfläche zusätzlich das Frontend.

## Aktueller Stand und Dokumentation (1.19.48)

**Verbindliche Hauptanleitungen:** [Add-on: DOCS.md](smartify_sip_manager/DOCS.md) und [Calling Card](docs/SIP-CALLING-CARD.md). Diese Dateien beschreiben die aktuellen Eingaben und trennen App-Store-/HACS-Updates.

- **OPTIONS pro Teilnehmer:** `qualify_frequency` unter Teilnehmer → OPTIONS (s), nach Speichern in Asterisk übernehmen; 0 = aus, 30 = 30 Sekunden.
- **Browser Mod:** Sichtbarkeitsentität einmal zentral unter Teilnehmer speichern; für alle Endgeräte gültig.
- **Calling Card:** eigene Nummer im Kopf als Statuspunkt (grün/rot/gelb), nicht in der Kontaktliste; Anrufrechte als ⛔; Hörergröße 24–50 px, Schriftgröße 11–24 px.
- **Status:** `NonQualified` und `Unknown` sind ungeprüft, nicht zwingend offline. Sensor `sensor.smartify_sip_teilnehmer` prüfen.
- **Native YAML-Karte:** derzeit noch nicht als vollständige Alternative ausgeliefert; SIP-Core-Telefonie benötigt dessen Frontend.
- **Cache:** niemals HACS- und /local-Bundle zugleich als Ressource laden.

## Installation des SIP Managers (Home Assistant OS / Supervised)

1. Ein aktuelles Home-Assistant-Backup erstellen (insbesondere Asterisk-Dateien, SIP-Core-Einstellungen und bisherige Smartify-Daten).
2. **Einstellungen → Apps (bzw. Add-ons) → App-Store → ⋮ → Repositories** öffnen und `https://github.com/smartify-your-home/Smartify-SIP-Manager` hinzufügen.
3. **Smartify SIP Manager** auswählen und installieren. Nach der Installation unter **Konfiguration** die Optionen prüfen; dann die App starten und über die Seitenleiste öffnen.
4. Bei Verwendung von Asterisk muss dessen Konfigurationsordner über die gemounteten App-Konfigurationen erreichbar sein. Den tatsächlichen Asterisk-Slug im Feld `asterisk_slug` überprüfen (der Vorgabewert ist nur ein Beispiel). Für AMI bei Bedarf den tatsächlichen Host/Port/Zugang eintragen. AMI vom Container erreichbar machen; `127.0.0.1` bezeichnet **den Manager-Container selbst**, nicht den Asterisk-Container.
5. Vor Änderungen an PJSIP/Dialplan oder SIP Core **Vorschau und Backups** verwenden und danach explizit speichern bzw. manuell reloaden.

**Achtung beim Umstieg von einer lokalen Installation:** Ein aus dem GitHub-Repository installiertes Add-on kann eine **andere vollständige Add-on-ID** als `/addons/local/smartify_sip_manager` erhalten. Es wird nicht automatisch über eine bestehende lokale Installation gelegt und übernimmt deren privaten `/data`-Inhalt nicht automatisch. Anlage/Kamera-Mapping vorher exportieren/sichern und in der neuen Installation wieder importieren bzw. anhand der bestehenden Konfiguration prüfen. Nicht beide Instanzen gleichzeitig konfigurieren lassen.

## Installation von Doorstation Card & Popup mit HACS

1. In HACS unter **⋮ → Benutzerdefinierte Repositories** die URL `https://github.com/smartify-your-home/Smartify-SIP-Manager` hinzufügen und als Typ **Dashboard** wählen.
2. **Smartify SIP Manager – Doorstation Frontend** installieren. HACS lädt die Datei `dist/smartify-sip-manager.js`; sie enthält **Doorstation Card, Popup und die SIP Calling Card**.
3. Die Dashboard-Ressource prüfen: `/hacsfiles/Smartify-SIP-Manager/smartify-sip-manager.js` (Typ **JavaScript-Modul**). HACS kann die Ressource je nach Konfiguration selbst hinzufügen.
4. **Alte Ressourcen** `/local/smartify-doorstation-card.js` und `/local/smartify-doorstation-popup.js` entfernen/deaktivieren, wenn dieselben Komponenten bereits manuell geladen werden. Keine doppelte Registrierung; Browser auf iPhone/iPad vollständig neu laden.
5. SIP Core und go2rtc separat installieren/konfigurieren; in SIP Core das Popup-Override `smartify-doorstation-popup` aktivieren. Die Dashboard-Card heißt `custom:smartify-doorstation-card`.

Beispiel-Karte:

```yaml
type: custom:smartify-doorstation-card
title: Haustüre
follow_sip_core: true
station_extension: "200"
stream: akuvox_s535
mode: mse
camera_mode: auto
show_sip: true
```

Das eigene SIP-Core-Popup wird über die SIP-Core-Option `popup_override_component: smartify-doorstation-popup` aktiviert. Detailliertes Kamera-Mapping, Beispiel-YAML und Voraussetzungen: [INSTALLATION-KAMERA-MAPPING.md](INSTALLATION-KAMERA-MAPPING.md).

## Funktionsumfang

- Asterisk/PJSIP: Nebenstellen, AOR/Auth/Endpoint, externe SIP-Eingänge, Rufgruppen und Dialplan-Analyse.
- SIP Core: bestehende Teilnehmer lesen, Konfiguration prüfen, Entwürfe und Kamera-Zuordnungen vorbereiten.
- go2rtc/RTSP: Streams anzeigen/testen, Kamera-Routing nach Anrufernummer.
- Werkzeuge: AMI-Status, Dateiverwaltung, Backup, Konfliktprüfung, Logs und Prüfbericht.

## Struktur

```text
Smartify-SIP-Manager/
├── repository.yaml                # Home-Assistant-App-Repository
├── hacs.json                      # HACS Dashboard-Metadaten
├── dist/
│   └── smartify-sip-manager.js    # HACS: Card + Popup als ein Bundle
├── frontend/                      # Versionierte Originaldateien der Frontend-Komponenten
│   ├── smartify-doorstation-card.js
│   └── smartify-doorstation-popup.js
├── smartify_sip_manager/
│   ├── config.yaml                # App-Version 1.19.21
│   ├── build.yaml
│   ├── Dockerfile
│   ├── run.sh
│   ├── DOCS.md                    # Beschreibung im App-Store
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── translations/
│   └── ...                        # Python/JS, Backend und Frontend
├── scripts/build-hacs-frontend.py
├── tests/
├── release-check.sh
└── INSTALLATION-KAMERA-MAPPING.md
```

## Sicherheit und Voraussetzungen

**Voraussetzungen:** Home Assistant OS bzw. Supervised mit Supervisor, ein erreichbares Asterisk-Add-on, SIP Core und ggf. go2rtc/WebRTC für Video. Die Frontend-Komponenten setzen die vorhandenen SIP-Core-Komponenten voraus; das Popup erweitert `sip-call-dialog`, es ersetzt SIP Core nicht.

Der Manager erhält **Schreibzugriff auf die Konfigurationsordner aller Apps/Add-ons** (`all_addon_configs:rw`), damit er die benötigten Custom-Dateien bearbeiten kann. **Das ist weitreichender Zugriff.** Nur auf vertrauenswürdigen Home-Assistant-Systemen installieren, Konfigurationen vor dem Schreiben prüfen und keine Log-/Export-Dateien mit echten Zugangsdaten in öffentliche Issues hochladen. AMI/Tailscale so eng wie möglich freigeben. Backups sind Pflicht, und Änderungen an einer aktiven Asterisk-Konfiguration können Anrufe unterbrechen.

## Entwicklung / Qualität

- `python3 scripts/build-hacs-frontend.py` baut `dist/smartify-sip-manager.js` aus den drei Originaldateien.
- `./release-check.sh` prüft Versionskonsistenz, Python-Unit-Tests und JavaScript-Syntax/Tests (falls Node.js installiert ist).
- Quellcode, Prüfberichte und ältere Anleitungen liegen im Repository; die aktuell gültigen Informationen stehen in der Haupt-README und in `smartify_sip_manager/DOCS.md`.

**Install-Guide:** [Markdown](docs/Install-Guide.md) · [PDF](docs/Smartify-SIP-Manager-Install-Guide.pdf)

**Versionen:** Manager `1.18.8` · Popup `3.3.1` · Doorstation Card `2.7.0`. Änderungsverlauf: [CHANGELOG](smartify_sip_manager/CHANGELOG.md). Die App wurde nicht auf einem produktiven HA-System getestet; die vorhandenen Unit-/Syntaxprüfungen ersetzen keinen End-to-End-Test mit Asterisk/SIP Core.

## Smartify SIP Calling Card (Neu in 1.19.22)

Asterisk-Teilnehmer werden über AMI alle 10 Sekunden in `sensor.smartify_sip_teilnehmer` veröffentlicht. Die Karte `custom:smartify-sip-calling-card` zeigt Registrierungs- und OPTIONS-Erreichbarkeit sowie optional Browser-Mod-Visibility je Nebenstelle. Details, Beispiel-YAML und Grenzen: [Calling Card](docs/SIP-CALLING-CARD.md).

## Klingeltonumleitung pro Teilnehmer (1.19.23)

Unter Teilnehmer gibt es **Ton**, **Player** und **Tondatei**. Wähle `HA-Mediaplayer`, die bestehende `media_player.*`-Entity und eine lokale Datei wie `/local/ring-tone.mp3` (entspricht `/config/www/ring-tone.mp3`). Nach dem Speichern gilt die Einstellung für alle Anrufwege, einschließlich Rufgruppen. Asterisk AMI liefert Klingel-/Gesprächsereignisse, HA übernimmt den Klingelton. Beim Abheben, Auflegen und Timeout wird der Ton gestoppt. Der Ringback-Ton des Anrufers wird nicht verändert.

**Beachte:** Dies ist vorerst eine zusätzliche Wiedergabe. Für ein Klingeln **ausschließlich** über Browser Mod muss der normale SIP-Core-Klingelton separat deaktiviert werden. Die tatsächliche Funktionsfähigkeit hängt von AMI-Berechtigungen und der Erreichbarkeit des gewählten Players ab. Insbesondere iOS kann Browser Mod bei gesperrtem Bildschirm pausieren.

### SIP-OPTIONS-Erreichbarkeitsprüfung je Teilnehmer (1.19.36)

Im SIP Manager in der Teilnehmertabelle unter **Zugang / OPTIONS → OPTIONS (s)** lässt sich die Frequenz der SIP-OPTIONS-Anfragen je Nebenstelle einstellen: `30` bedeutet alle 30 Sekunden; `0` deaktiviert die Prüfung; leer behält die vorhandene Asterisk-Einstellung bei. Anschließend **Speichern** und **Erzeugen & Übernehmen** ausführen. Der Manager schreibt die Einstellung in die AoR-Konfiguration, einschließlich eines Overrides für vom Asterisk-Add-on erzeugte Standard-Endpoints. Die Statuskarte kann dennoch gelb bleiben, wenn kein SIP-Kontakt registriert oder über AMI zugeordnet wird.

### Browser Mod zentral zuordnen (1.19.37)

Im SIP Manager unter **Teilnehmer → Browser Mod** für die jeweilige Nebenstelle eine Status-Entity wie `sensor.ipad_gang_browser_visibility` eintragen und **Speichern**. Die Calling Card verwendet anschließend auf sämtlichen Endgeräten dieselbe zentrale Zuordnung; keine separate Einrichtung pro iPhone oder Tablet. Das ✎ in der Calling Card ändert nur noch den lokalen Anzeigenamen. Für diese Zuordnung ist kein Asterisk-Konfigurationsneuladen notwendig, der Statusworker aktualisiert die HA-Entity automatisch.

## Pflichtprüfung vor jedem Release

Jedes künftige Release muss **Code und Dokumentation gemeinsam** aktualisieren. Vor dem Veröffentlichen prüfen:

1. `smartify_sip_manager/config.yaml`: neue Version und passende Add-on-Beschreibung.
2. `smartify_sip_manager/CHANGELOG.md`: vollständige Änderungen, Einschränkungen und erforderliche Aktionen nach Updates.
3. `README.md`: HACS-gerenderter Funktionsumfang, Installation und Trennung von Add-on/Frontend.
4. `hacs.json`: treffende Beschreibung der tatsächlich ausgelieferten Karten.
5. `smartify_sip_manager/README.md` und `smartify_sip_manager/DOCS.md`: aktuelle Hilfe, Feldnamen, Dialoge und Abläufe.
6. `docs/SIP-CALLING-CARD.md`: aktuelles Kartenverhalten, Statusfarben, Anrufrechte, Browser Mod, lokale versus zentrale Einstellungen.
7. Hinweise/Tooltips im Add-on-HTML sowie die gebündelte HACS-Frontend-Datei auf veraltete Versionen und Texte prüfen.
8. Änderungen an App und HACS getrennt testen, JS-Syntax prüfen und Cache-/Doppelressourcen-Hinweise dokumentieren.

**Ein Release gilt erst als fertig, wenn diese Liste abgearbeitet wurde.** Die Prüfung erfolgt bei jedem Release-Änderungsvorgang; automatische laufende Hintergrundkontrolle ist damit nicht eingerichtet.
