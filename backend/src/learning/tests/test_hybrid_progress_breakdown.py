"""Wire-shape tests for the hybrid course progress breakdown.

Covers:
- Hybrid course progress endpoint surfaces both module_progress and
  session_progress on the enrollment payload.
- Online course endpoint omits session_progress (key absent, not zero).
- next_session_at on the enrollment serializer is the earliest upcoming
  not-attended-eligibly session, excludes cancelled.
- Attendance-eligibility flip auto-recomputes enrollment progress (no
  manual update_progress() call needed).
- Cancelled sessions don't appear in the sessions array.
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from factories import CourseEnrollmentFactory, CourseFactory
from learning.models import (
    Course,
    CourseEnrollment,
    CourseModule,
    CourseSession,
    CourseSessionAttendance,
    EventModule,
    ModuleContent,
)


def _make_session(course, *, title="S", order=0, mandatory=True, days_offset=1, status=None, published=True):
    return CourseSession.objects.create(
        course=course, title=title, order=order,
        starts_at=timezone.now() + timezone.timedelta(days=days_offset),
        duration_minutes=60, is_mandatory=mandatory,
        status=status or CourseSession.Status.SCHEDULED,
        is_published=published,
    )


def _make_module_with_content(course, title="M", order=0):
    module = EventModule.objects.create(title=title, order=order, is_published=True)
    CourseModule.objects.create(course=course, module=module, order=order, is_required=True)
    ModuleContent.objects.create(
        module=module, title=f"{title}-content",
        content_type=ModuleContent.ContentType.TEXT,
        order=0, is_required=True, is_published=True,
    )
    return module


@pytest.mark.django_db
def test_hybrid_progress_endpoint_returns_breakdown(client, django_user_model):
    course = CourseFactory(
        status="published",
        format=Course.CourseFormat.HYBRID,
        hybrid_completion_criteria=Course.HybridCompletionCriteria.BOTH,
    )
    _make_module_with_content(course, title="M1", order=0)
    _make_session(course, title="S1", order=0, days_offset=-2, status=CourseSession.Status.COMPLETED)
    _make_session(course, title="S2", order=1, days_offset=7)

    enrollment = CourseEnrollmentFactory(course=course)
    client.force_login(enrollment.user)
    resp = client.get(f"/api/v1/courses/{course.uuid}/progress/")
    assert resp.status_code == 200, resp.content

    body = resp.json()
    assert "module_progress" in body["enrollment"]
    assert "session_progress" in body["enrollment"]
    sp = body["enrollment"]["session_progress"]
    assert sp["sessions_total"] == 2
    assert sp["sessions_attended"] == 0
    assert sp["criteria"] == "both"

    assert "sessions" in body
    assert len(body["sessions"]) == 2
    assert {s["title"] for s in body["sessions"]} == {"S1", "S2"}


@pytest.mark.django_db
def test_online_progress_endpoint_omits_session_progress(client):
    course = CourseFactory(status="published", format=Course.CourseFormat.ONLINE)
    _make_module_with_content(course, title="M1", order=0)
    enrollment = CourseEnrollmentFactory(course=course)

    client.force_login(enrollment.user)
    resp = client.get(f"/api/v1/courses/{course.uuid}/progress/")
    assert resp.status_code == 200

    body = resp.json()
    assert "module_progress" in body["enrollment"]
    assert "session_progress" not in body["enrollment"], (
        "Pure-online courses must omit session_progress (absent, not zero)."
    )
    assert "sessions" not in body


@pytest.mark.django_db
def test_cancelled_sessions_excluded_from_breakdown(client):
    course = CourseFactory(
        status="published",
        format=Course.CourseFormat.HYBRID,
        hybrid_completion_criteria=Course.HybridCompletionCriteria.SESSIONS_ONLY,
    )
    _make_session(course, title="S1", order=0, days_offset=-2, status=CourseSession.Status.COMPLETED)
    _make_session(course, title="S2-cancelled", order=1, days_offset=7,
                  status=CourseSession.Status.CANCELLED)

    enrollment = CourseEnrollmentFactory(course=course)
    client.force_login(enrollment.user)
    resp = client.get(f"/api/v1/courses/{course.uuid}/progress/")
    body = resp.json()

    titles = {s["title"] for s in body["sessions"]}
    assert "S1" in titles
    assert "S2-cancelled" not in titles, (
        "Cancelled sessions must not appear in the sessions wire array."
    )


@pytest.mark.django_db
def test_next_session_at_returns_earliest_upcoming_unattended():
    course = CourseFactory(status="published", format=Course.CourseFormat.HYBRID)
    enrollment = CourseEnrollmentFactory(course=course)
    s1 = _make_session(course, title="S1", order=0, days_offset=-1, status=CourseSession.Status.COMPLETED)
    s2 = _make_session(course, title="S2", order=1, days_offset=3)
    s3 = _make_session(course, title="S3", order=2, days_offset=10)

    # Mark S1 attended-eligibly. S2 should be the next surfaced upcoming.
    CourseSessionAttendance.objects.create(
        session=s1, enrollment=enrollment,
        attendance_minutes=60, is_eligible=True,
    )

    from learning.serializers import CourseEnrollmentSerializer
    enrollment.refresh_from_db()
    payload = CourseEnrollmentSerializer(enrollment).data
    assert payload["next_session_at"] is not None
    # Earliest upcoming + not-yet-attended-eligibly = S2.
    assert payload["next_session_at"].startswith(s2.starts_at.date().isoformat())


@pytest.mark.django_db
def test_attendance_eligibility_flip_recomputes_progress():
    course = CourseFactory(
        status="published",
        format=Course.CourseFormat.LIVE,
        hybrid_completion_criteria=Course.HybridCompletionCriteria.SESSIONS_ONLY,
    )
    enrollment = CourseEnrollmentFactory(course=course)
    s1 = _make_session(course, title="S1", order=0, days_offset=-2, status=CourseSession.Status.COMPLETED)
    s2 = _make_session(course, title="S2", order=1, days_offset=-1, status=CourseSession.Status.COMPLETED)

    # Initial attendance: not eligible. Progress stays 0%.
    CourseSessionAttendance.objects.create(
        session=s1, enrollment=enrollment,
        attendance_minutes=10, is_eligible=False,
    )
    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 0

    # Flip to eligible — signal should fire update_progress automatically.
    rec = CourseSessionAttendance.objects.get(session=s1, enrollment=enrollment)
    rec.is_eligible = True
    rec.attendance_minutes = 55
    rec.save()

    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 50, (
        f"Expected 50% (1 of 2 mandatory) after eligibility flip, got "
        f"{enrollment.progress_percent}%. Cascade signal should auto-recompute."
    )

    # Attend S2 too — progress hits 100, status auto-completes.
    CourseSessionAttendance.objects.create(
        session=s2, enrollment=enrollment,
        attendance_minutes=60, is_eligible=True,
    )
    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 100
    assert enrollment.status == CourseEnrollment.Status.COMPLETED
