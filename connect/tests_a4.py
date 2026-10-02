"""
Tests for the P1-A4 features, one class per assignment part.

    python manage.py test connect

These run on the real seed data (seed_demo_data), because the charts,
reports and exports are about the dataset the deployed site serves.
"""

from datetime import date, timedelta
from io import StringIO
from itertools import pairwise

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse

from .management.commands.seed_demo_data import HISTORY, STAFF_PASSWORD
from .models import (
    ExperienceFeedback,
    Match,
    MatchParticipant,
    MatchStatus,
    ProfileInterest,
    StudentProfile,
)
from .vega_charts import load_spec


def seed():
    call_command("seed_demo_data", stdout=StringIO())


class SeededTestCase(TestCase):
    """Every test class below starts from the seeded dataset."""

    @classmethod
    def setUpTestData(cls):
        seed()


# --- Part 4: deployment prerequisites (the committed seed data) ---------------


class SeedDataTests(SeededTestCase):

    def test_seed_builds_the_documented_dataset(self):
        self.assertEqual(StudentProfile.objects.count(), 8)
        self.assertEqual(Match.objects.count(), 3 + len(HISTORY))
        self.assertEqual(MatchParticipant.objects.count(), 55)
        self.assertEqual(ExperienceFeedback.objects.count(), 33)
        self.assertEqual(Match.objects.filter(status=MatchStatus.CANCELLED).count(), 1)

    def test_original_three_matches_keep_the_first_ids(self):
        # Docs, screenshots and the CI smoke test link /matches/1/ to /3/.
        codes = list(Match.objects.order_by("pk").values_list("check_in_code", flat=True)[:3])
        self.assertEqual(codes, ["QC-4827", "QC-5193", "QC-3312"])

    def test_no_student_is_in_two_matches_in_one_week(self):
        clashes = (MatchParticipant.objects
                   .values("profile", "match__week_start")
                   .annotate(n=Count("id")).filter(n__gt=1))
        self.assertEqual(list(clashes), [])

    def test_reseeding_changes_nothing(self):
        def snapshot():
            return (
                list(StudentProfile.objects.order_by("net_id")
                     .values_list("net_id", "onboarding_completed_at")),
                list(Match.objects.order_by("check_in_code")
                     .values_list("check_in_code", "scheduled_for", "status")),
                list(MatchParticipant.objects.order_by("match__check_in_code", "profile__net_id")
                     .values_list("compatibility_score", "match_reason", "checked_in_at")),
                ExperienceFeedback.objects.count(),
            )
        before = snapshot()
        seed()
        self.assertEqual(snapshot(), before)

    def test_course_staff_accounts_can_log_in(self):
        for username in ["tester", "mohitg2"]:
            user = User.objects.get(username=username)
            self.assertTrue(user.is_staff and user.is_superuser, username)
            self.assertTrue(user.check_password(STAFF_PASSWORD), username)
        self.assertTrue(self.client.login(username="tester", password=STAFF_PASSWORD))

    def test_students_have_no_password(self):
        # Students sign in through SSO later; nobody can log in as one now.
        student_users = User.objects.filter(student_profile__isnull=False)
        self.assertEqual(student_users.count(), 8)
        self.assertFalse(any(u.has_usable_password() for u in student_users))

    def test_verify_constraints_passes_on_the_seed(self):
        call_command("verify_constraints", stdout=StringIO())  # raises on failure


# --- Part 1.1: chart-ready internal API ------------------------------------------


class SummaryApiTests(SeededTestCase):

    def test_summary_is_a_bare_list_of_category_count_rows(self):
        response = self.client.get(reverse("connect:api-summary"))
        self.assertEqual(response["Content-Type"], "application/json")
        rows = response.json()
        self.assertIsInstance(rows, list)
        self.assertEqual(set(rows[0]), {"category", "count", "type"})
        # Most picked first, ties by name; nobody picked an activity.
        self.assertEqual([(r["category"], r["count"]) for r in rows[:3]],
                         [("Food", 4), ("Movies", 4), ("Fitness", 3)])
        self.assertEqual(sum(r["count"] for r in rows), ProfileInterest.objects.count())
        self.assertNotIn("Meeting activity", {r["type"] for r in rows})

    def test_matches_per_week_is_contiguous_weekly_records(self):
        records = self.client.get(reverse("connect:api-summary-matches-per-week")).json()["records"]
        dates = [date.fromisoformat(r["date"]) for r in records]
        self.assertEqual(dates[0], date(2026, 7, 13))
        self.assertEqual(dates[-1], date(2026, 9, 7))
        self.assertTrue(all(b - a == timedelta(weeks=1) for a, b in pairwise(dates)))
        self.assertEqual([r["count"] for r in records], [1, 1, 2, 2, 2, 3, 3, 3, 2])
        self.assertEqual(sum(r["count"] for r in records), Match.objects.count())
        self.assertEqual(sum(r["participants"] for r in records), MatchParticipant.objects.count())

    def test_a_week_without_matches_shows_as_zero(self):
        Match.objects.filter(week_start=date(2026, 8, 10)).delete()
        records = self.client.get(reverse("connect:api-summary-matches-per-week")).json()["records"]
        self.assertIn({"date": "2026-08-10", "count": 0, "participants": 0}, records)

    def test_public_json_endpoints_allow_any_origin(self):
        for name in ["api-summary", "api-summary-matches-per-week", "api-locations",
                     "api-matches", "api-locations-text"]:
            response = self.client.get(reverse("connect:" + name))
            self.assertEqual(response["Access-Control-Allow-Origin"], "*", name)

    def test_summary_endpoints_are_get_only(self):
        for name in ["api-summary", "api-summary-matches-per-week"]:
            self.assertEqual(self.client.post(reverse("connect:" + name)).status_code, 405)


# --- Part 1.2: Vega-Lite charts ---------------------------------------------------


class VegaLiteTests(SeededTestCase):

    def test_specs_load_their_data_from_the_summary_api(self):
        # The assignment: data.url pointing at our API, never inline values.
        for name, api in [("chart1", "api-summary"), ("chart2", "api-summary-matches-per-week")]:
            spec = load_spec(name)
            self.assertEqual(spec["$schema"], "https://vega.github.io/schema/vega-lite/v6.json")
            self.assertEqual(spec["data"]["url"], reverse("connect:" + api), name)
            self.assertNotIn("values", spec["data"], name)
        self.assertEqual(load_spec("chart1")["layer"][0]["mark"]["type"], "bar")
        self.assertEqual(load_spec("chart2")["mark"]["type"], "line")

    def test_served_spec_has_an_absolute_data_url(self):
        # Absolute, so the spec also loads its data inside the Vega-Lite editor.
        response = self.client.get(reverse("connect:vega-spec", args=["chart2"]))
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response.json()["data"]["url"],
                         "http://testserver" + reverse("connect:api-summary-matches-per-week"))

    def test_image_endpoints_return_png_and_jpeg(self):
        for path, content_type, magic in [("/vega-lite/chart1.png", "image/png", b"\x89PNG"),
                                          ("/vega-lite/chart2.jpg", "image/jpeg", b"\xff\xd8\xff")]:
            response = self.client.get(path)
            self.assertEqual(response["Content-Type"], content_type, path)
            self.assertTrue(response.content.startswith(magic), path)

    def test_images_still_render_with_no_data(self):
        Match.objects.all().delete()
        ProfileInterest.objects.all().delete()
        for path in ["/vega-lite/chart1.png", "/vega-lite/chart2.jpg"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_unknown_chart_or_format_is_404(self):
        for path in ["/vega-lite/chart9.png", "/vega-lite/chart1.gif", "/vega-lite/chart9.vl.json"]:
            self.assertEqual(self.client.get(path).status_code, 404, path)
