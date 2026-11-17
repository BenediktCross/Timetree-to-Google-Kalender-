# Geheimnisse und Kalenderdaten

- `_session_id` wie ein Passwort behandeln. Die Bridge benötigt kein TimeTree-Passwort. Den Cookie nur im Secret `TIMETREE_SESSION_ID` speichern.
- Dienstkontoschlüssel oder OAuth-Token nur im Secret `GOOGLE_CREDENTIALS_JSON` hinterlegen. Kein Eintrag in Quellcode, Actions-Inputs oder Repository-Variables.
- Echte Kalender-IDs und Konfiguration im Secret `SYNC_CONFIG_JSON` aufbewahren. Die IDs allein sind keine Zugriffsberechtigung, können aber private Metadaten sein.
- Runner und installierte Abhängigkeiten können die für diesen Schritt freigegebenen Secrets lesen. Schreibrechte auf das Repository entsprechend beschränken. Keine fremden Workflow-Änderungen ungeprüft übernehmen.
- Workflow nur per Zeitplan und manuell auf dem Standardbranch; keine Pull-Request-Ausführung mit Secrets, kein `pull_request_target`. Keine persistierten Checkout-Credentials, keine automatisch beschreibbaren Git-Branches und kein Cache für Kalenderdaten.
- Offizielle Actions sind an Commit-SHAs gebunden; Python-Abhängigkeiten sind in der ausgelieferten Lockdatei vollständig gepinnt. Änderungen gezielt prüfen und aktualisieren. Paket-Pinning ist kein Versprechen, dass eine Abhängigkeit für immer fehlerfrei bleibt.
- Geheimnisse kommen über Umgebungsvariablen an genau einen Schritt. Das Programm setzt keine Geheimnisse in URLs ein und folgt keinen HTTP-Redirects. TLS-Prüfung bleibt aktiv.
- Google-Dienstkonto nur für dedizierte Spiegelkalender freigeben, ohne IAM-Projektrollen. Mit Benutzer-OAuth sind die genehmigten Scopes weiter gefasst; der Kalender-ID-/Namensschutz bleibt deshalb zusätzlich wichtig.
- Nur Bridge-markierte Termine werden verändert. Standardmäßig sind nur Zusatzkalender zugelassen. Die optionale Einstellung `dedicated_primary` schreibt ausschließlich auf die konfigurierte Gmail-Adresse, wenn das Benutzer-OAuth-Token und die Google-Kalender-ID sowie der Name dazu passen. Ein separates Spiegelkonto verhindert eine Vermischung mit dem Alltagskalender. Fremde/importierte unmarkierte Termine bleiben erhalten.
- Volle TimeTree-Terminlisten liegen während des Laufs im Runner-Arbeitsspeicher und die gewünschten Text-/Zeitfelder werden an Google übertragen. In geteilten Kalendern Rechte der Beteiligten beachten.
- Keine sensiblen Rohdaten in Logs/Tests/Issues. GitHubs automatische Secret-Maskierung allein reicht nicht für komplette JSON-Schlüssel; diese Bridge gibt sie deshalb gar nicht aus.
- Bei versehentlicher Veröffentlichung zuerst Cookie erneuern bzw. Schlüssel/Token widerrufen, danach Secret ersetzen. Nur die Datei aus dem letzten Commit zu entfernen bereinigt nicht die Historie.
- Stoppen: `SYNC_ENABLED=false`; bei Bedarf Dienstkonto-Freigabe entfernen oder Benutzer-OAuth widerrufen. Für eine vollständige Entfernung Google-Spiegelkalender und die drei GitHub Secrets manuell löschen.
