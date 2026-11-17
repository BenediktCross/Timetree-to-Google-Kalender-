# Herkunft

Grundlage für das interne TimeTree-Abrufprotokoll ist:

- [Kumanogorou/timetree-to-google-calendar](https://github.com/Kumanogorou/timetree-to-google-calendar)
- Geprüfter Commit: `b603be4643b5055a4aba811cc25f219f69ddcc45`
- Autor: KumanoGorou, MIT-Lizenz, Copyright 2026.

Übernommen/adaptiert wurden Endpoint-Muster, `_session_id`-Cookie, `x-timetreea`-Header, `since=0`-/`chunk`-Paginierung und die bekannten Termin-Felder. Google-Abgleich, Actions-Workflow, Konfiguration, Konvertierung, Dokumentation und Tests wurden für diese Ausgabe neu geschrieben.

Die ursprüngliche morgige Tagesauswahl, globale Löschung zukünftiger Zieltermine, fest vorgegebene Japan-Zeitzone, lokale Token-Dateipersistenz und interaktive Fehlerwartezeit werden nicht verwendet. Der Original-Lizenzhinweis ist in `LICENSE` erhalten.

Keine Zugehörigkeit zu TimeTree, Google, GitHub oder OpenAI. Quellcode-Funde bestätigen das Vorhandensein einer Implementierung, nicht die Funktionsfähigkeit mit einem bestimmten Konto.
