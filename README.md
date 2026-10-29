# Smartify SIP Manager

**Version 1.19.22** – Verwaltung von Asterisk/PJSIP, SIP Core, go2rtc und Türstations-Kameras in Home Assistant.

Dieses Repository enthält **zwei getrennt installierbare Teile**:

- **Home-Assistant-App (früher: Add-on)** `smartify_sip_manager/` – der eigentliche Smartify SIP Manager mit eigenem Python-Webserver und Ingress. **Installation und Aktualisierung über den Home-Assistant-App-Store**, nicht HACS.
- **HACS-Dashboard-Frontend** `dist/smartify-sip-manager.js` – stellt **Smartify Doorstation Card** und **Smartify Doorstation Popup** sowie die **Smartify SIP Calling Card** bereit. **Installation und Updates optional über HACS** (Typ *Dashboard*). Der Manager ist davon unabhängig.

> **Wichtig:** HACS kann keine Apps/Add-ons installieren. Das Dashboard-Bundle enthält ausschließlich die Frontend-Komponenten, nicht den Python-/Asterisk-Manager. Für den kompletten Funktionsumfang benötigt man die App und bei Verwendung der Doorstation-Oberfläche zusätzlich das Frontend.

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
