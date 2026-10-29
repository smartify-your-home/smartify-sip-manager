# Smartify SIP Calling Card (v1.19.22)

Die Karte zeigt **alle von Asterisk AMI gemeldeten PJSIP-Endpunkte** sowie optional den Browser-Mod-Status von iPad/iPhone. Die Anzeige benötigt Smartify SIP Manager als Home-Assistant-App **und** das aktualisierte HACS-Dashboard-Frontend.

## Teilnehmer direkt in der Karte auswählen

Im Kopfbereich der Calling Card gibt es das Dropdown **Teilnehmer auswählen**. Es enthält automatisch alle von Asterisk erkannten Nebenstellen mit den Namen aus dem Smartify-SIP-Manager-Anlagenmodell. Mit **+ Hinzufügen** wird eine eigene Auswahl aufgebaut; über **×** lassen sich Teilnehmer wieder ausblenden. **Alle** setzt die Auswahl zurück. Neue Nebenstellen erscheinen automatisch im Dropdown.

Diese Auswahl wird derzeit im lokalen Browser-Speicher der HA-Oberfläche gespeichert: auf einem anderen iPad/Browser kann sie abweichen. Es werden dadurch keine SIP-Nebenstellen in Asterisk erstellt oder verändert. Die Browser-Mod-Entity-Zuordnung bleibt eine Kartenkonfiguration.

## Drag & Drop und Kartenbearbeitung (1.19.25)

Teilnehmer am Griff **⠿** ziehen, um ihre Reihenfolge zu ändern. Über **✎** können ein Anzeigename und die Browser-Mod-Visibility-Entity individuell für diese Karte gesetzt werden. Über **✕** wird der Eintrag nur aus der Karte entfernt; SIP-Benutzer und Konfiguration bleiben unverändert. **Alle** setzt die Anzeige zurück. Änderungen werden im lokalen Browser gespeichert und müssen auf anderen Geräten gegebenenfalls erneut vorgenommen werden. Ein geänderter Anzeigename in der Karte verändert niemals das SIP-Manager-Anlagenmodell.

## Einrichtung

1. Smartify SIP Manager 1.19.22 im App-Store neu installieren/aktualisieren und starten.
2. Unter **System / AMI** die Verbindung kontrollieren. Ein AMI-Benutzer mit PJSIP-Leserechten ist erforderlich. Der Manager startet ohne Änderungen an Asterisk einen Hintergrundmonitor.
3. In HACS das Dashboard-Frontend aktualisieren und die Home-Assistant-Seite vollständig neu laden.
4. Unter **Entwicklerwerkzeuge → Zustände** muss `sensor.smartify_sip_teilnehmer` erscheinen. Seine Attribute `participants` und `updated` stammen aus Asterisk. Bei fehlender Verbindung wird `unavailable` veröffentlicht.
5. In Browser Mod auf dem iPad eine stabile Browser-ID setzen und die tatsächliche Entity-ID des Visibility-Sensors unter **Entwicklerwerkzeuge → Zustände** ermitteln.

## Beispiel für das Dashboard

```yaml
type: custom:smartify-sip-calling-card
title: SIP Teilnehmer
entity: sensor.smartify_sip_teilnehmer
stale_seconds: 35
names:
  "100": iPhone Raphael
  "103": Samsung Amelie
  "104": iPad Visu
  "105": SmartifyService
  "200": Akuvox S535
browser_mod:
  "104": sensor.ipadvisu_browser_visibility
```

**Wichtig:** Die Browser-Mod-Entity ist nur ein **Beispiel**. Trage die echte Entity-ID ein. Weitere Browser-Mod-Geräte lassen sich durch zusätzliche Zuordnungen aufnehmen. Ohne Eintrag erfolgt keine Browser-Mod-Prüfung.

## Was bedeutet der Status?

- **Erreichbar:** Ein qualifizierter Asterisk-Kontakt hat auf SIP OPTIONS reagiert.
- **Nicht registriert:** Für den Endpoint ist kein Kontakt vorhanden.
- **Nicht erreichbar:** Kontakt vorhanden, aber SIP OPTIONS nicht erfolgreich.
- **Ungeprüft:** Kontakt vorhanden, aber noch keine erfolgreiche Qualifizierung (z. B. `qualify_frequency=0`).
- **Browser Mod sichtbar:** Der Visibility-Sensor ist `visible` oder `on`.
- **Browser Mod verborgen:** Browser Mod meldet `hidden`/`off`. Die Webseite kann trotzdem verbunden sein.
- **Browser Mod offline:** Der konfigurierte Visibility-Sensor ist `unknown`, `unavailable` oder fehlt.
- **Daten veraltet:** Der Monitor hat seit mehr als 35 Sekunden keinen frischen Asterisk-Snapshot geliefert.

**Keine Anrufgarantie:** SIP-OPTIONS/Browser-Visibility beweisen nicht, dass eine iOS-App bei gesperrtem Bildschirm klingelt oder Audio wiedergibt. Der Status ist eine Diagnoseanzeige.

## Aktualisierung

Der Manager fragt Asterisk per AMI alle **10 Sekunden** ab. Er sendet selbst keine SIP OPTIONS. Die Erreichbarkeitsprüfung muss an den Asterisk-AoRs gesondert aktiviert sein, zum Beispiel `qualify_frequency=10` und `qualify_timeout=3`. Das wird **nicht automatisch geändert**, weil es die produktive Konfiguration beeinflussen würde. Die Karte aktualisiert sich bei HA-State-Änderungen und prüft zusätzlich alle 5 Sekunden auf veraltete Daten.

Die per REST-API erzeugte Status-Entity ist eine **vom laufenden Manager veröffentlichte Laufzeit-Entity**. Bei einem HA-Neustart erscheint sie wieder, sobald der Manager den nächsten Snapshot erfolgreich sendet. Die Karte ändert keine Nebenstellen, Rufgruppen oder Asterisk-Konfiguration.

## Fehlerdiagnose

Wenn `sensor.smartify_sip_teilnehmer` fehlt, prüfe, ob die Manager-App läuft, der Supervisor-Token verfügbar und die AMI-Verbindung erfolgreich ist. Falls alle Kontakte `Nicht registriert` anzeigen, kontrolliere mit `asterisk -rx "pjsip show contacts"` die tatsächlichen Kontaktzeilen sowie die AMI-Berechtigungen. Bei abweichenden AOR-Namen muss die Endpoint-AOR-Zuordnung geprüft werden.

