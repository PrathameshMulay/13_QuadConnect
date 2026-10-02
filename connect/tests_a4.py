"""
Tests for the P1-A4 features, one class per assignment part.

    python manage.py test connect

These run on the real seed data (seed_demo_data), because the charts,
reports and exports are about the dataset the deployed site serves.
"""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase

from .management.commands.seed_demo_data import HISTORY, STAFF_PASSWORD
from .models import (
    ExperienceFeedback,
    Match,
    MatchParticipant,
    MatchStatus,
    StudentProfile,
)


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
