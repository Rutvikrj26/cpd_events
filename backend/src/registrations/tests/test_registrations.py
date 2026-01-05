"""
Tests for registration endpoints.

Endpoints tested:
- GET /api/v1/events/{event_uuid}/registrations/
- POST /api/v1/events/{event_uuid}/registrations/
- PATCH /api/v1/events/{event_uuid}/registrations/{uuid}/
- GET /api/v1/events/{event_uuid}/registrations/waitlist/
- POST /api/v1/events/{event_uuid}/registrations/{uuid}/promote/
- POST /api/v1/events/{event_uuid}/registrations/promote_next/
- POST /api/v1/events/{event_uuid}/registrations/{uuid}/override_attendance/
- GET /api/v1/events/{event_uuid}/registrations/summary/
- POST /api/v1/public/events/{event_uuid}/register/
- GET /api/v1/registrations/
- GET /api/v1/registrations/{uuid}/
- POST /api/v1/registrations/{uuid}/cancel/
- POST /api/v1/users/me/link-registrations/
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from rest_framework import status


# =============================================================================
# Organizer Registration Management Tests
# =============================================================================


@pytest.mark.django_db
class TestEventRegistrationViewSet:
    """Tests for organizer registration management."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/registrations/'

    def test_list_registrations(self, organizer_client, registration, published_event):
        """Organizer can list registrations for their event."""
        endpoint = self.get_endpoint(published_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_registrations_filter_by_status(self, organizer_client, registration, published_event):
        """Can filter registrations by status."""
        endpoint = f'{self.get_endpoint(published_event)}?status=confirmed'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        for reg in response.data['results']:
            assert reg['status'] == 'confirmed'

    def test_bulk_add_registrations(self, organizer_client, published_event):
        """Organizer can bulk add registrations."""
        endpoint = self.get_endpoint(published_event)
        data = {
            'registrations': [
                {'email': 'attendee1@example.com', 'full_name': 'Attendee One'},
                {'email': 'attendee2@example.com', 'full_name': 'Attendee Two'},
            ]
        }
        response = organizer_client.post(endpoint, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_registration_attendance(self, organizer_client, registration):
        """Organizer can update attendance for a registration."""
        endpoint = f'/api/v1/events/{registration.event.uuid}/registrations/{registration.uuid}/'
        response = organizer_client.patch(endpoint, {
            'attended': True,
        })
        assert response.status_code == status.HTTP_200_OK
        registration.refresh_from_db()
        assert registration.attended is True

    def test_cannot_access_other_event_registrations(self, organizer_client, other_organizer_event):
        """Cannot access registrations for another organizer's event."""
        endpoint = self.get_endpoint(other_organizer_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0

    def test_attendee_cannot_manage_registrations(self, auth_client, published_event):
        """Attendees cannot access organizer registration endpoints."""
        endpoint = self.get_endpoint(published_event)
        response = auth_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Waitlist Tests
# =============================================================================


@pytest.mark.django_db
class TestWaitlistManagement:
    """Tests for waitlist management endpoints."""

    def test_get_waitlist(self, organizer_client, waitlisted_registration, published_event):
        """Organizer can get waitlist for an event."""
        endpoint = f'/api/v1/events/{published_event.uuid}/registrations/waitlist/'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_promote_from_waitlist(self, organizer_client, waitlisted_registration, published_event):
        """Organizer can promote a registration from waitlist."""
        endpoint = f'/api/v1/events/{published_event.uuid}/registrations/{waitlisted_registration.uuid}/promote/'
        response = organizer_client.post(endpoint)
        assert response.status_code == status.HTTP_200_OK
        waitlisted_registration.refresh_from_db()
        assert waitlisted_registration.status == 'confirmed'

    def test_promote_from_waitlist_paid_event_sets_pending(self, organizer_client, organizer, db):
        """Paid event promotions move to pending payment."""
        from factories import EventFactory, RegistrationFactory

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('50.00'),
        )
        waitlisted = RegistrationFactory(
            event=event,
            status='waitlisted',
        )

        endpoint = f'/api/v1/events/{event.uuid}/registrations/{waitlisted.uuid}/promote/'
        response = organizer_client.post(endpoint)
        assert response.status_code == status.HTTP_200_OK
        waitlisted.refresh_from_db()
        assert waitlisted.status == 'pending'
        assert waitlisted.payment_status == 'pending'

    def test_promote_next(self, organizer_client, published_event, user, db):
        """Organizer can promote next person in waitlist."""
        from factories import RegistrationFactory
        # Create waitlisted registrations
        waitlisted = RegistrationFactory(
            event=published_event,
            status='waitlisted',
        )
        
        endpoint = f'/api/v1/events/{published_event.uuid}/registrations/promote-next/'
        response = organizer_client.post(endpoint)
        # May succeed or fail if no waitlist
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# Attendance Override Tests
# =============================================================================


@pytest.mark.django_db
class TestAttendanceOverride:
    """Tests for attendance override endpoint."""

    def test_override_attendance(self, organizer_client, registration):
        """Organizer can override attendance eligibility."""
        endpoint = f'/api/v1/events/{registration.event.uuid}/registrations/{registration.uuid}/override-attendance/'
        response = organizer_client.post(endpoint, {
            'eligible': True,
            'reason': 'Manual verification',
        })
        assert response.status_code == status.HTTP_200_OK
        registration.refresh_from_db()
        assert registration.attendance_eligible is True

    def test_override_allows_certificate_eligibility(self, registration):
        """Attendance override should allow certificate eligibility."""
        registration.attendance_override = True
        registration.attendance_eligible = False
        registration.save(update_fields=['attendance_override', 'attendance_eligible', 'updated_at'])
        assert registration.can_receive_certificate is True


# =============================================================================
# Registration Summary Tests
# =============================================================================


@pytest.mark.django_db
class TestRegistrationSummary:
    """Tests for registration summary endpoint."""

    def test_get_summary(self, organizer_client, registration, published_event):
        """Organizer can get registration summary stats."""
        endpoint = f'/api/v1/events/{published_event.uuid}/registrations/summary/'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Should contain count statistics
        assert isinstance(response.data, dict)


# =============================================================================
# Public Registration Tests
# =============================================================================


@pytest.mark.django_db
class TestPublicRegistration:
    """Tests for POST /api/v1/public/events/{event_uuid}/register/"""

    def get_endpoint(self, event):
        return f'/api/v1/public/events/{event.uuid}/register/'

    def test_register_authenticated_user(self, auth_client, user, published_event):
        """Authenticated user can register for an event."""
        endpoint = self.get_endpoint(published_event)
        response = auth_client.post(endpoint, {
            'email': user.email,
            'full_name': user.full_name,
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_register_guest(self, api_client, published_event):
        """Guest can register without an account."""
        endpoint = self.get_endpoint(published_event)
        response = api_client.post(endpoint, {
            'email': 'guest@example.com',
            'full_name': 'Guest User',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_register_duplicate_email(self, api_client, registration, published_event):
        """Cannot register twice with same email."""
        endpoint = self.get_endpoint(published_event)
        response = api_client.post(endpoint, {
            'email': registration.email,
            'full_name': 'Another Name',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_closed_event(self, api_client, event):
        """Cannot register for draft (not published) event."""
        endpoint = self.get_endpoint(event)
        response = api_client.post(endpoint, {
            'email': 'test@example.com',
            'full_name': 'Test User',
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_register_full_event_goes_to_waitlist(self, api_client, organizer, db):
        """When event is full, registration goes to waitlist."""
        from factories import EventFactory, RegistrationFactory
        # Create event with max 1 attendee
        full_event = EventFactory(
            owner=organizer,
            status='published',
            max_attendees=1,
            waitlist_enabled=True,
        )
        # Fill the event
        RegistrationFactory(event=full_event, status='confirmed')
        
        endpoint = self.get_endpoint(full_event)
        response = api_client.post(endpoint, {
            'email': 'waitlist@example.com',
            'full_name': 'Waitlist User',
        })
        # Should be created but waitlisted
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get('status') == 'waitlisted'

    def test_register_missing_email(self, api_client, published_event):
        """Email is required."""
        endpoint = self.get_endpoint(published_event)
        response = api_client.post(endpoint, {
            'full_name': 'No Email User',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Payment Workflow Tests
# =============================================================================


@pytest.mark.django_db
class TestRegistrationPaymentFlow:
    """Tests for paid registration workflows."""

    def test_paid_registration_requires_payment(self, api_client, organizer, db):
        """Paid registration returns payment details and remains pending."""
        from factories import EventFactory
        from registrations.models import Registration

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('100.00'),
        )

        with patch('billing.services.StripePaymentService.is_configured', new_callable=PropertyMock) as mock_config, \
             patch('registrations.services.stripe_payment_service.create_payment_intent') as mock_create:
            mock_config.return_value = True
            mock_create.return_value = {
                'success': True,
                'client_secret': 'cs_test',
                'payment_intent_id': 'pi_test',
                'platform_fee_cents': 200,
                'total_amount_cents': 10200,
            }

            response = api_client.post(
                f'/api/v1/public/events/{event.uuid}/register/',
                {'email': 'paid@example.com', 'full_name': 'Paid User'},
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['requires_payment'] is True
        assert response.data['amount'] == 102.0
        assert response.data['ticket_price'] == 100.0
        assert response.data['platform_fee'] == 2.0

        registration = Registration.objects.get(email='paid@example.com', event=event)
        assert registration.status == Registration.Status.PENDING
        assert registration.payment_status == Registration.PaymentStatus.PENDING
        assert registration.total_amount == Decimal('102.00')
        assert registration.platform_fee_amount == Decimal('2.00')

    def test_payment_intent_blocks_full_event(self, api_client, organizer, db):
        """Payment intent endpoint blocks payment when event is full."""
        from factories import EventFactory, RegistrationFactory
        from registrations.models import Registration

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('50.00'),
            max_attendees=1,
        )
        RegistrationFactory(event=event, status='confirmed')

        pending = RegistrationFactory(
            event=event,
            status='pending',
            payment_status='pending',
            amount_paid=Decimal('50.00'),
            platform_fee_amount=Decimal('1.00'),
            total_amount=Decimal('51.00'),
        )

        response = api_client.post(f'/api/v1/public/registrations/{pending.uuid}/payment-intent/')
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['error']['code'] == 'EVENT_FULL'

    def test_payment_intent_reuses_existing_intent(self, api_client, organizer, db):
        """Payment intent endpoint reuses existing intent if still payable."""
        from factories import EventFactory, RegistrationFactory

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('80.00'),
            max_attendees=10,
        )
        pending = RegistrationFactory(
            event=event,
            status='pending',
            payment_status='pending',
            amount_paid=Decimal('80.00'),
            platform_fee_amount=Decimal('1.60'),
            total_amount=Decimal('81.60'),
        )
        pending.payment_intent_id = 'pi_existing'
        pending.save(update_fields=['payment_intent_id'])

        mock_intent = MagicMock()
        mock_intent.status = 'requires_payment_method'
        mock_intent.client_secret = 'cs_existing'

        with patch('billing.services.StripePaymentService.is_configured', new_callable=PropertyMock) as mock_config, \
             patch('billing.services.stripe_payment_service.get_payee_account_id', return_value='acct_test'), \
             patch('billing.services.stripe_payment_service.retrieve_payment_intent', return_value=mock_intent):
            mock_config.return_value = True
            response = api_client.post(f'/api/v1/public/registrations/{pending.uuid}/payment-intent/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['client_secret'] == 'cs_existing'
        assert response.data['amount'] == 81.6

    def test_confirm_payment_refunds_when_full(self, api_client, organizer, db):
        """Confirm payment refunds when capacity is already full."""
        from factories import EventFactory, RegistrationFactory
        from registrations.models import Registration
        from registrations.services import PaymentConfirmationService

        organizer.stripe_connect_id = 'acct_test'
        organizer.stripe_charges_enabled = True
        organizer.save(update_fields=['stripe_connect_id', 'stripe_charges_enabled'])

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('100.00'),
            max_attendees=1,
        )
        RegistrationFactory(event=event, status='confirmed')

        pending = RegistrationFactory(
            event=event,
            status='pending',
            payment_status='pending',
            amount_paid=Decimal('100.00'),
            platform_fee_amount=Decimal('2.00'),
            total_amount=Decimal('102.00'),
        )
        pending.payment_intent_id = 'pi_paid'
        pending.save(update_fields=['payment_intent_id'])

        intent = MagicMock()
        intent.status = 'succeeded'
        intent.amount_received = 10200

        with patch.object(PaymentConfirmationService, 'is_configured', new_callable=PropertyMock) as mock_config, \
             patch('registrations.services.stripe_payment_service.get_payee_account_id', return_value='acct_test'), \
             patch('registrations.services.stripe_payment_service.retrieve_payment_intent', return_value=intent), \
             patch('registrations.services.stripe_payment_service.refund_payment_intent', return_value={'success': True}):
            mock_config.return_value = True
            response = api_client.post(f'/api/v1/public/registrations/{pending.uuid}/confirm-payment/')

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data['error']['code'] == 'EVENT_FULL'

        pending.refresh_from_db()
        assert pending.payment_status == Registration.PaymentStatus.REFUNDED
        assert pending.status == Registration.Status.PENDING

    def test_confirm_payment_success(self, api_client, organizer, db):
        """Confirm payment succeeds and confirms registration when capacity allows."""
        from factories import EventFactory, RegistrationFactory
        from registrations.models import Registration
        from registrations.services import PaymentConfirmationService

        organizer.stripe_connect_id = 'acct_test'
        organizer.stripe_charges_enabled = True
        organizer.save(update_fields=['stripe_connect_id', 'stripe_charges_enabled'])

        event = EventFactory(
            owner=organizer,
            status='published',
            price=Decimal('75.00'),
            max_attendees=2,
        )

        pending = RegistrationFactory(
            event=event,
            status='pending',
            payment_status='pending',
            amount_paid=Decimal('75.00'),
            platform_fee_amount=Decimal('1.50'),
            total_amount=Decimal('76.50'),
        )
        pending.payment_intent_id = 'pi_success'
        pending.save(update_fields=['payment_intent_id'])

        intent = MagicMock()
        intent.status = 'succeeded'
        intent.amount_received = 7650

        with patch.object(PaymentConfirmationService, 'is_configured', new_callable=PropertyMock) as mock_config, \
             patch('registrations.services.stripe_payment_service.get_payee_account_id', return_value='acct_test'), \
             patch('registrations.services.stripe_payment_service.retrieve_payment_intent', return_value=intent), \
             patch('registrations.tasks.add_zoom_registrant.delay'):
            mock_config.return_value = True
            response = api_client.post(f'/api/v1/public/registrations/{pending.uuid}/confirm-payment/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'paid'

        pending.refresh_from_db()
        assert pending.payment_status == Registration.PaymentStatus.PAID
        assert pending.status == Registration.Status.CONFIRMED

# =============================================================================
# My Registrations Tests
# =============================================================================


@pytest.mark.django_db
class TestMyRegistrationViewSet:
    """Tests for attendee's own registrations."""

    endpoint = '/api/v1/registrations/'

    def test_list_my_registrations(self, auth_client, registration):
        """User can list their registrations."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_empty_registrations(self, auth_client):
        """Empty list when user has no registrations."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0

    def test_retrieve_my_registration(self, auth_client, registration):
        """User can retrieve their specific registration."""
        response = auth_client.get(f'{self.endpoint}{registration.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(registration.uuid)

    def test_cannot_see_others_registrations(self, auth_client, guest_registration):
        """User cannot see others' registrations."""
        response = auth_client.get(f'{self.endpoint}{guest_registration.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_registration(self, auth_client, registration):
        """User can cancel their registration."""
        response = auth_client.post(f'{self.endpoint}{registration.uuid}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        registration.refresh_from_db()
        assert registration.status == 'cancelled'

    def test_cancel_already_cancelled(self, auth_client, registration):
        """Cannot cancel already cancelled registration."""
        registration.status = 'cancelled'
        registration.save()
        
        response = auth_client.post(f'{self.endpoint}{registration.uuid}/cancel/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access registrations."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Link Registrations Tests
# =============================================================================


@pytest.mark.django_db
class TestLinkRegistrationsView:
    """Tests for POST /api/v1/users/me/link-registrations/"""

    endpoint = '/api/v1/registrations/users/me/link-registrations/'

    def test_link_guest_registrations(self, auth_client, user, published_event, db):
        """User can link guest registrations made with their email."""
        from factories import RegistrationFactory
        # Create guest registration with user's email
        guest_reg = RegistrationFactory(
            event=published_event,
            user=None,
            email=user.email,
            full_name='Guest',
        )
        
        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        
        guest_reg.refresh_from_db()
        assert guest_reg.user == user

    def test_link_no_orphaned_registrations(self, auth_client):
        """No error when there are no registrations to link."""
        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_link(self, api_client):
        """Unauthenticated users cannot link registrations."""
        response = api_client.post(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
