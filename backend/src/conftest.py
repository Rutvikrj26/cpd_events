"""
Pytest fixtures for backend tests.

This module provides comprehensive fixtures for testing API endpoints.
Fixtures use factory_boy factories from factories.py for data generation.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

# Import factories
from factories import (
    AssignmentFactory,
    CertificateFactory,
    CertificateTemplateFactory,
    ContactFactory,
    ContactListFactory,
    CourseFactory,
    EventCustomFieldFactory,
    EventFactory,
    EventModuleFactory,
    EventSessionFactory,
    ModuleContentFactory,
    OrganizerFactory,
    RegistrationFactory,
    TagFactory,
    UserFactory,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _setup_role_groups(db):
    """Seed Django role groups + permissions before any test that touches the
    DB. Without this, tests that rely on `has_perm("learning.can_create_course")`
    or similar role-based gating fail with 403 because UserFactory creates the
    'instructor' / 'organizer' groups via get_or_create — empty, with no perms
    attached. Production sets these up via the `setup_groups` management
    command; tests need the same seeding.
    """
    from django.core.management import call_command
    call_command('setup_groups', verbosity=0)


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
def instructor_client(instructor):
    """API client authenticated as an instructor."""
    client = APIClient()
    client.force_authenticate(user=instructor)
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
    """A regular learner user."""
    return UserFactory(
        email='test@example.com',
        full_name='Test User',
        groups=['learner'],
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
    )


@pytest.fixture
def instructor(db):
    """An instructor user."""
    return UserFactory(
        email='instructor@example.com',
        full_name='Test Instructor',
        groups=['instructor'],
    )


@pytest.fixture
def other_organizer(db):
    """A different organizer user for permission testing."""
    return OrganizerFactory(
        email='other-organizer@example.com',
        full_name='Other Organizer',
    )


@pytest.fixture
def admin_user(db):
    """A Django superuser AND institution admin.

    Post-Phase-3, application RBAC gates on `admin` group membership rather
    than `is_staff`, so fixtures that want admin power in the app must also
    be added to the admin group.
    """
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        full_name='Admin User',
    )
    user.assign_role("admin")
    return user


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
def course(db, instructor):
    """A course owned by the instructor."""
    return CourseFactory(
        created_by=instructor,
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
def mock_stripe(settings):
    """Mock Stripe API for billing tests.

    Subscription/billing-portal mocks were removed when the platform moved
    to single-tenant; only the primitives the unified Checkout flow uses
    remain (Customer + checkout.Session + PaymentMethod).
    """
    settings.STRIPE_SECRET_KEY = 'sk_test_mock'
    with (
        patch('stripe.Customer') as mock_customer,
        patch('stripe.checkout.Session') as mock_checkout,
        patch('stripe.PaymentMethod') as mock_pm,
    ):
        mock_customer.create.return_value = MagicMock(id='cus_test123')
        mock_checkout.create.return_value = MagicMock(
            id='cs_test123',
            url='https://checkout.stripe.com/test',
        )
        yield MagicMock(
            Customer=mock_customer,
            checkout=MagicMock(Session=mock_checkout),
            PaymentMethod=mock_pm,
        )


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


@pytest.fixture
def stripe_products(db):
    """Stub — StripeProduct/StripePrice models were removed in the single-tenant
    transition (per-seat plans replaced with one-time course/event purchases)."""
    return None
