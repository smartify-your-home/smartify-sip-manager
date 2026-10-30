# Smartify SIP Calling Card – aktuelle Anleitung 1.19.40

Die HACS-Dashboard-Karte benötigt das separate Smartify SIP Manager Add-on und dessen HA-Sensor `sensor.smartify_sip_teilnehmer`. Für Anrufknöpfe muss SIP Core (`custom:sip-call-button`) installiert sein.

```yaml
type: custom:smartify-sip-calling-card
entity: sensor.smartify_sip_teilnehmer
title: Smartify SIP · Calling
```

## Status und eigene Nebenstelle

Unter ⚙ die **eigene Nebenstelle** auswählen. Sie verschwindet aus der Kontaktliste und wird oben rechts als Statuspunkt dargestellt: **grün** = Asterisk meldet Reachable, **rot** = Unreachable, **gelb/?** = ungeprüft, nicht zugeordnet oder Daten veraltet. „AMI verbunden“ wird nicht mehr angezeigt; bei veralteten Daten steht „Daten veraltet“.

Die drei flachen Statusfelder zeigen Erreichbar, Offline, Gesamt für die übrigen Kontakte. Ein registrierter Kontakt ohne SIP-OPTIONS-Prüfung ist nicht automatisch unerreichbar. Unter **Teilnehmer → OPTIONS (s)** kann `qualify_frequency` (0 = aus, 30 = 30 Sekunden) eingestellt werden. Asterisk-Änderungen benötigen **Speichern → Änderungen laden / Erzeugen & Übernehmen**.

## Kontaktanzeige, Berechtigungen, Browser Mod

Der SIP-Core-Hörer kann unter ⚙ auf **24–50 px** eingestellt werden und ist in einer entsprechend hohen Zeile zentriert; Schriftgröße **11–24 px**. Die Karte blendet einen aktiven Anrufknopf aus und zeigt **⛔**, wenn die gewählte eigene Nebenstelle nach `anruf_ziele` und `angerufen_von` den Kontakt nicht anrufen darf.

**Browser-Mod-Entities zentral im SIP Manager → Teilnehmer → Browser Mod eintragen** (z. B. `sensor.ipad_gang_browser_visibility`). Diese gelten auf allen Geräten. Sichtbar = kein Warnhinweis; sonst „BM n.ok“. Die lokalen Anzeigenamen, Reihenfolge, Größen und die Auswahl der eigenen Nummer sind weiterhin **je Browser** gespeichert. Unter ⚙: Teilnehmer hinzufügen, per ⠿ sortieren, per ✎ lokalen Anzeigenamen ändern, per ✕ aus Karte entfernen (nicht aus Asterisk).

## Installation und Cache

Das HACS-Dashboard-Frontend ist **nicht das Add-on**. Beide Komponenten getrennt aktualisieren. Nur **eine** Resource-URL für das gemeinsame Bundle registrieren: entweder HACS oder `/local/smartify/smartify-sip-manager.js?v=1.19.40`. Nie beide, da doppelte Custom Elements kollidieren können. Bei altem Stand WebView/Browser neu laden. Die diskutierte rein native YAML-Alternative wird derzeit **noch nicht als fertige Karte mitgeliefert**.

## Diagnose

In Entwicklerwerkzeuge → Zustände `sensor.smartify_sip_teilnehmer` kontrollieren: Attribute `participants`, `updated`, `call_rules`, `browser_mod_entities`. Sind alle Kontakte gelb oder werden 0 Kontakte gemeldet, AMI-Prüfung im Manager und Asterisk-Kommando `pjsip show contacts` vergleichen. Grün bedeutet nicht automatisch funktionierende RTP-/Video-/NAT-Verbindungen.
