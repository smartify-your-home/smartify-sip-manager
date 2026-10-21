# Smartify SIP Manager 1.3.7 – externe SIP-Eingänge

### Ziel

Linphone ist ausschließlich unter `beispielkonto@sip.linphone.org` angemeldet. Eingehende **Direktanrufe** nutzen die Tailscale-Adresse des Asterisk-Servers, beispielsweise `sip:104@100.x.x.x`. Die Cloud-Adresse ist die Absenderidentität, nicht die lokale Asterisk-Anmeldung.

### Bedienung

1. Unter **Asterisk → Externe SIP-Eingänge** „Bestehende Eingänge auslesen“ auswählen.
2. Den vorhandenen Eintrag `linphone-in` auf **Bearbeiten** öffnen. Nicht nochmals als neue Definition anlegen.
3. In **Quell-IP-Adressen** die tatsächlichen Tailscale-IPs jedes externen Gerätes eintragen, zum Beispiel `100.64.10.20/32`, je eine IP pro Zeile. Die IP der ausgehenden Linphone-Cloud-Server hier **nicht** eintragen, wenn die Anrufe direkt über das Tailnet zum Asterisk-Server gehen.
4. Unter **Erlaubte interne Nebenstellen** alle Rufnummern markieren, die dieser externe Zugang erreichen darf: beispielsweise 104 und 100. Es können mehrere sein.
5. Den bestehenden Dateinamen `pjsip_custom.conf` (oder den tatsächlich ausgelesenen Custom-Dateinamen) und `extensions.conf` auswählen. Beide müssen in TECH7Fox eingebunden sein.
6. **Konfiguration prüfen / Vorschau** zeigt den Identify-Eintrag in PJSIP und die Einzelziele im Dialplan.
7. **Beide Dateien mit Backup speichern** bestätigen. Backups werden im Custom-Ordner angelegt.
8. In Home Assistant die TECH7Fox-Asterisk-Konfiguration **kontrolliert neu laden** bzw. das Add-on neu starten. Es gibt keine automatische Neuladung durch Smartify.
9. In Linphone `sip:104@TAILSCALE-IP-ASTERISK` und danach andere freigegebene Rufnummern ausprobieren. Nicht freigegebene Nummern sollen über den eingeschränkten Kontext nicht erreichbar sein.

### Was nicht verändert wird

Der bestehende `[linphone-cloud]`-Endpoint für **ausgehende** Anrufe und andere Dialplan-Kontexte (beispielsweise `[default]`, `[parkedcallstimeout]`) bleiben unverändert. Der Generator überschreibt keine komplexen oder unbekannten Dialplan-Regeln. Falls eine PJSIP- oder Dialplan-Datei nur aus dem Standard-Verzeichnis geladen werden kann, ist sie nicht automatisch schreibbar.

### Sicherheit

IP-basierte Eingänge verwenden kein eigenes SIP-Passwort. Deshalb nur bestätigte Gerätenummern/-IPs eintragen, ausschließlich `/32` (IPv4) oder `/128` (IPv6) erlauben und den Portzugriff über Tailscale-ACLs beziehungsweise Host-Firewall auf diese Geräte begrenzen. Ein externer Cloud-Account-Name im SIP-From-Header allein ist kein Authentifizierungsmerkmal. Im Manager können pro Gerät beziehungsweise Berechtigungsgruppe getrennte Profile (z. B. `linphone-in`, `gast-in`) mit jeweils eigenem Quell-IP-Satz und eigenen erlaubten Nummern angelegt werden.

### Tests

Backend-/Browser-Tests verwenden simulierte Asterisk-Dateien. Sie bestätigen nicht die tatsächlich aktiven Asterisk-Includes und nicht den Audio-/SIP-Rufweg in deiner Installation.
