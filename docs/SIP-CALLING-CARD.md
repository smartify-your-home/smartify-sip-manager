# Smartify SIP Calling Card – aktuelle Anleitung 1.19.56

Die HACS-Dashboard-Karte benötigt das separate Smartify SIP Manager Add-on und dessen HA-Sensor `sensor.smartify_sip_teilnehmer`. Für Anrufe muss SIP Core geladen und als `window.sipCore` verfügbar sein; die Karte nutzt seine öffentliche Anrufsteuerung.

```yaml
type: custom:smartify-sip-calling-card
entity: sensor.smartify_sip_teilnehmer
title: Smartify SIP · Calling
```

## Status und eigene Nebenstelle

Unter ⚙ die **eigene Nebenstelle** auswählen. Sie verschwindet aus der Kontaktliste und wird oben rechts als Statuspunkt dargestellt: **grün** = Asterisk meldet Reachable, **rot** = Unreachable, **gelb/?** = ungeprüft, nicht zugeordnet oder Daten veraltet. „AMI verbunden“ wird nicht mehr angezeigt; bei veralteten Daten steht „Daten veraltet“.

Die drei flachen Statusfelder zeigen Erreichbar, Offline, Gesamt für die übrigen Kontakte. Ein registrierter Kontakt ohne SIP-OPTIONS-Prüfung ist nicht automatisch unerreichbar. Unter **Teilnehmer → OPTIONS (s)** kann `qualify_frequency` (0 = aus, 30 = 30 Sekunden) eingestellt werden. Asterisk-Änderungen benötigen **Speichern → Änderungen laden / Erzeugen & Übernehmen**.

## Kontaktanzeige, Berechtigungen, Browser Mod

Der Anrufhörer kann unter ⚙ auf **30–80 px** eingestellt werden und ist in einer entsprechend hohen Zeile zentriert; Schriftgröße **11–24 px**. Die Karte blendet einen aktiven Anrufknopf aus und zeigt **⛔**, wenn die gewählte eigene Nebenstelle nach `anruf_ziele` und `angerufen_von` den Kontakt nicht anrufen darf.

**Browser-Mod-Entities zentral im SIP Manager → Teilnehmer → Browser Mod eintragen** (z. B. `sensor.ipad_gang_browser_visibility`). Diese gelten auf allen Geräten. Sichtbar = kein Warnhinweis; sonst „BM n.ok“. Die lokalen Anzeigenamen, Reihenfolge, Größen und die Auswahl der eigenen Nummer sind weiterhin **je Browser** gespeichert. Unter ⚙: Teilnehmer hinzufügen, per ⠿ sortieren, per ✎ lokalen Anzeigenamen ändern, per ✕ aus Karte entfernen (nicht aus Asterisk).

## Installation und Cache

Das HACS-Dashboard-Frontend ist **nicht das Add-on**. Beide Komponenten getrennt aktualisieren. Nur **eine** Resource-URL für das gemeinsame Bundle registrieren: entweder HACS oder `/local/smartify/smartify-sip-manager.js?v=1.19.56`. Nie beide, da doppelte Custom Elements kollidieren können. Bei altem Stand WebView/Browser neu laden. Die diskutierte rein native YAML-Alternative wird derzeit **noch nicht als fertige Karte mitgeliefert**.

## Diagnose

In Entwicklerwerkzeuge → Zustände `sensor.smartify_sip_teilnehmer` kontrollieren: Attribute `participants`, `updated`, `call_rules`, `browser_mod_entities`. Sind alle Kontakte gelb oder werden 0 Kontakte gemeldet, AMI-Prüfung im Manager und Asterisk-Kommando `pjsip show contacts` vergleichen. Grün bedeutet nicht automatisch funktionierende RTP-/Video-/NAT-Verbindungen.


## Kontaktzeilen ab 1.19.54

Links zeigt jeder Kontakt ein neutrales Personen-Symbol statt eines Telefonhörers. Der SIP-Erreichbarkeits- und optionale Browser-Mod-Status steht zwischen Teilnehmername und Anrufschaltfläche mittig. Der Hörer rechts ist jetzt ein eigenständiger zentrierter MDI-Button, der die SIP-Core-Anrufmethoden verwendet. Im Bearbeitungsmodus steuert der Regler **Hörergröße** nun 30 bis 80 px (Standard 54 px) und skaliert den zentrierten Anrufbutton entsprechend. Bereits gespeicherte Einstellungen bleiben erhalten, soweit innerhalb der neuen Grenzen. Das Symbol wird ohne die bisherige Skalierung des eingebetteten SIP-Core-Kartenlayouts dargestellt.

## Calling Card 1.19.55 – abgeschnittenen Hörer behoben

Der Anrufknopf rechts ist ein eigenständiger, quadratischer Flex-Button mit `mdi:phone-outline` anstelle einer verkleinerten, abgeschnittenen SIP-Core-Karte. Das Symbol sitzt mittig und nutzt ca. 70 % der eingestellten Hörergröße (30–80 px). Anrufen, Annehmen und Auflegen verwenden die von SIP Core bereitgestellten Methoden `window.sipCore.startCall()`, `answerCall()` und `endCall()`; SIP Core muss im Browser geladen sein. Für die installierte Anlage ist ein Funktionstest nötig.

**Vollständige Datei im GitHub-Repository:** `frontend/smartify-sip-calling-card.js` (nur diese Karte). Das für HACS und die Add-on-Installation benötigte kombinierte Skript liegt unter `dist/smartify-sip-manager.js`; bei manueller Installation lautet sein Home-Assistant-Ziel `/config/www/smartify/smartify-sip-manager.js` und die Ressource `/local/smartify/smartify-sip-manager.js?v=1.19.55`. Die einzelne Quelldatei darf das kombinierte Skript nicht ersetzen. Bei HACS-Nutzung erfolgt das Update stattdessen über HACS.


### Cloud-Konten und Kartenhintergrund ab 1.19.56

Für SIP-Cloud-Konten (z. B. `linphone-cloud`/`linphone-in`) wird bei **unbekannter** SIP-Erreichbarkeit kein Fragezeichen mehr angezeigt; das Statusfeld bleibt leer. Ein über SIP OPTIONS tatsächlich erreichbarer oder ausdrücklich nicht erreichbarer Kontakt wird weiterhin entsprechend angezeigt. Cloud-Konten mit unbekannter Erreichbarkeit zählen nicht mehr in die Fragezeichen-Anzahl der Zusammenfassung. Die Kennzeichnung stammt aus der Teilnehmerkonfiguration sowie erkennbaren Cloud-Endpoint-Namen.

Der read-only SIP-Statusdienst fragt zusätzlich Asterisk AMI `PJSIPShowRegistrationsOutbound` ab und stellt bei eindeutiger Zuordnung den Wert `registration_status` im Sensor bereit (`registered`, `unregistered`, `rejected`, `stopped`). **Registriert** bedeutet nur Anmeldung von Asterisk beim SIP-Anbieter, nicht Erreichbarkeit des Mobiltelefons. Ist die Zusatzabfrage nicht verfügbar, bleibt der bisherige Kontaktstatus erhalten. Die Calling Card zeigt bei unbekannter Cloud-Erreichbarkeit absichtlich keine erfundene Statusanzeige.

Unter **⚙ → Hintergrundtransparenz** wird der Kartenhintergrund von 0 bis 100 % eingestellt: **0 % = wie bisher blickdicht, 100 % = vollständig transparent**. Schrift, Icons, Hörer und Status bleiben deckend. Die Einstellung wird wie Schrift- und Hörergröße lokal im jeweiligen Browser gespeichert und live als Vorschau angewendet. Optionaler YAML-Startwert: `background_transparency: 30`; eine lokale Slider-Einstellung hat Vorrang.

Ein GitHub-/CI-Test ersetzt keinen Live-Test der Registrierung mit deinem konkreten Provider oder des Browser-Themes.
