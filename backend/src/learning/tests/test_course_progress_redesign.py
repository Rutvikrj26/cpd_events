import pytest
from django.utils import timezone

from factories import CourseEnrollmentFactory, CourseFactory, UserFactory
from learning.models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseSession,
    CourseSessionAttendance,
    EventModule,
    ModuleContent,
    ModuleProgress,
)


def make_module(course, title, order):
    module = EventModule.objects.create(
        title=title,
        order=order,
        is_published=True,
    )
    CourseModule.objects.create(course=course, module=module, order=order, is_required=True)
    return module


def make_content(module, title, order=0, required=True):
    return ModuleContent.objects.create(
        module=module,
        title=title,
        content_type=ModuleContent.ContentType.TEXT,
        order=order,
        is_required=required,
        is_published=True,
    )


@pytest.mark.django_db
class TestCourseProgressRedesign:
    def test_progress_is_weighted_by_required_work_not_module_count(self):
        course = CourseFactory(format=Course.CourseFormat.ONLINE)
        enrollment = CourseEnrollmentFactory(course=course)

        short_module = make_module(course, "Short", 1)
        long_module = make_module(course, "Long", 2)
        short_content = make_content(short_module, "Only item")
        for idx in range(3):
            make_content(long_module, f"Long item {idx}", idx)

        ContentProgress.objects.create(
            course_enrollment=enrollment,
            content=short_content,
            status=ContentProgress.Status.COMPLETED,
            progress_percent=100,
        )
        # ModuleProgress is auto-created and rolled up by the
        # ContentProgress post_save signal (learning/signals.py).

        enrollment.update_progress()
        enrollment.refresh_from_db()

        assert enrollment.progress_percent == 25
        assert enrollment.modules_completed == 1
        assert enrollment.status == CourseEnrollment.Status.ACTIVE

    def test_assignments_contribute_to_progress_and_gate_completion(self):
        course = CourseFactory(format=Course.CourseFormat.ONLINE)
        enrollment = CourseEnrollmentFactory(course=course)
        module = make_module(course, "Module", 1)
        content = make_content(module, "Lesson")
        assignment = Assignment.objects.create(
            module=module,
            title="Assignment",
            instructions="Submit work.",
            max_score=100,
            passing_score=70,
        )

        ContentProgress.objects.create(
            course_enrollment=enrollment,
            content=content,
            status=ContentProgress.Status.COMPLETED,
            progress_percent=100,
        )
        # ModuleProgress auto-created via cascade signal.

        enrollment.update_progress()
        enrollment.refresh_from_db()

        assert enrollment.progress_percent == 50
        assert enrollment.status == enrollment.Status.ACTIVE

        AssignmentSubmission.objects.create(
            assignment=assignment,
            course_enrollment=enrollment,
            status=AssignmentSubmission.Status.GRADED,
            score=80,
            content={"text": "Done"},
        )

        enrollment.update_progress()
        enrollment.refresh_from_db()

        assert enrollment.progress_percent == 100
        assert enrollment.status == enrollment.Status.COMPLETED

    def test_quiz_completion_preserves_score_and_answers_position(self):
        course = CourseFactory(format=Course.CourseFormat.ONLINE)
        enrollment = CourseEnrollmentFactory(course=course)
        module = make_module(course, "Quiz module", 1)
        quiz = ModuleContent.objects.create(
            module=module,
            title="Quiz",
            content_type=ModuleContent.ContentType.QUIZ,
            order=1,
            is_required=True,
            is_published=True,
        )
        progress = ContentProgress.objects.create(course_enrollment=enrollment, content=quiz)

        progress.update_progress(
            100,
            position={"quiz_answers": {"q1": ["a"]}, "score": 100, "passed": True},
        )
        progress.refresh_from_db()

        assert progress.status == ContentProgress.Status.COMPLETED
        assert progress.last_position["score"] == 100
        assert progress.last_position["passed"] is True

    def test_live_course_progress_uses_required_session_attendance(self):
        user = UserFactory()
        course = CourseFactory(
            format=Course.CourseFormat.LIVE,
            hybrid_completion_criteria=Course.HybridCompletionCriteria.SESSIONS_ONLY,
        )
        enrollment = CourseEnrollmentFactory(course=course, user=user)
        session = CourseSession.objects.create(
            course=course,
            title="Live session",
            starts_at=timezone.now(),
            duration_minutes=60,
            is_mandatory=True,
            is_published=True,
        )

        enrollment.update_progress()
        enrollment.refresh_from_db()
        assert enrollment.progress_percent == 0
        assert enrollment.status == enrollment.Status.ACTIVE

        CourseSessionAttendance.objects.create(
            session=session,
            enrollment=enrollment,
            attendance_minutes=60,
            is_eligible=True,
        )
        enrollment.update_progress()
        enrollment.refresh_from_db()

        assert enrollment.progress_percent == 100
        assert enrollment.status == enrollment.Status.COMPLETED
