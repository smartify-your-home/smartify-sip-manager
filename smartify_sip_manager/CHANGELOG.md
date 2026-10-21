## Unreleased
- **Neu: Erreichbarkeit pro Teilnehmer** (Anlage → Teilnehmer, aufklappbar unter dem Namen von SIP-Telefon, HA-Gerät und Türstation).
  - **darf nur anrufen**: begrenzt, welche Nummern (Teilnehmer, Rufgruppen, Cloud-Teilnehmer) der Teilnehmer wählen darf.
  - **darf nur angerufen werden von**: begrenzt, wer den Teilnehmer direkt wählen darf.
  - Ohne Haken gilt wie bisher keine Einschränkung. Der Manager erzeugt dafür Dialplan-Einträge mit Prüfung (abgewiesene Anrufer: `Hangup(21)`); ein vorhandener eigener Eintrag derselben Nummer wird nicht überschrieben, sondern gemeldet.
  - Rufgruppen steuern ihre Anrufer weiterhin selbst; die Sperre „darf nur anrufen“ gilt auch für Rufgruppen-Nummern. „Verbindungen“ zeigt gesperrte Wege nicht mehr an.

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
