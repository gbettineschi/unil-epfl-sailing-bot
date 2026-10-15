"""Offline characterization of the original bot, including named defects.

These assertions describe the baseline, not the desired watcher behavior.
Never construct a credentialed bot or permit real HTTP in this suite.
"""

import configparser
import logging
import unittest
from datetime import date
from unittest.mock import Mock, patch

from bot import SailingBot, _normalize, _parse_day_token, _parse_hour_token


class LegacyBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch("requests.sessions.Session.request", side_effect=AssertionError("HTTP forbidden in offline tests")).start()
        self.bot = SailingBot.__new__(SailingBot)
        self.bot.log = logging.getLogger("test.legacy")
        self.bot.navigation_url = "https://example.invalid/navigation"
        self.bot.send_telegram = Mock()
        self.bot.paused = False
        self.bot._prev_slot_keys = set()
        self.bot._prev_navigation_slot_keys = set()
        self.bot._format_update = lambda slots, total: "course alert"
        self.bot._format_navigation_update = lambda slots, total: "navigation alert"

    def test_accents_and_case_are_ignored(self):
        self.assertEqual(_normalize("DÉRIVEUR"), "deriveur")
        self.assertIn(_normalize("Mar"), _normalize("Marine"))

    def test_day_aliases_resolve_to_fixed_dates(self):
        today = date(2026, 10, 15)
        for token, expected in [("auj", today), ("demain", date(2026, 10, 16)),
                                ("Saturday", date(2026, 10, 17)), ("sam", date(2026, 10, 17)),
                                ("jeudi", today), ("14.10", date(2027, 10, 14)),
                                ("2026-10-17", date(2026, 10, 17))]:
            with self.subTest(token=token):
                self.assertEqual(_parse_day_token(token, today), expected)

    def test_hour_aliases_preserve_exact_or_any(self):
        for token, expected in [("14", 840), ("14h30", 870), ("14:30", 870),
                                ("any", "any"), ("toutes", "any"), ("*", "any"),
                                ("25:00", None)]:
            with self.subTest(token=token):
                self.assertEqual(_parse_hour_token(token), expected)

    def test_requests_sort_by_priority_then_creation(self):
        self.bot.registration_requests = [
            {"id": "low", "priority": 9, "created": 1},
            {"id": "new", "priority": 1, "created": 3},
            {"id": "old", "priority": 1, "created": 2},
        ]
        self.bot._sort_requests()
        self.assertEqual([r["id"] for r in self.bot.registration_requests], ["old", "new", "low"])

    def test_boat_preference_precedes_start_time(self):
        request = {"day": "2026-10-17", "hour_min": None, "boats": ["aero", "laser"]}
        early = {"date": "17.10.2026", "time": "10:00–12:00", "support": "Laser"}
        preferred = {"date": "17.10.2026", "time": "14:00–16:00", "support": "RS Aero"}
        self.assertEqual(self.bot._request_candidates(request, [early, preferred]), [preferred, early])
        request["hour_min"] = 600
        self.assertEqual(self.bot._request_candidates(request, [early, preferred]), [early])

    def load_rules(self, rules):
        self.bot.config = configparser.ConfigParser()
        self.bot.config.read_dict({"navigation_libre_time_filters": rules})
        self.bot.navigation_time_filters = self.bot._load_navigation_time_filters()

    def test_all_four_time_bounds_are_inclusive(self):
        self.load_rules({"laser": "after 12:00, before 14:00, end_after 15:00, end_before 17:00"})
        for time, allowed in [("12:00–15:00", True), ("14:00–17:00", True),
                              ("11:59–15:00", False), ("14:01–17:00", False),
                              ("13:00–14:59", False), ("13:00–17:01", False)]:
            with self.subTest(time=time):
                self.assertEqual(self.bot._passes_navigation_time_filters({"support": "Laser", "time": time}), allowed)

    def test_longest_boat_pattern_replaces_broader_rule(self):
        self.load_rules({"catamaran": "after 17:00", "hobie cat 18": "after 12:00, before 18:00"})
        for time, allowed in [("13:00–15:00", True), ("19:00–21:00", False)]:
            with self.subTest(time=time):
                self.assertEqual(self.bot._passes_navigation_time_filters({"support": "Catamaran / Hobie Cat 18", "time": time}), allowed)
        self.assertTrue(self.bot._passes_navigation_time_filters({"support": "Laser", "time": "10:00–12:00"}))

    def test_legacy_defect_unknown_time_passes_time_constraints(self):
        self.load_rules({"laser": "after 12:00, end_before 17:00"})
        self.assertTrue(self.bot._passes_navigation_time_filters({"support": "Laser", "time": "unknown"}))

    def test_legacy_defect_unknown_date_passes_horizon(self):
        self.assertTrue(self.bot._within_days_ahead("unknown", 21))

    def test_calendar_key_is_stable_when_window_start_moves(self):
        slot = {"date": "17.10.2026", "time": "10:00–16:00", "support": "SUP", "planning_id": "42"}
        later = {**slot, "time": "11:00–16:00"}
        self.assertEqual(self.bot._navigation_slot_key(slot), self.bot._navigation_slot_key(later))

    def test_legacy_defect_disjoint_calendar_windows_share_key(self):
        slot = {"date": "17.10.2026", "time": "10:00–12:00", "support": "SUP", "planning_id": "42"}
        later = {**slot, "time": "14:00–16:00"}
        self.assertEqual(self.bot._navigation_slot_key(slot), self.bot._navigation_slot_key(later))

    def test_first_scan_is_a_silent_baseline(self):
        self.bot._prev_slot_keys = None
        self.bot._process_course_slots([{"href": "course-1"}])
        self.assertEqual(self.bot._prev_slot_keys, {"course-1"})
        self.bot.send_telegram.assert_not_called()

    def test_pause_consumes_new_slots_without_alerting_on_resume(self):
        self.bot.paused = True
        self.bot._process_course_slots([{"href": "course-1"}])
        self.bot.paused = False
        self.bot._process_course_slots([{"href": "course-1"}])
        self.assertEqual(self.bot._prev_slot_keys, {"course-1"})
        self.bot.send_telegram.assert_not_called()

    def test_failed_scan_preserves_baseline_but_empty_scan_clears_it(self):
        for method, field in [(self.bot._process_course_slots, "_prev_slot_keys"),
                              (self.bot._process_navigation_slots, "_prev_navigation_slot_keys")]:
            with self.subTest(source=field):
                setattr(self.bot, field, {"existing"})
                method(None)
                self.assertEqual(getattr(self.bot, field), {"existing"})
                method([])
                self.assertEqual(getattr(self.bot, field), set())

    def test_legacy_defect_failed_delivery_still_advances_baseline(self):
        self.bot.send_telegram.return_value = None  # Real sender also returns None on failure.
        self.bot._process_course_slots([{"href": "course-1"}])
        self.assertEqual(self.bot._prev_slot_keys, {"course-1"})
        self.bot.send_telegram.assert_called_once()

    def test_legacy_defect_cancellation_reports_success_when_verification_fails(self):
        response = Mock(text='<a href="?a=remove">Cancel</a>', url="https://example.invalid/slot")
        self.bot.navigation_session = Mock()
        self.bot.navigation_session.get.return_value = response
        self.bot._slot_status = Mock(return_value=("error", None, None))
        self.assertEqual(self.bot.cancel_navigation_slot(response.url), (True, "cancelled"))

    def test_wind_conversion_uses_knots(self):
        self.assertAlmostEqual(self.bot._kmh_to_knots(18.52), 10.0)


if __name__ == "__main__":
    unittest.main()
