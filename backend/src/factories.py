"""
Factory Boy factories for test data generation.

Usage:
    from factories import UserFactory, EventFactory

    user = UserFactory()  # Creates and saves a user
    user = UserFactory.build()  # Creates without saving
    users = UserFactory.create_batch(5)  # Creates 5 users
"""

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import timedelta


# =============================================================================
# User Factories
# =============================================================================


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = 'accounts.User'

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    full_name = factory.Faker('name')
    password = factory.PostGeneration(lambda obj, create, extracted, **kwargs: obj.set_password(extracted or 'testpass123'))
    account_type = 'attendee'
    email_verified = True
    is_active = True

    class Params:
        organizer = factory.Trait(
            account_type='organizer',
            organizer_slug=factory.Sequence(lambda n: f'organizer-{n}'),
            is_organizer_profile_public=True,
        )
        unverified = factory.Trait(
            email_verified=False,
        )


class OrganizerFactory(UserFactory):
    """Factory for creating Organizer users."""

    account_type = 'organizer'
    is_organizer_profile_public = True
    organizer_slug = factory.Sequence(lambda n: f'organizer-{n}')


# =============================================================================
# Organization Factories
# =============================================================================


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = 'organizations.Organization'

    name = factory.Sequence(lambda n: f'Organization {n}')
    slug = factory.Sequence(lambda n: f'org-{n}')
    description = factory.Faker('paragraph')
    created_by = factory.SubFactory(OrganizerFactory)
    is_active = True


class OrganizationMembershipFactory(DjangoModelFactory):
    """Factory for creating OrganizationMembership instances."""

    class Meta:
        model = 'organizations.OrganizationMembership'

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(OrganizerFactory)
    role = 'member'
    is_active = True
    invited_at = factory.LazyFunction(timezone.now)
    accepted_at = factory.LazyFunction(timezone.now)

    class Params:
        owner = factory.Trait(role='owner')
        admin = factory.Trait(role='admin')
        manager = factory.Trait(role='manager')
        pending = factory.Trait(
            accepted_at=None,
            invitation_token=factory.Faker('uuid4'),
        )


# =============================================================================
# Event Factories
# =============================================================================


class EventFactory(DjangoModelFactory):
    """Factory for creating Event instances."""

    class Meta:
        model = 'events.Event'

    title = factory.Sequence(lambda n: f'Test Event {n}')
    slug = factory.Sequence(lambda n: f'test-event-{n}')
    description = factory.Faker('paragraph')
    owner = factory.SubFactory(OrganizerFactory)
    status = 'draft'
    event_type = 'webinar'
    format = 'online'
    starts_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    duration_minutes = 120
    timezone = 'UTC'
    max_attendees = 100
    registration_enabled = True
    cpd_enabled = True
    cpd_credit_value = factory.Faker('pydecimal', left_digits=1, right_digits=1, positive=True)

    class Params:
        published = factory.Trait(status='published')
        live = factory.Trait(status='live')
        completed = factory.Trait(status='completed')
        cancelled = factory.Trait(status='cancelled')
        past = factory.Trait(
            starts_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=7)),
            status='completed',
        )
        in_person = factory.Trait(
            format='in-person',
            location='Test Venue, 123 Test Street',
        )


class EventSessionFactory(DjangoModelFactory):
    """Factory for creating EventSession instances."""

    class Meta:
        model = 'events.EventSession'

    event = factory.SubFactory(EventFactory)
    title = factory.Sequence(lambda n: f'Session {n}')
    description = factory.Faker('sentence')
    starts_at = factory.LazyAttribute(lambda o: o.event.starts_at)
    duration_minutes = 60
    order = factory.Sequence(lambda n: n)


class EventCustomFieldFactory(DjangoModelFactory):
    """Factory for creating EventCustomField instances."""

    class Meta:
        model = 'events.EventCustomField'

    event = factory.SubFactory(EventFactory)
    label = factory.Sequence(lambda n: f'Custom Field {n}')
    field_type = 'text'
    required = False
    order = factory.Sequence(lambda n: n)


# =============================================================================
# Registration Factories
# =============================================================================


class RegistrationFactory(DjangoModelFactory):
    """Factory for creating Registration instances."""

    class Meta:
        model = 'registrations.Registration'

    event = factory.SubFactory(EventFactory, published=True)
    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda o: o.user.email if o.user else factory.Faker('email').generate())
    full_name = factory.LazyAttribute(lambda o: o.user.full_name if o.user else factory.Faker('name').generate())
    status = 'confirmed'
    source = 'self'

    class Params:
        waitlisted = factory.Trait(status='waitlisted')
        cancelled = factory.Trait(status='cancelled')
        guest = factory.Trait(
            user=None,
            email=factory.Faker('email'),
            full_name=factory.Faker('name'),
        )
        with_attendance = factory.Trait(
            attended=True,
            attendance_eligible=True,
            total_attendance_minutes=120,
        )


# =============================================================================
# Certificate Factories
# =============================================================================


class CertificateTemplateFactory(DjangoModelFactory):
    """Factory for creating CertificateTemplate instances."""

    class Meta:
        model = 'certificates.CertificateTemplate'

    name = factory.Sequence(lambda n: f'Certificate Template {n}')
    owner = factory.SubFactory(OrganizerFactory)
    is_active = True
    is_default = False


class CertificateFactory(DjangoModelFactory):
    """Factory for creating Certificate instances."""

    class Meta:
        model = 'certificates.Certificate'

    registration = factory.SubFactory(RegistrationFactory, with_attendance=True)
    template = factory.SubFactory(CertificateTemplateFactory)
    issued_by = factory.LazyAttribute(lambda o: o.registration.event.owner)
    status = 'active'
    certificate_data = factory.LazyAttribute(lambda o: {
        'recipient_name': o.registration.full_name,
        'event_title': o.registration.event.title,
    })


# =============================================================================
# Contact Factories
# =============================================================================


class ContactListFactory(DjangoModelFactory):
    """Factory for creating ContactList instances."""

    class Meta:
        model = 'contacts.ContactList'

    name = factory.Sequence(lambda n: f'Contact List {n}')
    owner = factory.SubFactory(OrganizerFactory)
    description = factory.Faker('sentence')


class ContactFactory(DjangoModelFactory):
    """Factory for creating Contact instances."""

    class Meta:
        model = 'contacts.Contact'

    contact_list = factory.SubFactory(ContactListFactory)
    email = factory.Faker('email')
    full_name = factory.Faker('name')


class TagFactory(DjangoModelFactory):
    """Factory for creating Tag instances."""

    class Meta:
        model = 'contacts.Tag'

    name = factory.Sequence(lambda n: f'Tag {n}')
    owner = factory.SubFactory(OrganizerFactory)
    color = '#3B82F6'


# =============================================================================
# Billing Factories
# =============================================================================


class SubscriptionFactory(DjangoModelFactory):
    """Factory for creating Subscription instances."""

    class Meta:
        model = 'billing.Subscription'

    user = factory.SubFactory(OrganizerFactory)
    plan = 'free'
    status = 'active'


class InvoiceFactory(DjangoModelFactory):
    """Factory for creating Invoice instances."""

    class Meta:
        model = 'billing.Invoice'

    user = factory.SubFactory(OrganizerFactory)
    stripe_invoice_id = factory.Sequence(lambda n: f'in_{n:024d}')
    amount_cents = 0
    currency = 'usd'
    status = 'paid'


class PaymentMethodFactory(DjangoModelFactory):
    """Factory for creating PaymentMethod instances."""

    class Meta:
        model = 'billing.PaymentMethod'

    user = factory.SubFactory(OrganizerFactory)
    stripe_payment_method_id = factory.Sequence(lambda n: f'pm_{n:024d}')
    card_brand = 'visa'
    card_last4 = '4242'
    is_default = True


# =============================================================================
# Learning Factories
# =============================================================================


class EventModuleFactory(DjangoModelFactory):
    """Factory for creating EventModule instances."""

    class Meta:
        model = 'learning.EventModule'

    event = factory.SubFactory(EventFactory)
    title = factory.Sequence(lambda n: f'Module {n}')
    description = factory.Faker('paragraph')
    order = factory.Sequence(lambda n: n)
    is_published = False


class ModuleContentFactory(DjangoModelFactory):
    """Factory for creating ModuleContent instances."""

    class Meta:
        model = 'learning.ModuleContent'

    module = factory.SubFactory(EventModuleFactory)
    title = factory.Sequence(lambda n: f'Content {n}')
    content_type = 'text'
    order = factory.Sequence(lambda n: n)


class AssignmentFactory(DjangoModelFactory):
    """Factory for creating Assignment instances."""

    class Meta:
        model = 'learning.Assignment'

    module = factory.SubFactory(EventModuleFactory)
    title = factory.Sequence(lambda n: f'Assignment {n}')
    description = factory.Faker('paragraph')
    max_score = 100


class CourseFactory(DjangoModelFactory):
    """Factory for creating Course instances."""

    class Meta:
        model = 'learning.Course'

    title = factory.Sequence(lambda n: f'Course {n}')
    slug = factory.Sequence(lambda n: f'course-{n}')
    description = factory.Faker('paragraph')
    organization = factory.SubFactory(OrganizationFactory)
    status = 'draft'


class CourseEnrollmentFactory(DjangoModelFactory):
    """Factory for creating CourseEnrollment instances."""

    class Meta:
        model = 'learning.CourseEnrollment'

    course = factory.SubFactory(CourseFactory)
    user = factory.SubFactory(UserFactory)
    status = 'active'
