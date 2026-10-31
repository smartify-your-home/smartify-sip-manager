## 1.19.43 – Beta: Start des Einrichtungsassistenten sichtbar und diagnostizierbar

- Dialog öffnet unmittelbar beim Klick, bevor das Anlagenmodell geladen wird.
- Ladeanzeige sowie klare Fehlermeldung und Wiederholen-Knopf bei API-/Ingress-Problemen.
- Skript-Cachekennung aktualisiert. Keine automatische Änderung an Asterisk.

## 1.19.42 – Fix: Einrichtungsassistent-Button zuverlässig sichtbar

- Startbutton fest in der Aktionsleiste des HTML statt ausschließlich dynamisch durch JavaScript erzeugt.
- Wizard-Script mit Versionskennung geladen, um veraltete HA-Ingress-Browser-Caches zu vermeiden.
- Funktion des Assistenten bleibt Beta; vorhandene Asterisk-Konfiguration wird nicht automatisch überschrieben.

## 1.19.41 – Beta: Direkter Einrichtungsassistent (Testversion)

- Teilnehmer, Cloud-Ziele, Rufgruppen und HA-Anlagenparameter im Assistenten direkt bearbeiten.
- Serverseitige Validierung, Schreibkonfliktschutz und automatische Aktualisierung des Anlageneditors nach dem Speichern.
- Ungespeicherte Eingaben im bisherigen Editor werden nicht überschrieben.
- **Beta:** Cloud-Registrierungstests im Assistenten und echte HA-/Asterisk-End-to-End-Tests stehen noch aus.
- Vor Installation ein Home-Assistant-Backup anlegen. Für aktive Telefoniekonfigurationen weiterhin Vorschau/Backup und „Erzeugen & Übernehmen“ nutzen.

## Unreleased – Direkter Einrichtungsassistent (PR #27)

- Direkte Auswahl, Anlage und Bearbeitung von Home-Assistant-Systemwerten, SIP-Teilnehmern, externen Cloud-Zielen und Rufgruppen.
- Schrittweise Formulare für Codecs, OPTIONS, Browser Mod, Rechte, SIP-Adressen, Rufgruppen-Mitglieder und Klingelzeiten.
- Serverseitige Modellvalidierung und Hash-Konfliktkontrolle; keine automatische Asterisk-Übernahme.
- Noch keine Cloud-Verbindungstests und keine abgeschlossenen E2E-Tests. Kein Release.

## 1.19.40 – Dokumentation und App-/HACS-Hinweise vollständig überarbeitet

- Veraltete Add-on-README und DOCS.md (zuvor 1.19.21) auf den aktuellen Funktionsstand gebracht.
- Calling-Card-Anleitung (zuvor 1.19.22) vollständig überarbeitet: eigene Nummer, Statuspunkt, Rechte, Browser Mod, Größen, Cache und Diagnose.
- HACS-Bezeichnung aktualisiert: Doorstation **und** Calling Cards.
- Root-README mit aktuellem Funktionsüberblick, App-/HACS-Abgrenzung und Quellenlinks aktualisiert.
- Release-Checkliste verbindlich dokumentiert: Versionsgleichheit, Hinweise im Add-on, HACS-README, Kartenanleitungen, Changelog und Cache-Ressourcen prüfen.
- Keine Änderung am SIP-Routing oder der Asterisk-Konfiguration.

## 1.19.39 – Aufgeräumter Status im Calling-Card-Kopf

- Der Statuspunkt der eigenen Nebenstelle hat keinen grauen Hintergrundkreis mehr.
- Die redundante Anzeige „AMI verbunden“ entfällt; „Daten veraltet“ bleibt als Warnung erhalten.
- Der Status der eigenen Nebenstelle bleibt grün/rot/gelb und lässt sich antippen.

## 1.19.38 – Eigene Nebenstelle im Kopf der Calling Card

- Eigene Nebenstelle (im Zahnrad unter „Eigene Nebenstelle“) wird aus der normalen Kontaktliste ausgeblendet.
- Oben im Kartenkopf zeigt ein kompakter Statusknopf die eigene SIP-Erreichbarkeit: grün = durch Asterisk erreichbar bestätigt, rot = nachweislich nicht erreichbar, gelb = ungeprüft oder keine aktuellen Daten.
- Tippen auf den Statusknopf öffnet den Bearbeitungsmodus zur Auswahl der eigenen Nebenstelle.
- Die Summen Erreichbar/Offline/Gesamt zählen nur noch andere, tatsächlich auswählbare Kontakte.
- SIP-Core-Anrufknöpfe der übrigen Kontakte bleiben erhalten.

## 1.19.37 – Browser-Mod-Zuordnung zentral pro Teilnehmer

- Teilnehmer-Tabelle: `Browser Mod` erhält die globale Visibility-Entity (sensor.* oder binary_sensor.*).
- Die Zuordnung wird persistent im SIP-Manager-Anlagenmodell gespeichert und alle 10 Sekunden im HA-Statussensor als `browser_mod_entities` publiziert.
- Calling Card liest die Zuordnung zentral; frühere lokale Browser-Mod-Eingaben haben keinen Vorrang mehr. ✎ bearbeitet nur den lokalen Anzeigenamen.
- Veraltete manuelle YAML-Zuordnung bleibt als Fallback nutzbar, solange kein zentraler Wert für den Teilnehmer hinterlegt ist.
- Für alle Endgeräte dieselbe Zuordnung, unabhängig von ihrer lokalen Kartenkonfiguration.

## 1.19.36 – OPTIONS-Erreichbarkeitsprüfung pro Teilnehmer

- Teilnehmer-Tabelle: neues Feld **OPTIONS (s)** für `qualify_frequency` je Teilnehmer.
- Leer = vorhandenen Asterisk-Wert übernehmen; `0` = SIP-OPTIONS-Prüfung deaktiviert; `30` = alle 30 Sekunden prüfen. Erlaubt sind ganze Zahlen von 0 bis 3600.
- Anlagenmodell validiert und speichert den Wert dauerhaft; bestehende Teilnehmer ohne Angabe bleiben unverändert.
- Asterisk-Generator schreibt `qualify_frequency` im verwalteten PJSIP-AoR. Für bereits vom Asterisk-Add-on erzeugte Teilnehmer wird ein `(+type=aor)`-Override erzeugt.
- Änderungen wirken erst nach **Speichern → Erzeugen & Übernehmen** und Asterisk-Konfigurationsneuladen.
- Eine aktive OPTIONS-Prüfung macht nur tatsächlich registrierte und antwortende SIP-Kontakte grün; 0 Kontakte im AMI-Sensor müssen gesondert geprüft werden.
- Nicht live gegen die Asterisk-Installation getestet.

## 1.19.35 – Anrufberechtigung in Calling Card

- SIP-Manager veröffentlicht nur Nebenstellen-Berechtigungen im Statussensor, ohne SIP-Zugangsdaten.
- Im Zahnrad kann die eigene Nebenstelle gewählt werden. Die Karte prüft Anrufziele und „Angerufen von“; bei gesperrten Zielen steht ⛔ statt des Hörers.
- Ohne ausgewählte eigene Nebenstelle erfolgt keine irreführende Sperranzeige. Auswahl ist lokal pro Browser/Karte.
- SIP-Erreichbarkeit ist unabhängig von Anrufberechtigungen und wird weiterhin über Asterisk-Kontakte beurteilt.

## 1.19.34 – SIP-Hörersymbol wieder sichtbar

- Regression aus 1.19.33 korrigiert: Native SIP-Core-Anrufkomponente nicht mehr auf kleine Box zugeschnitten; stattdessen zentriert und maßstabsgetreu skaliert.
- Individuelle Hörergröße 24–50 px und dynamische Zeilenhöhe bleiben erhalten.
- SIP-Core-Karten erhalten aktualisierte Home-Assistant-Zustände auch dann, wenn die Calling Card nicht neu aufgebaut wird.
- Frontend-Syntax geprüft; Darstellung auf echten HA/iOS-Geräten noch zu testen.

## 1.19.33 – Hörergröße und flache Statusfelder

- Der SIP-Core-Anrufknopf wird mittig im Teilnehmerfeld platziert; seine sichtbare Größe folgt dem einstellbaren Hörerwert 24–50 px ohne die bisherige pauschale 90-px-Skalierung.
- Teilnehmerzeilen passen ihre Mindesthöhe dynamisch an die Hörergröße an.
- Die drei Statusfelder Erreichbar/Offline/Gesamt sind deutlich flacher (weniger Padding, kompakte Beschriftungen und Zahlen).
- Keine Änderung der SIP-Vermittlung. Darstellung der SIP-Core-Komponente auf iOS muss noch praktisch geprüft werden.

## 1.19.32 – AMI-Kontaktzuordnung nach offizieller Asterisk-Dokumentation

- Statusabfrage verwendet das dokumentierte `ContactList.Endpoint` unmittelbar zur Zuordnung von SIP-Kontakten zum Teilnehmer.
- `EndpointList.Aor` (Singular) wird zusätzlich zur bisherigen Variantenunterstützung berücksichtigt.
- Rückfallzuordnung über AoR und Contact-ObjectName bleibt bestehen.
- `NonQualified` und fehlende Kontaktprüfung werden nicht fälschlich als nachweislich offline klassifiziert.
- Die Asterisk-Anrufvermittlung und der Ringback-Ton bleiben unverändert. Keine Änderungen an pjsip.conf.
- Live-Test mit der konkreten Asterisk-Installation noch offen.

## 1.19.31 – Hörergröße in der Calling Card einstellbar

- Zahnrad-Bearbeitungsmodus: Regler **Hörergröße** von 24 bis 50 px, zusätzlich zur Schriftgröße.
- Einstellung wird lokal pro Karte/Browser gespeichert.
- SIP-Core-Anrufkomponente wird entsprechend skaliert, ohne die feste Teilnehmerzeilenhöhe von 50 px zu vergrößern.

## 1.19.30 – Teilnehmerzeilen auf 50 px begrenzt

- Der eingebettete SIP-Core-Anrufknopf beeinflusst die Teilnehmerzeilenhöhe nicht mehr: eigene absolute Positionierung und kompakte Skalierung.
- Teilnehmerzeilen haben eine feste Höhe von 50 px, unabhängig von der eingebetteten SIP-Core-Kartenhöhe.
- Die Direktanruf-Funktion bleibt eingebunden. Darstellung auf iOS noch nicht live geprüft.

## 1.19.29 – Kompakte Calling Card

- Kürzere Teilnehmerzeilen auch bei großer Schrift; Name einzeilig und gekürzt statt Zeilenumbruch.
- Keine Anzeige bei Browser Mod sichtbar; sonst nur `BM n.ok` in Rot.
- Ungeprüfter SIP-Kontakt nur als gelbes Fragezeichen mit Tooltip.
- Kompaktere Nebenstellenanzeige ohne 0-Kontakt-Text; Statistik zeigt Offline getrennt von Ungeprüft.
- Direkter SIP-Core-Anrufknopf bleibt sichtbar.

## 1.19.28 – Direktanruf und Schriftgröße der Calling Card

- Standardansicht: Pro Teilnehmer wird die offizielle SIP-Core-Komponente `custom:sip-call-button` für Direktanrufe eingebettet. Verwendet die bestehende SIP-Core-Anrufvermittlung und zeigt deren eigenen Anruf-/Auflegezustand.
- Zahnrad-Bearbeitungsmodus: Schriftgrößenregler (11–24 px) für Teilnehmernamen, Nebenstelleninformationen, Statusbadges und Kartentitel.
- Schriftgröße wird pro Browser und Karte gespeichert; keine Änderung des zentralen Teilnehmernamens.
- Bei fehlender SIP-Core-Karte wird ein Hinweis angezeigt. Live-Funktionstest mit HA/SIP Core steht noch aus.

## 1.19.27 – Bearbeitungsmodus der Calling Card

- Zahnrad rechts im Kartenkopf schaltet Bearbeitung an; im Standardmodus keine Bearbeiten-/Löschen-Knöpfe und keine Ziehgriffe.
- Dropdown zum Hinzufügen nur im Bearbeitungsmodus.
- Mit Häkchen wieder zur normalen Anzeige.
- Ein direkter Hörersymbol-Anruf ist noch nicht implementiert; erst mit verifizierter SIP-Core-Anruf-API.

## 1.19.26 – Browser-Mod-Entity-Fix

- Calling Card: gültige Entity-ID wie `sensor.ipad_gang_browser_visibility` wird wieder akzeptiert. Fehlerhafte Regex-Escapesequenz korrigiert.
- HACS-Bundle und App-Frontend synchronisiert.

## 1.19.25 – Calling Card: Teilnehmer sortieren und bearbeiten

- Reihenfolge per Ziehgriff (Pointer Drag & Drop, auch Touch-Geräte) verändern.
- ✎ öffnet die Bearbeitung für lokalen Anzeigenamen und Browser-Mod-Visibility-Entity.
- ✕ entfernt den Teilnehmer ausschließlich aus der Calling Card, **nicht** aus Asterisk oder dem SIP-Manager-Anlagenmodell.
- Anzeige-Reihenfolge, Auswahl und Kartenbearbeitungen werden lokal pro Browser gespeichert; auf anderen Geräten nicht automatisch synchron.
- Name kommt standardmäßig weiter aus dem SIP Manager.
- Die neuen Funktionen betreffen die Calling Card, nicht die produktive Anrufvermittlung.

## 1.19.24 – SIP-Erreichbarkeit korrigiert

- AMI-Kontaktkennung nun kompatibel mit AOR, Aor, AorName und ObjectName-Formaten wie `104/sip:...`.
- Positiven Kontaktstatus `Reachable` aus PJSIPShowContacts auswerten.
- Fehlt die eindeutige Kontaktzuordnung, erscheint **Ungeprüft** statt fälschlich **Nicht registriert/Nicht erreichbar**.
- Die SIP-Registrierung der HA Companion App ist unabhängig davon, ob Home Assistant aktuell geöffnet ist.

## 1.19.23 – Klingeltonausgabe je Teilnehmer (HA-Mediaplayer)

- Anlagenmodell: `ring_output` (Standard/HA-Mediaplayer), `ring_player`, `ring_media`, persistente Validierung.
- Teilnehmer-Tabelle: Modus, Ziel-Mediaplayer und /local/-Audiodatei konfigurierbar.
- AMI-DialBegin, DialEnd, BridgeEnter und Hangup steuern Wiedergabe und Stoppen. Rufgruppen werden über Linkedid koordiniert; 45-s-Sicherheitsablauf.
- Asterisk-Ringback und SIP-Vermittlung unverändert. HA-Audioausgabe setzt erreichbaren HA-Mediaplayer und aktiven Browser voraus.
- **Grenze:** Der eingebaute SIP-Core-Klingelton wird noch nicht automatisch stummgeschaltet; für ausschließlich externes Klingeln muss das in SIP Core separat eingerichtet werden. Verbindliche Klingelgarantie für gesperrte iOS-Geräte besteht nicht.
- Ungetestet mit produktiver SIP-/HA-Anlage; Testanrufe und AMI-Berechtigungen prüfen.

## 1.19.22 – SIP Calling Card / Browser Mod
- Calling Card: Teilnehmer direkt per Dropdown hinzufügen/entfernen, Namen automatisch aus dem SIP-Manager-Anlagenmodell übernehmen. Lokale Auswahl bleibt im Browser erhalten.

- Neu: SIP-Statusmonitor (AMI, 10-Sekunden-Intervall), mit Home-Assistant-Entity `sensor.smartify_sip_teilnehmer`.
- Neu: HACS-Karte `custom:smartify-sip-calling-card` mit Kontaktstatus, Fehlererkennung bei alten Daten und optionalem Browser-Mod-Sichtbarkeitsstatus pro Nebenstelle.
- Kein automatisches Umschreiben von `qualify_frequency`, Asterisk-Dateien oder Registrierungen; bestehende Anlagen bleiben unverändert.
- Dokumentation: `docs/SIP-CALLING-CARD.md`. 
- Hinweis: SIP OPTIONS und Browser Mod können Klingeln unter iOS-Sperrbildschirm nicht garantieren.

## 1.19.21 – Fixierte Spalten in der Teilnehmerübersicht
- Nummer und Name bleiben beim horizontalen Scrollen der Teilnehmer-Tabelle sichtbar.
- Tabellenkopf bleibt beim vertikalen Scrollen fixiert; andere Tabellen sind nicht betroffen.
- Keine Änderungen an Asterisk oder SIP-Konfiguration.

## 1.19.21 – Video-Codecs für externe Linphone-Endpoints
- Codec-Auswahl auch für externe SIP-Teilnehmer in der Teilnehmerübersicht.
- Bestehende Custom-Endpoints erhalten gezielte Video-Codec-Einschränkungen; Audio-Codecs bleiben verfügbar.
- Bei widersprüchlichen Regeln für denselben Endpoint erscheint eine Warnung.
- Vor Übernahme Vorschau prüfen; Live-Test mit Asterisk steht aus.

## 1.19.21 – Codec-Erweiterung für Default-Nebenstellen
- Individuelle Video-Codecs werden nun über einen gezielten Endpoint-Ergänzungsblock in custom/pjsip_custom.conf gesetzt.
- Bestehende Audio-Codecs bleiben erhalten; Authentifizierung und AOR werden nicht neu angelegt.
- Voraussetzung: pjsip_default.conf wird vor pjsip_custom.conf eingebunden.
- Noch kein Live-Test mit Asterisk erfolgt; nach Übernahme aktive Codecs kontrollieren.

## 1.19.21 – Video-Codecs pro Teilnehmer
- Auswahl für Video SIP: Automatisch, VP8, H.264, VP9, VP8 + H.264 oder kein Video.
- Auswahl wird im Anlagenmodell gespeichert und bei verwalteten PJSIP-Endpoints generiert; Audio-Codecs bleiben erhalten.
- Bei Asterisk-Default-Endpoints zeigt die Vorschau eine Warnung, da deren Codec-Freigaben nicht automatisch überschrieben werden.
- Regressionstests ergänzt. Kein automatischer Asterisk-Neustart.

## 1.19.17 – Auto Answer API und Teilnehmerauswahl korrigiert
- Fehlende Route `/api/sip-core/auto-answer/stage` in der expliziten POST-Allowlist ergänzt; behebt HTTP 404 „Auto Answer: Nicht gefunden“.
- Auto-Answer-Anruferliste: Checkbox und Teilnehmername links direkt nebeneinander, statt durch globale Input-Breite über die Karte verteilt.
- Keine Änderung an SIP Core, Asterisk, Popup oder aktiven Auto-Answer-Regeln.

## 1.19.16 – SIP Core Auto Answer pro Nebenstelle und Anrufer
Mitgeliefert: Popup 3.3.13 · Card 2.7.10

- Neue Auto-Answer-Steuerung unter Teilnehmer → SIP Core mit getrennten Einstellungen je Zielnebenstelle und expliziter Anruferfreigabe.
- SIP-Core-Popup prüft bei eingehenden Gesprächen die eigene Nebenstelle und den Anrufer gegen `popup_config.smartify.auto_answer_by_extension`, bevor es `sipCore.answerCall()` aufruft.
- Kein Eintrag = kein automatisches Abheben; Türstationen sind standardmäßig nicht freigegeben.
- Die globale SIP-Core-Option `auto_answer` wird beim Staging ausdrücklich auf `false` gesetzt, weil sie ohne Filter alle Anrufe annimmt.
- Konfiguration wird ausschließlich in den bestehenden YAML-Entwurf übernommen. Aktive Übernahme erfordert wie bisher Prüfung, Diff und explizite Bestätigung samt Backup.
- Nur für Smartify-Popup in SIP Core, nicht Linphone. JavaScript-Syntax statisch geprüft; reale Gerätetests ausstehend.

## 1.19.15 – Bild-in-Bild exakt Ecke auf Ecke
Mitgeliefert: Popup 3.3.12 · Card 2.7.10

- Die Eigenbild-Ecke rechts unten wird pixelgenau auf die sichtbare rechte untere Ecke des Hauptvideobildes gesetzt (0 px Abstand), nicht auf den größeren SIP-Container.
- Berücksichtigt schwarze Balken durch `object-fit:contain`, Video-Seitenverhältnis, Zoom, Bildschirmdrehung und veränderte Containergrößen.
- `ResizeObserver` und Videometadaten aktualisieren die Ausrichtung; Beobachter und Listener werden beim Auflegen entfernt.
- PiP bleibt vollständig innerhalb der sichtbaren Bildfläche; keine Änderungen an SIP-Stream, Hauptvideohöhe oder Popup-Registrierung.
- JavaScript-Syntaxprüfung erfolgreich; reale iPad-Darstellung noch zu testen.

## 1.19.14 – Eigenbild direkt in der Ecke des Hauptvideos
Mitgeliefert: Popup 3.3.11 · Card 2.7.9

- Das lokale Bild-in-Bild wird direkt in SIP Cores Videocontainer (Elternelement von `#remoteVideo`) platziert, statt als separates Element hinter oder außerhalb des Popups.
- Position rechts unten im Hauptvideo, maximal 28 % der Containerbreite (160 px), mit 8 px Abstand; kein Beschnitt, automatische Hoch-/Querformat-Erkennung.
- Wenn das Hauptvideo nicht vorhanden oder ausgeblendet ist, wird kein schwebendes Eigenbild außerhalb des Videos erzeugt.
- SIP-Videoübertragung, Popup-Initialisierung und 60-%-Hauptvideo-Begrenzung bleiben unverändert. Realer iPad-Test steht aus.

## 1.19.13 – SIP-Bild-in-Bild: lokale WebRTC-Verbindung richtig zugeordnet
Mitgeliefert: Popup 3.3.10 · Card 2.7.8

- Quellcode von TECH7Fox SIP Core geprüft: die laufende JsSIP-Sitzung heißt `window.sipCore.RTCSession` und deren PeerConnection `RTCSession.connection`.
- Bild-in-Bild liest den aktiven lokalen Video-Sendertrack aus dieser tatsächlichen Verbindung statt aus nicht existierenden `session/currentSession/activeSession`-Feldern.
- Vorschau nur bei aufgebautem Gespräch, aktivem, nicht stummgeschaltetem lokalen Videotrack und nicht für erkannte Türstationen.
- Seitenverhältnis, 60-%-Hauptvideo, Popup-Registrierung und SIP-Mediensteuerung unverändert.
- Syntax- und statische Strukturprüfung; realer iPad-Test noch ausstehend.

## 1.19.12 – Bild-in-Bild Seitenverhältnis
Mitgeliefert: Popup 3.3.9 · Card 2.7.7

- Lokale SIP-Bild-in-Bild-Vorschau verwendet das reale Videoseitenverhältnis über Videometadaten bzw. Track-Einstellungen und reagiert auf Drehungen.
- Hochformat als Vorschau-Standard, Querformat bei entsprechendem Stream; kein Bildbeschnitt dank `object-fit:contain`.
- Vorschauhöhe auf 30 % der Bildschirmhöhe begrenzt. Hauptvideo bleibt unverändert auf maximal 60 %.
- SIP-Core-Popup-Registrierung und Medienübertragung unverändert; PiP benötigt weiterhin einen zugänglichen lokalen Videotrack. iPad-Laufzeittest ausstehend.

## 1.19.11 – SIP-Bild-in-Bild (experimentell)
Mitgeliefert: Popup 3.3.8 · Card 2.7.6

- Zeigt beim normalen SIP-Teilnehmergespräch das **bereits übertragene lokale Video** klein über der regulären Anzeige, falls SIP Core den aktiven ausgehenden WebRTC-Sendertrack über seine Sitzung zugänglich macht.
- Türstationen mit konfigurierter Tür-/Klingelkennung bleiben ohne lokale Bild-in-Bild-Vorschau.
- Kein zweiter Kamerazugriff, kein Ändern von SIP-Tracks, Audio, Popup-Registrierung oder Videohöhenbegrenzung (60 %).
- Bei SIP-Core-Versionen mit nicht zugänglicher Sitzungs-/Senderstruktur erscheint keine Vorschau; die normale Anrufansicht bleibt erhalten. iPad-Laufzeittest steht aus.

## 1.19.10 – Videohöhe 60 %
Mitgeliefert: Popup 3.3.7 · Card 2.7.5

- SIP-Videohöhe statt 38 % nun maximal 60 % der dynamischen Bildschirmhöhe.
- Zusätzliche Höhenbegrenzung von Bildschirmhöhe minus 260/320 px auf minus 180 px angepasst; gilt auch für die vorhandene go2rtc-Größenbegrenzung.
- Keine Änderungen an SIP-Verbindung, Medienübertragung oder Popup-Registrierung.
- Statische JavaScript-Prüfung durchgeführt; Test auf iPad ausstehend.

## 1.19.9 – SIP-Video-Darstellung (vorsichtiger Versuch)
Mitgeliefert: Popup 3.3.6 · Card 2.7.4

- Videobegrenzung nur mit CSS im Popup und in der Doorstation Card; maximal 38 % der Bildschirmhöhe bzw. mit Platzreserve für Anrufbuttons.
- Kein MutationObserver, keine Änderung an nativen SIP-Medienelementen, deren Tracks oder an der Registrierung des Popups aus 1.19.8.
- Die Darstellung nativer SIP-Core-Videos in verschachtelten Shadow-DOM-Strukturen kann mit diesen CSS-Regeln möglicherweise nicht erreicht werden. Popup- und Video-Laufzeittest am iPad steht aus.

## 1.19.8 – Popup-Initialisierung
Mitgeliefert: Popup 3.3.5 · Card 2.7.2

- Popup-Registrierung nach dem Laden der SIP-Core-Komponente nochmals abgleichen, sodass ein bereits stattgefundenes `sipcore-update` nicht zu einem fehlenden Popup führt.
- Keine Manipulation am nativen SIP-Video; alle Änderungen aus 1.19.6 bleiben zurückgenommen.
- Rückmeldung über ausbleibende Popups unter 1.19.7. Ursache kann auch ein veraltetes/dupliziertes Dashboard-Skript sein; diese Änderung adressiert gezielt einen möglichen Initialisierungswettlauf.
- JavaScript-Syntax geprüft; iPad-Laufzeittest ausstehend.

## 1.19.7 – Hotfix
Mitgeliefert: Popup 3.3.3 · Card 2.7.2

- Rollback der SIP-Core-Videobegrenzung aus 1.19.6 wegen gemeldetem Popup-Ausfall.
- Wiederherstellung der unveränderten Popup-/Card-Implementierung aus 1.19.5; Anlage, SIP-Daten, Asterisk und Videokonfiguration unverändert.
- Keine neue native SIP-Video-Begrenzung; iPad-Laufzeittest noch notwendig.

## 1.19.6
Mitgeliefert: Popup 3.3.4 · Card 2.7.3

- SIP-Core-Videobild im Popup und in der eingebetteten SIP-Karte auf die sichtbare Bildschirmhöhe begrenzt. Scrollen zu den Anrufbuttons soll damit auf iPad und iPhone vermieden werden.
- Berücksichtigt den verfügbaren Viewport dynamisch statt den vom iOS Companion nicht zuverlässig an JavaScript übertragenen Seitenzoom zu schätzen.
- go2rtc-Anzeige, Türsteuerung sowie Audio-/Videoübertragung bleiben unverändert.
- Statische JS-Syntaxprüfung erfolgreich; die genaue SIP-Core-DOM-Struktur und der echte iPad-Laufzeittest stehen aus.

## 1.19.5
Mitgeliefert: Popup 3.3.3 · Card 2.7.2

- Popup-Video passt seine Höhe automatisch an die aktuelle Bildschirmhöhe an; für SIP-Core-Anruftasten wird vertikaler Platz reserviert. CSS-dvh berücksichtigt Geräteausrichtung und veränderliche Browserleisten.
- Auch das Videofeld der Doorstation Card wird anhand der verfügbaren Bildschirmhöhe und des eingestellten Seitenverhältnisses begrenzt.
- Vorhandene Video-Ein/Aus-Buttons und Audio-/SIP-Funktionen bleiben unverändert.
- Noch kein Zwei-Wege-SIP-Video; tatsächlicher iPad-/Home-Assistant-Laufzeittest ausstehend.

## 1.19.4
Mitgeliefert: Popup 3.3.2 · Card 2.7.1

- Bei jedem App-Start werden Card, Popup und gemeinsames HACS-Bundle automatisch aus der App nach `/homeassistant/www/smartify/` installiert bzw. aktualisiert. Öffentlich erreichbar unter `/local/smartify/`. Schreibvorgänge atomar und ausschließlich in Smartifys eigenem Verzeichnis; keine Asterisk- oder SIP-Core-Dateien betroffen.
- HA-Konfigurationsverzeichnis als `homeassistant_config:rw` gemountet. Fehler beim Kopieren verhindern den Start des Managers nicht, werden aber im Protokoll ausgegeben.
- **Ersteinrichtung:** Dashboard-Ressource `/local/smartify/smartify-sip-manager.js?v=1.19.4` als JavaScript-Modul einmalig registrieren; eventuell vorhandene HACS-Ressource desselben Bundles deaktivieren, um Doppelregistrierungen zu verhindern.
- **Wichtig:** Die Home-Assistant-Dashboard-Ressourcenregistrierung wird nicht automatisch verändert. Bei weiteren Updates kann für die Browser-Cache-Aktualisierung eine neue Versionskennung in der Ressourcen-URL oder das Leeren des Frontend-Cache nötig sein.
- Prüfungen statisch; HA-Installationstest ausstehend.

## 1.19.3
Mitgeliefert: Popup 3.3.2 · Card 2.7.1

- **Doorstation Card und Popup:** Button zum Anzeigen/Ausblenden des empfangenen go2rtc-Kamerabildes. Beim Ausblenden wird der Stream-Player entfernt statt nur visuell verdeckt; Audio und SIP-Verbindung werden nicht verändert.
- Das Popup setzt den Anzeigestatus nach dem Schließen zurück. Die Doorstation Card lässt das SIP-Core-Original mit dessen Mikrofon- und Kamerasteuerung unverändert eingebettet.
- **Noch nicht enthalten:** echtes bidirektionales SIP-Video mit zwei gleichzeitig dargestellten Medienstreams sowie zuverlässiges Stoppen des lokalen Video-Sendetracks durch Smartify. SIP Core kennzeichnet `sip_video` weiterhin als experimentell.
- Aufruf- und Medienlogik von Asterisk unverändert. Live-Test in Home Assistant/SIP Core ausstehend.

## 1.19.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Im Hauptbereich **Teilnehmer** einen eigenen Unterreiter **Anlage · Modell · Netzwerk** eingeführt.
- Der Unterreiter **Teilnehmer** zeigt die Teilnehmer-, Kamera- und Rufgruppenübersicht jetzt direkt am Anfang, ohne die langen Anlagenfelder davor.
- Beide Reiter verwenden weiterhin dasselbe gespeicherte Anlagenmodell und dieselben Feld-IDs; die Änderungserkennung und der globale Speichern-Button funktionieren auch im neuen Anlagenreiter.
- Alle vorhandenen Backend-Funktionen und Daten bleiben erhalten. Statische UI-Checks durchgeführt; praktischer HA-Test ausstehend.

## 1.19.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Anlagenkonfiguration neu angeordnet: links ausschließlich Name, Kunde und Nummernbereich; rechts die Modellaktionen und darunter die eigene Karte **Netzwerk & Adressen** mit LAN-IP, Tailscale-Name, Tailscale-IP und go2rtc-HTTPS-Adresse.
- Alle Feld-IDs, Werte, Erkennung, Speichern, Import und Export unverändert; Darstellung auf kleinen Displays weiterhin einspaltig.
- HTML-Struktur und Elementzuordnung geprüft; Live-Darstellung auf Home Assistant ausstehend.

## 1.19.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Die bisher überlappenden Hauptbereiche zu fünf Arbeitsbereichen zusammengefasst: **Übersicht**, **Teilnehmer**, **Rufgruppen & Verbindungen**, **Türstation & Video**, **System & Expertenwerkzeuge**.
- Sämtliche bisherigen Bearbeitungs- und Diagnoseansichten bleiben über Unterreiter erreichbar; manuelle Asterisk-, SIP-Core- und Dialplan-Editoren bleiben als Expertenfunktionen erhalten. Keine vorhandenen Daten oder API-Routen gelöscht.
- Redundante lokale PJSIP- und Dialplan-Reload-Schaltflächen ausgeblendet; der globale **Asterisk Reload** bleibt der zentrale, bestätigungspflichtige Weg.
- Navigation für Tablet/Smartphone responsiv angepasst; globale Buttons **Speichern / Änderungen laden / Asterisk Reload** bleiben erhalten.
- Neue Regressionstests für Reiter-Zuordnung, geschützte Bedienelemente und Reload-Einbindung ergänzt. Statische Prüfungen durchgeführt; Home-Assistant-Ende-zu-Ende-Test ausstehend.

## 1.18.16
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Die drei globalen Aktionen **Speichern**, **Änderungen laden** und **Asterisk Reload** besitzen nun einen einheitlichen Bestätigungsdialog mit ausdrücklich beschrifteten Schaltflächen **OK** und **Abbrechen**.
- **Abbrechen** beziehungsweise das Schließen des Dialogs führt keine der Aktionen aus. Der doppelte Browser-Bestätigungsdialog bei „Änderungen laden“ wurde entfernt.
- Die getrennten Schritte Speichern, Konfiguration übernehmen und PJSIP/Dialplan neu laden bleiben bestehen.
- Laufzeittest auf Home Assistant ausstehend.

## 1.18.15
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Rufnummernprüfung: Der Endpoint-Scanner berücksichtigt nur noch `pjsip*.conf` statt sämtliche Asterisk-`.conf`-Dateien. Unbeteiligte Dateien wie `default/minivm.conf` erzeugen dadurch keine irreführenden UnicodeDecodeError-Warnungen mehr.
- Tatsächlich nicht lesbare PJSIP-Dateien werden weiterhin gemeldet; die separate Dialplan- und Nummernreservierungsprüfung bleibt unverändert.
- Codeänderung im Repository; Live-Test auf Home Assistant ausstehend.

## 1.18.14
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Globaler Button **„Speichern“** in der dauerhaft sichtbaren Aktionsleiste: speichert das Anlagenmodell mit Teilnehmern und Rufgruppen über den bestehenden Speicherweg.
- Der Button ist auf die Bereiche „Anlage & Teilnehmer“ und „Rufgruppen-Manager“ begrenzt; andere Editoren behalten ihre eigenen Speicheraktionen.
- Die drei Schritte bleiben getrennt: **Speichern → Änderungen laden → Asterisk Reload**.
- GitHub-Merge bestätigt; vollständiger Laufzeittest auf Home Assistant nicht dokumentiert.

## 1.18.13
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Dauerhaft sichtbare, auch beim Scrollen erreichbare Aktionsleiste mit **„Änderungen laden“** und **„Asterisk Reload“**.
- „Änderungen laden“ übernimmt gespeicherte Teilnehmer-/Rufgruppenänderungen in die Asterisk-Konfigurationsdateien über die vorhandene Vorschau, Validierung und Backup-Funktion; ungespeicherte Modelländerungen werden abgewiesen.
- „Asterisk Reload“ führt nach Bestätigung über AMI nacheinander `pjsip reload` und `dialplan reload` aus.
- Laufzeittest auf Home Assistant ausstehend.

## 1.18.12
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Gemeinsames Asterisk-Auth-Passwort wird für die SIP-Core-Synchronisierung aus der gemounteten `default/pjsip_default.conf` ermittelt statt aus der Supervisor-API.
- Die Erkennung verlangt genau ein gemeinsames, nichtleeres Auth-Passwort; mehrere unterschiedliche Passwörter führen zu einem Abbruch.
- **Einschränkung:** Ein gemeinsames Auth-Passwort in dieser Datei bestätigt nicht unabhängig den Zustand des Asterisk-Schalters `auto_add`. Vor Überschreiben manueller Nebenstellen Vorschau prüfen.
- Live-Validierung der Erkennung und Übernahme ausstehend.

## 1.18.11
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Neue SIP-Core-Funktion **„Auto Add Secret prüfen“**: zeigt Status und Abweichungen vorhandener SIP-Core-Passwörter, ohne das Geheimnis selbst im Browser auszugeben.
- Explizite Aktion zum Überschreiben bestehender SIP-Core-Passwörter mit dem gemeinsamen Asterisk-Secret; mit Bestätigungsphrase, Änderungsprüfung, Backup und Übernahme über den vorhandenen SIP-Core-Optionsdialog.
- Erste Erkennung per Supervisor-API erwies sich auf der betroffenen Installation als unzureichend (Optionen nicht in der API-Antwort enthalten); in 1.18.12 auf Dateiauswertung umgestellt.
- Automatisierte Tests ergänzt, aber erfolgreiche Ende-zu-Ende-Prüfung nicht bestätigt.

## 1.18.10
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Startfehler aus 1.18.9 behoben:** `migration.py` ins Docker-Image aufgenommen.
- Python-Imports der Migrationsfunktionen für den Start über `app.py` korrigiert.
- Kein vollständiger HA-/Asterisk-Funktionstest bestätigt.

## 1.18.9
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Experimentelle Dialplan-Migration: einfache, klar erkannte Legacy-Routen sollen nach konservativer Prüfung aus den verwalteten Kontexten entfernt und aus dem Manager-Modell neu erzeugt werden; komplexe oder doppelte Routen werden blockiert.
- Gezielte Regressionstests und ein GitHub-Actions-Testworkflow ergänzt.
- **Bekannter Release-Fehler:** Die neue Datei `migration.py` war nicht im Dockerfile enthalten; die App startete wegen `ModuleNotFoundError` nicht. Korrigiert in 1.18.10.

## 1.18.8
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- AMI-Host standardmäßig automatisch aus Asterisk-Add-on-Slug ableiten (z. B. `3e533915_asterisk` → `3e533915-asterisk`); vorhandener manueller Host bleibt gültig.
- Alte Loopback-Einstellung `127.0.0.1` wird für diesen getrennten Manager-Container ebenfalls automatisch korrigiert.
- Prüfbericht: aktiver go2rtc-Kamerastream bedeutet nicht, dass das zugeordnete HA-Gerät selbst Video sendet; Meldung entsprechend präzisiert.
- Automatische Host-Auflösung mit Regressionstests abgesichert; Live-Verbindungstest in HA ausstehend.

## 1.18.7
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Erreichbarkeitsauswahl bei HA-Geräten, SIP-Telefonen, Türstationen und Cloud-Konten einheitlich in die Tabellenspalte „HA-Benutzer / Endpoint“ verschoben.
- Zweispaltige, separat aufklappbare Freigaben bleiben erhalten; keine Berechtigungslogik geändert.
- JavaScript-Syntax und Strukturprüfung erfolgreich; Live-HA-Test ausstehend.

## 1.18.6
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Fix: „Nur ausgewählte zulassen“ lässt sich für beide Richtungen wieder ausschalten. Eine alte Auswahl im DOM darf die aufgehobene Einschränkung nicht erneut aktivieren.
- JavaScript-Syntax und vier gezielte Zustandswechsel-Simulationen geprüft.

## 1.18.5
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Erreichbarkeit unter Teilnehmer: ausgehende und eingehende Anrufberechtigungen zweispaltig nebeneinander.
- Beide Berechtigungslisten besitzen eigene Pfeile zum Ein- und Ausklappen; jede auswählbare Nummer wird in einer eigenen Zeile dargestellt.
- Cloud-Konten verwenden dieselbe Ansicht; ihre Gruppen-/Asterisk-Regeln bleiben unverändert.
- UI-Syntaxprüfung erfolgreich, Home-Assistant-Laufzeittest ausstehend.

## 1.18.4
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Kritischer Hotfix:** Python-Syntaxfehler in `generator.py` (Zeile 851, nicht geschlossene Zeichenkette) beseitigt. Dieser Fehler verhinderte den Start von 1.18.3.
- Keine beabsichtigte Änderung an den Rufgruppen- oder Cloud-Berechtigungen gegenüber 1.18.3.

## 1.18.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Cloud-Konten: Eigene Berechtigung „direkt über Asterisk anrufbar nur von“. Eine leere aktivierte Liste blockiert lokale Direktwahl auf die Cloud-Nebenstelle (z. B. 907); der Gruppenruf auf 601 stellt weiterhin zu.
- Teilnehmergrafik: keine doppelte Verbindung Cloud → Gruppe; eingehende Cloud-Direktwahl respektiert die eingestellte Liste.
- **Wichtig:** Direkte Cloud-zu-Cloud-Gespräche zwischen Linphone-Konten laufen außerhalb von Asterisk und werden durch diese Einstellungen nicht gesperrt. Bestehende manuelle Dialplan-Einträge werden nicht überschrieben und müssen separat geprüft werden.
- Regressionstest für Rufgruppe 601, direkte Cloud-Verbindung und gesperrte Asterisk-Direktwahl ergänzt.

## 1.18.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Verbindungen: Cloud-Teilnehmer zeigen nur ausdrücklich freigegebene Rufziele sowie berechtigte Gruppen-/Mitgliederrufe an. Bloße Dialplan-Kontext-Treffer werden nicht mehr als Teilnehmerfreigabe ausgewiesen.
- Nicht freigegebene Nummern, die im Asterisk-Eingangskontext dennoch erreichbar erscheinen, werden als Prüfhinweis angezeigt. Das ist eine Diagnose, **keine neue Durchsetzungssperre**; bestehende manuelle Einträge und Dialplan-Muster müssen separat kontrolliert werden.

## 1.18.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Teilnehmernummern und Namen werden sofort in den Erreichbarkeits-Auswahllisten der anderen Teilnehmer aktualisiert, ohne die gesamte Tabelle neu zu zeichnen.
- Bestehende Checkbox-Auswahlen und der aufgeklappte Zustand bleiben dabei erhalten; bei Umnummerierungen werden vorhandene Freigaben für diese Nummer mitgezogen.

## 1.18.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Neu: Erreichbarkeit pro Teilnehmer** (Anlage → Teilnehmer, aufklappbar unter dem Namen von SIP-Telefon, HA-Gerät und Türstation).
  - **darf nur anrufen**: begrenzt, welche Nummern (Teilnehmer, Rufgruppen, Cloud-Teilnehmer) der Teilnehmer wählen darf.
  - **darf nur angerufen werden von**: begrenzt, wer den Teilnehmer direkt wählen darf.
  - Ohne Haken gilt wie bisher keine Einschränkung. Der Manager erzeugt dafür Dialplan-Einträge mit Prüfung (abgewiesene Anrufer: `Hangup(21)`); ein vorhandener eigener Eintrag derselben Nummer wird nicht überschrieben, sondern gemeldet.
  - Rufgruppen steuern ihre Anrufer weiterhin selbst; „darf nur anrufen“ gilt auch für Rufgruppen-Nummern. „Verbindungen“ zeigt gesperrte Wege nicht mehr an.

## 1.17.5
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Fix: Gespräch bricht direkt nach dem Abnehmen ab** (Anruf vom Handy über `linphone-in`). Linphone bietet mit Verschlüsselung `RTP/SAVPF` + `a=crypto` an. Wegen `media_use_received_transport` antwortete Asterisk ebenfalls mit `RTP/SAVPF`, aber ohne Schlüssel – Linphone legte sofort auf (BYE, Q.850 cause 16). Der Manager setzt am Eingang jetzt zusätzlich **`media_encryption=sdes`** und **`media_encryption_optimistic=yes`**: verschlüsselt, wenn das Handy es anbietet, sonst unverschlüsselt (geprüft gegen `res_pjsip_sdp_rtp.c`). Der Ausgang `linphone-cloud` bleibt unverändert.
- Neu angelegte Eingänge bekommen diese Zeilen gleich mit.

## 1.17.4
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Verbindungen**: Ein Cloud-Teilnehmer wird nur noch als Anrufer einer Rufgruppe gezeigt, wenn ihn die Gruppe auch durchlässt (Anrufer, Mitglied mit „Mitglieder dürfen anrufen“, „gleiches Handy wie“ oder Freigabe unter „darf anrufen“). Vorher reichte es, dass die Nummer im Kontext des Eingangs steht – z. B. erschien „908 → 600“, obwohl der Dialplan 908 abweist.

## 1.17.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Dringende Korrektur zu 1.17.2:** Die Option heißt in Asterisk `media_use_received_transport`, nicht `use_received_transport`. Mit der falschen Zeile hat Asterisk die Anschlüsse `linphone-in`/`linphone-cloud` gar nicht geladen („Identify … points to endpoint 'linphone-in' but endpoint could not be found“, „No matching endpoint found“). Erzeugen & Übernehmen korrigiert vorhandene falsche Zeilen automatisch.
- Neuer Test: Jede Endpoint-Option, die der Manager schreibt, wird gegen die Optionsliste aus dem Asterisk-Quellcode (res_pjsip) geprüft – so etwas kann nicht mehr unbemerkt ausgeliefert werden.

## 1.17.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Fix „Couldn't negotiate stream … audio (nothing)“ bei Linphone**: Linphone bietet mit eingeschaltetem **AVPF** (Standard bei linphone.org-Konten) das Profil `RTP/AVPF` an. Asterisk lehnt das ohne `use_avpf=yes` ab (`check_endpoint_media_transport` in `res_pjsip_sdp_rtp.c`). Der Manager setzt an den Anschlüssen der Cloud-Teilnehmer (Eingang/Ausgang) jetzt **`use_received_transport=yes`** – Asterisk übernimmt dann das angebotene Profil, egal ob AVP oder AVPF. Steht dort schon `use_avpf=` oder `use_received_transport=`, bleibt es unverändert.

## 1.17.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Eingänge: „weitere IPs“ heißt jetzt „weitere IPs (ohne Teilnehmer)“ und wiederholt keine IP mehr, die schon bei einem Teilnehmer unter „IP Handy“ steht. Beim Ergänzen übernommene Doppel (z. B. 100.64.10.20 bei LP Push Raphael und zusätzlich beim Eingang) werden beim Speichern entfernt – an der Wirkung in Asterisk ändert sich nichts.

## 1.17.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Realm automatisch**: Der Manager setzt den Anmelde-Bereich (`realm`) bei SIP-Telefonen und Türstationen selbst – auf die Domain, mit der sich das Gerät anmeldet:
  - Handy über Tailscale („gleiches Handy wie …“ gesetzt) → **Tailscale-IP von HA**
  - alle anderen → **LAN-IP von HA**
  - das Feld „Domain/Realm“ ist nur noch für Ausnahmen; leer zeigt es „auto: …“.
- Neues Feld **Tailscale-IP von HA** unter Anlage (wird bei „Erkennen“ gefunden, wenn das Tailscale-Add-on ohne Userspace-Networking läuft; sonst aus der Tailscale-App eintragen). Prüfbericht warnt, wenn sie für ein Handy über Tailscale fehlt.
- Hinweis: Bestehende SIP-Telefone/Türstationen bekommen beim nächsten Übernehmen `realm=<LAN-IP>`; übliche Geräte melden sich damit problemlos neu an.

## 1.16.4
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **„gleiches Handy wie“** bei SIP-Telefonen: Ein SIP-Konto (z. B. 130 über Tailscale) kann einem Cloud-Teilnehmer (Linphone-Konto mit Push) zugeordnet werden, wenn beide auf demselben Handy laufen.
  - Ruft das Handy über 130 eine Rufgruppe an, klingelt sein eigenes Linphone-Konto **nicht** mit (der Anrufer wird übersprungen) – auch ohne das Mitglieder-Häkchen, wenn 130 als Anrufer eingetragen ist.
  - Mit „Mitglieder dürfen die Gruppe anrufen“ zählt 130 automatisch als Mitglied, wenn das zugehörige Linphone-Konto unter „Klingelt bei“ steht – 130 muss nicht extra unter Anrufer.

## 1.16.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Neues Feld „Domain/Realm“** bei SIP-Telefonen und Türstationen (Spalte Zugang). Linphone legt die Zugangsdaten für den Bereich = Domain ab (z. B. die Tailscale-IP von HA); fragt Asterisk nach dem Standard-Bereich „asterisk“, scheitert die Anmeldung mit „Failed to authenticate“, obwohl das Passwort stimmt. Mit Realm = Domain klappt sie.
- Ein von Hand in `pjsip_custom.conf` gesetzter `realm=` bleibt beim Übernehmen erhalten.
- „Zugang“ zeigt als Server die eingetragene Domain/Realm, wenn gesetzt.

## 1.16.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Fehlerbehebung:** Wurde die letzte „IP Handy“ eines Eingangs gelöscht, blieb die alte IP in der identify-Zeile von Asterisk stehen. Jetzt entfernt „Erzeugen & Übernehmen“ die Zuordnung (mit Backup und Warnung in der Vorschau); werden nur einzelne IPs gelöscht, wird die `match=`-Zeile wie bisher angepasst.
- Hinweis unter „Eingänge“: Änderungen wirken in Asterisk erst nach „Erzeugen & Übernehmen“ (Speichern ändert nur das Modell).

## 1.16.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- „Vorhandene Rufgruppen und Rufziele aus dem Dialplan“: nur noch **eine** Scrollleiste (Tabelle höher, Kopfzeile bleibt beim Scrollen stehen).
- Vom Manager verwaltete Einträge, die je Kontext einmal im Dialplan stehen (z. B. 600 in `default` und `linphone-in`), erscheinen als **eine** Zeile „Smartify (verwaltet)“ mit beiden Kontexten und dem Knopf „Im Rufgruppen-Manager“ statt Bearbeiten in der Tabelle.

## 1.16.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Audio-Fix für Linphone**: „Couldn't negotiate stream … audio“ am Eingang und „Everyone is busy/congested“ beim Weiterruf entstanden, weil `linphone-in` nur alaw,ulaw erlaubte und Linphone (je nach Einstellung) nur Opus anbietet. Der Manager ergänzt jetzt bei allen Anschlüssen der Cloud-Teilnehmer (Ausgang und Eingang) **opus,ulaw,alaw** in der allow-Zeile (Abschnitt bleibt an seinem Platz).
- **IP direkt beim Cloud-Teilnehmer**: neues Feld „IP Handy“ neben Name, Adresse und Eingang (z. B. Tailscale-IP). Die Quell-IPs des Eingangs ergeben sich daraus automatisch; unter „Eingänge“ steht nur noch „nimmt an von: Raphael: 100.64.10.20 · …“ plus optional weitere IPs. Beim „ergänzen“ wandert eine vorhandene Eingangs-IP zum einzigen Nutzer.
- **Erkennung am Eingang über die IP**: Teilen sich mehrere Handys einen Eingang, unterscheidet der Dialplan sie bevorzugt über die Geräte-IP (`CHANNEL(pjsip,remote_addr)`), nur ohne IP über den Linphone-Benutzernamen.
- **Aufgeräumt**: Jeder Kontext prüft nur die Anrufer, die dort ankommen können (in `default` z. B. nur 104, in `linphone-in` nur die Handys); überspringen ebenso.
- **Alte Einträge des Eingangs-Werkzeugs** (z. B. `[linphone-in]` 104) übernimmt der Manager automatisch, sobald dieselbe Nummer über „darf anrufen“ oder eine Rufgruppe von ihm eingetragen wird; sonst bleiben sie stehen (mit Hinweis).

## 1.15.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Vorschau warnt, wenn bei „Mitglieder dürfen die Gruppe anrufen“ ein Cloud-Mitglied **keinen Eingang** hat – dann kann es die Gruppe vom Handy nicht erreichen („extension not found in context …“).

## 1.15.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Rufgruppen: neues Häkchen **„Mitglieder dürfen die Gruppe anrufen (Anrufer wird übersprungen)“**.
  - Alle unter „Klingelt bei“ dürfen die Gruppennummer selbst wählen – lokale Geräte und Cloud-Handys (die Gruppe wird dafür auch in den Kontext ihres Eingangs geschrieben, z. B. `linphone-in`).
  - **Wer anruft, klingelt nicht bei sich selbst**: lokal über das anrufende Gerät (`${CHANNEL(endpoint)}`), Cloud über den Eingang – teilen sich mehrere Handys einen Eingang, zusätzlich über den Linphone-Benutzernamen.
  - Ohne Häkchen bleibt alles wie bisher (z. B. Klingelgruppe nur für die Türstation).
- Verbindungen zeigt Mitglieder solcher Gruppen auch als Anrufer.

## 1.14.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Vorschau „Erzeugen & Übernehmen“ warnt jetzt deutlich, wenn eine Nummer aus einem Kontext **wegfällt**, in dem der Manager sie bisher eingetragen hatte (z. B. „600 ist danach aus dem Kontext ‚linphone-in‘ NICHT mehr erreichbar“) – samt Hinweis, wie es wieder geht.

## 1.14.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Pro SIP-Anrufer eine Kamera**: Die Liste der vorhandenen **Zuordnungen** und der Lade-/Speicherstatus stehen jetzt oben, darunter „Zuordnung anlegen oder ändern“; der Kompatibilitätshinweis ist ans Ende gerückt. Ein Klick auf eine Zuordnung lädt sie und springt zu den Eingabefeldern.

## 1.14.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Eingänge im Anlagen-Modell**: Unter *Anlage & Teilnehmer → Eingänge* stehen Eingänge für Anrufe von außen ohne Anmeldung (z. B. Linphone über Tailscale direkt an `sip:104@<Tailscale-IP>`) mit ihren **Quell-IPs** („nur von 100.64.10.20, …“). Beim Übernehmen pflegt der Manager die `match=`-Zeile des vorhandenen identify bzw. legt Endpoint + identify neu an („＋ Eingang anlegen“). Nur einzelne IPs, keine Netzbereiche.
- **Freigaben nur noch an einer Stelle**: „ergänzen“ liest bestehende Eingänge samt ihrer bisherigen Freigaben und überträgt diese in „darf anrufen“ der Cloud-Teilnehmer, die den Eingang nutzen. Ab dann ersetzt der Manager die Einträge des alten Werkzeugs im Eingangs-Kontext durch eigene (mit Backup) – nichts geht verloren, zurücknehmen geht über „darf anrufen“.
- Der Reiter **Externe SIP-Eingänge** ist nur noch zur Kontrolle (Tabelle, ohne Bearbeiten) und verweist auf die neue Stelle.
- Freigaben/Rufgruppen-Anrufer über einen Eingang: Das Linphone-Konto (`CALLERID(num)`) wird nur noch verglichen, wenn sich **mehrere** Teilnehmer denselben Eingang teilen – bei einem Teilnehmer reicht die Geräte-IP des Eingangs.
- Prüfbericht: Warnung, wenn ein genutzter Eingang keine Quell-IP hat.

## 1.13.4
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **„Anrufer“ sperrt jetzt wirklich**: Stehen Anrufer in einer Rufgruppe, dürfen nur diese die Gruppennummer wählen. Geprüft wird das anrufende Gerät über `${CHANNEL(endpoint)}` (nicht fälschbar wie die Anrufernummer); alle anderen werden mit `Hangup(21)` abgewiesen, im Asterisk-Log steht „… darf nicht anrufen“.
  - Vorher entschied „Anrufer“ nur über den Kontext – da 100–105 alle in `default` sind, konnte jeder die Gruppe wählen.
  - Cloud-Anrufer: geprüft werden Eingang (z. B. `linphone-in`) **und** das Linphone-Konto (`CALLERID(num)` = Benutzername der SIP-Adresse).
  - **Anrufer leer = alle** im Kontext dürfen wählen (wie bisher). Die Karte sagt das jetzt dazu.
- Auch Freigaben („darf anrufen“) im Eingang gelten nur noch für das freigegebene Linphone-Konto, nicht für jedes, das über denselben Eingang kommt.
- Neue Rufgruppen überspringen Nummern, die im eigenen Dialplan schon vergeben sind (z. B. eine bestehende 600).
- Verbindungen: Rufgruppen ohne Anrufer zeigen alle lokalen Teilnehmer als mögliche Anrufer.

## 1.13.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Fehlerbehebung Rufgruppen:** Gab es die Nummer einer Rufgruppe schon als eigenen Eintrag in `extensions.conf` (z. B. eine ältere, nicht „einfache“ Rufgruppe 600), wurde die Gruppe nicht geschrieben – gleichzeitig verschwand ein alter verwalteter Eintrag. Die Rufgruppe hatte danach keine Wirkung.
- Neu: **„Bestehenden Eintrag ersetzen“**
  - in der Vorschau „Erzeugen & Übernehmen“ direkt als Knopf neben der Warnung (setzt den Haken, speichert, rechnet neu),
  - im Rufgruppen-Manager als Häkchen je Gruppe.
  Der Manager entfernt dann den eigenen Eintrag dieser Nummer in den Kontexten der Gruppe – egal wie komplex – und schreibt die Rufgruppe neu (vorher Backup). Andere Nummern bleiben unangetastet.
- Liegt der eigene Eintrag in einer anderen Datei unter `custom/`, sagt die Warnung das jetzt dazu (diese Dateien ändert der Manager nicht).

## 1.13.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Ausgang und Eingang werden erkannt**: Der Manager liest aus der PJSIP-Konfiguration, wofür ein externer Anschluss taugt – *Ausgang* bei Anmeldedaten (`outbound_auth`), Registrierung oder `outbound_proxy`; *Eingang* bei Zuordnung ankommender Anrufe (`identify`) oder eigenem Kontext (z. B. `linphone-in`). Ohne eindeutige Angaben hilft der Name (`-in`, `-cloud`, `trunk` …).
- Beim externen Teilnehmer zeigt **Ausgang** zuerst die passenden Anschlüsse („passend als Ausgang“), die anderen stehen darunter unter „andere“ mit Hinweis „ist Eingang“ – umgekehrt genauso beim **Eingang**. Anschlüsse für beide Richtungen stehen in beiden Listen oben.
- Neue externe Teilnehmer bekommen Ausgang und Eingang automatisch richtig vorbelegt.
- Ist trotzdem etwas Vertauschtes gewählt, wird das Feld markiert und der **Prüfbericht** warnt mit Begründung („Erkannt an: eigener Kontext „linphone-in““).

## 1.13.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **„Wege“ heißen jetzt überall „Rufgruppen“**: in Anlage & Teilnehmer, Prüfbericht, Verbindungen, Vorschau und den Kommentaren im erzeugten Dialplan (`NoOp(Smartify: Rufgruppe …)`). Das Modell selbst bleibt gleich – gespeicherte Anlagen laden unverändert.
- Unter **Anlage & Teilnehmer** steht statt der alten Bearbeitungstabelle eine kompakte Übersicht (Nummer · Name · Anrufer · Klingelt bei · Klingelzeit) mit Knopf **„Im Rufgruppen-Manager bearbeiten →“**. Bearbeitet wird nur noch an einer Stelle.
- Beim ersten „Erzeugen & Übernehmen“ nach dem Update zeigt die Vorschau deshalb geänderte Kommentarzeilen im verwalteten Dialplan-Block – das ist erwartet.

## 1.13.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Neuer Reiter **Start → Rufgruppen-Manager**: Teilnehmer links (Türstationen · Lokal · Cloud) per **Ziehen** auf eine Gruppe legen – Zone **Anrufer** (wer die Gruppennummer wählt) oder **Klingelt bei** (alle gleichzeitig). Linien zeigen, wer in welcher Gruppe steckt (grau gestrichelt = Anrufer, grün = lokal, blau = Cloud).
  - Am iPad/Handy ohne Ziehen: Teilnehmer antippen, dann die Zone antippen.
  - Auf „＋ Neue Gruppe“ ziehen legt eine Gruppe mit der nächsten freien Nummer (600–699) an. Nummer, Name und Klingelzeit direkt in der Karte ändern, × entfernt ein Mitglied, ✕ löscht die Gruppe.
  - Türstationen können nur anrufen, nicht angerufen werden; Cloud-Teilnehmer als Anrufer brauchen einen Eingang – sonst kommt ein Hinweis.
- **Vorhandene Rufgruppen bearbeiten**: „ergänzen“ liest einfache Rufgruppen aus `extensions.conf` (eine Nummer, ein `Dial(…)` an mehrere Ziele, auch `PJSIP_DIAL_CONTACTS` und Linphone-Adressen) und übernimmt sie als Gruppen. Beim nächsten „Erzeugen & Übernehmen“ ersetzt der Manager den bisherigen Eintrag im selben Kontext (mit Backup). Komplexere eigene Einträge bleiben unangetastet.
- „ergänzen“ fügt neue Rufgruppen auch zu einem schon gespeicherten Modell hinzu (nach Nummer, bestehende bleiben unverändert).

## 1.12.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Neuer Reiter **Start → Verbindungen**: Grafik mit Spalten Kameras · Lokal · Asterisk/Wege · Anschlüsse · Cloud und farbigen Linien, wer wen erreichen kann – **aus dem tatsächlichen Dialplan berechnet** (exakte Einträge, Muster wie `_1XX`, `include =>`, Kontext je Endpoint; ohne context gilt `default`).
  - Linienarten: direkt (lokal), Wege, Lokal → Cloud (über Asterisk und Ausgang), Cloud → Lokal (über Eingang und Asterisk), Cloud ↔ Cloud (direkt über den Linphone-Server, ohne Anlage), Kamerabild.
  - Durchgezogen = funktioniert jetzt, gestrichelt = geplant (erst nach „Erzeugen & Übernehmen“).
  - Filter je Linienart; Klick auf einen Teilnehmer zeigt nur seine Verbindungen und listet „Kann erreichen“ / „Wird erreicht von“ mit Grund (z. B. „Muster _1XX@default“).
  - Zusammenfassung: Anzahl lokal/Cloud/Wege, ob sich alle lokalen erreichen, wie viel noch geplant ist.
- Teilnehmertabelle: Beim Ändern von Name oder Nummer wird die Tabelle nicht mehr neu gezeichnet – der Cursor springt nicht mehr aus dem nächsten Feld.
- Neue Dateien `verbindungen.py`, `verbindungen-ui.js`; API `/api/verbindungen` (nur lesend).

## 1.11.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- SIP-Core-**backup_user** (gilt für alle HA-Benutzer ohne eigenen Eintrag) wird beim Ergänzen als HA-Gerät übernommen, HA-Benutzer „alle übrigen HA-Benutzer (backup_user)“. Vorher fehlte er in der Liste, seine Nummer war aber belegt und ließ sich deshalb nicht neu anlegen.
- Prüfbericht und „Erzeugen & Übernehmen“ behandeln den backup_user als vorhandenen SIP-Core-Benutzer; sein HA-Benutzer wird nicht verändert.

## 1.11.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Kameras sind keine Teilnehmer mehr**: Kameras ohne SIP (z. B. `cam_pt2`) stehen in einer eigenen Liste **Kameras** mit RTSP-Quelle, Codec, Passwortstatus und „Bild bei Anruf von“ (welcher Teilnehmer ihren Stream nutzt). „Kameras finden“ sitzt direkt darunter.
- Typ „Kamera ohne SIP“ ist aus dem Teilnehmer-Menü verschwunden; Kameras kommen über „Kameras finden“ oder „ergänzen“ aus go2rtc.
- Prüfbericht: Hinweis, wenn eine Kamera von keinem Teilnehmer genutzt wird (mit Tipp, den Stream bei der Türstation einzutragen).
- Passwortstatus der Kameras wird nach „ergänzen“ sofort richtig angezeigt.

## 1.10.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Fehlerbehebung:** Ein gespeichertes Modell, das die neuen Regeln von 1.10 verletzt (z. B. derselbe HA-Benutzer bei 104 und 105), ließ sich nicht mehr laden – Teilnehmerliste und Prüfbericht blieben leer. Jetzt wird es beim Laden korrigiert (doppelter HA-Benutzer geleert, einzelne kaputte Einträge entfernt), die Korrekturen werden angezeigt und der Prüfbericht läuft wieder.
- „Ergänzen“ erkennt HA-Geräte, die es in SIP Core nicht mehr gibt, und bietet an, sie aus Modell, Wegen und Freigaben zu entfernen.

## 1.10.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **Anschlüsse sind keine Teilnehmer mehr**: `linphone-cloud`, `linphone-in` & Co. stehen nicht mehr in der Teilnehmertabelle, sondern als Info darunter („Ausgang für …“, „Eingang für …“). Video-Codecs am Anschluss werden automatisch ergänzt, wenn ein externes Ziel „Video SIP“ nutzt. Ältere Modelle werden beim Laden umgestellt (Video-Wunsch geht an die externen Ziele über, Verweise in Wegen werden entfernt).
- **HA-Benutzer frei wählbar**: Die Auswahl zeigt alle HA-Benutzer (Personen mit HA-Konto) mit Hinweis, bei welcher Nummer sie in SIP Core eingetragen sind. „Erzeugen & Übernehmen“ setzt die Zuordnung in SIP Core (z. B. 104: „Raph PC“ → „ipadvisu“). Doppelte Zuordnungen werden verhindert; beim Ergänzen aus SIP Core wird ein doppelter Eintrag leer gelassen.
- Prüfbericht zeigt abweichende HA-Benutzer zwischen Modell und SIP Core.
- Menü: „SIP-Telefon (meldet sich direkt an Asterisk an)“ zur klaren Abgrenzung zum Linphone-Cloud-Handy.

## 1.9.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **„darf anrufen“ beim Linphone-Teilnehmer**: interne Nummern (z. B. 104 iPad) und Weg-Rufnummern (z. B. 600) per Klick freigeben. „Erzeugen & Übernehmen“ schreibt die Freigaben in den Kontext des Eingangs (z. B. `linphone-in`); HA-Geräte klingeln auf allen angemeldeten Browsern, Wege mit allen ihren Zielen. Was dort schon freigegeben ist (z. B. über „Externe SIP-Eingänge“), bleibt unverändert und wird beim Ergänzen als Häkchen übernommen.
- **„Aus bestehender Konfiguration ergänzen“** statt ersetzen: fehlende Teilnehmer kommen dazu, vorhandene (auch umbenannte) bleiben unverändert; leere Anlagenfelder werden ergänzt.
- Externe Ziele werden jetzt in **allen** Dialplan-Dateien gesucht (`extensions.conf`, `extensions_custom.conf` und weitere Dateien im custom-Ordner); auch Kollisionsprüfung und Prüfbericht berücksichtigen sie.

## 1.8.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Externe Ziele (z. B. Linphone-Handy) haben jetzt **Ausgang** (z. B. `linphone-cloud`), **Eingang** (z. B. `linphone-in`) und **Adresse**. Der Eingang wird automatisch vorgeschlagen.
- Bei Wegen steht unter „Von“ der **Linphone-Teilnehmer** („Handy – kommt über linphone-in“) statt des Anschlusses. Der Weg wird im Kontext des Eingangs angelegt, damit Anrufe aus der Linphone Cloud ihn auch erreichen.
- Ausgehende Anschlüsse (z. B. `linphone-cloud`) sind bei „Von“ nicht mehr wählbar; bestehende Wege damit meldet der Prüfbericht als „zu unspezifisch“.

## 1.8.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- go2rtc: gleichwertige Einträge werden nicht mehr umgeschrieben – eine RTSP-Adresse mit `:554` (Standardport) bleibt so, wie sie ist, und ein leerer Stream `name:` wird nicht in `name: []` geändert. Die Vorschau zeigt nur noch echte Änderungen.

## 1.8.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Klarere Namen der Fähigkeiten: **„Bild“ heißt jetzt „Video HA“** (Kamerabild im HA-Popup über go2rtc), **„Video“ heißt „Video SIP“** (Video im SIP-Anruf, z. B. für Linphone). Spaltenköpfe, Legende, Tooltips und Prüfbericht angepasst. Das gespeicherte Modell bleibt unverändert kompatibel.

## 1.8.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Neuer Teilnehmertyp **Externes Ziel (SIP-Adresse)**, z. B. ein Handy über Linphone Cloud: Anschluss (Auswahl, z. B. `linphone-cloud`), SIP-Adresse (`name@sip.linphone.org`), Nummer **optional**. Ohne Nummer nur über Wege erreichbar, mit Nummer auch direkt anwählbar.
- Bestehende eigene Dialplan-Einträge wie `906 → Dial(PJSIP/linphone-cloud/sip:…)` werden beim „Übernehmen“ als externes Ziel erkannt; der eigene Eintrag bleibt unverändert.
- **Wege werden in den Dialplan geschrieben**: jeder Weg bekommt eine **Rufnummer** (Vorschlag ab 600), die die Türstation wählt. Verwalteter Block in `custom/extensions.conf`, im Kontext der anrufenden Geräte (`[kontext](+)` ergänzt bestehende Kontexte). Alle Ziele klingeln gleichzeitig, HA-Geräte auf allen angemeldeten Browsern (`PJSIP_DIAL_CONTACTS`), externe Ziele über ihren Anschluss. Nicht erreichbare Ziele werden übersprungen.
- Eigene Dialplan-Einträge mit derselben Nummer werden nie überschrieben (Warnung in der Vorschau).
- Neues Ziel **Dialplan** in „Erzeugen & Übernehmen“ mit Prüfung der Datei und optional `dialplan reload` über AMI.
- Prüfbericht: Wege ohne Rufnummer/Ziele, „noch nicht im Dialplan“, Hinweis „am Gerät 600 als Rufziel eintragen“.
- Wege-Auswahl: Ziele = HA-Geräte, Telefone, externe Ziele; Verweise bleiben gültig, wenn ein externes Ziel später eine Nummer bekommt.
- Erklärungen zu Bild, Video, iOS und Tür als Legende unter der Teilnehmertabelle und als Tooltip.

## 1.7.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Teilnehmer entfernen fragt nach und trägt den Teilnehmer auch aus allen Wegen aus.
- Vorschau „Erzeugen & Übernehmen“ warnt deutlich, wenn eine bisher verwaltete Nebenstelle wegfällt („wird aus Asterisk ENTFERNT“); das gespeicherte SIP-Passwort wird dabei verworfen.

## 1.7.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- AMI-Zugang einrichten: Das Asterisk-Add-on erzeugt `manager.conf` bei jedem Start neu und bindet `manager_custom.conf` nicht ein. Der Manager legt deshalb zusätzlich `custom/manager.conf` an – inhaltlich die erzeugte Datei mit unverändertem `[admin]` plus `#tryinclude manager_custom.conf`. Das Add-on verlinkt Dateien aus `custom/` beim Start und ersetzt damit die erzeugte Datei.
- Danach ist ein **Neustart des Asterisk-Add-ons** nötig (statt `manager reload`); die Oberfläche sagt das und zeigt den Kontrollbefehl `manager show users`.
- `[admin]`-Passwort wird aus den Asterisk-Add-on-Optionen gelesen, sonst aus dem in dieser App eingetragenen admin-Passwort.
- Hinweis: Wird später `ami_password` im Asterisk-Add-on geändert, „AMI-Zugang einrichten“ erneut ausführen.
- `manager.conf` bleibt für den allgemeinen Datei-Editor gesperrt; nur dieser Ablauf schreibt sie (mit Backup).

## 1.7.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- **AMI-Zugang einrichten** (Prüfbericht und Asterisk → Live-Status): legt in `custom/manager_custom.conf` einen eigenen AMI-Benutzer `smartify` mit zufälligem 32-Zeichen-Passwort an – nur aus dem internen Add-on-Netz `172.30.32.0/23` erreichbar, Rechte auf das Nötige beschränkt, mit Backup. Behebt „failed to pass IP ACL“ beim Benutzer `admin`.
- Der Manager nutzt den neuen Zugang sofort und speichert ihn zusätzlich in den eigenen App-Optionen (über den Supervisor).
- Danach zeigt er den fertigen `manager reload`-Befehl zum Kopieren und einen Knopf „Verbindung prüfen“.
- Prüft, ob `manager.conf` die Datei `manager_custom.conf` einbindet, und warnt sonst.
- Ein vorhandener eigener Abschnitt `[smartify]` wird nicht überschrieben; erneutes Einrichten ersetzt nur den eigenen Block (neues Passwort).
- Prüfbericht: AMI-Ablehnung wird als Gelb mit direktem Knopf angezeigt.

## 1.6.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- go2rtc wird robuster gefunden: zuerst `go2rtc_url` aus den App-Optionen, danach die LAN-IP aus dem Anlagen-Modell (`http://<LAN-IP>:1984`), danach die bekannten Add-on-Adressen. Ein falscher oder nicht auflösbarer Hostname blockiert nicht mehr.
- Fehlermeldung nennt jede versuchte Adresse mit Grund (z. B. „Name nicht auflösbar“).

## 1.6.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

Mehr Auswahllisten statt Tippen:

- **＋ Teilnehmer hinzufügen** als Menü: neue Türstation, SIP-Telefon, HA-Gerät, Kamera oder externen Anschluss anlegen – oder direkt vorhandene SIP-Core-Benutzer und externe Endpoints übernehmen (nur die, die noch nicht im Modell sind). Neue Nummern kommen automatisch aus dem Nummernbereich (nächste freie, belegte Asterisk-/SIP-Core-Nummern ausgenommen).
- **Nummer**: Vorschlagsliste der freien Nummern.
- **HA-Benutzer**: Auswahl aus den SIP-Core-Benutzern; füllt Nummer und Name mit.
- **Endpoint** (externer Anschluss): Auswahl aus den vorhandenen Asterisk-Endpoints.
- **Stream**: Vorschlagsliste der go2rtc-Streams mit Status (RTSP, Gerät sendet, leer).
- **Tür · Licht · Klingel** je Türstation: Vorschläge aus den HA-Entitäten, nach Domain gefiltert, passende Namen (Tür, Licht, Klingel) zuerst.
- **Klingelzeit** der Wege als feste Stufen.
- **Netzwerk erkennen**: LAN-IP (Supervisor), Tailscale-Name (externe/interne HA-Adresse) und daraus die go2rtc-HTTPS-Adresse; füllt nur leere Felder.
- Neue API-Routen `/api/anlage/auswahl`, `/api/anlage/netz` (nur lesend).

## 1.5.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Wege: „Von“ und „Ziele“ werden aus den vorhandenen Teilnehmern der Anlage per Auswahlliste gewählt (Mehrfachauswahl, Typ je Eintrag sichtbar) statt als Text eingegeben. Türstationen erscheinen nur bei „Von“, Kameras ohne SIP gar nicht.
- Nicht mehr vorhandene Teilnehmer in einem Weg werden rot markiert.
- Name des Wegs wird aus dem Anrufer vorgeschlagen (z. B. „Klingel Haustür“).
- Auswahl aktualisiert sich, wenn Nummer, Name oder Typ eines Teilnehmers geändert werden.

## 1.5.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

Der Manager erzeugt jetzt aus dem Anlagen-Modell die Konfiguration selbst – mit Vorschau, Backup und Bestätigung.

- Neuer Reiter **Start → Erzeugen & Übernehmen**: Vorschau je Ziel (Aktionen in Klartext und Unterschiede), Auswahl, Übernahme mit Versionsschutz (geändert seit Vorschau → abgebrochen).
  - **Asterisk**: verwalteter Block in `custom/pjsip_custom.conf`. Einfache bestehende Nebenstellen werden übernommen (Passwort und Einstellungen bleiben), neue Nebenstellen mit sicherem Passwort angelegt, Video-Codecs nach Fähigkeit gesetzt. Externe Anschlüsse (z. B. `linphone-cloud`) bekommen vp8/h264 direkt in ihrer Zeile ergänzt. Vom Asterisk-Add-on erzeugte Endpoints werden nie doppelt angelegt. Prüfung der erzeugten Datei vor dem Schreiben; optional `pjsip reload` über AMI.
  - **SIP Core**: `sip_video`, Popup-Komponente, `auto_open`, `smartify.camera_by_caller` mit Wiedergabe WebRTC, sobald iOS-Geräte in der Anlage sind; doppelte Kamera-Einträge unter `extensions` werden entfernt (Name/Symbol bleiben). Benutzer werden nicht verändert.
  - **go2rtc** (über `/api/config`, danach Neustart): RTSP-Streams aus dem Modell, leere Streams für Gerätekameras, `api.origin: "*"`, WebRTC-Candidate der LAN-IP. Fremde Streams bleiben erhalten; Backup unter `/data/backups`.
- **RTSP-Kameras automatisch erkennen**:
  - aus der go2rtc-Konfiguration beim „Übernehmen“ (Adresse, Pfad, Benutzer, Zusatz wie `video=h264&audio=pcma`; Passwort wandert in `/data/secrets.json`).
  - **Kameras finden**: Netzsuche im /24 von Home Assistant (Port 554/8554), Hersteller über RTSP-Server-Kennung und ONVIF, Pfadvorschlag für 11 Herstellerfamilien, **Testen** per RTSP DESCRIBE (Basic/Digest) mit Codec-Anzeige, **Übernehmen** als Kamera ins Modell.
- Prüfbericht: fehlendes RTSP-Passwort, H.265-Kameras, Optionen des Asterisk-Add-ons (über Supervisor, nur lesend), Doppelzuordnung nur noch bei echten Kamera-Feldern.
- **Zugang**-Knopf je SIP-Telefon/Türstation zeigt die SIP-Zugangsdaten für das Gerät.
- Passwörter erscheinen nie im Modell, im Export oder in Vorschauen.
- `hassio_api: true` (nur Lesen der Asterisk-Add-on-Optionen). Neue Dateien `generator.py`, `rtsp.py`.
- Noch nicht in 1.5: Wege in den Dialplan schreiben, SIP-Core-Benutzer anlegen, Tailscale Serve (bleibt Anleitung).

## 1.4.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

Erster Schritt zum Manager 2.0 (Konzept „Smartify SIP Manager 2.0“): ein Modell der ganzen Anlage und ein Prüfbericht über alle Schichten. **Es werden keine Asterisk-, SIP-Core- oder go2rtc-Dateien geändert.**

- Neuer Hauptbereich **Start** als Startseite mit **Prüfbericht** und **Anlage & Teilnehmer**.
- **Anlagen-Modell** `/data/anlage.json`: Anlage (Name, Kunde, Nummernbereich, LAN-IP, Tailscale-Name, go2rtc-HTTPS-Adresse), Teilnehmer mit Typ (HA-Gerät, SIP-Telefon, Türstation, Kamera ohne SIP, externer Anschluss) und Fähigkeiten (Kamerabild ins Popup, Video im SIP-Anruf, iOS-Gerät, Türöffner) sowie Wege. Versioniert, mit Backup bei jedem Speichern.
- **Übernehmen aus bestehender Konfiguration**: liest SIP-Core-Benutzer, Asterisk-Endpoints (Vorlagen aufgelöst), Popup-Kamerazuordnungen und go2rtc-Streams und schlägt das Modell vor. Gespeichert wird erst nach Prüfung.
- **Prüfbericht** (rot/gelb/Hinweis/OK, mit Ursache und Behebung) erkennt u. a.: Video gewünscht, aber Endpoint ohne vp8/h264; `sip_video: false`; Stream fehlt in go2rtc oder Gerät sendet nicht (Browser-ID/Publishing); keine HTTPS-Adresse für go2rtc; fehlendes CORS (`api.origin`); MSE trotz iOS-Geräten; `camera_mode: hidden`; Popup nicht aktiv; doppelte Kamera-Zuordnung; nicht angemeldete Nebenstellen (mit AMI); Türstationen ohne Weg.
- Effektive Codecs je Endpoint aus den Konfigurationsdateien mit aufgelösten Vorlagen; mit AMI zusätzlich live über `pjsip show endpoint`.
- **Export/Import je Kunde** (`smartify-anlage-<kunde>-<datum>.json`); das bisherige Gesamt-Backup enthält das Modell ebenfalls.
- Anleitung für Tailscale Serve (HTTPS für go2rtc) zum Kopieren; der Manager führt sie bewusst nicht selbst aus.
- Neue Dateien: `anlage.py` (Modell, Import, Prüfbericht), `anlage-ui.js` (Oberfläche); neue API-Routen `/api/anlage`, `/api/anlage/vorschlag`, `/api/anlage/export`, `/api/anlage/import`, `/api/pruefbericht`.

## 1.3.7
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Neuer Hauptbereich **Asterisk → Externe SIP-Eingänge**: IP-basierte eingehende Linphone/Tailscale-SIP-Anrufe mit separatem Endpoint, Identify und eigenem Dialplan-Kontext einrichten, einlesen und bearbeiten. Kein lokales Asterisk-Konto auf Linphone notwendig.
- Mehrere vertrauenswürdige Geräte-IP-Adressen pro Eingang (einzelne /32 bzw. /128), mehrere bestehende Asterisk-Nebenstellen als freigegebene Ziele per Checkbox. Jeder Teilnehmer erhält seine eigene direkt anrufbare Durchwahl; keine uneingeschränkte Dialplan-Freigabe.
- Bereits vorhandene Profile wie `linphone-in` werden aus den Custom-PJSIP- und extensions.conf-Dateien erkannt. PJSIP-Endpoint-Optionen werden bei IP-Änderungen beibehalten; `linphone-cloud` und andere Gruppen/Kontexte bleiben unberührt.
- Vorschau, Kollisionskontrolle gegen andere PJSIP Identify-IP-Regeln, Versionskennungen für beide Dateien, Bestätigung und Backups; wenn die zweite Datei nicht gespeichert werden kann, Rücksetzen der ersten Datei versuchen. Kein automatischer Asterisk-Reload.
- Erweitert: API-Routen `/api/inbound`, `/api/inbound/preview`, `/api/inbound/save`; neue Backend-Datei `inbound_routes.py` wird explizit im Docker-Image installiert.
- Nur unterstützte einfache Dialplan-Kontexte automatisch editieren. Weitere PJSIP-/Dialplan-Funktionen bleiben im Datei-Editor; unbekannte Kontexte nicht ersetzen.

## 1.3.6
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Nummernbelegung, PJSIP-Endpunkte und Dialplan-/Rufgruppenbelegung als EINE gemeinsame Hauptübersicht pro Rufnummer statt zweier getrennt angezeigter Tabellen. Anzeigename, Quelle, Kontext/Ziele und Aktionen stehen direkt in der Zeile.
- Detaillierte PJSIP-Zellen sind nur bei Bedarf über „Erweiterte Bearbeitung“ sichtbar; ein Klick auf „Bearbeiten“ öffnet den passenden Datensatz direkt.
- Custom-Nebenstellen werden nicht mehr ausschließlich in `custom/pjsip_custom.conf` gesucht. Vollständige, einfache AOR/Auth/Endpoint-Definitionen in weiteren Custom-`.conf`-Dateien werden mit ihrer echten Quelldatei erkannt, bearbeitet und bei Bedarf gezielt gelöscht.
- Kommentarblöcke zwischen Abschnitten werden dem folgenden Abschnitt zugeordnet bzw. als unberührter Text erhalten; sie sperren kein ansonsten einfaches PJSIP-Dreierpaket mehr.
- Bei mehreren Custom-Definitionen derselben Nummer bleibt das automatische Editieren/Löschen gesperrt. Standarddefinitionen, Vorlagen und komplexe Strukturen bleiben geschützt.
- Vor Löschen aktuelle Dialplan- und SIP-Core-Verweise erneut prüfen. Bei Belegung wird der konkrete Blocker (z. B. Gruppe 600@default) angezeigt; keine automatische Löschung von Rufgruppen, SIP-Core-Konten oder Asterisk-Reloads.
- Versionskontrolle pro bearbeiteter Quelldatei, Backup und strukturierte Eingabeprüfung bleiben erhalten. Lokale Tests sind keine Bestätigung des aktiven Asterisk-Dialplans.

## 1.3.5
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Bereits belegte Nebenstellennummern im Formular und in neuen Tabellenzeilen sichtbar gesperrt; Neuanlage-Schaltflächen können nicht mehr versehentlich verwendet werden.
- Vorhandene Custom-Nebenstellen aus der Übersicht in die editierbare Tabelle öffnen; dort Bearbeiten und Löschen (mit zweifacher Bestätigung, Versionskontrolle und Backup).
- Löschschutz für Gruppen- und SIP-Core-Referenzen; nur eindeutige, einfache Custom-AOR/Auth/Endpoint-Dreiergruppen können gelöscht werden. Kein automatischer Asterisk-Reload.
- Reserviert auch teilweise vorhandene numerische PJSIP-Abschnitte (z. B. nur AOR/Auth), die der reine Endpoint-Scan bisher übersah.
- Server prüft Doppelvergaben beim tatsächlichen Speichern nochmals. Nicht lesbare Runtime-/Realtime-Konfiguration bleibt als mögliche Lücke gekennzeichnet.

## 1.3.4
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Smartify-Manager mit hellem Standardtheme (schwarze Schrift/hellgraue Flächen) und umschaltbarem dunklem Theme; Calibri/Carlito-Fallback für beide.
- Add-on-Container auf Home-Assistant-Base-Python mit `with-contenv`-Startskript umgestellt. Behebt die bekannte Ursache fehlender `SUPERVISOR_TOKEN`-Variablen beim Containerstart. Vollständiger Rebuild erforderlich.
- AMI-ACL-Hinweis (172.30.x.x) in der Diagnose, Anleitung für getrennten AMI-Benutzer.
- PJSIP-/SIP-Core-Eingabefelder zeigen ausdrücklich keine 12-Zeichen-Mindestlänge; die bereits erlaubte Länge 1–128 bleibt. Das Passwortschema einer externen Integration kann dieser Manager nicht abändern.
- Keine Änderung an Popup, Card, Asterisk-Konfigurationsdateien oder SIP-Core-Konten durch das Update.

# Changelog – Smartify SIP Manager

Format: neueste Version oben. Die Add-on-Version steht ausschließlich in `config.yaml`;
die mitgelieferten Frontend-Versionen in `FRONTEND_VERSIONS` (`app.py`) und im Kopf der jeweiligen JS-Datei.

## 1.3.3
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- PJSIP-Tabelle um editierbare AOR-/Endpoint-Detailwerte ergänzt, inklusive `qualify_frequency`, Transport, Expiration, DTMF und NAT/RTP.
- Ausgehende Endpoint-only-Definitionen (`[linphone-cloud]`) als eigene Tabelle mit Bearbeiten/Neu anlegen (nur bekannte Parameter).
- Dialplan in eigene Zellen zerlegt: NoOp-Beschreibung, lokale Ziele, externer Endpoint, SIP-URI, Timeout und Hangup.
- Direkte Bearbeitung auch für einfache externe Einzelrufe (109) und gemischte lokale/Cloud-Parallelrufe (600), unter Beibehaltung anderer Kontexte.
- Komplexe Regeln bleiben nur lesbar. Custom-Datei-Schreibschutz, Backup, Versionsprüfung und manueller Reload bleiben erhalten.

## 1.3.2
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Echte Dialplan-Abläufe (`NoOp`, `Dial`, `Goto`, `Playback`, `Hangup` usw.) samt Quelldatei und Kontext statt „siehe Datei“; aufklappbare Detailansicht.
- PJSIP-AOR/Auth/Endpoint tabellarisch verwalten: `max_contacts`, Kontaktverhalten, Kontext, Codecs, Benutzer, Passwortwechsel; neue Zeile und Linphone-Voreinstellung.
- Einfache vorhandene Rufgruppen tabellarisch bearbeiten; neue lokale/externe Gruppen mit vorhandenen Nebenstellen anlegen.
- Direkter Schreibweg in eine bereits existierende und wirksame **Custom-Datei** mit Optimistic Lock, Syntaxprüfung, Backup und expliziter Bestätigung. Kein automatischer Reload; separate AMI-Aktionen mit Nachfrage.
- Kein Passwortzwang auf 12 Zeichen im PJSIP-Generator oder bei neuen SIP-Core-Teilnehmern. Schwache Passwörter werden weiterhin als Risiko markiert.
- Komplexe Asterisk-Abschnitte und unbekannte Dialplan-Aktionen bleiben vor automatischer Ersetzung geschützt (Rohdatei-Editor).

## 1.3.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (unverändert)

- Nebenstellen-Generator mit frei einstellbarem `max_contacts`, `remove_existing`, `remove_unavailable`, `qualify_frequency` und Registrierungszeiten.
- Eingaben für SIP-Anmeldename, Dialplan-Kontext, Transport, Codecs, DTMF-Modus und NAT-/RTP-Parameter. Komfortvorlagen für ein oder mehrere Geräte.
- Gemeinsamer PJSIP-Builder mit Wertevalidierung, verständlichen Warnungen und automatischer Ungültigmachung veralteter Vorschauen.
- Keine automatische Speicherung, kein Asterisk-Reload; Nummernbelegungsprüfung vor dem Generieren und vor Übernahme in den Editor.

## 1.3.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0 (JS-Komponenten unverändert)

- **Neue Navigation in fachlicher Reihenfolge:** (1) Asterisk mit vorhandenen und neuen Nebenstellen, (2) SIP Core mit aktiver Konfiguration, Teilnehmern, Video/RTSP, Popup und Card, (3) Rufgruppen aus extensions.conf/Custom-Dateien. Diagnose und Dateiverwaltung unter „Werkzeuge“.
- **Nummernbelegung unter Asterisk und Rufgruppen:** `/api/number-plan` sammelt PJSIP-Endpoints, numerische Dialplan-Ziele/Rufgruppen mit Datei und Kontext sowie verfügbare SIP-Core-Teilnehmer. Hinweise zum begrenzten Geltungsbereich (keine Garantiezusage über freie Nummern).
- Neue Nebenstellen oder Gruppen mit bereits gefundener Nummer können nicht mehr aus dem Generator erzeugt werden. Rufgruppenziele dürfen nur aus in den Dateien erkannten Nebenstellen bestehen. Auswahlknöpfe statt freier Eingabe für häufige Ziele.
- **SIP-Core-Teilnehmerauswahl nur aus vorhandenen Asterisk-Nebenstellen.** Vorhandene SIP-Core-Einträge werden angezeigt; ändern oder ergänzen erfolgt zunächst nur im YAML-Entwurf. Vorhandene Passwörter werden bei Änderungen beibehalten, Neuanlagen erfordern ein eigenes Passwort.
- Änderung an der aktiven SIP-Core-Konfiguration weiterhin nur über vorhandenen Diff/Bestätigungs-/Backup-Workflow, niemals direkt bei Teilnehmerauswahl.
- Rufgruppen und sonstige Dialplan-Ziele erscheinen mit Nummer, Kontext, Quelldatei und erkannten Zielen; ein Button kann den Entwurf in eine bereits vorhandene, bearbeitbare `extensions.conf` vorbereiten. Keine automatische Speicherung und kein Reload.
- Alten freien Benutzer-Generator aus der Hauptnavigation entfernt; keine zweite gleichrangige Konfigurationsstrecke mehr. Beispiel-Rufgruppen aus dem RTSP/Popup-Bereich entfernt.

## 1.2.1
Mitgeliefert: Popup 3.3.1 · Card 2.7.0

- **AMI korrigiert:** Asterisk sendet nach der Anmeldung ein „FullyBooted“-Ereignis. In 1.2.0 wurde es als Antwort auf den nächsten Befehl gelesen, sodass Befehle leer blieben oder eine fremde Antwort zeigten. Jede AMI-Aktion trägt jetzt eine eigene ActionID, nur die passende Antwort wird ausgewertet, fremde Ereignisse werden übersprungen. Alte („Response: Follows“) und neue Befehlsantworten werden unterstützt; „keine Nebenstellen“ gilt nicht mehr als Fehler.
- **Neu: „Verbindung Schritt für Schritt prüfen“** unter Live & Befehle: zeigt Optionen, Verbindung, Anmeldung, Nebenstellenabruf und Befehlsrecht einzeln mit Ergebnis; warnt, wenn als Host 127.0.0.1 eingetragen ist.
- Klarere Fehlermeldungen (Zeitüberschreitung, Verbindung abgelehnt, kein AMI an der Adresse, Anmeldung verweigert).
- **Server:** Unerwartete Fehler liefern jetzt eine verständliche Meldung statt einer leeren Antwort und werden im Protokoll vermerkt.
- **Oberfläche:** Skriptfehler erscheinen als rote Leiste oben, ungültige Server-Antworten mit HTTP-Status; Status-Fehler stehen direkt im Live-Kasten.
- Tests um eine nachgebaute Asterisk-AMI ergänzt (FullyBooted, fremde Ereignisse, alte und neue Befehlsantworten, falsches Passwort, nicht erreichbarer Host).

## 1.2.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0

**Für den Einsatz bei Kunden**
- Keine persönlichen Vorgabewerte mehr (Linphone-Adresse, Licht-Entität, Benutzernamen, Streamnamen). Felder sind leer mit Beispielen; Konsolenbefehle und Anleitungen verwenden den konfigurierten Asterisk-Slug.
- Backups werden begrenzt: je Datei die letzten 30 Stände (`custom/.smartify-backups`, `/data/backups`), ältere werden automatisch gelöscht.
- Neuer Bereich **Sicherung**: Export und Import von Kamera-Zuordnungen und SIP-Core-Entwurf je Installation (mit Backup vor dem Import).
- Teilnehmer lassen sich aus der aktiven SIP-Core-Konfiguration in den Generator übernehmen (ohne Passwörter).

**Diagnose**
- Neuer Bereich **Prüfung**: Benutzerabgleich SIP Core ↔ Asterisk ↔ Home Assistant (fehlende Nebenstellen, `ha_username` passt zu keinem Benutzer inkl. Hinweis auf Groß-/Kleinschreibung, fehlender `backup_user`, doppelte Einträge, schwache Passwörter, fehlendes `popup_config.extensions`).
- Prüfung der Asterisk-Dateien: „#“-Kommentare (mit Ein-Klick-Korrektur), doppelte Abschnitte, Verweise auf nicht definierte AOR/Auth, Dialplan-Fehler. Wird vor jedem Speichern automatisch ausgeführt.
- go2rtc-Streams als Vorschläge in allen Streamfeldern und **Stream testen** mit Standbild. Adresse automatisch gesucht oder über die neue Option `go2rtc_url`.

**Bedienung**
- **In SIP Core übernehmen** (Bereich Entwurf & Übernahme): Unterschiede zur aktiven Konfiguration ansehen, dann über den Konfigurationsdialog der Integration übernehmen. Vorher wird die aktive Konfiguration gesichert; bei unbekanntem Dialog bricht der Manager ohne Änderung ab; danach wird das Ergebnis geprüft. Platzhalter-Passwörter und leere Teilnehmerlisten werden abgelehnt.
- **Zusammenführen** statt „nur in leeren Entwurf“: Vorlagen und Kamera-Zuordnungen werden gezielt in den Entwurf eingefügt; `users`/`backup_user` bleiben geschützt, `camera_by_caller` wird vollständig ersetzt. Passwörter sind in allen Unterschiedsanzeigen maskiert.
- **Asterisk-Befehle über AMI** ohne Konsole: freigegebene Abfragen (Kontakte, Nebenstellen, Transporte, Dialplan …) sowie `pjsip reload` und `dialplan reload` mit Bestätigung.
- Navigation in Gruppen: Start · SIP Core · Kameras & Türen · Asterisk · Diagnose.
- Optionsbeschreibungen auf Deutsch und Englisch im Add-on-Konfigurationsdialog.

**Technik**
- Oberfläche aufgeteilt in `index.html`, `app.js`, `app.css`; Sicherheitsrichtlinie ohne `unsafe-inline` für Skripte.
- PyYAML im Image (für Prüfen, Zusammenführen und Übernehmen).
- Automatische Tests (`tests/`) und `release-check.sh` (Versionen, Syntax, Tests) vor jedem Release.

## 1.1.0
Mitgeliefert: Popup 3.3.1 · Card 2.7.0

- **Entitätsvorschläge** in allen Tür-, Licht- und Klingelfeldern (Kameras je Anrufer, SIP Core, Vorlagen): passende Home-Assistant-Entitäten erscheinen beim Tippen, gefiltert nach geeigneter Domain und sortiert nach Schlüsselwörtern sowie nach Bezeichnung und Streamname der Station.
- Unter jedem Entitätsfeld eine Prüfung: gültiges Format, in HA vorhanden, passende Domain, aktueller Zustand. Ein eingetippter Anzeigename wird automatisch in die Entitäts-ID umgewandelt, wenn er eindeutig ist.
- `/api/entities` liefert zusätzlich `device_class` und Zustand, sortiert, inklusive `event`, `script`, `input_boolean`, `input_button`, `cover`.
- **Versionslogik vereinheitlicht:** Die Oberfläche zeigt die echte Add-on-Version aus `config.yaml` (über `/api/status`) statt eines festen „VERSION 1.0“. Frontend-Versionen und Cache-Parameter (`?v=`) werden ebenfalls aus einer Quelle eingesetzt.
- Ressourcenpfade korrigiert: `/local/…` statt `/config/www/…` in der Anleitung.
- Dockerfile: `python3` wird nur noch nachinstalliert, wenn das Basis-Image keins mitbringt (vermeidet eine doppelte Python-Installation auf `python:3.12-alpine`).
- README auf den aktuellen Stand gebracht, Versionshistorie hierher verschoben; überholte Aussagen entfernt.

## 1.0.3
Mitgeliefert: Popup 3.3.0 · Card 2.7.0

- Kamera-Zuordnungen werden dauerhaft unter `/data/camera_mapping.json` gespeichert (SHA256-Konfliktprüfung, Backup in `/data/backups/`).
- Reiter „Kameras je Anrufer“: Caller-ID, go2rtc-Stream, Wiedergabe, Videoanzeige, Klingel-, Tür- und Lichtentität.
- Zwei abgestimmte YAML-Ausgaben: `popup_config.smartify.camera_by_caller` für SIP Core und eine Doorstation-Card, die dieses Mapping übernimmt.
- Popup 3.3.0 und Card 2.7.0 werten `camera_by_caller` aus.

## 1.0.2
- Nebenstellen werden ohne AMI aus den gemounteten Asterisk-Dateien erkannt (nur lesend, ohne Passwörter).

## 1.0.1
- Start-Korrektur: `python3` explizit installiert (Fehler `python3: not found` beim Start).

## 1.0.0
- Fehlende Custom-Dateien nur per ausdrücklichem Klick anlegen; Default-Dateien nie überschreiben.
- `/api/health` zeigt den echten Mount-Status, Schreibzugriffe ohne Asterisk-Mount werden verweigert.

## 0.8.1
- Serialisierte Schreibvorgänge, Symlink-Prüfung, keine Zugriffslogs pro Seitenaufruf.

## 0.8
- Erste Kamera-je-Anrufer-Vorschau (damals noch ohne dauerhafte Speicherung und ohne Unterstützung im Popup; beides seit 1.0.3 vorhanden).

## 0.7
- Herstellerunabhängige RTSP-Einbindung über benannte go2rtc-Streams, MSE/WebRTC getrennt wählbar, Zugangsdaten in der Vorschau maskiert.

## 0.6
- Praxisvorlagen (Smartify-Popup, Original-Popup, go2rtc, Klingelton, Tür, Licht), Übernahme nur in einen leeren Entwurf.

## 0.5
- Datei-Editor für alle `.conf` (Default nur lesend), SIP-Core-Entwurf mit Backup, rotierende Logs.

## 0.4
- Geführte Abläufe „Schritt für Schritt“, Nebenstellen-Generator, AMI-Livestatus (lesend), Entitätssuche.

## 0.1
- Erste lauffähige Add-on-Basis über Ingress.
