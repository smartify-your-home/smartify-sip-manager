# Smartify SIP Manager – Install-Guide

Stand: Manager 1.18.5 · Popup 3.3.1 · Card 2.7.0

## Überblick

Der Smartify SIP Manager richtet eine komplette Sprech- und Videoanlage in Home Assistant ein: Türstationen, SIP-Telefone, HA-Geräte (iPad, Browser) und Linphone-Handys in der Cloud. Er beschreibt die Anlage in einem Modell und schreibt daraus die Konfiguration von Asterisk, SIP Core und go2rtc – mit Vorschau und Backup vor jedem Schreiben.

| Baustein | Aufgabe |
|---|---|
| Asterisk-Add-on | Telefonanlage: Nebenstellen (PJSIP), Rufgruppen (Dialplan) |
| SIP Core (HACS) | Telefon im HA-Frontend, Popup bei Anruf |
| Smartify Doorstation Popup + Card | Popup mit Kamerabild, Türöffner, Licht |
| go2rtc | Kamerastreams (RTSP) und Gerätekameras für das Popup |
| Browser Mod | Kamera des iPads als Stream veröffentlichen |
| Tailscale (+ Serve) | Zugriff von unterwegs, HTTPS für go2rtc, direkte Anrufe vom Handy |
| Linphone (App + sip.linphone.org) | Handys mit Push, auch ohne Tailscale erreichbar |
| Smartify SIP Manager | Modell, Prüfbericht, Rufgruppen-Manager, Erzeugen & Übernehmen |

```
Türstation ─┐                                   ┌─ Ausgang linphone-cloud ─→ sip.linphone.org ─Push→ Linphone-Handy
SIP-Telefon ┼──────────→  Asterisk  ←───────────┤
HA-Gerät  ──┘        (Nebenstellen, Rufgruppen)  └─ Eingang linphone-in  ←── Tailscale ←── Linphone-Handy (nur Handy-IP)
go2rtc ── Kamerabild im Popup ──→ HA-Gerät
```

Lokale Geräte sprechen direkt mit Asterisk; Linphone-Handys werden über den **Ausgang** angerufen und rufen über den **Eingang** (Tailscale) herein.

## Voraussetzungen

Vor dem Manager müssen Asterisk, SIP Core und go2rtc laufen; Tailscale nur, wenn Handys oder Geräte von außen dazukommen.

- [ ] **Asterisk-Add-on** installiert und gestartet (Slug z. B. `3e533915_asterisk` – den tatsächlichen Slug in den Manager-Optionen `asterisk_slug` prüfen)
- [ ] **SIP Core** über HACS installiert, Benutzer je HA-Gerät angelegt (Nebenstelle + HA-Benutzer)
- [ ] **go2rtc** erreichbar (Port 1984), Kamerastreams eingetragen
- [ ] **Browser Mod** für Gerätekameras (Browser-ID = Streamname, z. B. `ipad_gang`)
- [ ] **Smartify Doorstation Popup + Card** unter `/config/www/` (im Browser `/local/…`) und als Dashboard-Ressourcen eingebunden (`?v=` bei jeder neuen Version anpassen)
- [ ] **Tailscale-Add-on** mit Serve auf Port 8443 für go2rtc (HTTPS für iPhone/iPad)
- [ ] **Linphone-Konten** für alle Handys (sip.linphone.org) und ein Ausgangs-Konto für Asterisk (`linphone-cloud`)

### Netzwerk-Regeln

- Tailscale-Namen (`*.ts.net`) lösen Asterisk und die Add-on-Container meist nicht auf – überall, wo Asterisk vergleicht, die **Tailscale-IP** `100.x.y.z` eintragen.
- go2rtc braucht `api.origin: '*'`, damit Browser Mod das Kamerabild veröffentlichen darf (CORS).
- Die Tailscale-IP eines Geräts bleibt gleich, solange es im Tailnet bleibt: in der Tailscale-App unter dem Gerät oder in der Admin-Konsole unter Machines.
- `127.0.0.1` in den Manager-Optionen (AMI) ist der Manager-Container selbst, nicht Asterisk. Läuft Asterisk in einem anderen Container, dort eine tatsächlich erreichbare Adresse eintragen.

## Installation Schritt für Schritt

Die Reihenfolge ist immer: Modell aufbauen → speichern → Prüfbericht → Vorschau → übernehmen mit Reload.

1. **Manager installieren**: In Home Assistant unter *Einstellungen → Apps → App-Store → ⋮ → Repositories* `https://github.com/smartify-your-home/Smartify-SIP-Manager` hinzufügen, **Smartify SIP Manager** installieren und starten (Start ist manuell), über die Seitenleiste **Smartify SIP** öffnen. Die Versionsnummer steht neben dem Titel im Kopf der Seite. Updates kommen über den App-Store (nicht über HACS); ggf. vorher *⋮ → Nach Updates suchen*.
2. **Prüfbericht öffnen** (Start → Prüfbericht). Meldet er „AMI nicht verfügbar“: Knopf **„AMI-Zugang einrichten“** → legt den Benutzer `smartify` an → danach das **Asterisk-Add-on einmal neu starten** (nicht nur reloaden).
3. **Anlage & Teilnehmer → „Aus bestehender Konfiguration ergänzen“**: liest SIP Core, Asterisk, go2rtc und den Dialplan ein (Teilnehmer, Kameras, Rufgruppen, Eingänge). Bestehendes bleibt unverändert, nur Neues kommt dazu.
4. **Anlage-Daten** ausfüllen: LAN-IP von HA, Tailscale-Name, Tailscale-IP von HA, go2rtc-HTTPS-Adresse (`https://<tailscale-name>:8443`). „Erkennen“ füllt das meist selbst.
5. Teilnehmer, Kameras und Rufgruppen prüfen bzw. anlegen (Abschnitte unten) und **speichern**.
6. **Prüfbericht** erneut laufen lassen, Fehler beheben.
7. **Erzeugen & Übernehmen → Vorschau erzeugen**: Aktionen und „Unterschiede anzeigen“ lesen. Warnungen wie „… NICHT mehr erreichbar“ ernst nehmen.
8. **Übernehmen** mit Häkchen **„Asterisk danach neu laden“** (pjsip reload / dialplan reload). Vor jedem Schreiben legt der Manager ein Backup an.
9. Test-Checkliste am Ende abarbeiten.

## Teilnehmer anlegen

Jeder Teilnehmer hat einen Typ, eine Nummer aus dem Nummernbereich (Standard 100–199, einstellbar) und Fähigkeiten; Kameras und Anschlüsse sind keine Teilnehmer.

| Typ | Wofür | Wichtig |
|---|---|---|
| HA-Gerät | iPad, Browser mit SIP Core | HA-Benutzer je Nummer nur einmal; backup_user = „alle übrigen“ |
| SIP-Telefon | Tischtelefon, Softphone im LAN | Zugangsdaten über Knopf „Zugang“ |
| Türstation | Klingel mit Lautsprecher, optional Kamera | ruft eine Rufgruppe an, wird selbst nicht angerufen |
| Externes Ziel (Cloud) | Linphone-Handy | eigener Abschnitt unten |

### Fähigkeiten

- **Video HA** = Kamerabild im HA-Popup, wenn dieser Teilnehmer anruft (über go2rtc, braucht einen Stream).
- **Video SIP** = Video im SIP-Anruf selbst (z. B. für Linphone); der Manager ergänzt vp8/h264.
- **iOS** = iPhone/iPad, Wiedergabe per WebRTC statt MSE.
- **Tür** = „Tür öffnen“-Knopf bei Anrufen dieser Station.

### Türstation mit Video einrichten

1. „＋ Teilnehmer hinzufügen → Türstation“, Name vergeben (bekommt die nächste freie Nummer).
2. **Kameras → „Kameras finden“**: sucht RTSP im Netz, Passwort eingeben, übernehmen → wird zum go2rtc-Stream. Passwörter liegen nur im Manager, nie im Modell oder Export.
3. In der Zeile der Türstation den **Stream** wählen, **Video HA** anhaken; **Video SIP** nur, wenn die Station H.264 im Anruf sendet.
4. **Tür** anhaken und Türöffner-, Licht- und Klingel-Entität aus den Listen wählen.
5. Im Rufgruppen-Manager eine Klingelgruppe anlegen (Türstation = Anrufer).
6. Nach dem Übernehmen über **„Zugang“** Benutzer, Passwort und Server holen und in der Türstation eintragen: Server = LAN-IP von HA, Port 5060 UDP, Rufziel der Klingeltaste = Gruppennummer.

## Erreichbarkeit einschränken (ab 1.18)

Standardmäßig darf jeder lokale Teilnehmer jede Nummer wählen. Pro Teilnehmer lässt sich das unter **Anlage & Teilnehmer** im aufklappbaren Bereich **Erreichbarkeit** begrenzen:

| Einstellung | Gilt für | Wirkung |
|---|---|---|
| darf nur anrufen | SIP-Telefon, HA-Gerät, Türstation | nur die angehakten Nummern (Teilnehmer, Rufgruppen, Cloud-Teilnehmer) sind wählbar |
| darf nur angerufen werden von / direkt über Asterisk anrufbar nur von | alle Teilnehmer inkl. Cloud-Teilnehmer | nur die angehakten lokalen Teilnehmer dürfen die Nummer direkt wählen |

- Ohne Haken: keine Einschränkung. Haken ohne angehakte Nummer: komplett gesperrt.
- Abgewiesene Anrufer bekommen `Hangup(21)`; im Asterisk-Log steht „Smartify: … darf nicht anrufen“.
- **Grenzen:** Geprüft werden nur Nummern, die der Manager kennt (Teilnehmer, Rufgruppen, Cloud-Direktwahl). Eigene Dialplan-Einträge und Muster wie `_X.` bleiben unberührt; ein vorhandener eigener Eintrag derselben Nummer wird **nicht überschrieben**, sondern in der Vorschau gemeldet. Rufgruppen steuern ihre Anrufer selbst (Rufgruppen-Manager) und klingeln ihre Mitglieder unabhängig von „direkt anrufbar nur von“. Gespräche direkt zwischen zwei Linphone-Konten laufen außerhalb von Asterisk und sind nicht sperrbar.
- Die Grafik **Verbindungen** zeigt gesperrte Wege nicht mehr an.

## Cloud-Teilnehmer (Linphone)

Ein Linphone-Handy ist ein „Externes Ziel“ mit zwei Wegen: Asterisk ruft es über den **Ausgang** an, und es ruft selbst über den **Eingang** herein.

| Feld | Bedeutung | Beispiel |
|---|---|---|
| Adresse | Linphone-Konto des Handys | `name@sip.linphone.org` |
| Nummer | Direktwahl von innen (optional) | 906 |
| Ausgang | Anschluss mit Anmeldung bei sip.linphone.org | `linphone-cloud` |
| Eingang | Anschluss für Anrufe vom Handy, eigener Kontext | `linphone-in` |
| IP Handy | Tailscale-IP des Handys, nur für den Eingang | `100.64.10.20` |
| darf anrufen | Nummern und Rufgruppen, die das Handy wählen darf | 104, 600 |

- **Ausgang/Eingang** werden erkannt: Ausgang = Anmeldedaten oder Registrierung, Eingang = identify oder eigener Kontext. Die Auswahl zeigt die passenden zuerst; Vertauschtes markiert der Prüfbericht.
- **Eingang ohne Anmeldung**: Asterisk nimmt Anrufe nur von den eingetragenen Handy-IPs an (`identify match=`). Nur einzelne IPs, keine Netzbereiche.
- **Mehrere Handys an einem Eingang**: jedes Handy bekommt seine eigene IP; der Dialplan unterscheidet sie darüber.
- **Codecs**: Der Manager stellt an Ausgang und Eingang `opus,ulaw,alaw` sicher.
- **Verschlüsselung**: Am Eingang setzt der Manager (ab 1.17.5) `media_encryption=sdes` und `media_encryption_optimistic=yes`: SRTP wird angenommen, wenn das Handy es anbietet, sonst läuft der Ton unverschlüsselt. Der Ausgang `linphone-cloud` bleibt unverändert.
- **Direktanruf vom Handy**: `sip:<Nummer>@homeassistant.<tailnet>.ts.net` über Tailscale.
- Der Reiter „Externe SIP-Eingänge“ ist nur noch zur Kontrolle; alte Einträge übernimmt der Manager, sobald dieselbe Nummer unter „darf anrufen“ angehakt ist.

## Rufgruppen

Eine Rufgruppe ist eine Nummer (üblich 600–699, frei wählbar, 2–8 Ziffern), die mehrere Teilnehmer gleichzeitig klingeln lässt; bearbeitet wird sie im **Rufgruppen-Manager** durch Ziehen (am iPad: antippen, dann Zone antippen).

| Einstellung | Wirkung |
|---|---|
| Klingelt bei | alle diese klingeln gleichzeitig; wer hier fehlt, klingelt nicht |
| Anrufer leer | jeder im Kontext darf die Nummer wählen |
| Anrufer gefüllt | nur diese dürfen wählen, alle anderen werden abgewiesen (`Hangup(21)`) |
| Mitglieder dürfen anrufen | alle unter „Klingelt bei“ dürfen wählen; der Anrufer klingelt nicht bei sich selbst |
| Bestehenden Eintrag ersetzen | eine eigene gleichnamige Nummer in `extensions.conf` wird ersetzt (mit Backup) |

### Typische Gruppen

- **Klingel Haustür**: Anrufer = Türstation, Klingelt bei = iPad + Handys, Mitglieder-Häkchen **aus**.
- **Familie**: Klingelt bei = iPad + alle Handys, Mitglieder-Häkchen **an**, Anrufer = dieselben (nie leer lassen, sonst darf jeder).

### Wichtig

- Geprüft wird das anrufende Gerät (`CHANNEL(endpoint)`), nicht die fälschbare Anrufernummer.
- Asterisk sucht eine Nummer im Kontext des Anrufers: HA-Geräte landen in `default`, Handys in `linphone-in`. Cloud-Mitglieder brauchen daher einen Eingang, sonst „extension not found in context“.
- Die Vorschau warnt, wenn eine Nummer aus einem Kontext wegfällt.

## Linphone-App einstellen

Medienverschlüsselung auf „Keine“ (oder SRTP ohne „Pflicht“) und PCMU/PCMA einschalten – sonst kommt kein Ton zustande.

| Einstellung | Wert | Warum |
|---|---|---|
| Medienverschlüsselung | Keine, oder SRTP **nicht** verpflichtend | Asterisk kann kein ZRTP; SRTP wird am Eingang nur optimistisch angenommen |
| Codecs | Opus + PCMU + PCMA an | gemeinsamer Codec mit Asterisk |
| Push | an | Handy klingelt auch im Ruhezustand |
| Video | an, wenn Video SIP gewünscht | Bild der Türstation im Anruf |

- Der Weg Handy → Tailscale → Asterisk ist bereits durch Tailscale (WireGuard) verschlüsselt.
- Ruft Asterisk über `linphone-cloud` ins Internet hinaus, läuft der Ton dort ohne SRTP **unverschlüsselt**.
- Direktanrufe ins Haus: `sip:<Nummer>@homeassistant.<tailnet>.ts.net`; das Handy muss dazu in Tailscale verbunden sein.

## Android-Handy einrichten (Linphone 6 + Tailscale)

Ein Linphone-Konto reicht: Klingeln per Push über sip.linphone.org, Anrufe ins Haus direkt über Tailscale an `sip:<Nummer>@homeassistant.<tailnet>.ts.net` – ein zweites SIP-Konto ist nicht nötig.

### Welche Adresse wählen?

| Konto in Linphone | Adresse fürs Haus | Warum |
|---|---|---|
| Cloud-Konto (sip.linphone.org) | `600@homeassistant.<tailnet>.ts.net` | bei `Nummer@IP` ersetzt Linphone die IP durch sip.linphone.org (404) |
| HA-Konto (direkt bei Asterisk, über Tailnet) | `600@<Tailscale-IP von HA>`, z. B. `600@100.64.10.10` | Domain = Realm = Tailscale-IP, sonst „Failed to authenticate“ |

### 1. Tailscale

1. Tailscale installieren, mit demselben Konto wie HA anmelden, VPN-Anfrage erlauben.
2. Android → Einstellungen → Netzwerk → VPN → Tailscale: **Durchgehend aktives VPN** an.
3. Akku: Tailscale **Nicht eingeschränkt**.
4. **Tailscale-IP des Handys** notieren (`100.x.y.z`, in der App beim eigenen Gerät) – Namen wie `*.ts.net` gehen in Asterisk nicht.

#### Handy einer anderen Person (eigenes Tailnet, HA geteilt)

Das Handy liegt in einem fremden Tailnet, HA wird dorthin geteilt. Ohne Zugriffsregel kommt der Anruf zwar bei Asterisk an, die Antworten erreichen das Handy aber nie (Timeout nach 32 s).

1. HA (Machine) mit dem Tailscale-Konto der Person teilen; sie nimmt die Einladung an.
2. In der Zugriffsregel (ACL) eine Regel anlegen: **Quelle = das geteilte homeassistant**, **Ziel = Tailscale-IP des Handys**.
3. Auf dem Handy nur **ein** Tailscale-Konto verwenden – jedes Konto ist ein eigenes Gerät mit eigener IP, und nur diese IP steht im Manager.
4. Die Gruppe mit dem HA-Namen wählen, z. B. `sip:601@homeassistant.<tailnet>.ts.net`. Bei `Nummer@IP` ersetzt Linphone die IP durch sip.linphone.org (→ 404 Not Found).

### 2. Linphone (getestet mit 6.2.8)

1. Mit dem **eigenen linphone.org-Konto** anmelden (je Person ein Konto).
2. Berechtigungen: Mikrofon, Kamera, Benachrichtigungen, Vollbild-Benachrichtigung; Akku **Nicht eingeschränkt**.
3. Einstellungen → Anrufe: Medienverschlüsselung **nicht als Pflicht** („erzwingen“ aus), am sichersten „Keine“; kein ZRTP-Zwang.
4. Einstellungen → Audio: **Opus, PCMU, PCMA** an.
5. Konto → Kontoeinstellungen → **Erweiterte Einstellungen**:
   - **Ausgehender Proxy leer** lassen. Steht dort `sip:sip.linphone.org`, geht jeder Anruf über den Linphone-Server und erreicht die Tailscale-IP nie („Netzwerkfehler“).
   - Transport TLS und Registrar `sip:sip.linphone.org;transport=tls` **so lassen** – das betrifft nur Anmeldung und Push.
   - AVPF darf an bleiben (der Manager setzt `media_use_received_transport=yes`, ab 1.17.3).
6. **Kontakte für das Haus anlegen** mit voller SIP-Adresse, z. B. „Zuhause Gruppe“ `sip:600@homeassistant.<tailnet>.ts.net`, „iPad“ `sip:104@homeassistant.<tailnet>.ts.net`. Nur `600` ins Wählfeld tippen geht nicht – Linphone hängt dann `@sip.linphone.org` an.

### 3. Im Manager

1. Anlage: **Tailscale-IP von HA** eintragen.
2. Cloud-Teilnehmer: Name, Adresse `name@sip.linphone.org`, Ausgang `linphone-cloud`, Eingang `linphone-in`, **IP Handy** = Tailscale-IP des Handys.
3. **darf anrufen**: Nummern/Rufgruppen, die das Handy wählen darf; Rufgruppen im Rufgruppen-Manager (z. B. „Mitglieder dürfen anrufen“).
4. Speichern → **Erzeugen & Übernehmen mit Reload** (Speichern allein ändert Asterisk nicht).

### 4. Test

1. Vom Handy über den Kontakt `sip:600@…` anrufen → im Log `Executing [600@linphone-in:1]`, die anderen Mitglieder klingeln, das eigene Handy nicht.
2. Von 104 die 600 anrufen → Handy klingelt per Push.
3. Ton in beide Richtungen prüfen.

### Fehlerbilder am Handy

| Symptom / Log | Ursache | Lösung |
|---|---|---|
| „Netzwerkfehler“, im Asterisk-Log nichts | nur Nummer gewählt (→ `@sip.linphone.org`) oder Ausgehender Proxy gesetzt | Kontakt mit `sip:600@homeassistant.<tailnet>.ts.net`; Ausgehenden Proxy leeren |
| `No matching endpoint found` | Handy-IP nicht beim Eingang bzw. nicht übernommen | IP Handy eintragen, übernehmen |
| `Couldn't negotiate stream … audio`, Anruf bricht nach 2–4 s ab | AVPF-Angebot abgelehnt oder Verschlüsselung als Pflicht | Manager ≥ 1.17.3 übernehmen; Verschlüsselung nicht als Pflicht |
| `Identify 'linphone-in-identify' points to endpoint 'linphone-in' but endpoint could not be found` | Anschluss enthält eine Option, die Asterisk nicht kennt – der ganze Abschnitt wird verworfen | Manager ≥ 1.17.3 übernehmen (korrigiert `media_use_received_transport`) |
| `has no configured AORs` | Handy versucht sich am Eingang anzumelden (zweites SIP-Konto mit derselben IP) | zweites Konto löschen oder IP Handy leeren |
| `Failed to authenticate` trotz richtigem Passwort | nur bei eigenem SIP-Konto: Realm passt nicht zur Domain | Manager ≥ 1.17: Realm automatisch (Tailscale-IP von HA eintragen) |
| Gespräch bricht direkt nach dem Abnehmen ab, Handy schickt sofort BYE | Handy bietet RTP/SAVPF mit Schlüssel an, Asterisk antwortet SAVPF ohne Schlüssel | Manager ≥ 1.17.5: am Eingang `media_encryption=sdes` + `media_encryption_optimistic=yes` |
| Anruf über Tailscale: bei dir klingelt es, beim Anrufer nach 32 s „Timeout“ (408) | Handy in fremdem Tailnet: Antworten von HA werden nicht durchgelassen | ACL-Regel: Quelle geteiltes homeassistant → Ziel Tailscale-IP des Handys |
| Rückruf aus dem Verlauf endet mit Timeout, Ziel ist eine `192.168.…`-Adresse | Asterisk schrieb die eigene LAN-IP als Absender | am Ausgang die Absender-Domain (`from_domain`) auf die Tailscale-IP bzw. Domain von HA setzen; alte Verlaufseinträge löschen. *(Der Manager erzeugt diese Zeile nicht selbst – von Hand in `pjsip_custom.conf` ergänzen.)* |
| 404 Not Found beim Wählen von `Nummer@IP` mit dem Cloud-Konto | Linphone ersetzt bei reiner Nummer die IP durch sip.linphone.org | Mit HA-Namen wählen: `Nummer@homeassistant.<tailnet>.ts.net` |

Ausnahme: Wer statt Push ein eigenes SIP-Konto direkt bei Asterisk nutzt (z. B. 130), stellt beim Teilnehmer „gleiches Handy wie“ auf den Cloud-Teilnehmer, damit das eigene Linphone-Konto nicht mitklingelt; Transport UDP, Domain = Tailscale-IP von HA.

## Stolpersteine und Fehlerbilder

Die meisten Fehler zeigt das Asterisk-Log eindeutig; die Tabelle ordnet Meldung, Ursache und Lösung zu.

| Meldung / Symptom | Ursache | Lösung |
|---|---|---|
| `Couldn't negotiate stream … audio (nothing)` | Linphone bietet RTP/AVPF an (Standard), Asterisk ohne AVPF-Unterstützung lehnt ab; oder Verschlüsselung als Pflicht; oder kein gemeinsamer Codec | Manager ≥ 1.17.3 (AVPF wird angenommen, `opus` ergänzt); in Linphone Verschlüsselung nicht als Pflicht, PCMU/PCMA an |
| `Everyone is busy/congested (1:0/0/1)` | Ziel nicht erreichbar: Konto existiert nicht, oder Ton nicht verhandelt | Ziel prüfen, Fehler davor im Log lesen |
| `extension not found in context 'linphone-in'` | Nummer steht nicht im Kontext des Eingangs | Handy als Anrufer bzw. „Mitglieder dürfen anrufen“, Eingang beim Teilnehmer wählen, Nummer unter „darf anrufen“ anhaken |
| `Smartify: … darf nicht anrufen` | Anrufer nicht in der Rufgruppe bzw. durch „Erreichbarkeit“ gesperrt | Anrufer hinzufügen bzw. Sperre prüfen; bei Handys IP prüfen |
| AMI: `Authentication failed` / ACL rejecting | Benutzer fehlt oder nur 127.0.0.1 erlaubt | Knopf „AMI-Zugang einrichten“, Asterisk-Add-on neu starten |
| go2rtc `Name does not resolve` | Tailscale-Name im Container nicht auflösbar | IP oder interne Adresse verwenden |
| „Setting up go2rtc publishing failed“ / 404 stream not found | Stream fehlt in go2rtc oder CORS gesperrt | Stream = Browser-ID anlegen, `api.origin: '*'` |
| Kamerabild am iPhone schwarz | MSE auf iOS | Fähigkeit **iOS** → Wiedergabe WebRTC |
| Rufgruppe wird nicht geschrieben | eigene gleichnamige Nummer in `extensions.conf` | „Bestehenden Eintrag ersetzen“ |
| Erreichbarkeits-Sperre greift nicht | eigener Eintrag derselben Nummer bleibt bestehen (Warnung in der Vorschau) | eigenen Eintrag entfernen, dann übernimmt ihn der Manager |
| Änderung wirkt nicht | kein Reload nach dem Übernehmen | Häkchen Reload setzen bzw. `pjsip reload` / `dialplan reload` |

### Nützliche Befehle (HA-Terminal)

```sh
docker exec $(docker ps --format '{{.Names}}' | grep -m1 asterisk) asterisk -rx "pjsip show endpoint linphone-in"
docker exec $(docker ps --format '{{.Names}}' | grep -m1 asterisk) asterisk -rx "pjsip set logger on"
docker exec $(docker ps --format '{{.Names}}' | grep -m1 asterisk) asterisk -rx "dialplan show 600@linphone-in"
```

## Test-Checkliste

Nach jedem Übernehmen einmal durchgehen; bei einem Fehler das Asterisk-Log daneben offen haben.

- [ ] Prüfbericht ohne Fehler, AMI verbunden
- [ ] HA-Gerät → HA-Gerät direkt (z. B. 104 → 105)
- [ ] Türstation klingeln: Popup mit Bild auf iPad und Browser, Türöffner schaltet
- [ ] Kamerabild auf dem iPhone (WebRTC) und am PC
- [ ] HA-Gerät → Handy per Direktwahl (z. B. 906)
- [ ] Handy → HA-Gerät über Tailscale (`sip:104@homeassistant.<tailnet>.ts.net`)
- [ ] Rufgruppe von jedem Mitglied aus: alle anderen klingeln, der Anrufer nicht
- [ ] Nicht freigegebenes Gerät ruft die Gruppe an → wird abgewiesen
- [ ] Teilnehmer mit Einschränkung „darf nur anrufen“ wählt eine nicht angehakte Nummer → wird abgewiesen (Log: „darf nicht anrufen“)
- [ ] Ton in beide Richtungen, bei Video SIP auch Bild
- [ ] Handy im Ruhezustand klingelt über Push
