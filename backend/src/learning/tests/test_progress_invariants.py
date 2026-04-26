"""Invariants and lock-on-completion tests for CourseEnrollment progress.

Background: prior to the progress refactor, ``CourseEnrollment.update_progress()``
unconditionally recomputed ``progress_percent`` from leaf data. That broke
two real-world cases:

1. **Archived courses with no surviving leaf data** — e.g. Pharmacology
   Refresher (Emily completed 180 days ago, course later archived). Recompute
   produced 0% even though ``status=COMPLETED`` and a certificate had been
   issued.
2. **Manual instructor completion overrides** — recompute could revert
   ``mark_complete_manually()``.

The fix is one no-op short-circuit + one save-time invariant. These tests
pin both.
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from factories import CourseEnrollmentFactory, CourseFactory, UserFactory
from learning.models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    CourseEnrollment,
    CourseModule,
    EventModule,
    ModuleContent,
)


def _make_module(course, title="M1", order=0):
    module = EventModule.objects.create(title=title, order=order, is_published=True)
    CourseModule.objects.create(course=course, module=module, order=order, is_required=True)
    return module


def _make_content(module, *, title="C", required=True, order=None):
    if order is None:
        order = module.contents.count()
    return ModuleContent.objects.create(
        module=module,
        title=title,
        content_type=ModuleContent.ContentType.TEXT,
        order=order,
        is_required=required,
        is_published=True,
    )


@pytest.mark.django_db
def test_update_progress_is_noop_for_completed():
    """Once status=COMPLETED, recompute must NOT touch progress_percent.

    Reproduces the Pharmacology Refresher bug: a learner finishes the course,
    cert is issued, then the course is archived. Years later we have no
    ContentProgress rows but the historical fact of completion stands.
    """
    course = CourseFactory(status="published")
    module = _make_module(course)
    _make_content(module)
    enrollment = CourseEnrollmentFactory(course=course)

    enrollment.status = CourseEnrollment.Status.COMPLETED
    enrollment.progress_percent = 100
    enrollment.completed_at = timezone.now()
    enrollment.save()

    # Wipe every leaf row — simulates an archived course.
    ContentProgress.objects.filter(course_enrollment=enrollment).delete()

    enrollment.update_progress()
    enrollment.refresh_from_db()

    assert enrollment.progress_percent == 100
    assert enrollment.status == CourseEnrollment.Status.COMPLETED


@pytest.mark.django_db
def test_save_clamps_completed_to_100():
    """Saving with status=COMPLETED but progress<100 must auto-clamp.

    Catches every code path that flips status without normalising the rest
    of the row (seed updates, admin actions, future bugs).
    """
    course = CourseFactory(status="published")
    enrollment = CourseEnrollmentFactory(course=course)

    enrollment.status = CourseEnrollment.Status.COMPLETED
    enrollment.progress_percent = 57  # deliberately wrong
    enrollment.completed_at = None  # deliberately missing
    enrollment.save()

    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 100
    assert enrollment.completed_at is not None


@pytest.mark.django_db
def test_contentprogress_save_clamps_completed_to_100():
    """Mirror invariant on ContentProgress: setting status=COMPLETED with a
    non-100 percent or missing completed_at must auto-normalise on save.
    Lets the player safely drop the defensive dual progress_percent check.
    """
    course = CourseFactory(status="published")
    module = _make_module(course)
    content = _make_content(module)
    enrollment = CourseEnrollmentFactory(course=course)

    cp = ContentProgress.objects.create(
        course_enrollment=enrollment,
        content=content,
        status=ContentProgress.Status.IN_PROGRESS,
        progress_percent=42,
    )
    cp.status = ContentProgress.Status.COMPLETED
    cp.progress_percent = 42  # deliberately wrong
    cp.completed_at = None  # deliberately missing
    cp.save()

    cp.refresh_from_db()
    assert cp.progress_percent == 100
    assert cp.completed_at is not None


@pytest.mark.django_db
def test_grading_recomputes_progress_for_active_enrollment():
    """Grading a passing submission updates progress_percent even when the
    completion threshold isn't met (e.g. one of two assignments graded).

    Pre-refactor, ``check_completion()`` short-circuited on success and
    progress_percent was never touched, so the bar lagged reality.
    """
    course = CourseFactory(status="published")
    module = _make_module(course)
    content = _make_content(module)

    assignment_1 = Assignment.objects.create(
        module=module, title="A1", max_score=100, passing_score=70, submission_type="text",
    )
    assignment_2 = Assignment.objects.create(
        module=module, title="A2", max_score=100, passing_score=70, submission_type="text",
    )

    enrollment = CourseEnrollmentFactory(course=course)
    # Mark the single content complete so the only outstanding work is
    # the two assignments.
    ContentProgress.objects.create(
        course_enrollment=enrollment,
        content=content,
        status=ContentProgress.Status.COMPLETED,
        progress_percent=100,
    )
    enrollment.update_progress()
    enrollment.refresh_from_db()
    initial_pct = enrollment.progress_percent
    assert enrollment.status == CourseEnrollment.Status.ACTIVE

    # Grade ONE assignment passing — completion criteria still unmet
    # because A2 is outstanding.
    submission = AssignmentSubmission.objects.create(
        assignment=assignment_1, course_enrollment=enrollment,
        status=AssignmentSubmission.Status.GRADED, score=85,
    )
    enrollment.update_progress()
    enrollment.refresh_from_db()

    assert enrollment.status == CourseEnrollment.Status.ACTIVE
    assert enrollment.progress_percent > initial_pct, (
        "Progress should advance when an assignment is graded passing, "
        "even if the course-completion threshold isn't reached."
    )


@pytest.mark.django_db
def test_completed_enrollment_with_no_leaf_data_reports_100():
    """The Pharmacology Refresher case verbatim. End-state: status=COMPLETED
    + zero ContentProgress / ModuleProgress rows + cert issued. Re-running
    update_progress() should preserve the 100% reading.
    """
    course = CourseFactory(status="archived")  # archived after completion
    enrollment = CourseEnrollmentFactory(course=course)
    enrollment.status = CourseEnrollment.Status.COMPLETED
    enrollment.progress_percent = 100
    enrollment.completed_at = timezone.now()
    enrollment.save()

    # No leaf rows exist.
    assert not ContentProgress.objects.filter(course_enrollment=enrollment).exists()

    # Repeated recompute (simulating multiple page loads / API calls).
    for _ in range(3):
        enrollment.update_progress()
        enrollment.refresh_from_db()

    assert enrollment.progress_percent == 100


@pytest.mark.django_db
def test_adding_required_content_recomputes_active_enrollees():
    """When required content is added to a published course, ACTIVE
    enrollees' stored progress should be recomputed by signal — without
    waiting for the learner to visit the player.

    COMPLETED enrollments are intentionally not in scope here (auto-complete
    + COMPLETED-lock means a completed learner stays at 100%; new structure
    doesn't retroactively un-graduate them).
    """
    course = CourseFactory(status="published")
    module1 = _make_module(course, title="M1", order=0)
    c1 = _make_content(module1, title="C1")
    module2 = _make_module(course, title="M2", order=1)
    _make_content(module2, title="C2")
    enrollment = CourseEnrollmentFactory(course=course)

    # Learner completes M1's content. 1 of 2 required units done → 50%.
    ContentProgress.objects.create(
        course_enrollment=enrollment,
        content=c1,
        status=ContentProgress.Status.COMPLETED,
        progress_percent=100,
    )
    enrollment.update_progress()
    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 50
    assert enrollment.status == CourseEnrollment.Status.ACTIVE

    # Organizer adds a third required content to M1 (2 of 3 known units
    # already exist; this brings the denominator to 3). Signal must
    # recompute enrollee → 1 of 3 = 33%.
    _make_content(module1, title="C1b")

    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 33, (
        f"Expected 33% after content add, got {enrollment.progress_percent}%. "
        "ModuleContent post_save signal should have triggered "
        "_recompute_enrollees_for_course."
    )


@pytest.mark.django_db
def test_cancelled_session_drops_from_completion_denominator():
    """Per D2: when a session is CANCELLED, every active enrollee's
    progress recomputes — the cancelled session leaves the denominator,
    attendance rows survive, and progress moves up if the learner had
    already attended the remaining mandatory sessions.
    """
    from learning.models import Course, CourseSession, CourseSessionAttendance
    course = CourseFactory(
        status="published",
        format=Course.CourseFormat.LIVE,
        hybrid_completion_criteria=Course.HybridCompletionCriteria.SESSIONS_ONLY,
    )
    enrollment = CourseEnrollmentFactory(course=course)

    # Two mandatory sessions; learner attended only the first.
    s1 = CourseSession.objects.create(
        course=course, title="S1", order=0,
        starts_at=timezone.now() - timezone.timedelta(days=2),
        duration_minutes=60, is_mandatory=True,
        status=CourseSession.Status.COMPLETED, is_published=True,
    )
    s2 = CourseSession.objects.create(
        course=course, title="S2", order=1,
        starts_at=timezone.now() - timezone.timedelta(days=1),
        duration_minutes=60, is_mandatory=True,
        status=CourseSession.Status.SCHEDULED, is_published=True,
    )
    CourseSessionAttendance.objects.create(
        session=s1, enrollment=enrollment,
        attendance_minutes=60, is_eligible=True,
    )
    enrollment.update_progress()
    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 50  # 1 of 2

    # Cancel S2 → denominator drops to 1; learner is now 100% / COMPLETED
    # because the only remaining mandatory session was already attended.
    s2.status = CourseSession.Status.CANCELLED
    s2.save()  # signal fires; recompute happens automatically.

    enrollment.refresh_from_db()
    assert enrollment.progress_percent == 100, (
        f"Expected 100% after cancellation, got {enrollment.progress_percent}%. "
        "_session_cancellation_cascade signal should drop S2 from the denominator."
    )


@pytest.mark.django_db
def test_mark_complete_manually_survives_subsequent_update_progress():
    """Manual instructor completion must not be reverted by recompute."""
    course = CourseFactory(status="published")
    module = _make_module(course)
    _make_content(module)
    instructor = UserFactory()
    enrollment = CourseEnrollmentFactory(course=course)

    # Instructor manually marks complete (no leaf progress required).
    enrollment.mark_complete_manually(completed_by=instructor)
    enrollment.refresh_from_db()
    assert enrollment.status == CourseEnrollment.Status.COMPLETED
    assert enrollment.progress_percent == 100

    enrollment.update_progress()
    enrollment.refresh_from_db()

    assert enrollment.status == CourseEnrollment.Status.COMPLETED
    assert enrollment.progress_percent == 100
