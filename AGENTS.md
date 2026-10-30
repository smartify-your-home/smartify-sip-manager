# AGENTS.md – Verbindliche Projektanweisungen

Diese Anweisungen gelten für jede Arbeit am Smartify SIP Manager. **Vor Änderungen zuerst diese Datei und die aktuelle Version in `smartify_sip_manager/config.yaml` lesen.** Nicht von früheren Chat-Zusammenfassungen oder Versionsnummern ausgehen.

## Pflicht bei jeder Codeänderung und jedem Release

1. Den tatsächlichen Stand der betroffenen Dateien auf dem Standardbranch lesen und die Änderung vollständig umsetzen.
2. Immer prüfen, ob Beschriftungen, Tooltips, Hilfe, Beispiele und Bedienabläufe im Add-on (`smartify_sip_manager/index.html`, zugehörige UI-Dateien), HACS und Dashboard noch zutreffen.
3. **Dokumentation zeitgleich mit der Funktion ändern**, insbesondere:
   - `README.md` (HACS-Anzeige durch `render_readme`)
   - `smartify_sip_manager/README.md`
   - `smartify_sip_manager/DOCS.md` (Add-on-Hinweise)
   - `docs/SIP-CALLING-CARD.md` (bei Calling-Card-Änderungen)
   - `smartify_sip_manager/CHANGELOG.md`
   - `hacs.json` und UI-Hilfetexte, wenn relevant.
4. Version in `smartify_sip_manager/config.yaml` erhöhen, soweit ein Release beabsichtigt ist; Versionsangaben und Beispiele in Dokumentation abstimmen. Keine veralteten Links, Versions-Query-Parameter oder Erklärungen stehen lassen.
5. Wenn Frontend-Dateien verändert werden, **HACS-Bundle und ausgelieferte Kopien synchronisieren**: `dist/smartify-sip-manager.js`, `smartify_sip_manager/frontend/smartify-sip-manager.js` und ggf. `smartify_sip_manager/frontend/smartify-sip-calling-card.js`. Syntax prüfen.
6. App-Store-Add-on und HACS-Frontend sind **zwei getrennte Installations-/Updatewege**. Nicht behaupten, HACS aktualisiere den Python-Manager.
7. Tests und mögliche Restprobleme offen benennen. Nie einen Live-Test oder ein erfolgreich veröffentlichtes Release behaupten, ohne dies verifiziert zu haben.
8. **Dokumentationsprüfung ist ein verpflichtender Teil der Definition of Done.** Fehlen aktualisierte Hinweise oder Releasenotes, ist die Aufgabe nicht abgeschlossen.

## SIP-/Calling-Card-spezifische Regeln

- SIP-Status über Asterisk AMI; `NonQualified`/unbekannt ist nicht automatisch offline.
- Eigene Nebenstelle erscheint als Statuspunkt oben und wird aus der Kontaktliste ausgeblendet.
- Anrufrechte (`anruf_ziele` und `angerufen_von`) berücksichtigen; gesperrte Ziele ⛔.
- Browser-Mod-Entities pro Teilnehmer zentral im Manager pflegen, nicht pro Endgerät separat.
- `qualify_frequency` pro Teilnehmer im AoR (OPTIONS-Sekunden) verwalten.
- Lokale UI-Einstellungen von zentralen Konfigurationen unterscheiden.
- An bestehenden SIP-/Asterisk-Konfigurationen nur gezielt mit Vorschau/Backup arbeiten.

## Vorgehen für Coding-Assistenten

Bei **Beginn jeder neuen Aufgabe an diesem Repository** diese Datei lesen. Vor Abschluss relevante Docs, Changelog und UI-Texte gegen die tatsächliche Implementierung prüfen. Bei Unsicherheit erst Code inspizieren, nicht raten.
