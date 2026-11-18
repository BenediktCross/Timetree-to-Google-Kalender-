# TimeTree → Google Kalender → ChatGPT

**Für die Einrichtung in diesem Repository zuerst [INBETRIEBNAHME.md](INBETRIEBNAHME.md) öffnen.** Dort stehen die direkten Links zu Secrets, Tests und Zeitplan. Code-Tests verwenden ausschließlich erfundene Daten.

Stand der Quellenprüfung **17. November 2026**. Der [GitHub-Workflow](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions/workflows/sync.yml) synchronisiert die eingerichteten Kalender alle zwei Stunden.

Eine kostenlose, zeitgesteuerte Bridge lässt sich mit diesen Dateien aufsetzen. **Eine offiziell unterstützte, garantiert dauerhafte und wartungsfreie TimeTree-Synchronisierung ist nicht verfügbar.** Vor der Aktivierung müssen insbesondere Vollständigkeit, Wiederholungen und ChatGPT-Zugriff mit deinen Kalendern geprüft werden.

## 1. Was nachgewiesen ist – und was nicht

| Bestandteil | Stand | Bedeutung |
|---|---|---|
| Alte öffentliche TimeTree-API | Offiziell am 22.12.2023 eingestellt | Alte Personal-Access-Token-/Connect-App-Anleitungen helfen hier nicht. [TimeTree-Mitteilung](https://timetreeapp.com/intl/en/newsroom/2023-12-14/connect-app-api-202312) |
| Offizieller TimeTree-Export | Automatischer Export in externe Kalender laut Hilfe nicht verfügbar | Es gibt keinen hier bestätigten offiziellen ICS-Abo-Link für private TimeTree-Kalender. [TimeTree-Hilfe](https://support.timetreeapp.com/hc/en-us/articles/360000629341-How-to-Use-Other-Calendars-such-as-Google-Calendar) |
| Verlinktes Projekt | Quellcode geprüft, Commit `b603be4643b5055a4aba811cc25f219f69ddcc45` | Nutzt `_session_id` und `/api/v1/calendar/{id}/events/sync?since=…`; kopiert normalerweise nur morgen, löscht vorher zukünftige Zieltermine und setzt Japan-Zeit voraus. [Projekt](https://github.com/Kumanogorou/timetree-to-google-calendar/tree/b603be4643b5055a4aba811cc25f219f69ddcc45) |
| Diese Bridge | Offline-Test-Suite und [GitHub-Codeprüfung](https://github.com/BenediktCross/Timetree-to-Google-Kalender-/actions/workflows/verify.yml) | Die Tests decken IDs, Änderungen, Löschplanung, Paginierung, Kalendertrennung und Schreibschutz ab. |
| Alle historischen/zukünftigen TimeTree-Termine | **Unbestätigt** | Es werden alle Seiten ab `since=0` ohne Datumsfilter verarbeitet. Ob TimeTree dabei tatsächlich alles liefert, ist nicht öffentlich zugesichert. |
| Löschungen aus TimeTree | Reale Löschmeldungen im TimeTree-Änderungsabruf gesehen | Explizite Löschdatensätze werden verarbeitet, darunter das [in einem TimeTree-Sync-Projekt dokumentierte Feld `deactivated_at`](https://github.com/shiva9ro/timetree-to-gcal). Wenn ein bereits gespiegelter Termin im Vollabruf fehlt, prüft die Bridge den separaten TimeTree-Änderungsabruf auf einen expliziten Löschdatensatz. Löschung ohne diesen Nachweis erfordert `full_snapshot_confirmed=true`. |
| Wiederholungen | RFC-RRULE, EXDATE und RDATE implementiert, synthetisch getestet | Verschobene Vorkommen mit `EXDATE`, mit begrenzter Hauptserie oder ohne aktiven Haupttermin werden einzeln gespiegelt. Bei begrenzten Serien ohne `EXDATE` bleiben die gelieferten Regeln erhalten. Andere erkennbare Ausnahmeformen stoppen den Lauf. Live prüfen, wie TimeTree die Ausnahmen deiner Serien liefert. |
| TimeTree-Sitzung | Ablaufzeit **nicht zugesichert** | Ein neuer Cookie kann manuell nötig werden. Kein automatischer Passwortlogin und keine Umgehung von Login-Schutz. |
| Google Calendar API | Standardnutzung derzeit ohne Zusatzkosten | Quoten gelten. Die aktuelle Dokumentation kündigt Änderungen oberhalb hoher Nutzungsgrenzen an; kein Zahlungsprofil nötig für diese Einrichtung. [Google-Quoten](https://developers.google.com/workspace/calendar/api/guides/quota) |
| GitHub Actions | Kostenloses Kontingent verfügbar | Standard-Runner in öffentlichen Repositories sind kostenlos; private Repositories teilen sich ein Kontingent mit anderer Nutzung. Ohne Zahlungsmittel stoppt kostenpflichtige Mehrnutzung. [GitHub-Abrechnung](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Zeitplan | Best effort, kein Echtzeitdienst | Ausführung kann verspätet sein/ausfallen. Öffentliche Repositories: Deaktivierung nach 60 Tagen ohne Repository-Aktivität. [GitHub-Zeitplan](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) |
| Langfristiger Produktionsbetrieb auf Actions | **Keine Zusage** | GitHub positioniert Actions für den Softwareentwicklungszyklus und beschränkt den Einsatz als allgemeine Serverless-Plattform. Ob diese persönliche periodische Bridge akzeptiert wird, ist nicht bestätigt. Ein Testlauf macht daraus keine garantierte Hosting-Erlaubnis. [Nutzungsbedingungen](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions) |
| Google-Kalender in ChatGPT | Für den eingerichteten Kalender **TimeTree** bestätigt | ChatGPT konnte importierte Termine im Google-Zusatzkalender lesen. Für andere Konten gelten deren Freigaben und App-Einstellungen. [OpenAI-Hilfe](https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt) |

**„Vollständig kostenlos“ bezieht sich auf die Bridge innerhalb der kostenlosen Kontingente, ohne Kreditkarte, Cloud-Testguthaben, Railway oder bezahlten Server.** Ein benötigter ChatGPT-Tarif/Connector wird dadurch nicht kostenlos freigeschaltet. Falls dein kostenloses ChatGPT-Konto den Connector nicht anbietet, ist das Gesamtziel mit diesen Vorgaben nicht vollständig erreichbar.

## 2. Dateien und Verhalten

```text
.github/workflows/sync.yml    Automatisierung alle zwei Stunden
.github/workflows/verify.yml  Code-Prüfung ohne Kalenderzugang bei Änderungen
INBETRIEBNAHME.md             Kurze Einrichtung mit Links zu diesem Repository
sync.py                       TimeTree-Abruf, Konvertierung und Google-Abgleich
config.example.json           Vorlage; echte Konfiguration kommt in ein Secret
requirements.txt              Abhängigkeiten für den Runner
requirements-setup.txt        Nur für optionalen lokalen OAuth-Login
authorize_google.py           Optionaler einmaliger OAuth-Login
merge_snapshots.py            Kostenlose manuelle Notfallmigration
examples/snapshot.example.json Erfundene Quelldaten zum Prüfen
tests/test_sync.py             Offline-Tests für Abgleich und Schutzregeln
FALLBACK.md                    Grenzen und kostenlose Alternativen
SECURITY.md                    Umgang mit Geheimnissen und Daten
TESTBERICHT.md                 Prüfungen und noch offene Live-Tests
THIRD_PARTY_NOTICES.md         Herkunft und Änderungen gegenüber dem Projekt
LICENSE                       MIT-Lizenz
```

TimeTree bleibt bei dieser Einweg-Synchronisierung führend. Termine mit identischem Beginn und Ende erhalten für Google eine Dauer von einer Minute. Bearbeitungen an Spiegelterminen in Google werden beim nächsten Lauf zurückgesetzt; Änderungen fließen nicht zurück nach TimeTree. Synchronisiert werden Titel, Notiz (`note`), Ort (`location`), Beginn/Ende, ganztägige Termine und unterstützte Wiederholungen. Undatierte TimeTree-Memos werden übersprungen. Kommentare, Bilder, Chats, Teilnehmer, TimeTree-Erinnerungen und Farbzuordnungen werden nicht übertragen. Google-Erinnerungen der Spiegeltermine sind deaktiviert; niemand wird eingeladen.

Jeder Lauf lädt alle konfigurierten Quellen vollständig und prüft alle Google-Ziele, bevor er schreibt. Anschließend werden neue/geänderte Termine übertragen; erst nach erfolgreichen Schreiboperationen beginnen Löschungen. Nur mit diesem Namespace und dieser Quelle markierte Termine werden verändert. Bei einem Fehler während des Schreibens können bereits einzelne Änderungen erfolgt sein: Google bietet keine Transaktion über mehrere Termine. Der nächste erfolgreiche Lauf gleicht sie ab.

Die feste Google-ID wird aus Namespace, TimeTree-Kalender-ID und TimeTree-Termin-ID gebildet. Deshalb braucht der Runner keinen dauerhaften lokalen Speicher und keinen GitHub-Cache. Gleichnamige Termine in unterschiedlichen TimeTree-Kalendern bleiben absichtlich getrennt. Unmarkierte Dubletten aus anderen Importern werden nicht automatisch entfernt.

## 3. Zuerst ChatGPT und einen Testkalender prüfen

1. Öffne [Google Kalender](https://calendar.google.com/) mit dem Google-Konto, das du in ChatGPT verwenden willst.
2. Links bei „Weitere Kalender“ → „+“ → „Neuen Kalender einrichten“. Name zum Beispiel **TimeTree – Familie**. Zeitzone **Europe/Berlin**.
3. Lege dort einen harmlosen Testtermin mit einem einmaligen Namen an, etwa „TT-Verbindungstest 8472“, für morgen.
4. In ChatGPT die App [Google Calendar](https://chatgpt.com/plugins/plugin_connector_1p_f8509de903288191b14a160c6c5d20b0) hinzufügen und Google verbinden. Bezeichnungen variieren nach Oberfläche. Verbinde dein persönliches Google-Konto, **nicht** das später erstellte Dienstkonto.
5. Frage: „Suche über Google Kalender den Termin TT-Verbindungstest 8472 für morgen im Kalender TimeTree – Familie. Nenne Beginn und Kalender.“
6. Prüfe die tatsächliche Connector-Antwort. Falls sie den Zusatzkalender nicht erreicht, prüfe das verbundene Konto und teste im neuen Chat. Als zweite Zieloption gibt es den Hauptkalender eines [separaten Gmail-Kontos](FALLBACK.md#c-chatgpt-erreicht-den-zusatzkalender-nicht).
7. Lösche danach nur diesen manuell angelegten Testtermin. Er hätte keine Bridge-Markierung und würde vom Skript ohnehin nicht verändert.

## 4. Google-Zugang einrichten – ohne Kreditkarte

### Empfohlen: Dienstkonto auf einen von dir angelegten Zusatzkalender beschränken

1. Öffne [Google Cloud Console](https://console.cloud.google.com/) und erstelle ein Projekt, z. B. `timetree-bridge`. **Keinen kostenlosen Cloud-Test starten, kein Abrechnungskonto verbinden und keine Kreditkarte hinterlegen.** Das Cloud-Projekt ist hier nur für API-Zugang und Identität da.
2. „APIs & Dienste“ → „Bibliothek“ → **Google Calendar API** → „Aktivieren“.
3. „IAM & Verwaltung“ → „Dienstkonten“ → „Dienstkonto erstellen“. Gib einen Namen an. Projektrollen sind für den Zugriff auf den freigegebenen Kalender nicht erforderlich.
4. Öffne das Dienstkonto → „Schlüssel“ → „Schlüssel hinzufügen“ → „Neuen Schlüssel erstellen“ → **JSON**. Speichere die heruntergeladene Datei sicher. Sie enthält einen privaten Schlüssel.
5. Kopiere die Dienstkonto-E-Mail (`client_email`, endet auf `iam.gserviceaccount.com`).
6. Im **Test-/Zielkalender** in Google Kalender → Einstellungen → „Für bestimmte Personen oder Gruppen freigeben“ → Dienstkonto-E-Mail hinzufügen → **Termine ändern**. Keine Kalenderverwaltung nötig. Keine öffentliche Freigabe aktivieren.
7. Unter „Kalender integrieren“ die **Kalender-ID** kopieren. Sie endet für den hier unterstützten Zusatzkalender auf `@group.calendar.google.com`. Die private iCal-Adresse ist etwas anderes und wird nicht benötigt.
8. Weitere TimeTree-Kalender später genauso vorbereiten. Du kannst entweder ein separates Google-Ziel je Quelle nutzen oder mehrere Quellen in ein gemeinsames dediziertes Ziel spiegeln.

Das Dienstkonto erstellt keinen Kalender. Der Kalender gehört weiterhin dir. Googles Warnung vor dienstkontoeigenen Kalendern bezieht sich auf die Kalendererstellung; diese erfolgt hier ausdrücklich durch dich. Siehe [Google: Kalender und Eigentümer](https://developers.google.com/workspace/calendar/api/concepts/events-calendars).

Falls die Organisation externe Freigabe oder Dienstkontoschlüssel verbietet, verwende das folgende OAuth-Verfahren oder ein privates Google-Konto. Die Sperre nicht durch zusätzliche Adminrechte umgehen.

### Optional: Benutzer-OAuth statt Dienstkonto

Dieser Weg benötigt deinen PC einmal zur Autorisierung; danach läuft der PC nicht dauerhaft.

1. Im Cloud-Projekt Google Auth Platform konfigurieren; persönlichen App-Namen und E-Mail angeben.
2. OAuth-Client vom Typ **Desktop-App** anlegen; Datei als `credentials.json` lokal im Projektordner speichern.
3. Bei externer App im Status „Testing“ laufen Refresh-Tokens für Kalenderzugriffe üblicherweise nach sieben Tagen ab. Für längerfristige persönliche Nutzung den zulässigen Produktionsstatus einrichten und anschließend neu autorisieren. Verifikation/Organisationsregeln können abhängig von der Nutzung gelten. Ein nicht ablaufendes Token wird nicht zugesichert. [Google OAuth-Tokenregeln](https://developers.google.com/identity/protocols/oauth2#expiration)
4. Auf deinem PC Python 3.12 installieren und im Projektordner ausführen:

   ```bash
   python -m venv .venv
   # Linux/macOS:
   .venv/bin/python -m pip install -r requirements-setup.txt
   .venv/bin/python authorize_google.py
   # Windows stattdessen:
   # .venv\Scripts\python -m pip install -r requirements-setup.txt
   # .venv\Scripts\python authorize_google.py
   ```

5. Im Browser mit dem Kalenderbesitzer anmelden. Den Inhalt der erzeugten `token.json` später als `GOOGLE_CREDENTIALS_JSON` hinterlegen. `credentials.json` oder `token.json` nie hochladen/committen. In Actions gibt es keinen Browserlogin-Fallback.

## 5. TimeTree-Kalender und Sitzung ermitteln

1. Auf deinem eigenen Computer im Browser normal bei [TimeTree Web](https://timetreeapp.com/) anmelden und den gewünschten Kalender öffnen.
2. Entwicklertools mit F12 öffnen → „Network/Netzwerk“ → neu laden. Nach **`events/sync`** filtern.
3. Einen passenden Fetch/XHR-Aufruf auswählen. Das vom Projekt verwendete Muster ist:

   ```text
   https://timetreeapp.com/api/v1/calendar/12345678/events/sync?since=0
   ```

4. Die Zahl zwischen `calendar/` und `/events/` ist die **TimeTree-Kalender-ID**. Pro Quellkalender den richtigen Wert ermitteln. Eine öffentliche Freigabe-URL ist keine solche ID.
5. Entwicklertools → Application/Anwendung → Storage/Speicher → Cookies → `https://timetreeapp.com` → **`_session_id`**. Nur dessen **Wert** kopieren; nicht `_session_id=` und keine anderen Cookies.
6. Verwende nur Kalender, die dieses angemeldete TimeTree-Konto lesen darf. Alle hier konfigurierten Quellen müssen mit demselben Cookie erreichbar sein. Mehrere Kalender unterschiedlicher Konten ohne gemeinsame Mitgliedschaft benötigen getrennte Installationen mit getrennten Secrets/Zielen.
7. Cookie weder in diesen Chat noch in Screenshots, Issues oder Quellcode einfügen. Ein Browser-Export als HAR kann ebenfalls Cookies enthalten; solche Dateien nicht veröffentlichen.

Falls der Request nicht mehr existiert, anders aufgebaut ist oder bereits im Browser scheitert, ist der Adapter **nicht als funktionsfähig bestätigt**. Nicht wahllos Endpunkte oder Authentifizierungsheader ausprobieren. In diesem Fall gilt [FALLBACK.md](FALLBACK.md).

## 6. Eigenes GitHub-Repository und Secrets anlegen

Empfohlen ist zunächst ein **privates Repository** auf GitHub Free: Code, Ausführung und Logs sind dann nicht öffentlich und es greift nicht die für öffentliche Repositories dokumentierte 60-Tage-Regel. Private Actions-Nutzung ist aber begrenzt.

1. Neues leeres Repository anlegen, z. B. `timetree-google-bridge`, ohne kostenpflichtigen Tarif. Entpackte Projektdateien hochladen oder per Git pushen. Den gesamten Inhalt einschließlich `.github/workflows/sync.yml` auf den Standardbranch `main` übernehmen. Der ZIP-Ordner selbst darf nicht als zusätzliche Ebene über den Projektdateien landen. Bei Web-Upload versteckte Ordner kontrollieren; alternativ die Workflow-Datei mit „Add file → Create new file“ unter dem vollständigen Pfad anlegen.
2. Keine echten Zugangsdaten mit hochladen. `config.example.json` bleibt eine Vorlage; das Skript nimmt bevorzugt `SYNC_CONFIG_JSON` aus der Umgebung.
3. Repository → „Settings“ → „Secrets and variables“ → „Actions“ → „Secrets“ → „New repository secret“.
4. Genau diese drei Secrets anlegen:

   | Secret | Inhalt |
   |---|---|
   | `TIMETREE_SESSION_ID` | Nur der Wert des `_session_id`-Cookies |
   | `GOOGLE_CREDENTIALS_JSON` | Gesamter JSON-Dienstkontoschlüssel **oder** vollständige OAuth-`token.json` |
   | `SYNC_CONFIG_JSON` | Angepasste vollständige Konfiguration nach untenstehendem Muster |

5. Konfigurationsvorlage kopieren und deine Werte einsetzen. Zunächst **`full_snapshot_confirmed: false`** belassen:

   ```json
   {
     "namespace": "my-timetree-bridge",
     "calendars": [
       {
         "timetree_calendar_id": "12345678",
         "google_calendar_id": "DEINE_ID@group.calendar.google.com",
         "expected_google_calendar_name": "TimeTree – Familie",
         "timezone": "Europe/Berlin",
         "all_day_timezone": "UTC",
         "all_day_end_mode": "inclusive",
         "full_snapshot_confirmed": false,
         "allow_empty_source": false,
         "max_deletions": 25,
         "max_delete_fraction": 1.0
       }
     ]
   }
   ```

6. Mehrere Kalender: in `calendars` weitere Objekte mit jeweils anderer TimeTree-ID ergänzen. Dasselbe Google-Ziel ist zulässig; dann muss der erwartete Kalendername übereinstimmen. Zeitgebundene Termine verwenden die von TimeTree gelieferten IANA-Zeitzonen und ersatzweise `timezone`. Für Ganztagstermine verwendet die neue Vorlage `all_day_timezone: UTC` und ein inklusives TimeTree-Enddatum, wie [von einer Community-Integration dokumentiert](https://github.com/acdcnow/HA_timetree_import#timetree-web-api-reference). Bestehende Konfigurationen ohne `all_day_timezone` behalten die bisherige Zeitzonenwahl. Überprüfe die Anzeige an einem mehrtägigen Termin, bevor du planmäßige Läufe aktivierst.
7. „Settings → Actions → General“: Actions aktivieren und die beiden offiziellen `actions/checkout`-/`actions/setup-python`-Actions zulassen. Der Workflow braucht nur `contents: read`. Es wird kein eigener GitHub-PAT benötigt.
8. Für eine neue Einrichtung kannst du den Zeitplan über `SYNC_ENABLED=false` pausieren, bis der manuelle Abgleich geprüft ist.

## 7. Live-Prüfung vor der Automatisierung

Diese Schritte sind erforderlich, um aus dem getesteten Programm eine für deine Kalender bestätigte Einrichtung zu machen.

1. Repository → „Actions“ → „TimeTree nach Google Kalender“ → „Run workflow“ auf dem Standardbranch → Modus **`probe`**.
2. Grüne Tests + Meldung „Probe erfolgreich“ bedeuten: Abruf und bekannte Formate sind verarbeitbar. Sie beweisen **keine** vollständige Historie. Bei rotem Lauf erst die verständliche Fehlermeldung bearbeiten.
3. Erneut mit **`dry-run`** starten. Das liest beide Dienste und zeigt nur Anzahlen für Anlegen/Ändern/Löschen. Es schreibt nichts nach Google.
4. Auf deinem dedizierten Testkalender **`apply`** manuell starten. Danach in Google die TimeTree-Daten prüfen. Besonders: sehr alter Termin, Termin weit in der Zukunft, ein- und mehrtägiger Ganztagstermin, Serie über die Sommerzeitumstellung sowie ausgelassenes/verschobenes Einzelvorkommen. Die reine Anzahl von Serien ist nicht die Anzahl ihrer Vorkommen.
5. Zweites unverändertes **`dry-run`**: Erwartung **0 anlegen / 0 aktualisieren / 0 löschen**. Danach zweites `apply`: weiterhin keine zusätzlichen Termine.
6. In TimeTree einen Testtermin anlegen und einen vorhandenen Testtermin zeitlich/titelmäßig ändern. Nach `apply` müssen genau diese Änderungen sichtbar sein, ohne zweite Kopie.
7. In TimeTree einen synchronisierten Testtermin löschen; eine andere Testveranstaltung als Kontrolle stehen lassen. `dry-run` starten. Die Bridge prüft dafür zusätzlich den TimeTree-Änderungsabruf, wenn der Termin im Vollabruf fehlt. Ein unterstützter Löschdatensatz sollte zur geplanten Löschung führen. `apply` und Ergebnis prüfen.
8. Liefert er keine Löschdatensätze, vergleiche die vollständigen Browserantworten ab **`since=0` bis `chunk=false`** mit TimeTree. Erst wenn entfernte Termine fehlen, aktive Kontrolltermine enthalten sind und alte/zukünftige Stichproben stimmen, für diesen Kalender **`full_snapshot_confirmed: true`** setzen und `SYNC_CONFIG_JSON` aktualisieren. Anschließend Testlöschung erneut mit `dry-run`/`apply` prüfen. **Die Einstellung ist deine Annahme nach einem Praxistest, kein Vollständigkeitsnachweis des Anbieters.** Bei einer späteren stillen Teilantwort können dennoch berechtigte Termine als fehlend gelten.
9. Den **letzten** Termin eines reinen TimeTree-Testkalenders löschen und das Verhalten prüfen. Gibt es einen Tombstone, kann die Bridge ihn automatisch entfernen. Gibt TimeTree stattdessen eine komplett leere Antwort zurück, stoppt `allow_empty_source=false` absichtlich. Wenn die Leerung zweifelsfrei gewollt ist: `full_snapshot_confirmed=true` und `allow_empty_source=true` für diesen Kalender setzen, dann neu testen. Diese Option erlaubt künftig auch bei einer scheinbar erfolgreichen leeren Fehlantwort das Leeren des Spiegels. Danach je nach gewünschter Automatisierung beibehalten oder zurücksetzen.
10. `max_deletions=25` begrenzt Löschungen je Quelle und Lauf, einschließlich Dublettenbereinigung. `max_delete_fraction=1.0` erlaubt innerhalb dieses Limits auch die Löschung aller Spiegeltermine, z. B. des letzten Termins. Mit `0.5` schützt du zusätzlich vor mehr als 50 % Löschungen; dann kann das automatische Löschen des letzten Termins blockiert werden. Große beabsichtigte Bereinigungen erst prüfen und Limits gezielt anpassen. Ein ausgelöster Löschschutz stoppt **vor sämtlichen Schreiboperationen dieses Laufs**.
11. Zum Schluss denselben neu gespiegelten Termin ausdrücklich über den Google-Kalender-Connector in ChatGPT suchen. Erstellen/Ändern/Löschen einmal bis zur ChatGPT-Antwort durchtesten. Ohne diesen Schritt ist das eigentliche Ziel noch nicht bestätigt.

Wenn besondere Serien falsch erscheinen oder die Vollständigkeit nicht nachweisbar ist, die Automatisierung nicht als vollständig funktionierend einstufen. Besonders bearbeitete Serienvorkommen brauchen ggf. einen an echte, lokal redigierte Daten angepassten Adapter. Diese Version verspricht dafür keine universelle Kompatibilität.

## 8. Zeitplan aktivieren und kostenlos halten

1. Der Zeitplan ist standardmäßig aktiv. Zum Pausieren unter Repository → „Settings“ → „Secrets and variables“ → „Actions“ → „Variables“ die Variable `SYNC_ENABLED` auf `false` setzen. Zum Fortsetzen auf `true` setzen oder die Variable entfernen.
2. Der Workflow ist für **alle zwei Stunden zur Minute 17** eingeplant, in UTC: 00:17, 02:17 usw. In Berlin entspricht das im Winter 01:17, 03:17 usw., im Sommer 02:17, 04:17 usw. Die Ausführung kann verzögert werden; „jederzeit abfragen“ bedeutet Datenstand des letzten erfolgreichen Laufs, nicht Echtzeit.
3. Private Repositories: Der Sync-Job hat ein Zeitlimit von **30 Minuten**, damit auch große Änderungen an der Historie vollständig durchlaufen. Das ist eine Obergrenze pro Lauf, keine Aussage über den tatsächlichen Minutenverbrauch oder das monatliche kostenlose Kontingent. Auch andere Repositories/Produkte können dasselbe Kontingent verbrauchen. [Aktuelle GitHub-Abrechnung](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
4. GitHub → Kontoeinstellungen → „Billing and licensing/Usage“ kontrollieren. Kein Zahlungsmittel hinterlegen. Ist das kostenlose Kontingent erschöpft, stoppt die Ausführung; es entsteht dadurch keine zuverlässige Dauerverfügbarkeit.
5. Keine Artefakte, Paketablagen oder persistenten Actions-Caches werden erzeugt. Logs und die kurze Job-Zusammenfassung reichen aus. Die direkte und transitive Paketversionierung steht in `requirements.txt`; das Setup-OAuth-Paket läuft nicht auf dem Runner.
6. Große Nachträge, etwa eine neue Personenzuordnung in rund 2.000 Terminbeschreibungen, können mehrere Minuten dauern. Der Workflow lässt dafür bis zu 30 Minuten zu und protokolliert den Schreibfortschritt nach jeweils 100 Änderungen. Bereits erfolgreiche Änderungen werden bei einem erneuten Abgleich erkannt und nicht nochmals geschrieben.
7. Öffentliches Repository als Option: Standard-Runner bleiben kostenlos, aber Logs/Anzahlen und Code sind öffentlich; Secrets bleiben separat. Nach 60 Tagen ohne Repository-Aktivität kann der Zeitplan deaktiviert werden. Regelmäßig selbst prüfen und bei Bedarf über Actions reaktivieren. Kein automatischer Schein-Commit/Keepalive ist enthalten.
8. Beachte die verlinkten Actions-Nutzungsgrenzen. Dieses Repository ist ein Softwareprojekt mit Tests; daraus folgt keine bestätigte Erlaubnis, Actions unbegrenzt als produktiven Kalenderdienst zu nutzen. Die kostenlose Migration/Google-Quelle in `FALLBACK.md` vermeidet diese Hosting-Abhängigkeit.

Pause: Variable `SYNC_ENABLED` auf `false` setzen oder Workflow in Actions deaktivieren. Bisherige Spiegeltermine bleiben erhalten. Ein normaler erfolgreicher Lauf schreibt nur tatsächliche Änderungen und wiederholt nicht sämtliche Termine.

## 9. Logs und Fehlerbehebung

Actions → letzter Lauf → Schritt „Kalender abgleichen“. Geloggt werden nur Seiten-/Datensatzanzahlen, Pläne und technische Statuscodes. Keine Termine, Titel, IDs, Cookie-Werte, Schlüssel, API-Antworten oder URLs. Bibliotheken und GitHub selbst sind trotzdem Teil der Verarbeitung; Secrets sind keine zusätzliche Ende-zu-Ende-Verschlüsselung gegenüber dem Runner.

| Meldung/Symptom | Vorgehen |
|---|---|
| TimeTree HTTP 401/403, Login-Seite statt JSON | Im Browser anmelden, Cookie erneuern und `TIMETREE_SESSION_ID` ersetzen. Google wird nicht vor vollständigem Abruf geändert. |
| TimeTree HTTP 404/Formatfehler | Richtige Kalender-ID, Mitgliedschaft und aktuellen Browser-Request prüfen. Die interne Schnittstelle kann geändert worden sein. |
| Google-Anmeldung fehlgeschlagen | Dienstkontoschlüssel/Token prüfen; bei OAuth ggf. nach Produktionsumstellung neu autorisieren. Keine Geheimnisse in Issues posten. |
| Google HTTP 403/404 | Calendar API aktiv? Ziel-ID richtig? Google-Dienstkonto mit der `client_email` aus der Secret-JSON für den konkreten Zielkalender mit „Änderungen vornehmen und Termindetails ansehen“ freigegeben? Organisationsregeln oder Quoten? |
| Kalendername stimmt nicht | Namen exakt inkl. Leerzeichen, Gedankenstrich und Großschreibung korrigieren. |
| Wiederholungs-/Ausnahmefehler | Nicht überspringen: echte Datendarstellung prüfen. Sonst könnte ein gelöschtes Serienvorkommen fälschlich wieder erscheinen. |
| TimeTree leer / Löschschutz | In TimeTree gegenprüfen; nur bei beabsichtigter Bereinigung passende Optionen/Limits setzen. |
| HTTP 429/5xx | Begrenzte Retries mit Wartezeit sind eingebaut. Beim nächsten Zeitplan wird neu abgeglichen. |
| HTTP 412 | Jemand hat den Google-Termin parallel geändert; nächsten Lauf abwarten. Gleichzeitige lokale Instanzen abstellen. |
| HTTP 409/410 bei einem früher in Google gelöschten Spiegeltermin | Die Bridge versucht eine Wiederherstellung, wenn Google die feste ID samt Bridge-Markierung und ETag liefert. Bei verbleibendem Konflikt Termin im Google-Papierkorb wiederherstellen und erneut laufen lassen. Falls das nicht geht: Zeitplan pausieren, **einen neuen leeren dedizierten Zielkalender** anlegen/freigeben, Konfiguration auf ihn umstellen und zuerst dry-run/apply testen. Alten Spiegelkalender anschließend in Google manuell entfernen. Nicht nur den Namespace ändern: sonst bleiben alte Kopien stehen. |
| Keine neuen Läufe | Variable/Standardbranch/Actions-Aktivierung, Kontingent und bei öffentlichem Repo Inaktivitätsregel prüfen. |
| Google korrekt, ChatGPT findet nichts | Richtiges verbundenes Google-Konto, Zielkalender, Connector-Berechtigungen, Tarif und Connector-Aktualisierung prüfen. Die Bridge kann dessen Umfang nicht erweitern. |

Für E-Mail-Fehlerbenachrichtigungen GitHub → persönliche Einstellungen → Notifications → Actions konfigurieren. Die Bridge selbst verschickt keine Nachrichten und benötigt keinen weiteren Dienst. Ausbleibende Cron-Läufe erzeugen keinen fehlgeschlagenen Job und damit nicht zwingend eine Fehlermail: gelegentlich „letzter erfolgreicher Lauf“ prüfen.

## 10. Lokal prüfen und kostenlose Notfallalternative

Ohne Zugangsdaten:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python sync.py --config config.example.json --snapshot examples/snapshot.example.json --probe
```

Mit realer lokaler `config.json` und sicher bereitgestellten Umgebungsvariablen (nicht in Shell-History eingeben) ist `python sync.py` immer nur ein Dry-Run; erst `python sync.py --apply` schreibt. Läuft GitHub bereits, lokale Schreibläufe vermeiden.

Bei Ausfall gilt [FALLBACK.md](FALLBACK.md): Ein manueller Browser-Snapshot kann mit den beiliegenden Werkzeugen nach Google migriert werden, sofern du im Browser noch an die Daten kommst. Danach Google als führenden Kalender zu verwenden ist die dauerhaft einfachere kostenlose Alternative. **Ein Snapshot aktualisiert sich nicht von selbst.** Ist auch der TimeTree-Browserzugriff ausgefallen, kann dieses Paket keine nicht mehr zugänglichen Daten exportieren.
