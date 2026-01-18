"""
Tests for LMS logic (Availability, Progress Rollup).
"""

import pytest
from django.utils import timezone

from learning.models import ContentProgress, EventModule, ModuleContent, ModuleProgress


@pytest.mark.django_db
class TestModuleAvailability:
    def test_availability_immediate(self, event, user, registration):
        """Test immediate release modules."""
        module = EventModule.objects.create(
            event=event,
            title="Immediate Module",
            release_type=EventModule.ReleaseType.IMMEDIATE,
            is_published=True
        )
        assert module.is_available_for(user, registration=registration) is True

    def test_availability_unpublished(self, event, user, registration):
        """Test unpublished modules are hidden."""
        module = EventModule.objects.create(
            event=event,
            title="Hidden Module",
            release_type=EventModule.ReleaseType.IMMEDIATE,
            is_published=False
        )
        assert module.is_available_for(user, registration=registration) is False

    def test_availability_scheduled_future(self, event, user, registration):
        """Test scheduled release is enforced."""
        future_date = timezone.now() + timezone.timedelta(days=7)
        module = EventModule.objects.create(
            event=event,
            title="Future Module",
            release_type=EventModule.ReleaseType.SCHEDULED,
            release_at=future_date,
            is_published=True
        )
        assert module.is_available_for(user, registration=registration) is False

        # Past date
        module.release_at = timezone.now() - timezone.timedelta(days=1)
        module.save()
        assert module.is_available_for(user, registration=registration) is True

    def test_availability_prerequisite_chains(self, event, user, registration):
        """Test prerequisite chains."""
        # Module 1 (Prereq)
        module1 = EventModule.objects.create(
            event=event,
            title="Module 1",
            release_type=EventModule.ReleaseType.IMMEDIATE,
            is_published=True,
            order=1
        )
        # Module 2 (Dependent)
        module2 = EventModule.objects.create(
            event=event,
            title="Module 2",
            release_type=EventModule.ReleaseType.PREREQUISITE,
            prerequisite_module=module1,
            is_published=True,
            order=2
        )

        # Initially locked
        assert module2.is_available_for(user, registration=registration) is False

        # Complete Module 1
        prog1 = ModuleProgress.objects.create(
            registration=registration,
            module=module1,
            status=ModuleProgress.Status.COMPLETED
        )

        # Now available
        assert module2.is_available_for(user, registration=registration) is True


@pytest.mark.django_db
class TestProgressRollup:
    def test_progress_rollup_registration(self, event, user, registration):
        """Test content progress rolling up to module status for Registrations."""
        module = EventModule.objects.create(event=event, title="Module 1")

        # 2 Contents
        c1 = ModuleContent.objects.create(module=module, title="C1", content_type='text', is_required=True, order=1)
        c2 = ModuleContent.objects.create(module=module, title="C2", content_type='text', is_required=True, order=2)
        # Optional content shouldn't count towards total
        c3 = ModuleContent.objects.create(module=module, title="Opt", content_type='text', is_required=False, order=3)

        # Create Module Progress tracker
        mod_prog = ModuleProgress.objects.create(
            registration=registration,
            module=module
        )

        # Initial State
        mod_prog.update_from_content()  # Recalculate based on total
        assert mod_prog.contents_total == 2
        assert mod_prog.contents_completed == 0
        assert mod_prog.progress_percent == 0
        assert mod_prog.status == ModuleProgress.Status.NOT_STARTED

        # Complete C1
        cp1 = ContentProgress.objects.create(
            registration=registration,
            content=c1,
            status=ContentProgress.Status.COMPLETED
        )
        mod_prog.refresh_from_db()
        mod_prog.update_from_content()

        assert mod_prog.contents_completed == 1
        assert mod_prog.progress_percent == 50
        assert mod_prog.status == ModuleProgress.Status.IN_PROGRESS
        assert mod_prog.started_at is not None

        # Complete C2
        cp2 = ContentProgress.objects.create(
            registration=registration,
            content=c2,
            status=ContentProgress.Status.COMPLETED
        )
        mod_prog.refresh_from_db()
        mod_prog.update_from_content()

        assert mod_prog.contents_completed == 2
        assert mod_prog.progress_percent == 100
        assert mod_prog.status == ModuleProgress.Status.COMPLETED
        assert mod_prog.completed_at is not None
