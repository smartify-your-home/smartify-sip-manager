# Smartify SIP – Kamera-Routing (Manager 1.18.8)

## Dateien / Versionen

- `smartify_sip_manager/` – Home-Assistant-App 1.18.8 (Änderungen: `smartify_sip_manager/CHANGELOG.md`).
- `frontend/smartify-doorstation-popup.js` – Popup 3.3.1 (camera_by_caller ab 3.3.0).
- `frontend/smartify-doorstation-card.js` – Doorstation Card 2.7.0 (camera_by_caller ab 2.7.0).

## Upgrade

1. **Sicherung** des laufenden HA-Setups und der aktuellen SIP-Core-Integration anfertigen.
2. Das Repository `https://github.com/smartify-your-home/Smartify-SIP-Manager` im Home-Assistant-App-Store hinzufügen und **Smartify SIP Manager 1.18.8** installieren/aktualisieren. Der Umstieg von einer lokalen Installation erzeugt ggf. eine separate App-ID; Einstellungen und private Daten vorher sichern.
3. **Empfohlen:** In HACS das Repository als Typ **Dashboard** hinzufügen. Dadurch wird die kombinierte Ressource `/hacsfiles/Smartify-SIP-Manager/smartify-sip-manager.js` installiert; sie enthält Popup 3.3.1 und Card 2.7.0. Die Ressource als **JavaScript-Modul** registrieren, falls HACS das nicht automatisch erledigt. Frühere `/local/`-Ressourcen für Popup/Card deaktivieren, damit nichts doppelt geladen wird.
4. Im Manager den Reiter **Kameras je Anrufer** öffnen. Pro tatsächlich von Asterisk übertragener Caller-ID (z. B. 200 oder 201) den bestehenden go2rtc-Stream eintragen; optional Klingel-, Tür- und Lichtentitäten ergänzen (beim Tippen erscheinen passende Entitäten als Vorschläge; unter dem Feld wird geprüft, ob die Entität existiert). **Zuordnung übernehmen → Kamera-Zuordnungen dauerhaft speichern.** Die Daten liegen unabhängig von der offenen Manager-Seite unter `/data/camera_mapping.json` und werden beim nächsten Start geladen.
5. **In SIP-Core-Entwurf zusammenführen** (oder Popup-YAML kopieren). Nur die neuen `popup_override_component`- und `popup_config.smartify`-Schlüssel in die vorhandene SIP-Core-Konfiguration übernehmen. Vorhandene `users`, Passwörter, `popup_config.extensions`, `popup_config.buttons` etc. unbedingt erhalten. SIP Core über **Einstellungen → Geräte & Dienste → SIP Core → Konfigurieren** speichern.
6. Die vom Manager erzeugte **Doorstation-Card-YAML kopieren** und als Dashboard-Karte einfügen. Die Card enthält **keine zweite Kopie der Kameratabelle**; sie liest das Mapping direkt aus `window.sipCore.config.popup_config.smartify.camera_by_caller`.
7. HA-Frontend vollständig neu laden (auch iPad / iPhone). `go2rtc`-Streams vorab einzeln prüfen. Testanruf pro Türstation durchführen; Caller-ID, korrekten Stream, SIP-Audio, Türöffner und Licht testen.

## Beispiel: Kamera-Mapping (in die bestehende SIP-Core-YAML integrieren)

```yaml
popup_override_component: smartify-doorstation-popup
popup_config:
  auto_open: true
  large: true
  smartify:
    stream: cam_pt2   # Fallback, falls keine Station zutrifft
    camera_mode: always
    mode: mse
    camera_by_caller:
      "200":
        label: Haustür
        stream: akuvox_s535
        mode: mse
        camera_mode: auto
        bell_entity: binary_sensor.akuvox_s535_klingel
        door_entity: switch.haustuer
        door_service: turn_on
        door_confirm: true
      "201":
        label: Garage
        stream: garage_cam
        mode: webrtc
        camera_mode: always
```

Die Beispiel-Streamnamen und `switch.haustuer` sind Platzhalter und müssen auf die tatsächlich vorhandenen Werte geändert werden. Insbesondere bei Weiterleitung über Asterisk/Rufgruppe muss `remoteExtension` die **Anrufernummer** 200/201 liefern (nicht die angerufene 600/104). Die Card zeigt während eines Anrufs `SIP · <Nummer>` zum Prüfen.

## Beispiel: Card

```yaml
type: custom:smartify-doorstation-card
title: Smartify Türstationen
follow_sip_core: true
station_extension: "200"  # Standby-Vorschau; im Anruf übernimmt die Gegenstelle
stream: cam_pt2          # Fallback bei nicht zugeordnetem Anrufer
mode: mse
camera_mode: always
show_sip: true
show_status: true
```

## Technische Details und Grenzen

- **Zentrales Laufzeit-Mapping** ist die aktive SIP-Core-Konfiguration, nicht die Add-on-Datenbank. Der Manager speichert Entwürfe, aber schreibt nicht direkt in die laufende SIP-Core-Integration. Eine Änderung im Manager wird erst nach Übernahme der YAML dort live.
- Das Popup erbt weiterhin vom originalen `sip-call-dialog` und behält dessen **SIP-Sprechfunktionen, Tasten, DTMF und bestehende `popup_config.buttons`**. Automatisch gewählt wird dessen Videoquelle; die jeweiligen Tür-/Lichtaktionen mit Bestätigungsdialog stellt die Smartify Card bereit. `door_confirm` im Mapping bestätigt daher die Türöffnung in der Card, nicht automatisch in einem bereits separat konfigurierten originalen Popup-Button.
- Das Popup zeigt Video im Modus `auto` während des SIP-Anrufs auch dann weiter, wenn der Klingel-Binary-Sensor nur 2 Sekunden `on` bleibt. Die Card zeigt außerdem optional die Kamera bei einem aktiven Klingel-Binary-Sensor ohne SIP-Gespräch.
- Falls der Anrufer nicht zugeordnet ist, wird auf den Standardstream zurückgefallen. **Bei fremden oder unbekannten SIP-Anrufern zeigt die Card nicht versehentlich den Türöffner einer anderen Station**.
- `sipCore.remoteExtension` wird von SIP Core bereitgestellt. Der Wert muss mit den Zuordnungsschlüsseln übereinstimmen. Bei einer Rufgruppe oder geänderter Asterisk Caller-ID kann Anpassung erforderlich sein.
- Python und JavaScript wurden syntaktisch geprüft und mit Mock-Anrufen getestet. Ein echter SIP-, go2rtc- und iPad-/iPhone-Integrationstest kann nur im eigenen HA-System erfolgen.
