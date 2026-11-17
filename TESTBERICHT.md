# Prüfbericht – 17. November 2026

## Tatsächlich ausgeführt

- Original-Repository per GitHub-Connector gelesen; festgehaltener Quellstand `b603be4643b5055a4aba811cc25f219f69ddcc45`, MIT-Lizenz gelesen.
- Primärquellen von TimeTree, Google, GitHub und OpenAI geprüft; konkrete Links und daraus folgende Einschränkungen stehen in `README.md`.
- Python-3.12-Umgebung erstellt, Laufzeit- und optionale Setup-Abhängigkeiten installiert. Abhängigkeiten sind auf die erfolgreich installierten Versionen gepinnt.
- `python -m unittest discover -s tests -v`: **36 Tests erfolgreich**.
- `python sync.py --config config.example.json --snapshot examples/snapshot.example.json --probe`: erfolgreich, ein erfundener Termin verarbeitet, kein Google-Zugriff.
- Python-Dateien kompiliert; `pip check` meldet keine widersprüchlichen Abhängigkeiten. Workflow-YAML geparst; Cron-Zeitplan, Timeout und minimale Berechtigungen geprüft.
- ZIP-Archiv inklusive verstecktem `.github`-Ordner erstellt und auf Integrität geprüft; keine echten Secrets oder Kalenderdaten enthalten.

## Ergänzungen nach dem ersten GitHub-Lauf

- Der [ursprüngliche Code-Workflow](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions/runs/44053009156) war erfolgreich. Im [manuellen Kalenderlauf](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions/runs/44053298290) fehlten die Konfiguration und beide Zugangsdaten. Der Abgleich stoppte vor der ersten Anfrage an TimeTree.
- Die erweiterte Testsuite lief lokal mit Python 3.12, **45 Tests erfolgreich**. Sie prüft zusätzlich `deactivated_at`, Ganztagsdaten in UTC, die Winterzeitumstellung, bekannte verschobene Serienvorkommen, Wiederherstellung markierter Google-Termine und die separate Gmail-Zieloption. Das Ergebnis für den aktuellen Commit steht unter [Code und Schutztests](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions/workflows/verify.yml).

## Inhalt der ursprünglichen Tests

- Stabile Quellschlüssel bei Titel-/Zeitänderungen; keine Dubletten im zweiten Lauf.
- Vergleich von UTC-/lokaler Google-Zeitdarstellung; Rücksetzen einer Google-seitigen Änderung.
- Trennung gleicher Termin-IDs verschiedener TimeTree-Kalender und fremder Namespaces.
- Ein- und mehrtägige Ganztagstermine mit exklusivem/inklusivem Enddatum.
- RRULE mit UNTIL, EXDATE und lokaler Sommerzeit; Abbruch bei unbekannter Wiederholung oder separater Ausnahme.
- Fehlerhafte Pflichtfelder verhindern Google-Zugriff.
- Expliziter Löschdatensatz entfernt auch den letzten Termin; fehlende Vollständigkeitsbestätigung verhindert Löschung durch Fehlen.
- Leere Antwort und Löschgrenzen stoppen geplante Änderungen; unmarkierte Google-Termine bleiben erhalten.
- Dublettenbereinigung nur innerhalb der eigenen Markierungen.
- TimeTree-Paginierung, letzte Version eines wiederholt gelieferten Datensatzes, festgefahrener Cursor und falsche Kalenderzuordnung.
- Sanitisierte HTTP-401-Meldung, begrenzte Wiederholung bei Rate-Limit, Google-Paginierung ohne Datumsfenster und Namensprüfung.
- Idempotenter Insert nach HTTP 409; Kollision mit fremdem Termin wird nicht überschrieben.
- Dry-Run schreibt nichts; Fehler beim Upsert verhindert anschließende Löschungen.
- Reihenfolge Anlegen → Ändern → Löschen; vorherige Fehler beim zweiten Quell- oder Zielkalender verhindern sämtliche Schreiboperationen.
- Primärkalender wird abgelehnt; bestehendes OAuth-Token ohne explizites type-Feld wird akzeptiert.
- Snapshot-Merger verlangt eine letzte Seite mit `chunk=false`.

## Nicht ausgeführt / nicht bestätigt

- Kein TimeTree- oder Google-Kontologin und keine Kalender-Zugangsdaten verwendet. GitHub-Repository und Workflow-Läufe wurden über die verbundene GitHub-App geprüft.
- Kein authentifizierter TimeTree-Live-Abruf. Der interne Endpoint, seine Vollständigkeit, Löschdatensätze, Token-Laufzeit und echten Serien-Ausnahmen sind nicht als aktuell funktionierend bewiesen.
- Keine Google-Termine angelegt, geändert oder gelöscht. Dienstkonto-Freigabe und OAuth-Autorisierung für deine Konten sind noch einzurichten.
- Ein echter zeitgesteuerter Kalenderabgleich ist noch nicht nachgewiesen; dafür fehlen die privaten Zugangsdaten und die Live-Abnahme. Der separate Code-Workflow verwendet ausschließlich erfundene Daten.
- Kein ChatGPT-Connectorzugriff auf deinen Zielkalender nachgewiesen; keine Zusage über kostenlose Connector-Verfügbarkeit oder Neben-/Zusatzkalender.
- Keine Zusage von GitHub für den langfristigen produktiven Bridge-Betrieb; kein Dauertest und keine Verfügbarkeitsgarantie.

Die Live-Abnahme in Abschnitt 7 der Anleitung ist Bestandteil der Einrichtung. Nur ein eigener erfolgreicher Test bestätigt die Funktion für das konkrete Konto und den getesteten Datenstand.
