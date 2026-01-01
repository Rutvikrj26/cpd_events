"""
Pytest fixtures for backend tests.

This module provides comprehensive fixtures for testing API endpoints.
Fixtures use factory_boy factories from factories.py for data generation.
"""

import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

# Import factories
from factories import (
    UserFactory,
    OrganizerFactory,
    OrganizationFactory,
    OrganizationMembershipFactory,
    EventFactory,
    EventSessionFactory,
    EventCustomFieldFactory,
    RegistrationFactory,
    CertificateTemplateFactory,
    CertificateFactory,
    ContactListFactory,
    ContactFactory,
    TagFactory,
    SubscriptionFactory,
    EventModuleFactory,
    ModuleContentFactory,
    AssignmentFactory,
    CourseFactory,
)


User = get_user_model()


# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """API client authenticated as a regular attendee user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def organizer_client(organizer):
    """API client authenticated as an organizer."""
    client = APIClient()
    client.force_authenticate(user=organizer)
    return client


@pytest.fixture
def other_organizer_client(other_organizer):
    """API client authenticated as a different organizer."""
    client = APIClient()
    client.force_authenticate(user=other_organizer)
    return client


@pytest.fixture
def admin_client(admin_user):
    """API client authenticated as a Django admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def user(db):
    """A regular attendee user."""
    return UserFactory(
        email='test@example.com',
        full_name='Test User',
    )


@pytest.fixture
def unverified_user(db):
    """An attendee user with unverified email."""
    return UserFactory(
        email='unverified@example.com',
        email_verified=False,
    )


@pytest.fixture
def organizer(db):
    """An organizer user."""
    return OrganizerFactory(
        email='organizer@example.com',
        full_name='Test Organizer',
        organizer_slug='test-organizer',
    )


@pytest.fixture
def other_organizer(db):
    """A different organizer user for permission testing."""
    return OrganizerFactory(
        email='other-organizer@example.com',
        full_name='Other Organizer',
        organizer_slug='other-organizer',
    )


@pytest.fixture
def admin_user(db):
    """A Django superuser/admin."""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        full_name='Admin User',
    )


# =============================================================================
# Organization Fixtures
# =============================================================================


@pytest.fixture
def organization(db, organizer):
    """An organization owned by the organizer."""
    org = OrganizationFactory(
        name='Test Organization',
        created_by=organizer,
    )
    # Create owner membership
    OrganizationMembershipFactory(
        organization=org,
        user=organizer,
        role='owner',
    )
    return org


@pytest.fixture
def org_member(db, organization):
    """A member of the organization."""
    member_user = OrganizerFactory()
    OrganizationMembershipFactory(
        organization=organization,
        user=member_user,
        role='member',
    )
    return member_user


# =============================================================================
# Event Fixtures
# =============================================================================


@pytest.fixture
def event(db, organizer):
    """A draft event owned by the organizer."""
    return EventFactory(
        owner=organizer,
        title='Test Event',
        status='draft',
    )


@pytest.fixture
def published_event(db, organizer):
    """A published event ready for registration."""
    return EventFactory(
        owner=organizer,
        title='Published Event',
        status='published',
    )


@pytest.fixture
def live_event(db, organizer):
    """A live event currently in progress."""
    return EventFactory(
        owner=organizer,
        title='Live Event',
        status='live',
        starts_at=timezone.now() - timedelta(hours=1),
    )


@pytest.fixture
def completed_event(db, organizer):
    """A completed past event."""
    return EventFactory(
        owner=organizer,
        title='Completed Event',
        status='completed',
        starts_at=timezone.now() - timedelta(days=7),
    )


@pytest.fixture
def other_organizer_event(db, other_organizer):
    """An event owned by another organizer for permission testing."""
    return EventFactory(
        owner=other_organizer,
        title='Other Organizer Event',
    )


@pytest.fixture
def event_with_sessions(db, event):
    """An event with multiple sessions."""
    event.is_multi_session = True
    event.save(update_fields=['is_multi_session'])
    EventSessionFactory(event=event, title='Session 1', order=0)
    EventSessionFactory(event=event, title='Session 2', order=1)
    EventSessionFactory(event=event, title='Session 3', order=2)
    return event


@pytest.fixture
def event_with_custom_fields(db, event):
    """An event with custom registration fields."""
    EventCustomFieldFactory(event=event, label='Company', field_type='text', order=0)
    EventCustomFieldFactory(event=event, label='Dietary Requirements', field_type='select', order=1)
    return event


# =============================================================================
# Registration Fixtures
# =============================================================================


@pytest.fixture
def registration(db, published_event, user):
    """A confirmed registration for the user."""
    return RegistrationFactory(
        event=published_event,
        user=user,
        email=user.email,
        full_name=user.full_name,
        status='confirmed',
    )


@pytest.fixture
def attended_registration(db, completed_event, user):
    """A registration with attendance marked."""
    return RegistrationFactory(
        event=completed_event,
        user=user,
        email=user.email,
        full_name=user.full_name,
        status='confirmed',
        attended=True,
        attendance_eligible=True,
        total_attendance_minutes=120,
    )


@pytest.fixture
def guest_registration(db, published_event):
    """A guest registration (no user account)."""
    return RegistrationFactory(
        event=published_event,
        user=None,
        email='guest@example.com',
        full_name='Guest User',
        status='confirmed',
    )


@pytest.fixture
def waitlisted_registration(db, published_event, user):
    """A waitlisted registration."""
    return RegistrationFactory(
        event=published_event,
        user=user,
        status='waitlisted',
    )


# =============================================================================
# Certificate Fixtures
# =============================================================================


@pytest.fixture
def certificate_template(db, organizer):
    """A certificate template owned by the organizer."""
    return CertificateTemplateFactory(
        owner=organizer,
        name='Default Template',
        is_default=True,
    )


@pytest.fixture
def certificate(db, attended_registration, certificate_template):
    """An issued certificate."""
    return CertificateFactory(
        registration=attended_registration,
        template=certificate_template,
        issued_by=attended_registration.event.owner,
    )


# =============================================================================
# Contact Fixtures
# =============================================================================


@pytest.fixture
def contact_list(db, organizer):
    """A contact list owned by the organizer."""
    return ContactListFactory(
        owner=organizer,
        name='Test Contact List',
    )


@pytest.fixture
def contact(db, contact_list):
    """A contact in the contact list."""
    return ContactFactory(
        contact_list=contact_list,
        email='contact@example.com',
        full_name='Test Contact',
    )


@pytest.fixture
def tag(db, organizer):
    """A tag owned by the organizer."""
    return TagFactory(
        owner=organizer,
        name='VIP',
    )


# =============================================================================
# Billing Fixtures
# =============================================================================


@pytest.fixture
def subscription(db, organizer):
    """A subscription for the organizer (may already exist from signal)."""
    from billing.models import Subscription
    # Signal auto-creates subscription for organizers, so get or update it
    sub, created = Subscription.objects.get_or_create(
        user=organizer,
        defaults={'plan': 'free', 'status': 'active'}
    )
    return sub


# =============================================================================
# Learning Fixtures
# =============================================================================


@pytest.fixture
def event_module(db, event):
    """A learning module for an event."""
    return EventModuleFactory(
        event=event,
        title='Test Module',
    )


@pytest.fixture
def module_content(db, event_module):
    """Content within a module."""
    return ModuleContentFactory(
        module=event_module,
        title='Introduction',
        content_type='text',
    )


@pytest.fixture
def assignment(db, event_module):
    """An assignment within a module."""
    return AssignmentFactory(
        module=event_module,
        title='Quiz 1',
        max_score=100,
    )


@pytest.fixture
def course(db, organization):
    """A course owned by the organization."""
    return CourseFactory(
        organization=organization,
        title='Test Course',
    )


# =============================================================================
# Common Test Data Fixtures
# =============================================================================


@pytest.fixture
def event_create_data():
    """Valid data for creating an event."""
    return {
        'title': 'New Test Event',
        'description': 'A test event description',
        'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
        'ends_at': (timezone.now() + timedelta(days=7, hours=2)).isoformat(),
        'timezone': 'UTC',
        'max_attendees': 100,
        'registration_enabled': True,
        'cpd_credit_value': '1.5',
        'event_type': 'webinar',
        'event_format': 'online',
    }


@pytest.fixture
def registration_create_data(user):
    """Valid data for creating a registration."""
    return {
        'email': user.email,
        'full_name': user.full_name,
    }


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_stripe():
    """Mock Stripe API for billing tests."""
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_sub, \
         patch('stripe.checkout.Session') as mock_checkout, \
         patch('stripe.billing_portal.Session') as mock_portal, \
         patch('stripe.PaymentMethod') as mock_pm:
        mock_customer.create.return_value = MagicMock(id='cus_test123')
        mock_sub.create.return_value = MagicMock(
            id='sub_test123',
            status='active',
        )
        mock_checkout.create.return_value = MagicMock(
            id='cs_test123',
            url='https://checkout.stripe.com/test',
        )
        mock_portal.create.return_value = MagicMock(
            url='https://billing.stripe.com/test',
        )
        yield MagicMock(
            Customer=mock_customer,
            Subscription=mock_sub,
            checkout=MagicMock(Session=mock_checkout),
            billing_portal=MagicMock(Session=mock_portal),
            PaymentMethod=mock_pm,
        )


@pytest.fixture
def mock_zoom():
    """Mock Zoom API for integration tests."""
    mock_instance = MagicMock()
    mock_instance.create_meeting.return_value = {
        'id': 123456789,
        'join_url': 'https://zoom.us/j/123456789',
    }
    mock_instance.refresh_token.return_value = True
    yield mock_instance


@pytest.fixture
def mock_email():
    """Mock email sending for tests."""
    with patch('django.core.mail.send_mail') as mock:
        yield mock


@pytest.fixture
def mock_cloud_tasks():
    """Mock Google Cloud Tasks for async task tests."""
    with patch('common.cloud_tasks.enqueue_task') as mock:
        yield mock
