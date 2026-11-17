# Deine nächsten Schritte

Die Dateien sind vorbereitet. **Es werden noch keine echten Kalender synchronisiert.**

## 1. Zugangsdaten einrichten

Öffne [Repository-Secrets](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/settings/secrets/actions) und lege über „New repository secret“ diese Einträge an:

| Name | Was eintragen? |
|---|---|
| `TIMETREE_SESSION_ID` | Nur den Wert des `_session_id`-Cookies aus deinem angemeldeten TimeTree-Webbrowser |
| `GOOGLE_CREDENTIALS_JSON` | Vollständiger Google-Dienstkontoschlüssel als JSON; alternativ das erzeugte Benutzer-OAuth-Token |
| `SYNC_CONFIG_JSON` | Angepasste `config.example.json`, mit deinen Quell-/Zielkalender-IDs und dem exakten Google-Kalendernamen |

Keine Geheimnisse in den Chat, in Issues oder als Repository-Datei kopieren. Das Repository ist derzeit öffentlich. Das Dienstkonto benötigt „Termine ändern“ auf einem von dir angelegten dedizierten Google-Zusatzkalender. Der Hauptkalender ist gesperrt.

Die kostenlosen Google-/TimeTree-Einrichtungsschritte stehen in [README – Abschnitte 3 bis 6](README.md).

## 2. Manuell prüfen

Öffne [Actions](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions) → „TimeTree nach Google Kalender“ → „Run workflow“ auf `main`. Nacheinander:

1. **probe**: nur TimeTree abrufen und bekannte Formate prüfen.
2. **dry-run**: Google zusätzlich lesen; Änderungen nur planen.
3. **apply**: auf den dedizierten Testkalender schreiben und mit TimeTree vergleichen.
4. Nochmals **dry-run**: unverändert sollten 0 neue/0 geänderte/0 gelöschte Termine erscheinen.

Anlegen, Bearbeiten, Löschen, alte/zukünftige Termine und Serien-Ausnahmen gemäß [README – Abschnitt 7](README.md) prüfen. Löschung durch bloßes Fehlen ist zunächst deaktiviert. Erst nach dem beschriebenen Vollständigkeitstest `full_snapshot_confirmed=true` setzen. Ein komplett leerer Quellkalender wird zusätzlich geschützt.

Zum Schluss einen gespiegelten Testtermin ausdrücklich über den Google-Kalender-Connector in ChatGPT suchen. Die Bridge kann keine fehlenden Connector-Rechte oder Tarifbeschränkungen aufheben.

## 3. Zeitplan aktivieren

Erst nach erfolgreichem Live-Test unter [Actions-Variablen](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/settings/variables/actions) anlegen:

- Name: `SYNC_ENABLED`
- Wert: `true`

Dann ist alle zwei Stunden ein schreibender Lauf eingeplant. Ohne diese Variable oder mit `false` läuft keine automatische Kalender-Synchronisierung. Mit `false` kannst du jederzeit pausieren.

GitHub-Läufe können verspätet sein/ausfallen. Bei öffentlichen Repositories kann der Zeitplan nach 60 Tagen ohne Repository-Aktivität deaktiviert werden. TimeTree-Cookies können ablaufen. Details, Quellen und kostenlose Ausweichlösung: [README](README.md), [FALLBACK](FALLBACK.md).

## Was grüne Code-Tests beweisen

„Code und Schutztests“ prüft interne Logik mit erfundenen Daten und simulierten Diensten. Dieser Workflow erhält keine Kalender-Secrets und schreibt keine Termine. Er beweist keinen Live-Zugriff auf deine Konten oder vollständige Unterstützung aller TimeTree-Datenformen.
