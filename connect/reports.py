"""
Reports and exports (P1-A4 Part 3).

    GET /reports/               grouped summaries, totals and the download buttons
    GET /export/students.csv    every student profile as CSV
    GET /export/students.json   the same rows as JSON, with metadata

Both downloads hold the same rows, ordered by name, and are named with the
time they were made in local time (students_YYYY-MM-DD_HH-MM.csv / .json),
so a second download never overwrites the first.

They carry what the student pages already show. The Illinois email is
left out: it is the one contact detail, and a public file is no place
for it.
"""

import csv

from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .charts import students_by_college_data
from .models import CampusLocation, Match, MatchParticipant, MatchStatus, StudentProfile

UPCOMING = [MatchStatus.PROPOSED, MatchStatus.CONFIRMED]

# Spreadsheet apps run a cell that starts with one of these as a formula.
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")

# The columns of both exports, in order.
FIELDS = ["net_id", "full_name", "college", "department", "preferred_connection",
          "social_energy", "conversation_style", "group_preference", "interests",
          "matches", "sso_verified", "onboarded_on"]


def student_records():
    """Every student profile as a dict with the FIELDS keys, ordered by name
    then NetID."""
    students = (StudentProfile.objects
                .annotate(matches=Count("match_participations"))
                .prefetch_related("interests")
                .order_by("full_name", "net_id"))
    return [{
        "net_id": s.net_id,
        "full_name": s.full_name,
        "college": s.college,
        "department": s.department,
        "preferred_connection": s.get_preferred_connection_display(),
        "social_energy": s.get_social_energy_display(),
        "conversation_style": s.get_conversation_style_display(),
        "group_preference": s.get_group_preference_display(),
        "interests": [i.name for i in s.interests.all()],
        "matches": s.matches,
        "sso_verified": s.is_sso_verified,
        "onboarded_on": (timezone.localdate(s.onboarding_completed_at)
                         if s.onboarding_completed_at else None),
    } for s in students]


def _attachment(response, extension, now):
    stamp = now.strftime("%Y-%m-%d_%H-%M")
    response["Content-Disposition"] = f'attachment; filename="students_{stamp}.{extension}"'
    return response


def _cell(value):
    """One CSV cell: a list joined with "; ", and text a spreadsheet would
    run as a formula made literal with a leading apostrophe."""
    if isinstance(value, list):
        value = "; ".join(value)
    if isinstance(value, str) and value.startswith(FORMULA_START):
        return "'" + value
    return value


@require_GET
def students_csv(request):
    """GET /export/students.csv - a header row, then one row per student."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    writer = csv.DictWriter(response, fieldnames=FIELDS)  # raises on a field not listed
    writer.writeheader()
    for row in student_records():
        writer.writerow({field: _cell(value) for field, value in row.items()})
    return _attachment(response, "csv", timezone.localtime())


@require_GET
def students_json(request):
    """GET /export/students.json - {"generated_at", "record_count", "students"}."""
    now = timezone.localtime()
    rows = student_records()
    response = JsonResponse({
        "generated_at": now.isoformat(timespec="seconds"),
        "record_count": len(rows),
        "students": rows,
    }, json_dumps_params={"indent": 2})
    return _attachment(response, "json", now)


@require_GET
def reports(request):
    """GET /reports/ - students per college and matches per venue, with totals."""
    colleges = [(college, friend, squad, friend + squad)
                for college, friend, squad in students_by_college_data()]
    # Approved venues, and any other venue that has hosted a match, so the
    # venue rows always add up to the match total.
    venues = (CampusLocation.objects
              .annotate(total=Count("matches"),
                        completed=Count("matches", filter=Q(matches__status=MatchStatus.COMPLETED)),
                        upcoming=Count("matches", filter=Q(matches__status__in=UPCOMING)))
              .filter(Q(is_approved=True) | Q(total__gt=0))
              .order_by("-total", "name"))
    matches = Match.objects.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=MatchStatus.COMPLETED)),
        upcoming=Count("id", filter=Q(status__in=UPCOMING)),
        cancelled=Count("id", filter=Q(status=MatchStatus.CANCELLED)),
    )
    return render(request, "connect/reports.html", {
        "colleges": colleges,
        "venues": venues,
        "totals": {
            "students": sum(row[3] for row in colleges),
            "friend": sum(row[1] for row in colleges),
            "squad": sum(row[2] for row in colleges),
            "matches": matches,
            "participants": MatchParticipant.objects.count(),
        },
    })
