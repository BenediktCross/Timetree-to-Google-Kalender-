#!/usr/bin/env python3
"""Manuelle Browser-JSON-Seiten in einen Snapshot zusammenführen; enthält Privatdaten."""
import argparse
import json
import os
from pathlib import Path
from sync import SyncError, read_json


def merge(paths):
    calendars, last = {}, None
    for path in paths:
        data = read_json(Path(path).read_text(encoding="utf-8"), "Browser-Seite")
        if not isinstance(data, dict) or not isinstance(data.get("events"), list) or type(data.get("chunk")) is not bool:
            raise SyncError("events/chunk fehlt im Browser-Snapshot.")
        for event in data["events"]:
            if not isinstance(event, dict) or not event.get("id") or not event.get("calendar_id"):
                raise SyncError("Snapshot enthält Datensätze ohne IDs.")
            calendars.setdefault(str(event["calendar_id"]), {})[str(event["id"])] = event
        last = data
    if last is None or last["chunk"]:
        raise SyncError("Letzte Seite muss chunk=false enthalten. Pro Aufruf genau einen Kalender zusammenführen.")
    if len(calendars) != 1:
        raise SyncError("Genau ein Quellkalender pro Aufruf erwartet.")
    return {"calendars": {k: list(v.values()) for k, v in calendars.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages", nargs="+")
    parser.add_argument("--output", default="snapshot.json")
    args = parser.parse_args()
    try:
        os.umask(0o077)
        data = merge(args.pages)
        Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Snapshot geschrieben. Nicht committen; Vollständigkeit durch Stichproben prüfen.")
    except (SyncError, OSError):
        print("Snapshot unvollständig/ungültig. Reihenfolge und alle Seiten prüfen; keine Daten geschrieben.")
        raise SystemExit(1)
