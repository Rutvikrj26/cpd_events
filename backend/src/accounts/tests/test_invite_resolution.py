"""Tests for `_resolve_invitee` fallback behavior.

Regression: when the frontend sends a `contact_uuid` that no longer
resolves to a Contact in the inviter's address book (stale chip,
contact deleted between dialog open and submit, cross-tenant uuid),
the resolver should fall back to the `email` field if it's present
rather than dropping the row with a `<unknown>: Contact not found in
your address book` error.
"""

from __future__ import annotations

import uuid as uuid_lib

import pytest

from accounts.models import LearningInvitation
from accounts.services import create_invitations
from contacts.models import Contact, ContactList


@pytest.fixture
def organizer_contact(db, organizer):
    """A Contact in the organizer's personal list (a.k.a. address book)."""
    contact_list = ContactList.get_or_create_for_user(organizer)
    return Contact.objects.create(
        contact_list=contact_list,
        email='picked@example.com',
        full_name='Picked Contact',
    )


@pytest.mark.django_db
class TestResolveInviteeFallback:
    def _invite(self, organizer, event, invitees):
        return create_invitations(
            inviter=organizer,
            target_type=LearningInvitation.TargetType.EVENT,
            target=event,
            invitees=invitees,
            personal_message='',
            comp=False,
        )

    def test_valid_contact_uuid_only_still_works(
        self, organizer, published_event, organizer_contact, monkeypatch,
    ):
        """The org-initiated invite path (contact_uuid only, no email) must
        not regress. This is what the typeahead picker has always sent."""
        monkeypatch.setattr(
            'accounts.services._queue_invitation_email', lambda _id: None,
        )
        result = self._invite(
            organizer,
            published_event,
            [{'contact_uuid': str(organizer_contact.uuid)}],
        )
        assert len(result.created) == 1
        assert result.created[0].email == 'picked@example.com'
        assert not result.skipped

    def test_stale_contact_uuid_with_email_falls_through(
        self, organizer, published_event, monkeypatch,
    ):
        """contact_uuid points to a row that does NOT exist for this
        inviter, but the payload also carries an email — we fall back
        to the email path (auto-create a Contact and send the invite)
        instead of failing."""
        monkeypatch.setattr(
            'accounts.services._queue_invitation_email', lambda _id: None,
        )
        bogus_uuid = str(uuid_lib.uuid4())
        result = self._invite(
            organizer,
            published_event,
            [{
                'contact_uuid': bogus_uuid,
                'email': 'fallback@example.com',
                'full_name': 'Fallback User',
            }],
        )
        assert len(result.created) == 1, result
        assert result.created[0].email == 'fallback@example.com'
        # The auto-created Contact is in the organizer's list with
        # source='invite' (the email-path provenance).
        contact = Contact.objects.get(
            contact_list__owner=organizer, email='fallback@example.com',
        )
        assert contact.source == 'invite'
        assert contact.full_name == 'Fallback User'

    def test_cross_tenant_contact_uuid_with_email_falls_through(
        self, organizer, other_organizer, published_event, monkeypatch,
    ):
        """A contact_uuid that exists but belongs to a DIFFERENT inviter
        must not be honoured — but with email present we still ship the
        invite under this inviter's address book."""
        monkeypatch.setattr(
            'accounts.services._queue_invitation_email', lambda _id: None,
        )
        other_list = ContactList.get_or_create_for_user(other_organizer)
        cross_tenant = Contact.objects.create(
            contact_list=other_list,
            email='cross@example.com',
            full_name='Cross Tenant',
        )
        result = self._invite(
            organizer,
            published_event,
            [{
                'contact_uuid': str(cross_tenant.uuid),
                'email': 'cross@example.com',
                'full_name': 'Cross Tenant',
            }],
        )
        assert len(result.created) == 1
        assert result.created[0].email == 'cross@example.com'
        # The contact landed in *organizer*'s list (not other's).
        Contact.objects.get(
            contact_list__owner=organizer, email='cross@example.com',
        )

    def test_bogus_contact_uuid_with_no_email_surfaces_uuid(
        self, organizer, published_event, monkeypatch,
    ):
        """When neither lookup nor fallback can succeed, the error
        message should at least include the contact_uuid that was
        rejected — no more `<unknown>: Contact not found`."""
        monkeypatch.setattr(
            'accounts.services._queue_invitation_email', lambda _id: None,
        )
        bogus_uuid = str(uuid_lib.uuid4())
        result = self._invite(
            organizer,
            published_event,
            [{'contact_uuid': bogus_uuid}],
        )
        assert not result.created
        assert len(result.skipped) == 1
        skipped = result.skipped[0]
        assert skipped.status == 'invalid_email'
        assert bogus_uuid in skipped.reason
        assert skipped.email == '<unknown>'
