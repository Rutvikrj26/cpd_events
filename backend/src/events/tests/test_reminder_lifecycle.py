"""Reminder lifecycle: enqueue, cancel, reschedule, idempotency."""

from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import DEFAULT_REMINDER_OFFSETS_MINUTES, Event
from events.services import (
    build_event_join_url,
    cancel_event_reminders,
    enqueue_event_reminders,
    reschedule_event_reminders,
)
from integrations.models import ScheduledEmail


@pytest.fixture
def published_event(db):
    from factories import EventFactory

    return EventFactory(
        published=True,
        starts_at=timezone.now() + timedelta(days=2),
        reminder_offsets_minutes=[1440, 60, 0],  # T-24h, T-1h, T-now
    )


@pytest.fixture
def confirmed_registration(db, published_event):
    from factories import RegistrationFactory

    return RegistrationFactory(event=published_event, status='confirmed')


@pytest.mark.django_db
class TestEnqueueEventReminders:
    def test_creates_one_row_per_future_offset(self, published_event, confirmed_registration):
        rows = enqueue_event_reminders(confirmed_registration)
        assert rows == 3
        assert ScheduledEmail.objects.filter(
            event=published_event, registration=confirmed_registration, template_key='event_reminder'
        ).count() == 3

    def test_skips_past_offsets(self, db):
        from factories import EventFactory, RegistrationFactory

        # Event in 30 minutes — T-1h offset is already in the past, should be skipped.
        event = EventFactory(
            published=True,
            starts_at=timezone.now() + timedelta(minutes=30),
            reminder_offsets_minutes=[1440, 60, 0],  # only T-now is future-feasible (≈now)
        )
        reg = RegistrationFactory(event=event, status='confirmed')
        rows = enqueue_event_reminders(reg)
        # 1440 (T-24h) and 60 (T-1h) are past; 0 (T-now) is in 30 min → 1 row.
        assert rows == 1

    def test_idempotent_under_repeat_call(self, published_event, confirmed_registration):
        first = enqueue_event_reminders(confirmed_registration)
        second = enqueue_event_reminders(confirmed_registration)
        assert first == 3 and second == 3
        # Unique constraint must keep the count at 3, not 6.
        assert ScheduledEmail.objects.filter(
            event=published_event, registration=confirmed_registration
        ).count() == 3

    def test_uses_default_offsets_when_field_empty(self, db):
        from factories import EventFactory, RegistrationFactory

        event = EventFactory(
            published=True,
            starts_at=timezone.now() + timedelta(days=14),  # all default offsets in future
            reminder_offsets_minutes=[],
        )
        reg = RegistrationFactory(event=event, status='confirmed')
        rows = enqueue_event_reminders(reg)
        assert rows == len(DEFAULT_REMINDER_OFFSETS_MINUTES)

    def test_skips_unpublished_events(self, db):
        from factories import EventFactory, RegistrationFactory

        event = EventFactory(starts_at=timezone.now() + timedelta(days=2))  # default = draft
        reg = RegistrationFactory(event=event, status='confirmed')
        rows = enqueue_event_reminders(reg)
        assert rows == 0


@pytest.mark.django_db
class TestCancelEventReminders:
    def test_cancels_only_pending_for_target_registration(self, published_event):
        from factories import RegistrationFactory

        reg_a = RegistrationFactory(event=published_event, status='confirmed')
        reg_b = RegistrationFactory(event=published_event, status='confirmed')
        enqueue_event_reminders(reg_a)
        enqueue_event_reminders(reg_b)

        cancelled = cancel_event_reminders(registration=reg_a)
        assert cancelled == 3
        # reg_a's are CANCELLED, reg_b's still PENDING.
        assert ScheduledEmail.objects.filter(
            registration=reg_a, status=ScheduledEmail.Status.CANCELLED
        ).count() == 3
        assert ScheduledEmail.objects.filter(
            registration=reg_b, status=ScheduledEmail.Status.PENDING
        ).count() == 3

    def test_event_scope_cancels_all_registration_reminders(self, published_event):
        from factories import RegistrationFactory

        reg_a = RegistrationFactory(event=published_event, status='confirmed')
        reg_b = RegistrationFactory(event=published_event, status='confirmed')
        enqueue_event_reminders(reg_a)
        enqueue_event_reminders(reg_b)

        cancelled = cancel_event_reminders(event=published_event)
        assert cancelled == 6


@pytest.mark.django_db
class TestRescheduleOnStartsAtChange:
    def test_signal_cancels_and_reenqueues_when_starts_at_moves(self, published_event, confirmed_registration):
        enqueue_event_reminders(confirmed_registration)
        original_send_ats = sorted(
            ScheduledEmail.objects.filter(
                event=published_event, status=ScheduledEmail.Status.PENDING
            ).values_list('send_at', flat=True)
        )

        # Push the event two more days out — the signal should reschedule.
        published_event.starts_at = published_event.starts_at + timedelta(days=2)
        published_event.save()

        # Old rows are now CANCELLED; new rows exist for the new times.
        cancelled_count = ScheduledEmail.objects.filter(
            event=published_event, status=ScheduledEmail.Status.CANCELLED
        ).count()
        pending_qs = ScheduledEmail.objects.filter(
            event=published_event, status=ScheduledEmail.Status.PENDING
        )
        assert cancelled_count == 3
        assert pending_qs.count() == 3
        new_send_ats = sorted(pending_qs.values_list('send_at', flat=True))
        assert new_send_ats != original_send_ats


@pytest.mark.django_db
class TestSignalCancelsOnRegistrationCancel:
    def test_cancel_registration_cancels_pending_reminders(self, published_event, confirmed_registration):
        enqueue_event_reminders(confirmed_registration)
        confirmed_registration.status = 'cancelled'
        confirmed_registration.save()

        cancelled = ScheduledEmail.objects.filter(
            registration=confirmed_registration, status=ScheduledEmail.Status.CANCELLED
        ).count()
        assert cancelled == 3


@pytest.mark.django_db
class TestSignalCancelsOnEventCancel:
    def test_cancel_event_cancels_all_registration_reminders(self, published_event):
        from factories import RegistrationFactory

        reg = RegistrationFactory(event=published_event, status='confirmed')
        enqueue_event_reminders(reg)

        published_event.status = 'cancelled'
        published_event.save()

        cancelled = ScheduledEmail.objects.filter(
            event=published_event, status=ScheduledEmail.Status.CANCELLED
        ).count()
        assert cancelled == 3


@pytest.mark.django_db
class TestBuildEventJoinUrl:
    def test_user_registration_uses_event_lobby(self, published_event, confirmed_registration, settings):
        settings.FRONTEND_URL = 'https://example.test'
        url = build_event_join_url(published_event, confirmed_registration)
        assert url == f"https://example.test/events/{published_event.uuid}/lobby"

    def test_guest_registration_uses_registration_lobby(self, published_event, settings):
        from factories import RegistrationFactory

        settings.FRONTEND_URL = 'https://example.test'
        guest = RegistrationFactory(event=published_event, guest=True, status='confirmed')
        url = build_event_join_url(published_event, guest)
        assert url == f"https://example.test/r/{guest.uuid}/lobby"
