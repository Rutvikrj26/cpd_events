"""
Tests for add_zoom_registrant task.

Tests for the background task that adds confirmed registrations
to Zoom meetings as registrants.
"""

from unittest.mock import patch

import pytest


@pytest.mark.django_db
class TestAddZoomRegistrantTask:
    """Tests for registrations.tasks.add_zoom_registrant."""

    def test_successful_registrant_addition(self, published_event, user, db):
        """Task successfully adds registrant to Zoom meeting."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup: Event with Zoom meeting ID
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        # Create confirmed registration
        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            full_name='John Doe',
            email='john@example.com',
        )

        mock_result = {
            'success': True,
            'join_url': 'https://zoom.us/j/123?tk=unique',
            'registrant_id': 'reg-abc123',
        }

        with patch('accounts.services.zoom_service.add_meeting_registrant', return_value=mock_result) as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is True
        mock_add.assert_called_once_with(
            event=published_event,
            email='john@example.com',
            first_name='John',
            last_name='Doe',
        )

        registration.refresh_from_db()
        assert registration.zoom_registrant_join_url == 'https://zoom.us/j/123?tk=unique'
        assert registration.zoom_registrant_id == 'reg-abc123'

    def test_idempotency_skips_already_registered(self, published_event, user, db):
        """Task skips if registration already has zoom_registrant_id."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup: Event with Zoom meeting
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        # Registration already has Zoom registrant ID
        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            zoom_registrant_id='already-registered',
            zoom_registrant_join_url='https://zoom.us/j/old',
        )

        with patch('accounts.services.zoom_service.add_meeting_registrant') as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is True  # Returns True for idempotency
        mock_add.assert_not_called()  # But doesn't call API

    def test_skips_non_confirmed_registration(self, published_event, user, db):
        """Task skips registrations that are not confirmed."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        # Pending registration
        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.PENDING,
        )

        with patch('accounts.services.zoom_service.add_meeting_registrant') as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is False
        mock_add.assert_not_called()

    def test_skips_waitlisted_registration(self, published_event, user, db):
        """Task skips waitlisted registrations."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        # Waitlisted registration
        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.WAITLISTED,
        )

        with patch('accounts.services.zoom_service.add_meeting_registrant') as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is False
        mock_add.assert_not_called()

    def test_skips_event_without_zoom_meeting(self, published_event, user, db):
        """Task skips when event has no Zoom meeting ID."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Event without Zoom
        published_event.zoom_meeting_id = ''
        published_event.save(update_fields=['zoom_meeting_id'])

        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
        )

        with patch('accounts.services.zoom_service.add_meeting_registrant') as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is False
        mock_add.assert_not_called()

    def test_schedules_retry_on_api_error(self, published_event, user, db):
        """Task schedules retry on Zoom API error instead of raising."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            full_name='Jane Smith',
            email='jane@example.com',
        )

        mock_result = {
            'success': False,
            'error': 'Rate limit exceeded',
        }

        with (
            patch('accounts.services.zoom_service.add_meeting_registrant', return_value=mock_result),
            patch('registrations.tasks.add_zoom_registrant.delay') as mock_delay,
        ):
            result = add_zoom_registrant(registration.id, retry_count=0)

        # Should return False and schedule retry
        assert result is False
        mock_delay.assert_called_once_with(registration.id, retry_count=1)

        # Registration should have error recorded
        registration.refresh_from_db()
        assert registration.zoom_add_attempt_count == 1
        assert 'Rate limit exceeded' in registration.zoom_add_error

    def test_max_retries_exceeded_does_not_retry(self, published_event, user, db):
        """Task stops retrying after MAX_RETRIES exceeded."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            full_name='Max Retry User',
            email='maxretry@example.com',
        )

        mock_result = {
            'success': False,
            'error': 'Persistent failure',
        }

        with (
            patch('accounts.services.zoom_service.add_meeting_registrant', return_value=mock_result),
            patch('registrations.tasks.add_zoom_registrant.delay') as mock_delay,
        ):
            # Simulate already at max retries (5)
            result = add_zoom_registrant(registration.id, retry_count=5)

        # Should return False and NOT schedule retry
        assert result is False
        mock_delay.assert_not_called()

        # Should have final error message
        registration.refresh_from_db()
        assert 'Max retries exceeded' in registration.zoom_add_error

    def test_returns_false_for_nonexistent_registration(self, db):
        """Task returns False for non-existent registration ID."""
        from registrations.tasks import add_zoom_registrant

        result = add_zoom_registrant(999999)

        assert result is False

    def test_handles_single_name(self, published_event, user, db):
        """Task handles registrants with single-word names."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            full_name='Madonna',  # Single name
            email='madonna@example.com',
        )

        mock_result = {
            'success': True,
            'join_url': 'https://zoom.us/j/123?tk=abc',
            'registrant_id': 'reg-single',
        }

        with patch('accounts.services.zoom_service.add_meeting_registrant', return_value=mock_result) as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is True
        mock_add.assert_called_once()
        call_kwargs = mock_add.call_args[1]
        assert call_kwargs['first_name'] == 'Madonna'
        assert call_kwargs['last_name'] == ''

    def test_handles_multi_part_name(self, published_event, user, db):
        """Task correctly splits multi-part names."""
        from factories import RegistrationFactory
        from registrations.models import Registration
        from registrations.tasks import add_zoom_registrant

        # Setup
        published_event.zoom_meeting_id = '123456789'
        published_event.save(update_fields=['zoom_meeting_id'])

        registration = RegistrationFactory(
            event=published_event,
            user=user,
            status=Registration.Status.CONFIRMED,
            full_name='Mary Jane Watson Parker',  # Multi-part name
            email='mj@example.com',
        )

        mock_result = {
            'success': True,
            'join_url': 'https://zoom.us/j/123?tk=abc',
            'registrant_id': 'reg-multi',
        }

        with patch('accounts.services.zoom_service.add_meeting_registrant', return_value=mock_result) as mock_add:
            result = add_zoom_registrant(registration.id)

        assert result is True
        call_kwargs = mock_add.call_args[1]
        assert call_kwargs['first_name'] == 'Mary'
        assert call_kwargs['last_name'] == 'Jane Watson Parker'
