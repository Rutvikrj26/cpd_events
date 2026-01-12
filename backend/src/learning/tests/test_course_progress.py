import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from events.models import Event
from learning.models import ContentProgress, Course, CourseEnrollment, CourseModule, EventModule, ModuleContent, ModuleProgress
from organizations.models import Organization
from registrations.models import Registration


# Helper to create users since factories might not be fully available contextually
def make_user(email='test@example.com'):
    return User.objects.create(email=email, password='password')


@pytest.mark.django_db
class TestCourseProgressArchitecture:
    def test_course_enrollment_progress(self):
        """Verify progress can be linked to a CourseEnrollment."""
        # Setup
        user = make_user()
        org = Organization.objects.create(name="Test Org", slug="test-org")
        course = Course.objects.create(title="Test Course", slug="test-course", organization=org)
        enrollment = CourseEnrollment.objects.create(course=course, user=user)

        # Internal structure
        event_module = EventModule.objects.create(title="Test Module")
        # Link module to course (via CourseModule if it exists?)
        # Wait, CourseModule definition:
        course_module = CourseModule.objects.create(course=course, module=event_module)

        content = ModuleContent.objects.create(module=event_module, title="Test Content", content_type='text')

        # Create Progress
        progress = ContentProgress.objects.create(
            course_enrollment=enrollment, content=content, status=ContentProgress.Status.IN_PROGRESS
        )

        assert progress.course_enrollment == enrollment
        assert progress.registration is None
        assert progress.pk is not None

        # Verify Module Progress creation
        mod_progress = ModuleProgress.objects.create(course_enrollment=enrollment, module=event_module)
        assert mod_progress.course_enrollment == enrollment

    def test_event_registration_progress(self):
        """Verify progress can still be linked to a Registration (Backwards Compatibility)."""
        user = make_user('eventuser@example.com')
        # Event requires owner? Check model. Assuming defaults or optional.
        # Event usually requires owner.
        org_user = make_user('owner@example.com')
        event = Event.objects.create(
            title="Test Event", starts_at=timezone.now(), duration_minutes=60, owner=org_user, slug="test-event"
        )
        registration = Registration.objects.create(event=event, user=user)

        module = EventModule.objects.create(event=event, title="Event Module")
        content = ModuleContent.objects.create(module=module, title="Event Content", content_type='text')

        progress = ContentProgress.objects.create(registration=registration, content=content)

        assert progress.registration == registration
        assert progress.course_enrollment is None

    def test_validation_mutual_exclusivity(self):
        """Ensure one cannot have BOTH registration and course_enrollment."""
        user = make_user('conflict@example.com')
        org = Organization.objects.create(name="Conflict Org", slug="conflict-org")

        # Course context
        course = Course.objects.create(title="Conflict Course", slug="conflict-course", organization=org)
        enrollment = CourseEnrollment.objects.create(course=course, user=user)

        # Event context
        org_user = make_user('conflict_owner@example.com')
        event = Event.objects.create(
            title="Conflict Event", starts_at=timezone.now(), duration_minutes=60, owner=org_user, slug="conflict-event"
        )
        registration = Registration.objects.create(event=event, user=user)

        module = EventModule.objects.create(title="Shared Module")
        content = ModuleContent.objects.create(module=module, title="Shared Content", content_type='text')

        # Try creating with both
        progress = ContentProgress(registration=registration, course_enrollment=enrollment, content=content)

        with pytest.raises(ValidationError):
            progress.clean()

    def test_validation_at_least_one(self):
        """Ensure one MUST have either registration or course_enrollment."""
        module = EventModule.objects.create(title="Orphan Module")
        content = ModuleContent.objects.create(module=module, title="Orphan Content", content_type='text')

        progress = ContentProgress(content=content)

        with pytest.raises(ValidationError):
            progress.clean()
