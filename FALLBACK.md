# Kostenlose Alternativen und ihre Grenzen

## A. Cloud-Abruf scheitert, TimeTree Web funktioniert noch

Die Bridge enthält einen **manuellen Snapshot-Importer**. Er benötigt keinen laufenden Server und keine bezahlten Dienste. Das ist ein Migrations-/Notfallwerkzeug, keine unbeaufsichtigte Synchronisierung.

1. Zeitplan durch `SYNC_ENABLED=false` pausieren.
2. In deinem Browser bei TimeTree normal anmelden, Entwicklertools → Netzwerk → `events/sync` öffnen.
3. Für genau einen Kalender die JSON-Antworten eines vollständigen Abrufs ab `since=0` in Reihenfolge als `pages/01.json`, `pages/02.json` usw. lokal speichern. Nur Response-JSON speichern, **keinen HAR mit Cookies**. Falls der Browser nur seit früherem Cursor lädt, sind das keine vollständigen Snapshots. Ein Ende mit `chunk=false` allein beweist keinen vollständigen Start.
4. Alle Seiten bis zur letzten Antwort mit `chunk=false` sammeln. Erreichst du keinen vollständigen Abruf, darfst du insbesondere keine Löschung durch Fehlen aktivieren.
5. Python 3.12 und die normalen Abhängigkeiten installieren; dann:

   ```bash
   python merge_snapshots.py pages/01.json pages/02.json --output snapshot.json
   python sync.py --config config.json --snapshot snapshot.json --probe
   python sync.py --config config.json --snapshot snapshot.json
   python sync.py --config config.json --snapshot snapshot.json --apply
   ```

   Bei nur einer Seite nur diese eine nennen. `config.json` für diesen Lauf auf genau den enthaltenen TimeTree-Kalender beschränken. Weitere Kalender separat migrieren. Der Merger erkennt doppelte Quell-IDs und behält deren letzte Version; er kann fehlende Seiten oder einen falschen Startcursor nicht zuverlässig nachweisen. Für einen leeren Quellkalender ist der Kalender-Schlüssel manuell in einem Snapshot nach dem untenstehenden Format anzugeben.

6. Google-Zugang erfolgt über die Umgebungsvariable `GOOGLE_CREDENTIALS_JSON`, wie im Hauptprogramm. Dateien privat halten. Das Repository enthält nur `snapshot.example.json` mit erfundenen Daten.
7. Beim erstmaligen Import `full_snapshot_confirmed=false` lassen. So löst ein unvollständiger Snapshot keine Löschung durch fehlende Termine aus. Noch besser ist für die Migration ein neues leeres dediziertes Google-Ziel.
8. Ergebnisse einschließlich aller Serien-Ausnahmen visuell prüfen. Diese Alternative verwendet denselben Adapter und behebt keine unbekannte TimeTree-Datenkodierung.

Das interne Snapshot-Format lautet:

```json
{
  "calendars": {
    "12345678": [
      {
        "id": "stabile-quell-id",
        "calendar_id": 12345678,
        "title": "Beispiel",
        "all_day": false,
        "start_at": 1794988800000,
        "end_at": 1794992400000,
        "recurrences": []
      }
    ]
  }
}
```

`start_at` und `end_at` sind Unix-Millisekunden. Für normale Termine werden ohne RRULE keine Vorkommen erfunden. Bei nicht unterstützten Daten stoppt die Konvertierung.

## B. TimeTree-Schnittstelle dauerhaft unbrauchbar oder GitHub-Dauerbetrieb nicht geeignet

**Die bestätigte kostenlose Alternative für neue Termine ist Google Kalender als führender Kalender.**

1. Bestehende Termine einmalig per obigem Snapshot übernehmen, soweit verfügbar, oder wichtige Termine manuell in Google übertragen. Einen offiziell zugesicherten TimeTree-Gesamtexport gibt es laut [TimeTree-Hilfe](https://support.timetreeapp.com/hc/en-us/articles/360000629341-How-to-Use-Other-Calendars-such-as-Google-Calendar) nicht.
2. Google-Zusatzkalender für die bisherigen TimeTree-Mitglieder mit geeigneten Rechten freigeben; Einladung und Kontoauswahl prüfen.
3. Bridge danach deaktivieren. Neue Termine, Änderungen und Löschungen direkt in diesem Google-Kalender erledigen.
4. Wenn gewünscht, den Google-Kalender über den Systemkalender auf dem Smartphone in TimeTree **anzeigen**. [TimeTree beschreibt die Anzeige externer Kalender](https://support.timetreeapp.com/hc/en-us/articles/360000639682-I-want-to-display-another-calendar-such-as-Google-Calendar). Das ist keine automatische Rücksynchronisierung von gemeinsam genutzten TimeTree-Kalendern. Externe Kalender in einen TimeTree-Gemeinschaftskalender zu importieren ist laut TimeTree keine automatisch aktualisierte Verbindung.
5. ChatGPT greift weiter über seinen Google-Kalender-Connector zu, sofern dein Konto diesen und den Zielkalender unterstützt.

Damit entfallen sowohl ein dauerhaft laufender PC als auch GitHub-Runner und TimeTree-Cookie-Erneuerungen. Die Arbeitsweise ändert sich aber: TimeTree ist dann nicht mehr die führende Terminablage. Ein Produktwechsel erfüllt das Abfrageziel, nicht die ursprüngliche Anforderung einer automatischen TimeTree-Quelle.

## C. ChatGPT erreicht den Zusatzkalender nicht

Diese Variante umgeht die Abhängigkeit von einem Google-Zusatzkalender. Die Authentifizierung und ChatGPT-Suche müssen mit deinem Konto geprüft werden.

1. Lege ein separates kostenloses Gmail-Konto als Spiegel an. Halte deinen bisherigen persönlichen Google-Hauptkalender aus der Konfiguration heraus.
2. Führe die [Google-OAuth-Schritte](README.md#optional-benutzer-oauth-statt-dienstkonto) mit **diesem separaten Google-Konto** durch. Das erzeugte `token.json` kommt als `GOOGLE_CREDENTIALS_JSON` in GitHub Secrets.
3. Verwende in `SYNC_CONFIG_JSON` bei jeder Quelle, die in den Hauptkalender des Spiegelkontos schreiben soll, diese Zielfelder. Kalendername und Adresse müssen exakt zu deinem separaten Konto passen.

   ```json
   "google_target_type": "dedicated_primary",
   "google_calendar_id": "dein-timetree-spiegel@gmail.com",
   "expected_google_calendar_name": "Name des Hauptkalenders im separaten Konto"
   ```

4. Starte `dry-run`. Der Workflow vergleicht Googles tatsächlichen Hauptkalender des OAuth-Kontos mit dieser Gmail-Adresse und dem Kalendernamen. Danach wie üblich in `apply` testen.
5. Verbinde das separate Konto in [Google Calendar für ChatGPT](https://chatgpt.com/plugins/plugin_connector_1p_f8509de903288191b14a160c6c5d20b0). [OpenAI unterstützt mehrere verbundene Google-Kalenderkonten](https://help.openai.com/en/articles/6825453-chatgpt-release-notes). Frage ausdrücklich nach einem neu gespiegelten Testtermin aus dem separaten Konto.
6. Falls bereits aus demselben TimeTree-Kalender ins alte Google-Ziel gespiegelt wurde, entferne diesen alten Spiegel nach erfolgreichem Test aus der Suche oder lösche den dedizierten Spiegelkalender in Google. Eine geänderte Ziel-ID bereinigt den alten Zielkalender nicht automatisch.

## Was keine bestätigte Lösung ist

- Ein erfundener TimeTree-ICS-Link oder ein angeblich noch gültiges Token der alten öffentlichen API.
- Google-ICS-Abonnement einer statischen Datei: Ohne aktualisierte Quelle übernimmt es keine TimeTree-Änderungen; Aktualisierungsintervalle sind zudem nicht steuerbar.
- Ein alter einmaliger Smartphone-Import: Änderungen/Löschungen werden dadurch nicht dauerhaft übernommen.
- Dasselbe Cookie-Skript auf Google Apps Script, Cloudflare oder einem anderen Gratisdienst: Das ändert den Scheduler, repariert aber keinen abgeschalteten TimeTree-Zugang und keine unklare Vollständigkeit.
- Allgemeines Browser-Scraping als „garantiert kostenlos und wartungsfrei“: UI, Login, Schutzabfragen und Sitzungsablauf bleiben Abhängigkeiten.
- Eine beliebige Drittanbieter-Sync-Seite ohne geprüfte kostenlose Dauerbedingungen.

Wenn TimeTree als führende Quelle zwingend erhalten bleiben muss und dessen Zugriff dauerhaft nicht mehr funktioniert, gibt es nach den geprüften Quellen **keine hier nachgewiesene automatische Alternative**, die alle Anforderungen erfüllt. Das lässt sich durch einen anderen kostenlosen Hoster nicht beheben.
