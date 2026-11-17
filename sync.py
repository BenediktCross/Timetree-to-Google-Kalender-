#!/usr/bin/env python3
"""TimeTree -> Google. Internal TimeTree protocol adapted from Kumanogorou (MIT).

Never logs response bodies, credentials, event titles, URLs or calendar IDs.
Full source + destination preflight precedes all writes; writes are not atomic.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from dateutil.rrule import rrulestr

LOG = logging.getLogger("sync")
OWNER = "timetree-github-v1"
SCOPES = ["https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/calendar.readonly"]


class SyncError(Exception):
    """Only sanitized, developer-controlled messages may be passed here."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(text, label):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        raise SyncError(f"{label}: ungültiges JSON; Inhalte werden aus Datenschutzgründen nicht geloggt.") from None


def flag(value, label):
    if type(value) is not bool:
        raise SyncError(f"{label}: true oder false erwartet.")
    return value


def load_config(path):
    raw = os.environ.get("SYNC_CONFIG_JSON")
    if not raw:
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except OSError:
            raise SyncError("SYNC_CONFIG_JSON fehlt; alternativ lokale config.json anlegen.") from None
    cfg = read_json(raw, "Konfiguration")
    if not isinstance(cfg, dict) or not isinstance(cfg.get("calendars"), list) or not cfg["calendars"]:
        raise SyncError("Konfiguration: calendars muss eine nicht leere Liste sein.")
    cfg.setdefault("namespace", "my-timetree-bridge")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,64}", str(cfg["namespace"])):
        raise SyncError("namespace: 3–64 Buchstaben, Ziffern, Unterstriche oder Bindestriche erwartet.")
    seen = set()
    for c in cfg["calendars"]:
        if not isinstance(c, dict):
            raise SyncError("Jeder calendars-Eintrag muss ein Objekt sein.")
        source = str(c.get("timetree_calendar_id", ""))
        target = c.get("google_calendar_id", "")
        if not re.fullmatch(r"[1-9][0-9]*", source) or source in seen:
            raise SyncError("TimeTree-Kalender-IDs müssen positive, eindeutige Zahlen sein.")
        seen.add(source)
        c["timetree_calendar_id"] = source
        c.setdefault("google_target_type", "secondary")
        target_types = {
            "secondary": r"[^@\s]+@group\.calendar\.google\.com",
            "dedicated_primary": r"[^@\s]+@gmail\.com",
        }
        target_pattern = target_types.get(str(c["google_target_type"]))
        if not target_pattern or not isinstance(target, str) or not re.fullmatch(target_pattern, target):
            raise SyncError("Google-Ziel: ID des Zusatzkalenders oder Gmail-Adresse eines separaten Kontos mit google_target_type=dedicated_primary angeben.")
        if not isinstance(c.get("expected_google_calendar_name"), str) or not c["expected_google_calendar_name"]:
            raise SyncError("expected_google_calendar_name fehlt.")
        c.setdefault("timezone", "Europe/Berlin")
        for field in ("timezone", "all_day_timezone"):
            if field in c:
                time_zone(c[field], f"Konfiguration {field}")
        for name in ("full_snapshot_confirmed", "allow_empty_source"):
            c[name] = flag(c.get(name, False), name)
        for name, default in (("max_deletions", 25), ("max_delete_fraction", 1.0)):
            value = c.get(name, default)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise SyncError(f"{name}: nicht negative Zahl erwartet.")
            c[name] = value
        if c["max_delete_fraction"] > 1:
            raise SyncError("max_delete_fraction darf höchstens 1 sein.")
        c.setdefault("all_day_end_mode", "exclusive")
        if c["all_day_end_mode"] not in ("exclusive", "inclusive"):
            raise SyncError("all_day_end_mode muss exclusive oder inclusive sein.")
    names = {}
    for c in cfg["calendars"]:
        key = c["google_calendar_id"]
        if key in names and names[key] != c["expected_google_calendar_name"]:
            raise SyncError("Für dasselbe Google-Ziel wurden verschiedene erwartete Namen angegeben.")
        names[key] = c["expected_google_calendar_name"]
    return cfg


def request_json(session, method, url, *, label, allowed=(), **kwargs):
    """Bounded retries. No redirect may forward a secret to another host."""
    for attempt in range(4):
        try:
            r = session.request(method, url, timeout=(10, 30), allow_redirects=False, **kwargs)
        except requests.RequestException:
            if attempt == 3:
                raise SyncError(f"{label}: Netzwerkfehler/Timeout; nächster Lauf kann fortsetzen.") from None
            time.sleep(2 ** attempt)
            continue
        if r.status_code in allowed:
            return r.status_code, {}
        retryable = r.status_code == 429 or r.status_code >= 500
        if r.status_code == 403 and label == "Google":
            try:
                reasons = {e.get("reason") for e in r.json().get("error", {}).get("errors", [])}
                retryable = bool(reasons & {"rateLimitExceeded", "userRateLimitExceeded"})
            except (ValueError, TypeError, AttributeError):
                pass
        if retryable and attempt < 3:
            try:
                delay = max(2 ** attempt, float(r.headers.get("Retry-After", 0)))
            except ValueError:
                delay = 2 ** attempt
            if not math.isfinite(delay) or delay > 30:
                raise SyncError(f"{label}: Rate-Limit; Server verlangt längere Pause. Nächsten Lauf abwarten.")
            time.sleep(delay)
            continue
        if not 200 <= r.status_code < 300:
            hints = {
                401: "Anmeldung abgelaufen; TimeTree-Cookie bzw. Google-Autorisierung erneuern.",
                403: "Zugriff verweigert; Berechtigungen, Freigabe, API-Aktivierung und Quota prüfen.",
                404: "Kalender/Termin nicht erreichbar; IDs, Freigabe oder Schnittstelle prüfen.",
                409: "Termin-ID kollidiert; keine fremden Termine überschrieben.",
                410: "Termin-ID wurde bei Google gelöscht; Anleitung zur Wiederherstellung beachten.",
                412: "Google-Termin wurde gleichzeitig geändert; nächsten Lauf abwarten.",
                429: "Rate-Limit; nächsten Lauf abwarten.",
            }
            raise SyncError(f"{label}: HTTP {r.status_code}. " + hints.get(r.status_code, "Abruf/Schreiben fehlgeschlagen; Schnittstelle prüfen."))
        if r.status_code == 204:
            return r.status_code, {}
        try:
            data = r.json()
        except ValueError:
            raise SyncError(f"{label}: statt JSON kam z. B. eine Login-/Fehlerseite. Sitzung/Schnittstelle prüfen.") from None
        if not isinstance(data, dict):
            raise SyncError(f"{label}: unerwartetes JSON-Format.")
        return r.status_code, data
    raise SyncError(f"{label}: Wiederholungen ausgeschöpft.")


def fetch_source(session, source, cookie):
    """Upstream protocol: since=0, then all chunks; no persisted cursors."""
    cursor, seen, events = 0, {"0"}, {}
    for page in range(1000):
        _, data = request_json(
            session, "GET", f"https://timetreeapp.com/api/v1/calendar/{source}/events/sync",
            label="TimeTree", params={"since": cursor},
            headers={"x-timetreea": "web/2.1.0/ja", "Accept": "application/json"},
            cookies={"_session_id": cookie})
        if not isinstance(data.get("events"), list) or type(data.get("chunk")) is not bool:
            raise SyncError("TimeTree: events-Liste oder boolesches chunk fehlt. Keine Google-Änderung.")
        for event in data["events"]:
            if not isinstance(event, dict) or not event.get("id"):
                raise SyncError("TimeTree: Termin ohne gültige ID. Keine Google-Änderung.")
            if str(event.get("calendar_id")) != source:
                raise SyncError("TimeTree: unerwartete Kalenderzuordnung. Keine Google-Änderung.")
            events[str(event["id"])] = event
        if data["chunk"] is False:
            LOG.info("TimeTree: %d Seiten vollständig empfangen, %d eindeutige Datensätze.", page + 1, len(events))
            return list(events.values())
        cursor = data.get("since")
        if type(cursor) not in (str, int) or str(cursor) in seen or str(cursor) == "":
            raise SyncError("TimeTree: ungültiger/wiederholter Seiten-Cursor. Keine Google-Änderung.")
        seen.add(str(cursor))
    raise SyncError("TimeTree: mehr als 1000 Seiten; Abbruch ohne Google-Änderung.")


def timestamp(value, tz):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise SyncError("TimeTree: start_at/end_at als Unix-Millisekunden erwartet; keine Einheit geraten.")
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone(tz)
    except (ValueError, OverflowError, OSError):
        raise SyncError("TimeTree: ungültiger Zeitstempel.") from None


def time_zone(value, label):
    try:
        return ZoneInfo(value)
    except (KeyError, TypeError, ValueError):
        raise SyncError(f"{label}: unbekannte IANA-Zeitzone.") from None


def recurrence(lines, all_day, start, tz):
    if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
        raise SyncError("TimeTree: recurrences muss eine Liste von Zeichenketten sein.")
    result = []
    for line in lines:
        if "\n" in line or "\r" in line or ":" not in line:
            raise SyncError("TimeTree: ungültige Wiederholungszeile.")
        head, value = line.split(":", 1)
        if head == "RRULE":
            # TimeTree's date-only UNTIL is interpreted as end of that local day.
            def until(match):
                raw = match.group(1)
                if all_day:
                    if len(raw) != 8:
                        raise SyncError("TimeTree: ganztägiges UNTIL muss ein Datum sein.")
                    return "UNTIL=" + raw
                if re.fullmatch(r"\d{8}", raw):
                    dt = datetime.strptime(raw, "%Y%m%d").replace(hour=23, minute=59, second=59, tzinfo=tz)
                elif re.fullmatch(r"\d{8}T\d{6}", raw):
                    dt = datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=tz)
                else:
                    return "UNTIL=" + raw
                return "UNTIL=" + dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            try:
                value = re.sub(r"UNTIL=([^;]+)", until, value)
                parts = dict(x.split("=", 1) for x in value.split(";"))
                if "COUNT" in parts and "UNTIL" in parts:
                    raise ValueError()
                if parts.get("FREQ") not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
                    raise ValueError()
                rrulestr(value, dtstart=start.replace(tzinfo=None) if all_day else start)
            except (ValueError, TypeError, OverflowError):
                raise SyncError("TimeTree: nicht unterstützte RRULE; keine Google-Änderung.") from None
            result.append("RRULE:" + value)
        elif head.split(";")[0] in ("EXDATE", "RDATE"):
            kind = head.split(";")[0]
            date_tz = tz
            if ";TZID=" in head:
                try:
                    date_tz = ZoneInfo(head.split(";TZID=", 1)[1])
                except (KeyError, ValueError):
                    raise SyncError("TimeTree: unbekannte Zeitzone in EXDATE/RDATE.") from None
            elif head not in (kind, kind + ";VALUE=DATE", kind + ";VALUE=DATE-TIME"):
                raise SyncError("TimeTree: unbekannte EXDATE/RDATE-Parameter.")
            values = []
            for raw in value.split(","):
                try:
                    if all_day:
                        if re.fullmatch(r"\d{8}", raw):
                            day = datetime.strptime(raw, "%Y%m%d").date()
                        else:
                            fmt = "%Y%m%dT%H%M%SZ" if raw.endswith("Z") else "%Y%m%dT%H%M%S"
                            dt = datetime.strptime(raw, fmt)
                            zone = timezone.utc if raw.endswith("Z") else date_tz
                            day = dt.replace(tzinfo=zone).astimezone(tz).date()
                        values.append(day.strftime("%Y%m%d"))
                    else:
                        utc = raw.endswith("Z")
                        dt = datetime.strptime(raw.rstrip("Z"), "%Y%m%dT%H%M%S")
                        dt = dt.replace(tzinfo=timezone.utc if utc else date_tz)
                        values.append(dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
                except ValueError:
                    raise SyncError("TimeTree: EXDATE/RDATE passt nicht zum Terminformat.") from None
            result.append(kind + (";VALUE=DATE:" if all_day else ":") + ",".join(values))
        else:
            raise SyncError("TimeTree: unbekannte Wiederholungsart; keine Google-Änderung.")
    return result


def is_deleted(event):
    for field in ("deactivated_at", "deleted_at"):
        value = event.get(field)
        if value is None or value == "":
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise SyncError(f"TimeTree: unbekannte {field}-Kodierung.")
        if value > 0:
            return True
    deleted = event.get("deleted")
    if deleted is not None and type(deleted) is not bool:
        raise SyncError("TimeTree: unbekannte deleted-Kodierung.")
    return deleted is True


def normalize(events, c, namespace):
    desired, deleted, by_id = {}, set(), {}
    format_errors = Counter()
    bounded_without_exclusion = 0
    for event in events:
        if not isinstance(event, dict) or not event.get("id") or str(event.get("calendar_id")) != c["timetree_calendar_id"]:
            raise SyncError("TimeTree/Snapshot: fehlende ID oder falscher Kalender.")
        source_id = str(event["id"])
        if source_id in by_id:
            raise SyncError("Snapshot: doppelte Quell-ID; erst Seiten zusammenführen.")
        by_id[source_id] = event

    by_uuid = {event["uuid"]: event for event in by_id.values()
               if isinstance(event.get("uuid"), str) and event["uuid"]}
    for source_id, event in by_id.items():
        key = digest([namespace, c["timetree_calendar_id"], source_id])
        if is_deleted(event):
            deleted.add(key)
            continue
        if event.get("category") == 2:
            # TimeTree uses category 2 for undated memos.
            continue
        for field in ("recurring_event_id", "recurrence_id", "original_start_at", "parent_event_id"):
            if event.get(field) not in (None, "", 0):
                raise SyncError("TimeTree: separate Serien-Ausnahme erkannt. Mapping ist unbestätigt; Abbruch.")
        parent_id = event.get("parent_id")
        parent_uuid = event.get("recurring_uuid")
        has_parent_id = parent_id not in (None, 0, "0", "")
        if has_parent_id or parent_uuid:
            parent = by_id.get(str(parent_id)) if has_parent_id else by_uuid.get(str(parent_uuid))
            if parent is event or (parent and parent_uuid and parent.get("uuid") != parent_uuid):
                raise SyncError("TimeTree: widersprüchlicher Bezug eines Serienvorkommens.")
            if parent and not is_deleted(parent):
                parent_lines = event_body(parent, c)["recurrence"]
                has_exclusion = any(line.startswith(("EXDATE:", "EXDATE;")) for line in parent_lines)
                bounded = bool(parent_lines) and all(
                    line.startswith("RRULE:") and re.search(r"(?:[:;])(?:COUNT|UNTIL)=", line)
                    for line in parent_lines)
                if event.get("recurrences") or not (has_exclusion or bounded):
                    raise SyncError("TimeTree: verschobenes Serienvorkommen ohne EXDATE und ohne begrenzte Hauptserie.")
                if not has_exclusion:
                    bounded_without_exclusion += 1
        try:
            body = event_body(event, c)
        except SyncError as exc:
            format_errors[str(exc)] += 1
            continue
        body["extendedProperties"] = {"private": {
            "ttOwner": OWNER, "ttNamespace": namespace,
            "ttSource": c["timetree_calendar_id"], "ttKey": key,
        }}
        desired[key] = body
    if format_errors:
        messages = "; ".join(f"{count} × {message}" for message, count in format_errors.items())
        raise SyncError(f"TimeTree: nicht importierbare Termine. {messages}")
    if bounded_without_exclusion:
        LOG.warning("TimeTree: %d Einzelvorkommen aus begrenzten Serien ohne EXDATE. Die gelieferten Serienregeln bleiben erhalten.",
                    bounded_without_exclusion)
    return desired, deleted


def event_body(event, c):
    if "all_day" not in event:
        raise SyncError("TimeTree: all_day fehlt.")
    all_day = flag(event["all_day"], "TimeTree all_day")
    all_day_zone = c.get("all_day_timezone", c["timezone"])
    start_zone = all_day_zone if all_day else event.get("start_timezone") or c["timezone"]
    end_zone = all_day_zone if all_day else event.get("end_timezone") or start_zone
    tz = time_zone(start_zone, "TimeTree Startzeitzone")
    end_tz = time_zone(end_zone, "TimeTree Endzeitzone")
    start = timestamp(event.get("start_at"), tz)
    end = timestamp(event.get("end_at"), end_tz)
    start_utc, end_utc = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end_utc < start_utc:
        raise SyncError("TimeTree: Ende liegt vor Beginn.")
    unspecified_end = not all_day and end_utc == start_utc
    if unspecified_end:
        end = (start_utc + timedelta(minutes=1)).astimezone(end_tz)
    for field in ("title", "note", "location"):
        if event.get(field) is not None and not isinstance(event[field], str):
            raise SyncError("TimeTree: unerwarteter Textfeld-Typ.")
    if all_day:
        sd, ed = start.date(), end.date()
        if c["all_day_end_mode"] == "inclusive" or end.time().replace(tzinfo=None) != datetime.min.time():
            ed += timedelta(days=1)
        if ed <= sd:
            ed = sd + timedelta(days=1)
        gs, ge = {"date": sd.isoformat()}, {"date": ed.isoformat()}
    else:
        gs = {"dateTime": start.isoformat(), "timeZone": start_zone}
        ge = {"dateTime": end.isoformat(), "timeZone": end_zone}
    lines = event.get("recurrences")
    rules = recurrence([] if lines is None else lines, all_day, start, tz)
    body = {
        "summary": event.get("title") or "(Ohne Titel)",
        "description": event.get("note") or "",
        "location": event.get("location") or "",
        "start": gs, "end": ge, "recurrence": rules,
        "reminders": {"useDefault": False}, "status": "confirmed",
    }
    if unspecified_end:
        body["endTimeUnspecified"] = True
    return body


def google_session(*, requires_user=False):
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not raw:
        raise SyncError("GitHub Secret GOOGLE_CREDENTIALS_JSON fehlt.")
    info = read_json(raw, "GOOGLE_CREDENTIALS_JSON")
    if requires_user and isinstance(info, dict) and info.get("type") == "service_account":
        raise SyncError("dedicated_primary benötigt Benutzer-OAuth für das separate Google-Konto.")
    # Keep Google authentication dependencies out of the source-only probe.
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials

    try:
        if info.get("type") == "service_account":
            if info.get("token_uri") != "https://oauth2.googleapis.com/token":
                raise ValueError()
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif info.get("type") in (None, "authorized_user"):
            creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
        else:
            raise ValueError()
        # Refresh errors must never print token endpoint response bodies.
        creds.refresh(Request())
        return AuthorizedSession(creds)
    except Exception:
        raise SyncError("Google-Anmeldung fehlgeschlagen. JSON-Schlüssel/Freigabe bzw. OAuth-Refresh-Token erneuern; kein Browserlogin in Actions.") from None


class Google:
    def __init__(self, session):
        self.session = session

    def call(self, method, calendar, suffix="", **kwargs):
        return request_json(self.session, method,
                            "https://www.googleapis.com/calendar/v3/calendars/" + quote(calendar, safe="") + suffix,
                            label="Google", **kwargs)

    def preflight(self, calendar, expected, *, dedicated_primary=False):
        _, metadata = self.call("GET", "primary" if dedicated_primary else calendar)
        if dedicated_primary and metadata.get("id") != calendar:
            raise SyncError("Google: OAuth-Konto und konfigurierte Gmail-Adresse stimmen nicht überein. Keine Änderung.")
        if metadata.get("summary") != expected:
            raise SyncError("Google-Kalendername stimmt nicht mit expected_google_calendar_name überein. Keine Änderung.")
        items, token, seen = [], None, set()
        while True:
            params = {"maxResults": 2500, "singleEvents": "false", "showDeleted": "false"}
            if token:
                params["pageToken"] = token
            _, data = self.call("GET", calendar, "/events", params=params)
            if not isinstance(data.get("items", []), list):
                raise SyncError("Google: unerwartete Terminliste.")
            items.extend(data.get("items", []))
            token = data.get("nextPageToken")
            if not token:
                return items
            if not isinstance(token, str) or token in seen or len(seen) >= 1000:
                raise SyncError("Google: ungültige Seitennavigation; keine Änderung.")
            seen.add(token)

    def insert(self, calendar, body):
        # Fixed source key survives ephemeral runners, retried POSTs and lost responses.
        event = {**body, "id": "tt" + body["extendedProperties"]["private"]["ttKey"]}
        status, _ = self.call("POST", calendar, "/events", json=event,
                              params={"sendUpdates": "none"}, allowed=(409,))
        if status == 409:
            _, existing = self.call("GET", calendar, "/events/" + event["id"])
            if existing.get("extendedProperties", {}).get("private") != body["extendedProperties"]["private"]:
                if existing.get("status") == "cancelled":
                    raise SyncError("Google: gelöschte Termin-ID ohne Bridge-Markierung. Wiederherstellung laut Anleitung nötig.")
                raise SyncError("Google: ID-Kollision mit fremdem Termin; Abbruch.")
            if existing.get("id") != event["id"] or not existing.get("etag"):
                raise SyncError("Google: bestehender Termin bei ID-Konflikt ohne gültige ID/ETag.")
            self.update(calendar, existing, body)

    def update(self, calendar, old, body):
        self.call("PUT", calendar, "/events/" + quote(old["id"], safe=""), json=body,
                  headers={"If-Match": old["etag"]}, params={"sendUpdates": "none"})

    def delete(self, calendar, old):
        self.call("DELETE", calendar, "/events/" + quote(old["id"], safe=""),
                  headers={"If-Match": old["etag"]}, params={"sendUpdates": "none"}, allowed=(404, 410))


def same_content(old, new):
    # Compare actual fields, not only a cached source fingerprint: user edits are corrected.
    for field in ("summary", "description", "location", "recurrence"):
        if (old.get(field) or ([] if field == "recurrence" else "")) != new[field]:
            return False
    if bool(old.get("endTimeUnspecified")) != bool(new.get("endTimeUnspecified")):
        return False
    dates = ("start",) if new.get("endTimeUnspecified") else ("start", "end")
    for field in dates:
        a, b = old.get(field, {}), new[field]
        if "date" in b:
            if a.get("date") != b["date"]:
                return False
        else:
            try:
                if datetime.fromisoformat(a["dateTime"].replace("Z", "+00:00")) != datetime.fromisoformat(b["dateTime"]):
                    return False
                if a.get("timeZone") != b["timeZone"] and (new["recurrence"] or a.get("timeZone")):
                    return False
            except (KeyError, ValueError, TypeError):
                return False
    return old.get("reminders") == new["reminders"] and old.get("status", "confirmed") == "confirmed"


def plan(c, namespace, desired, deleted, existing):
    owned = {}
    for event in existing:
        p = event.get("extendedProperties", {}).get("private", {})
        if p.get("ttOwner") == OWNER and p.get("ttNamespace") == namespace and p.get("ttSource") == c["timetree_calendar_id"]:
            if not re.fullmatch(r"[a-f0-9]{64}", p.get("ttKey", "")) or not event.get("id") or not event.get("etag"):
                raise SyncError("Google: verwalteter Termin ohne gültigen Schlüssel/ETag. Keine Änderung.")
            owned.setdefault(p["ttKey"], []).append(event)
    inserts, updates, removals = [], [], []
    for key, body in desired.items():
        expected_id = "tt" + key
        candidates = sorted(owned.get(key, []), key=lambda event: (event["id"] != expected_id, event["id"]))
        if not candidates:
            inserts.append(body)
        else:
            if not same_content(candidates[0], body):
                updates.append((candidates[0], body))
            removals.extend(candidates[1:])
    for key, candidates in owned.items():
        if key in deleted or (c["full_snapshot_confirmed"] and key not in desired):
            removals.extend(candidates)
    active_count = sum(len(x) for x in owned.values())
    if removals and (len(removals) > c["max_deletions"] or len(removals) / active_count > c["max_delete_fraction"]):
        raise SyncError("Löschschutz: geplante Löschungen überschreiten max_deletions/max_delete_fraction. Dry-Run prüfen und Grenzwerte gezielt anpassen.")
    if not desired and not deleted and owned and not c["allow_empty_source"]:
        raise SyncError("TimeTree ist leer, Google enthält Spiegeltermine. allow_empty_source ist false; Sitzung und tatsächliche Leerung manuell prüfen.")
    if not c["full_snapshot_confirmed"]:
        LOG.warning("Vollständigkeit unbestätigt: Löschung durch bloßes Fehlen ist deaktiviert; explizite Löschdatensätze werden berücksichtigt.")
    return inserts, updates, removals


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--probe", action="store_true", help="Nur TimeTree abrufen/prüfen, kein Google-Zugriff")
    parser.add_argument("--apply", action="store_true", help="Änderungen schreiben; Standard ist Dry-Run")
    parser.add_argument("--snapshot", help="Manueller JSON-Snapshot statt TimeTree-Abruf")
    args = parser.parse_args(argv)
    if args.probe and args.apply:
        raise SyncError("--probe und --apply schließen sich aus.")
    cfg = load_config(args.config)
    snapshots = None
    if args.snapshot:
        try:
            snapshots = read_json(Path(args.snapshot).read_text(encoding="utf-8"), "Snapshot")["calendars"]
        except (OSError, KeyError, TypeError):
            raise SyncError("Snapshot: Datei nicht lesbar oder calendars fehlt.") from None
        if not isinstance(snapshots, dict):
            raise SyncError("Snapshot: calendars muss ein Objekt sein.")
    else:
        cookie = os.environ.get("TIMETREE_SESSION_ID", "")
        if not cookie or re.search(r"[\r\n;]", cookie):
            raise SyncError("TIMETREE_SESSION_ID fehlt/ist ungültig; nur Cookie-Wert ohne Namen eintragen.")
    sources = []
    with requests.Session() as session:
        for index, c in enumerate(cfg["calendars"], 1):
            LOG.info("Quelle %d/%d: Abruf und Formatprüfung.", index, len(cfg["calendars"]))
            if snapshots is None:
                events = fetch_source(session, c["timetree_calendar_id"], cookie)
            else:
                events = snapshots.get(c["timetree_calendar_id"])
                if not isinstance(events, list):
                    raise SyncError("Snapshot enthält nicht alle konfigurierten Kalender.")
            desired, deleted = normalize(events, c, cfg["namespace"])
            LOG.info("Quelle %d: %d Termine/Serien, %d Löschdatensätze.", index, len(desired), len(deleted))
            sources.append((c, desired, deleted))
    if args.probe:
        LOG.info("Probe erfolgreich: nur Formatprüfung; Vollständigkeit und Live-Synchronisierung damit NICHT bewiesen.")
        return
    requires_user = any(c["google_target_type"] == "dedicated_primary" for c, _, _ in sources)
    google = Google(google_session(requires_user=requires_user))
    existing, plans = {}, []
    for c, desired, deleted in sources:
        target = c["google_calendar_id"]
        if target not in existing:
            existing[target] = google.preflight(target, c["expected_google_calendar_name"],
                                                dedicated_primary=c["google_target_type"] == "dedicated_primary")
        plans.append((target, *plan(c, cfg["namespace"], desired, deleted, existing[target])))
    counts = [sum(len(p[i]) for p in plans) for i in (1, 2, 3)]
    LOG.info("Plan: %d anlegen, %d aktualisieren, %d löschen. Modus: %s.", *counts, "APPLY" if args.apply else "DRY-RUN")
    if args.apply:
        # Upserts for every calendar succeed before any deletion begins.
        for target, inserts, updates, _ in plans:
            for body in inserts:
                google.insert(target, body)
            for old, body in updates:
                google.update(target, old, body)
        for target, _, _, removals in plans:
            for old in removals:
                google.delete(target, old)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"\nTimeTree → Google: {'angewendet' if args.apply else 'nur geplant'}\n\n")
            f.write(f"Anlegen: {counts[0]}, Aktualisieren: {counts[1]}, Löschen: {counts[2]}.\n")
    LOG.info("Lauf erfolgreich beendet.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    try:
        main()
    except SyncError as error:
        LOG.error("%s", error)
        sys.exit(1)
    except Exception as error:
        # A traceback could include URLs, response bodies or credentials.
        LOG.error("Unerwarteter Fehler (%s). Keine sensiblen Details geloggt; Format/Abhängigkeiten prüfen. Ein teilweise ausgeführter Lauf wird beim nächsten Lauf abgeglichen.", type(error).__name__)
        sys.exit(1)
