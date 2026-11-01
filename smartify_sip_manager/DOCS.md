# Smartify SIP Manager v1.19.54 – Add-on-Dokumentation

**Einheitliche Übernahme im Assistenten:** In den letzten Schritten von Home Assistant & System, SIP-Teilnehmer, Cloud-Konto und Türstation gibt es jetzt „Erzeugen & Übernehmen …“. Der Knopf validiert und speichert zuerst das Anlagenmodell, danach wird der unveränderte Originalbereich „Erzeugen & Übernehmen“ im selben Dialog angezeigt. Dort müssen die betroffenen Ziele anhand der Vorschau ausgewählt und die Übernahme separat bestätigt werden. SIP-Core-Auto-Answer und Passwortverwaltung nutzen ihre eigenen gesicherten Übernahmewege; kein automatischer Reload ohne bewusste Entscheidung.


Im grafischen Rufgruppen-Manager **innerhalb des Einrichtungsassistenten** steht jetzt „Erzeugen & Übernehmen …“. Der Knopf speichert zunächst eventuelle Modelländerungen und zeigt danach direkt darunter die bestehende vollständige Vorschau mit auswählbaren Konfigurationszielen. Die Übernahme selbst erfordert weiterhin die separate Bestätigung und erstellt Backups; es findet keine automatische, ungeprüfte Übernahme statt. Beim Schließen kehren beide originalen Manager-Oberflächen an ihre Stelle zurück.


**Auto Answer direkt im Assistenten (ab 1.19.48):** Bei einem vorhandenen SIP-Core-Teilnehmer (`HA-Gerät`) erscheint im zweiten Schritt eine Auto-Answer-Checkbox mit auswählbaren erlaubten SIP-Core-Anrufern. „Änderung prüfen“ nutzt die vorhandene SIP-Core-Stage-/Diff-API; „Geprüfte Regel in SIP Core übernehmen“ verlangt eine ausdrückliche Bestätigung und nutzt Backup, Versionsprüfung und Verifikation des vorhandenen SIP-Core-Übernahmemechanismus. Unbekannte Rufnummern oder die eigene Nebenstelle werden nicht freigegeben; globales Auto Answer wird deaktiviert. SIP-Telefon, Türstation und Cloud sehen dieses Feld nicht. Für neue Teilnehmer muss zuerst ein SIP-Core-Benutzer eingerichtet sein.


**Rufgruppen im Assistenten:** Der Assistent zeigt jetzt den **originalen grafischen Rufgruppen-Manager direkt im Assistentenfenster**. Drag-and-drop und Antippen auf Mobilgeräten, neue Gruppen, Teilnehmerzuordnungen und Speichern sind dieselben Funktionen wie im Hauptmanager; die Originaloberfläche wird beim Schließen zurück an ihre vorherige Stelle gesetzt. Es ist **keine Weiterleitung** und keine zweite, abweichende Implementierung. Die eigentliche Asterisk-Übernahme bleibt ein separater bestätigter Schritt.


**Kontextabhängige Felder (ab 1.19.48):** Bei Cloud-Zielen erscheinen nur SIP-Adresse/Provider, eingehender und ausgehender Anschluss, Video-Codecs und optionale Quell-IPs. Browser Mod, lokaler Klingelton, HA-Stream, lokale OPTIONS-Erreichbarkeitsprüfung und Türöffner werden nicht angeboten. Bei SIP-Telefonen bleiben Endpoint, Codecs und OPTIONS; bei HA/SIP-Core-Teilnehmern zusätzlich Browser Mod und lokale Klingeltonausgabe; bei Türstationen Tür/Licht/Klingel und Kamerabild. Bereits gespeicherte, ausgeblendete Felder werden beim Bearbeiten nicht gelöscht.


**Linphone-Cloud-Vorlage (noch nicht veröffentlicht):** Im Assistenten unter „Cloud-Konto“ den Anbieter **Linphone** auswählen und nur den vorhandenen Linphone-Benutzernamen eingeben. Daraus wird die SIP-Adresse `benutzername@sip.linphone.org` gebildet. Für neue Einträge werden `linphone-cloud` (ausgehender Endpoint) und `linphone-in` (eingehender Anschluss) vorausgefüllt, bleiben aber im nächsten Schritt bearbeitbar. Andere Anbieter können mit „Manuell“ eingerichtet werden. Die Vorlage erstellt kein Konto beim Anbieter, hinterlegt kein Anbieter-Passwort und ersetzt nicht die gesonderte Einrichtung der Asterisk-Verbindungen.


**Version 1.19.49:** Im Einrichtungsassistenten bietet „Passwörter verwalten“ die Auswahl einzelner oder mehrerer SIP-Core- und bearbeitbarer PJSIP-Teilnehmer. Sichere Passworterzeugung, Bestätigung, Backup und Versionsprüfung sind eingebaut. SIP Core und PJSIP werden getrennt übernommen; der PJSIP-Reload erfolgt bewusst danach. Cloud-Passwörter können nicht beim externen SIP-Anbieter geändert werden. Bestehende SIP-Clients müssen neu konfiguriert werden.


Der Einrichtungsassistent verlinkt jetzt kontextabhängig zu den bestehenden Editoren für SIP Core (Benutzer und Auto Answer), PJSIP (AOR, Authentifizierung, Codecs und weitere Expertenoptionen), Cloud-SIP-Eingänge, Türstation, Anrufrechte, Live-Status sowie Vorschau und Übernahme. Diese Werkzeuge öffnen sich im jeweiligen Manager-Bereich; Änderungen werden nicht automatisch übernommen. Passwortwechsel und insbesondere ein gemeinsamer Passwortwechsel für mehrere Teilnehmer sind **noch nicht im Assistenten umgesetzt**. Die Konfigurationsbearbeitung bleibt auf die bewährten bestehenden Manager-Funktionen verteilt.


Die HA-Entitätsvorschläge werden beim Tippen **sofort nach jedem Buchstaben gefiltert**, auch nach Teilbegriffen im Anzeigenamen oder in der Entity-ID. Pfeiltasten wählen Treffer aus, Enter übernimmt den Treffer, Escape schließt die Vorschläge.


Im Einrichtungsassistenten bieten **HA-Benutzer, Stream, Browser-Mod-Status, Türöffner, Licht, Klingel und Klingelton-Mediaplayer** kontextabhängige Vorschläge aus der vorhandenen Home-Assistant-/Anlagen-Auswahl. Die Entitätslisten sind nach passender Domain bzw. Funktion gefiltert; Freitexteingabe bleibt möglich, falls eine HA-Entität noch nicht erfasst wurde. Bei nicht verfügbarer HA-API werden keine erfundenen Vorschläge angezeigt.


Bei der Auswahl bestehender Teilnehmer erscheint neben Nummer und Name eine Kurzkennzeichnung der Herkunft: **HA-User**, **SIP**, **SIP-Türstation** oder **Cloud**. Die Kennzeichnung basiert auf dem gespeicherten Teilnehmertyp.

**OPTIONS – Erreichbarkeitsprüfung:** Neue Teilnehmer erhalten standardmäßig **30 s**. **0 s = deaktiviert**. Bei bestehenden Teilnehmern bleiben gespeicherte Werte erhalten; leer bedeutet, dass Asterisk seinen bisherigen Wert behält.


## Einrichtungsassistent (seit 1.19.49)

Der Button **✨ Einrichtungsassistent** im Manager öffnet vier Bereiche: Home Assistant & System, SIP-Teilnehmer, Cloud-Konto / externes SIP-Ziel und Rufgruppe. Im Assistenten kann ein **bestehender Teilnehmer oder eine vorhandene Rufgruppe ausgewählt und gezielt bearbeitet** oder ein neuer Eintrag erstellt werden. Der Assistent verwendet dasselbe Anlagenmodell wie die bisherigen Editoren, keine zusätzliche Konfigurationsdatei.

Teilnehmer: Nummer, Name, Typ, HA-Benutzer, Endpoint, Stream, Codec-Auswahl, SIP-OPTIONS-Frequenz, zentrale Browser-Mod-Statusentität, Realm und Anrufberechtigungen. Cloud-Teilnehmer: SIP-Adresse, Ausgangs-/Eingangsanschluss, Quell-IPs und Freigaben. Rufgruppen: Nummer, Name, Klingelzeit, Anrufer und Klingelziele. System: LAN-/Tailscale-/go2rtc-Parameter. Angaben werden schrittweise bearbeitet und **erst durch „Validieren & speichern“** an die vorhandene Servervalidierung übergeben.

**Sicherheitsgrenzen:** Das Modell wird vor dem Speichern erneut geladen und der Versions-Hash geprüft; fremde Änderungen werden nicht überschrieben. Ein vorhandener Teilnehmer behält nicht bearbeitete Felder. Weder SIP-Passwörter noch Asterisk-Dateien werden durch den Assistenten direkt geändert. **Nach Änderungen an Gruppen, SIP-Zugängen, Codecs oder Rechten im Bereich „Erzeugen & Übernehmen“ die Vorschau prüfen, Backup anlegen und separat übernehmen.** Schon geöffnete Editoren nach dem Speichern neu laden, damit sie keine veralteten Werte anzeigen.

**Noch offen vor produktiver Freigabe:** echte Cloud-Registrierungs- und Verbindungstests, automatisierte Browser-/End-to-End-Tests und Prüfung an einer realen Asterisk-/Home-Assistant-Installation. Die Beta dient dem Praxistest; die fehlenden Funktionen werden vor einer stabilen Freigabe ergänzt.


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

Es gibt zwei Installationswege für das Frontend: **HACS-Dashboard** mit `smartify-sip-manager.js` oder manuelle Ressource `/local/smartify/smartify-sip-manager.js?v=1.19.52`. **Nie beide gleichzeitig registrieren**, sonst drohen doppelte Custom-Elemente und Versionskonflikte. App und HACS getrennt aktualisieren. Nach einem Update Dashboard/Companion-WebView vollständig neu laden; ggf. Ressourcen-URL mit neuer Versionskennung versehen.

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


**Version 1.19.49:** Der Button „✨ Einrichtungsassistent“ steht direkt in der oberen Aktionsleiste neben Speichern/Änderungen laden. Nach App-Update neu öffnen; bei altem Browserinhalt Cache/Ingress-Ansicht vollständig neu laden.


## Piper-TTS-Alarmanruf (ab 1.19.49, Praxistest erforderlich)

Der Smartify-SIP-Manager kann nach Installation der neuen Backend-Version einen Text via Home-Assistant-Piper erzeugen, den von Piper gelieferten WAV-Streaming-Header (RIFF-/data-Länge `0xFFFFFFFF`) reparieren, die WAV-Datei in `/media/smartify-sip-alarms` ablegen und über den bestehenden Asterisk-AMI-Zugang einen ausgehenden SIP-Anruf starten. Keine manuell angelegten WAV-Dateien, kein FFmpeg und kein separates Python-Skript in Home Assistant erforderlich.

**Voraussetzungen:** Piper-TTS-Entität (z. B. `tts.piper`), laufender Asterisk mit gemeinsamem `/media`-Mount, funktionierender AMI-Zugang mit Originate-Recht. Unter den App-Optionen `alarm_endpoint` (z. B. `linphone-cloud`), `alarm_destination` (vollständiges `sip:benutzer@sip.linphone.org`), `alarm_tts_engine` und ein selbst erzeugtes, mindestens 24 Zeichen langes `alarm_api_key` konfigurieren. Die SIP-Adresse kommt ausschließlich aus diesen App-Optionen, nicht aus dem API-Aufruf.

Der Manager stellt `POST /api/alarm/tts-call` bereit. Dieser Endpunkt ist ausschließlich mit dem Header `X-Alarm-Token` benutzbar; alle anderen Manager-Endpunkte bleiben ingressgeschützt. Home Assistant benötigt nur einen `rest_command` (keine externen Skripte):

```yaml
rest_command:
  smartify_alarm_tts:
    url: "http://<manager-addon-host>:8099/api/alarm/tts-call"
    method: POST
    headers:
      X-Alarm-Token: !secret smartify_alarm_api_key
      Content-Type: application/json
    payload: '{"message": {{ message | to_json }}}'
    timeout: 60
```

`<manager-addon-host>` muss als **vom Home-Assistant-Core-Container erreichbarer interner Hostname** ermittelt und eingesetzt werden. Der Ingress-Pfad der Browseroberfläche ist nicht gleich dem internen API-Hostnamen. Die App veröffentlicht dafür keinen externen Port.

In einer Automation kann dann `rest_command.smartify_alarm_tts` mit `message` aufgerufen werden. Die Antwort `queued: true` bestätigt nur den Auftrag über AMI, **nicht** die Annahme oder Audiowiedergabe. Erst nach einem End-to-End-Test produktiv einsetzen. Der Anruf ist Zusatzalarmierung und ersetzt niemals lokale Rauchmelder-Sirenen. Für einen Cloud-Anruf ist Internet erforderlich.

**Offene Punkte vor einer stabilen Freigabe:** Verbindungs-/Erreichbarkeitstest aus Home Assistant, Test der Supervisor-geschützten TTS-Proxy-URL, Wiederholungslogik bei Nichtannahme, vorab gespeicherte Ersatzansage sowie sichere automatische Bereinigung alter Audiodateien. Bis dahin die bisherigen Alarmwege beibehalten.


### Mehrere Alarmempfänger (ab 1.19.50)

In den App-Optionen unter `alarm_destinations` mehrere vollständige SIP-URIs durch Komma, Semikolon oder Zeilenumbruch trennen. Beispiel: `sip:erstes@sip.linphone.org,sip:zweites@sip.linphone.org`. Bei leerem Feld wird `alarm_destination` weiterverwendet. Ein Aufruf von `rest_command.smartify_alarm_tts` löst alle aktiven Zielanrufe parallel aus, mit **einmalig** erzeugter Piper-Ansage. Es werden keine SIP-Konten verändert. `queued_count` ist die Anzahl von Asterisk angenommener Originate-Aufträge, nicht die Zahl angenommener Gespräche. Aktuell sind weder eine sequenzielle Eskalation noch Wiederholungsanrufe implementiert. Die lokale Rauchmelder-Sirene bleibt unabhängig aktiv.


### Anruferkennung für Alarmanrufe (ab 1.19.51)

In **Apps → Smartify SIP Manager → Konfiguration** die Felder `alarm_caller_name` (z. B. `Hausalarm`) und `alarm_caller_number` (z. B. `999`) setzen. Standard bleibt `RAUCHALARM` / `999`. Die Daten werden validiert und für alle konfigurierten SIP-Alarmziele in Asterisk AMI `Originate` übernommen. Der angerufene SIP-Provider kann die Darstellung trotzdem überschreiben. Die Home-Assistant-Rauchalarm-Automation ändert sich nicht.


### Alarmkonfiguration – aktueller Stand (1.19.52)

Die Alarmfelder werden unter **Einstellungen → Apps → Smartify SIP Manager → Konfiguration** bearbeitet, nicht in einem eigenen grafischen Alarm-Dialog. `alarm_destinations` enthält bis zu zwölf vollständige SIP-URIs, getrennt durch Komma, Semikolon oder Zeilenumbruch. Wenn dieses Feld leer ist, gilt ausschließlich der ältere Einzelwert `alarm_destination`; bei ausgefüllter Liste wird `alarm_destination` ignoriert. Beide Optionen sind wegen Abwärtskompatibilität derzeit sichtbar. `alarm_caller_name` (Standard `RAUCHALARM`) und `alarm_caller_number` (Standard `999`, nur Ziffern) steuern die an Asterisk übergebene Caller-ID. Die Anzeige im angerufenen Linphone-Client kann von SIP-Provider oder Kontaktbuch abweichen. Interne Kurznummern wie `100` und gewöhnliche Telefonnummern wie `+43664...` werden in `alarm_destinations` noch nicht unterstützt und benötigen andere Routing-Logik bzw. einen SIP-Trunk. Parallele Anrufaufträge sind keine bestätigte Zustellung; es gibt bislang keine automatische Wiederholung bei Nichtannahme.


### Wahlwiederholung bei nicht angenommenen Alarmanrufen (ab 1.19.53)

In den **Add-on-Optionen** sind `alarm_call_attempts` (Standard 3, Werte 1–5), `alarm_ring_seconds` (Standard 30, Werte 10–90 Sekunden) und `alarm_retry_pause_seconds` (Standard 30, Werte 0–300 Sekunden) einstellbar. Pro konfigurierter SIP-Adresse läuft ein unabhängiger Anrufablauf; alle Empfänger starten parallel. Statt eines reinen `Async: true`-Auftrags verwendet die Wahlwiederholung ein synchrones AMI-Originate-Ergebnis: `Response: Success` beendet die Wahlversuche für diesen Empfänger, ein ausdrücklich negatives Ergebnis löst nach der Pause den nächsten Versuch aus. Kann der Manager das Ergebnis wegen einer AMI-Verbindungsstörung **nicht eindeutig feststellen**, wird zur Vermeidung versehentlicher Doppelanrufe nicht automatisch erneut gewählt. Die Piper-Ansage wird nur einmal pro Alarm erzeugt. Die REST-Antwort bestätigt nur die Annahme des Alarmauftrags, nicht die Zustellung; die Ergebnisse stehen im Add-on-Log. **Bekannte Einschränkungen:** Laufende Wiederholungen liegen nur im Speicher und werden durch Add-on-Neustart abgebrochen. Eine Annahme ist keine Bestätigung, dass die gesamte Sprachnachricht gehört wurde. Ein neuer separater Automations-Trigger startet einen eigenen Alarm. Das System ersetzt niemals die lokale Rauchmelder-Sirene.


### Calling Card und Konfigurationshinweise (ab 1.19.54)

Die Calling Card zeigt statt Telefon-Avataren neutrale Personen-Symbole; Teilnehmerstatus und Browser-Mod-Status stehen mittig zwischen Name und größerem Anrufhörer. Der Regler **Hörergröße** reicht von 30 bis 80 px (Standard 54 px). Die Größe der tatsächlich gerenderten Schaltfläche hängt von der SIP-Core-Karte ab.

Die übersetzten Hinweise unter den App-Konfigurationsfeldern erklären die Alarmziele, TTS, Caller-ID sowie die Wahlwiederholung: `alarm_call_attempts: 3` ist der Standard; **1 Versuch deaktiviert die Wahlwiederholung**. `alarm_ring_seconds: 30` bedeutet 30 Sekunden Klingeldauer je Versuch. `alarm_retry_pause_seconds: 30` bedeutet 30 Sekunden Wartezeit; **0 bedeutet sofort wiederholen, nicht deaktivieren**.
