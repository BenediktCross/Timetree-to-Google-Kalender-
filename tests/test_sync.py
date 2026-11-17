import copy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import requests
import sync
from merge_snapshots import merge


def config(**changes):
    c = {"timetree_calendar_id": "12345678", "google_calendar_id": "demo@group.calendar.google.com",
         "expected_google_calendar_name": "Demo", "timezone": "Europe/Berlin",
         "all_day_end_mode": "exclusive", "full_snapshot_confirmed": True,
         "allow_empty_source": False, "max_deletions": 25, "max_delete_fraction": 1.0}
    c.update(changes)
    return c


def event(**changes):
    e = {"id": 1, "calendar_id": 12345678, "title": "Test", "all_day": False,
         "start_at": 1794988800000, "end_at": 1794992400000, "recurrences": []}
    e.update(changes)
    return e


def desired(c=None, **changes):
    return sync.normalize([event(**changes)], c or config(), "demo")[0]


def mirrored(body):
    return {**copy.deepcopy(body), "id": "tt" + body["extendedProperties"]["private"]["ttKey"], "etag": '"v1"'}


def response(data, status=200):
    r = Mock(status_code=status, headers={})
    r.json.return_value = data
    return r


class ConversionTests(unittest.TestCase):
    def test_stable_key_and_update(self):
        a, b = desired(), desired(title="Geändert", start_at=1794992400000, end_at=1794996000000)
        self.assertEqual(list(a), list(b))
        p = sync.plan(config(), "demo", b, set(), [mirrored(next(iter(a.values())))])
        self.assertEqual([len(x) for x in p], [0, 1, 0])

    def test_idempotent_and_google_utc_equivalence(self):
        d = desired()
        old = mirrored(next(iter(d.values())))
        for field in ("start", "end"):
            from datetime import timezone
            old[field]["dateTime"] = datetime.fromisoformat(old[field]["dateTime"]).astimezone(timezone.utc).isoformat()
        self.assertEqual([len(x) for x in sync.plan(config(), "demo", d, set(), [old])], [0, 0, 0])

    def test_google_edit_corrected(self):
        d = desired()
        old = mirrored(next(iter(d.values())))
        old["summary"] = "Änderung in Google"
        self.assertEqual(len(sync.plan(config(), "demo", d, set(), [old])[1]), 1)

    def test_same_source_event_id_in_two_calendars_is_distinct(self):
        a = desired()
        c = config(timetree_calendar_id="987")
        b = desired(c, calendar_id=987)
        self.assertNotEqual(list(a), list(b))

    def test_all_day_multiday_exclusive(self):
        def ms(s):
            return int(datetime.fromisoformat(s).timestamp() * 1000)
        body = next(iter(desired(all_day=True, start_at=ms("2026-11-17T00:00:00+01:00"), end_at=ms("2026-11-20T00:00:00+01:00")).values()))
        self.assertEqual(body["start"], {"date": "2026-11-17"})
        self.assertEqual(body["end"], {"date": "2026-11-20"})

    def test_all_day_inclusive(self):
        d = desired(config(all_day_end_mode="inclusive"), all_day=True,
                    start_at=1794870000000, end_at=1794956400000)
        b = next(iter(d.values()))
        self.assertEqual(b["end"]["date"], "2026-11-19")

    def test_all_day_utc_dates_and_exceptions_independent_of_calendar_zone(self):
        c = config(timezone="America/New_York", all_day_timezone="UTC", all_day_end_mode="inclusive")
        body = next(iter(desired(c, all_day=True,
                                 start_at=1794873600000, end_at=1794960000000,
                                 recurrences=["RRULE:FREQ=WEEKLY", "EXDATE:20261124T000000Z"]).values()))
        self.assertEqual(body["start"]["date"], "2026-11-17")
        self.assertEqual(body["end"]["date"], "2026-11-19")
        self.assertEqual(body["recurrence"][1], "EXDATE;VALUE=DATE:20261124")

    def test_timed_event_uses_source_timezones_across_dst_fold(self):
        start = datetime.fromisoformat("2026-10-25T02:30:00+02:00")
        end = datetime.fromisoformat("2026-10-25T02:30:00+01:00")
        body = next(iter(desired(config(timezone="UTC"), start_timezone="Europe/Berlin",
                                 end_timezone="Europe/Berlin", start_at=int(start.timestamp() * 1000),
                                 end_at=int(end.timestamp() * 1000)).values()))
        self.assertEqual(body["start"]["dateTime"], start.isoformat())
        self.assertEqual(body["end"]["dateTime"], end.isoformat())

    def test_same_start_and_end_gets_one_minute_duration(self):
        start = event()["start_at"]
        body = next(iter(desired(end_at=start).values()))
        self.assertNotIn("endTimeUnspecified", body)
        duration = datetime.fromisoformat(body["end"]["dateTime"]) - datetime.fromisoformat(body["start"]["dateTime"])
        self.assertEqual(duration.total_seconds(), 60)
        old = mirrored(body)
        self.assertTrue(sync.same_content(old, body))
        with self.assertRaisesRegex(sync.SyncError, "Ende liegt vor Beginn"):
            desired(end_at=start - 1000)

    def test_google_may_omit_timezone_for_single_event(self):
        d = desired()
        old = mirrored(next(iter(d.values())))
        old["start"].pop("timeZone")
        old["end"].pop("timeZone")
        self.assertEqual(sync.plan(config(), "demo", d, set(), [old]), ([], [], []))

    def test_recurrence_with_date_until_and_exception(self):
        b = next(iter(desired(recurrences=["RRULE:FREQ=WEEKLY;UNTIL=20270331", "EXDATE:20261124T080000Z"]).values()))
        self.assertIn("UNTIL=20270331T215959Z", b["recurrence"][0])
        self.assertEqual(b["recurrence"][1], "EXDATE:20261124T080000Z")

    def test_recurrence_preserves_local_time_across_dst(self):
        b = next(iter(desired(recurrences=["RRULE:FREQ=WEEKLY;COUNT=30"]).values()))
        rule = sync.rrulestr(b["recurrence"][0], dtstart=datetime.fromisoformat(b["start"]["dateTime"]).replace(tzinfo=sync.ZoneInfo("Europe/Berlin")))
        occurrences = list(rule)
        self.assertEqual(occurrences[0].hour, occurrences[-1].hour)
        self.assertNotEqual(occurrences[0].utcoffset(), occurrences[-1].utcoffset())

    def test_unknown_recurrence_stops(self):
        with self.assertRaises(sync.SyncError):
            desired(recurrences=["MYSTERY:abc"])

    def test_exception_object_stops(self):
        with self.assertRaises(sync.SyncError):
            desired(parent_event_id=99)

    def test_detached_occurrence_with_exdate_and_memo(self):
        master = event(uuid="master", recurrences=["RRULE:FREQ=WEEKLY", "EXDATE:20261124T080000Z"])
        moved = event(id=2, parent_id=1, recurring_uuid="master", title="Verschoben")
        memo = event(id=3, category=2, start_at=None, end_at=None, all_day=None)
        events, deleted = sync.normalize([moved, memo, master], config(), "demo")
        self.assertFalse(deleted)
        moved_body = next(body for body in events.values() if body["summary"] == "Verschoben")
        self.assertEqual(moved_body["recurrence"], [])
        master_body = next(body for body in events.values() if body["summary"] == "Test")
        self.assertIn("EXDATE:20261124T080000Z", master_body["recurrence"])
        self.assertEqual(len(events), 2)

    def test_detached_occurrence_without_matching_exclusion_fails(self):
        master = event(uuid="master", recurrences=["RRULE:FREQ=WEEKLY"])
        moved = event(id=2, parent_id=1, recurring_uuid="master")
        with self.assertRaisesRegex(sync.SyncError, "EXDATE"):
            sync.normalize([master, moved], config(), "demo")

    def test_detached_occurrence_after_shortened_series_or_without_master(self):
        master = event(uuid="master", recurrences=["RRULE:FREQ=DAILY;COUNT=1"])
        moved = event(id=2, parent_id=1, recurring_uuid="master",
                      start_at=master["start_at"] + 86400000, end_at=master["end_at"] + 86400000)
        self.assertEqual(len(sync.normalize([master, moved], config(), "demo")[0]), 2)
        self.assertEqual(len(sync.normalize([moved], config(), "demo")[0]), 1)

    def test_missing_end_or_all_day_stops(self):
        with self.assertRaises(sync.SyncError):
            desired(end_at=None)
        e = event()
        del e["all_day"]
        with self.assertRaises(sync.SyncError):
            sync.normalize([e], config(), "demo")


class PlanningTests(unittest.TestCase):
    def test_absence_deletes_only_marked_events(self):
        old = mirrored(next(iter(desired().values())))
        foreign = {"id": "personal", "summary": "Keep"}
        p = sync.plan(config(allow_empty_source=True), "demo", {}, set(), [old, foreign])
        self.assertEqual(p[2], [old])

    def test_unconfirmed_full_snapshot_never_absence_deletes(self):
        old = mirrored(next(iter(desired().values())))
        p = sync.plan(config(full_snapshot_confirmed=False), "demo", desired(id=2), set(), [old])
        self.assertEqual(p[2], [])

    def test_explicit_tombstone_deletes_last_event(self):
        old = mirrored(next(iter(desired().values())))
        d, deleted = sync.normalize([event(deleted_at=1795000000000)], config(), "demo")
        self.assertEqual(sync.plan(config(), "demo", d, deleted, [old])[2], [old])

    def test_deactivated_at_deletes_without_snapshot_confirmation(self):
        c = config(full_snapshot_confirmed=False)
        old = mirrored(next(iter(desired(c).values())))
        record = {"id": 1, "calendar_id": 12345678, "deactivated_at": 1795000000000}
        d, deleted = sync.normalize([record], c, "demo")
        self.assertEqual(sync.plan(c, "demo", d, deleted, [old])[2], [old])
        self.assertEqual(desired(c, deactivated_at=0), desired(c))
        with self.assertRaisesRegex(sync.SyncError, "deactivated_at"):
            desired(c, deactivated_at="invalid")

    @patch("sync.fetch_source")
    def test_only_missing_managed_events_are_removed_by_confirmed_changes(self, fetch):
        c = config(full_snapshot_confirmed=False)
        d = desired(id=2)
        missing = mirrored(next(iter(desired(id=1).values())))
        missing["created"] = "2026-11-22T00:00:00Z"
        active = mirrored(next(iter(d.values())))
        fetch.return_value = [{"id": 1, "deactivated_at": 1795500000000},
                              {"id": 2, "deactivated_at": 1795500000000},
                              {"id": 3, "deactivated_at": 1795500000000}]
        deleted = sync.confirm_deletions([missing, active], d, set(), c, "demo", "example")
        self.assertEqual(fetch.call_args.kwargs["changes_since"], 1795219200000)
        self.assertEqual(sync.plan(c, "demo", d, deleted, [missing, active]), ([], [], [missing]))
        fetch.reset_mock()
        sync.confirm_deletions([active], d, set(), c, "demo", "example")
        fetch.assert_not_called()

    def test_empty_response_guard(self):
        old = mirrored(next(iter(desired().values())))
        with self.assertRaises(sync.SyncError):
            sync.plan(config(), "demo", {}, set(), [old])

    def test_deletion_limit_prevents_all_writes(self):
        old = mirrored(next(iter(desired().values())))
        with self.assertRaisesRegex(sync.SyncError, "Löschschutz"):
            sync.plan(config(max_deletions=0), "demo", desired(id=2), set(), [old])

    def test_duplicate_cleanup(self):
        d = desired()
        old = mirrored(next(iter(d.values())))
        duplicate = {**copy.deepcopy(old), "id": "zz-duplicate"}
        self.assertEqual(sync.plan(config(), "demo", d, set(), [old, duplicate])[2], [duplicate])

    def test_unrelated_source_and_namespace_untouched(self):
        a = mirrored(next(iter(desired().values())))
        b = copy.deepcopy(a)
        b["extendedProperties"]["private"]["ttNamespace"] = "other"
        c = copy.deepcopy(a)
        c["extendedProperties"]["private"]["ttSource"] = "987"
        self.assertEqual(sync.plan(config(), "demo", {}, set(), [b, c]), ([], [], []))


class NetworkTests(unittest.TestCase):
    def test_all_chunks_and_latest_version(self):
        session = Mock()
        session.request.side_effect = [response({"events": [event()], "chunk": True, "since": 55}),
                                       response({"events": [event(title="latest")], "chunk": False})]
        self.assertEqual(sync.fetch_source(session, "12345678", "SECRET")[0]["title"], "latest")
        self.assertEqual(session.request.call_args_list[0].kwargs["params"], {"since": 0})
        self.assertEqual(session.request.call_args_list[1].kwargs["params"], {"since": 55})

    def test_changes_endpoint_accepts_scoped_tombstone_without_calendar_id(self):
        session = Mock()
        tombstone = {"id": 1, "deactivated_at": 1795500000000}
        session.request.return_value = response({"events": [tombstone], "chunk": False})
        self.assertEqual(sync.fetch_source(session, "12345678", "example", changes_since=123), [tombstone])
        self.assertTrue(session.request.call_args.args[1].endswith("/calendar/12345678/events"))
        self.assertEqual(session.request.call_args.kwargs["params"], {"since": 123})

    def test_stalled_cursor_fails(self):
        session = Mock()
        session.request.return_value = response({"events": [], "chunk": True, "since": 0})
        with self.assertRaises(sync.SyncError):
            sync.fetch_source(session, "12345678", "secret")

    def test_wrong_calendar_fails(self):
        session = Mock()
        session.request.return_value = response({"events": [event(calendar_id=999)], "chunk": False})
        with self.assertRaises(sync.SyncError):
            sync.fetch_source(session, "12345678", "secret")

    def test_401_message_contains_no_body(self):
        session = Mock()
        session.request.return_value = response({"secret": "NEVER-PRINT"}, 401)
        with self.assertRaises(sync.SyncError) as e:
            sync.fetch_source(session, "12345678", "secret")
        self.assertNotIn("NEVER-PRINT", str(e.exception))
        self.assertIn("HTTP 401", str(e.exception))

    @patch("sync.time.sleep")
    def test_rate_limit_retries(self, sleep):
        session = Mock()
        session.request.side_effect = [response({}, 429), response({"ok": True})]
        self.assertEqual(sync.request_json(session, "GET", "https://example.invalid", label="TimeTree")[1], {"ok": True})
        sleep.assert_called_once()

    def test_google_preflight_pages_and_name(self):
        g = sync.Google(Mock())
        g.call = Mock(side_effect=[(200, {"summary": "Demo"}),
                                   (200, {"items": [{"id": "one"}], "nextPageToken": "next"}),
                                   (200, {"items": [{"id": "two"}]})])
        self.assertEqual(len(g.preflight("x", "Demo")), 2)
        self.assertNotIn("timeMin", g.call.call_args_list[1].kwargs["params"])
        g.call = Mock(return_value=(200, {"summary": "Wrong"}))
        with self.assertRaises(sync.SyncError):
            g.preflight("x", "Demo")

    def test_dedicated_primary_requires_correct_oauth_calendar(self):
        g = sync.Google(Mock())
        g.call = Mock(side_effect=[(200, {"id": "mirror@gmail.com", "summary": "Demo"}), (200, {"items": []})])
        self.assertEqual(g.preflight("mirror@gmail.com", "Demo", dedicated_primary=True), [])
        self.assertEqual(g.call.call_args_list[0].args, ("GET", "primary"))
        self.assertEqual(g.call.call_args_list[1].args, ("GET", "mirror@gmail.com", "/events"))
        g.call = Mock(return_value=(200, {"id": "private@gmail.com", "summary": "Demo"}))
        with self.assertRaisesRegex(sync.SyncError, "OAuth-Konto"):
            g.preflight("mirror@gmail.com", "Demo", dedicated_primary=True)
        g.call.assert_called_once()

    def test_insert_retry_collision_updates_owned_event(self):
        b = next(iter(desired().values()))
        g = sync.Google(Mock())
        g.call = Mock(side_effect=[(409, {}), (200, mirrored(b)), (200, {})])
        g.insert("x", b)
        self.assertEqual(g.call.call_args_list[-1].args[0], "PUT")

    def test_insert_collision_never_overwrites_foreign(self):
        g = sync.Google(Mock())
        g.call = Mock(side_effect=[(409, {}), (200, {"id": "other"})])
        with self.assertRaises(sync.SyncError):
            g.insert("x", next(iter(desired().values())))

    def test_insert_conflict_restores_only_marked_event(self):
        b = next(iter(desired().values()))
        g = sync.Google(Mock())
        cancelled = {**mirrored(b), "status": "cancelled"}
        g.call = Mock(side_effect=[(409, {}), (200, cancelled), (200, {})])
        g.insert("x", b)
        self.assertEqual(g.call.call_args.args[0], "PUT")
        self.assertEqual(g.call.call_args.kwargs["json"]["status"], "confirmed")
        cancelled.pop("extendedProperties")
        g.call = Mock(side_effect=[(409, {}), (200, cancelled)])
        with self.assertRaisesRegex(sync.SyncError, "Wiederherstellung"):
            g.insert("x", b)


class EndToEndOfflineTests(unittest.TestCase):
    def run_main(self, c=None, events=None, args=None, google=None):
        cfg = {"namespace": "demo", "calendars": [c or config()]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps({"calendars": {"12345678": [event()] if events is None else events}}))
            with patch.dict(os.environ, {"SYNC_CONFIG_JSON": json.dumps(cfg)}, clear=True), \
                 patch("sync.google_session"), patch("sync.Google", return_value=google):
                sync.main(["--snapshot", str(path)] + (args or []))

    def test_dry_run_no_writes(self):
        g = Mock()
        g.preflight.return_value = []
        self.run_main(google=g)
        g.insert.assert_not_called()
        g.update.assert_not_called()
        g.delete.assert_not_called()

    def test_malformed_source_never_contacts_google(self):
        g = Mock()
        with self.assertRaises(sync.SyncError):
            self.run_main(events=[event(end_at=None)], args=["--apply"], google=g)
        g.preflight.assert_not_called()

    def test_failed_upsert_does_not_delete(self):
        g = Mock()
        g.preflight.return_value = [mirrored(next(iter(desired(id=9).values())))]
        g.insert.side_effect = sync.SyncError("Simulierter Fehler")
        with self.assertRaises(sync.SyncError):
            self.run_main(args=["--apply"], google=g)
        g.delete.assert_not_called()

    def test_apply_creates_then_updates_then_deletes(self):
        g = Mock()
        g.preflight.return_value = [mirrored(next(iter(desired(id=9).values()))),
                                   mirrored(next(iter(desired(id=2, title="Before").values())))]
        self.run_main(events=[event(), event(id=2, title="After")], args=["--apply"], google=g)
        self.assertEqual([x[0] for x in g.method_calls], ["preflight", "insert", "update", "delete"])

    def test_google_preflight_failure_means_no_writes(self):
        g = Mock()
        g.preflight.side_effect = sync.SyncError("Simulierter Lesefehler")
        with self.assertRaises(sync.SyncError):
            self.run_main(args=["--apply"], google=g)
        g.insert.assert_not_called()
        g.update.assert_not_called()
        g.delete.assert_not_called()

    def test_second_source_invalid_means_no_google_access(self):
        cfg = {"namespace": "demo", "calendars": [config(), config(timetree_calendar_id="99")]}
        with patch.dict(os.environ, {"SYNC_CONFIG_JSON": json.dumps(cfg), "TIMETREE_SESSION_ID": "fake"}, clear=True), \
             patch("sync.fetch_source", side_effect=[[event()], [event(calendar_id=99, end_at=None)]]), \
             patch("sync.google_session") as auth:
            with self.assertRaises(sync.SyncError):
                sync.main(["--apply"])
            auth.assert_not_called()

    def test_second_target_invalid_means_no_writes(self):
        c2 = config(timetree_calendar_id="99", google_calendar_id="two@group.calendar.google.com")
        cfg = {"namespace": "demo", "calendars": [config(), c2]}
        g = Mock()
        g.preflight.side_effect = [[], sync.SyncError("Zweites Ziel nicht lesbar")]
        with patch.dict(os.environ, {"SYNC_CONFIG_JSON": json.dumps(cfg), "TIMETREE_SESSION_ID": "fake"}, clear=True), \
             patch("sync.fetch_source", side_effect=[[event()], [event(calendar_id=99)]]), \
             patch("sync.google_session"), patch("sync.Google", return_value=g):
            with self.assertRaises(sync.SyncError):
                sync.main(["--apply"])
        g.insert.assert_not_called()
        g.update.assert_not_called()
        g.delete.assert_not_called()

    def test_oauth_original_token_without_type_supported(self):
        info = {"client_id": "fake", "client_secret": "fake", "refresh_token": "fake"}
        with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_JSON": json.dumps(info)}, clear=True), \
             patch("google.oauth2.credentials.Credentials.from_authorized_user_info") as creds, \
             patch("google.auth.transport.requests.AuthorizedSession") as session:
            sync.google_session()
            creds.assert_called_once()
            session.assert_called_once()

    def test_primary_calendar_rejected(self):
        with self.assertRaises(sync.SyncError):
            self.run_main(c=config(google_calendar_id="primary"), google=Mock())

    def test_user_oauth_required_for_dedicated_primary(self):
        c = config(google_calendar_id="mirror@gmail.com", google_target_type="dedicated_primary")
        g = Mock()
        g.preflight.return_value = []
        self.run_main(c=c, google=g)
        g.preflight.assert_called_once_with("mirror@gmail.com", "Demo", dedicated_primary=True)

        info = {"type": "service_account"}
        with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_JSON": json.dumps(info)}, clear=True):
            with self.assertRaisesRegex(sync.SyncError, "Benutzer-OAuth"):
                sync.google_session(requires_user=True)

    def test_snapshot_merge_last_page_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "page.json"
            p.write_text(json.dumps({"events": [event()], "chunk": True}))
            with self.assertRaises(sync.SyncError):
                merge([p])
            p.write_text(json.dumps({"events": [event()], "chunk": False}))
            self.assertEqual(len(merge([p])["calendars"]["12345678"]), 1)


if __name__ == "__main__":
    unittest.main()
