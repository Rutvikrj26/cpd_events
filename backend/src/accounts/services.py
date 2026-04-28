"""
Accounts app services.

Encapsulates the multi-model orchestration for inviting learners to events
and courses. The view layer stays thin; here we own:

    - resolving each invitee row (contact_uuid OR email) into a canonical
      (email, full_name, contact) triple
    - upserting a Contact under the inviter's personal ContactList when
      the invitee is a brand-new email (auto-add per the locked plan)
    - creating or refreshing a single PENDING LearningInvitation per
      (target, email)
    - queuing the invitation email send

Accept-time orchestration (creating the Registration / CourseEnrollment)
also lives here so the public view doesn't need to know the multi-app
plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone

from accounts.models import LearningInvitation, User
from contacts.models import Contact, ContactList


# Tokens use Django's TimestampSigner with a salt scoped to this feature.
# Verifying on accept means a leaked DB column doesn't yield valid links —
# same pattern the recording stream view uses.
INVITE_TOKEN_SALT = 'learning-invitation'
# Tokens stay valid for 30 days from issue (matches the row's expires_at
# default). The signer's max_age is the upper bound; the row's expires_at
# is the authoritative gate the view checks.
INVITE_TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def sign_invite_token(invitation: LearningInvitation) -> str:
    """Returns a URL-safe signed token. Caller embeds in the accept link."""
    signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
    return signer.sign(f"{invitation.uuid}:{invitation.token}")


def verify_invite_token(uuid_str: str, token: str) -> Optional[LearningInvitation]:
    """Returns the invitation iff the signed token resolves to a row whose
    UUID + secret match. Returns None on any signature/age/match failure
    so callers can answer with a uniform 404 (don't leak which invitations
    exist).
    """
    signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
    try:
        unsigned = signer.unsign(token, max_age=INVITE_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    try:
        signed_uuid, signed_secret = unsigned.split(':', 1)
    except ValueError:
        return None
    if signed_uuid != str(uuid_str):
        return None
    invitation = LearningInvitation.objects.filter(uuid=uuid_str).first()
    if invitation is None or invitation.token != signed_secret:
        return None
    return invitation


# =============================================================================
# Invite creation
# =============================================================================


@dataclass
class InviteResult:
    """One row of the bulk-invite response."""

    email: str
    invitation_uuid: Optional[str] = None
    status: Literal['created', 'refreshed', 'already_registered', 'invalid_email', 'error'] = 'created'
    reason: str = ''


@dataclass
class InviteBatchResult:
    created: list[InviteResult]
    refreshed: list[InviteResult]
    skipped: list[InviteResult]


def _resolve_invitee(
    *,
    inviter: User,
    contact_uuid: Optional[str],
    email: Optional[str],
    full_name: str,
) -> tuple[str, str, Optional[Contact]]:
    """Normalize one invitee row to (email, full_name, contact|None).

    Resolution rules:
      - contact_uuid wins. We pull the Contact (must belong to inviter)
        and use its email + full_name.
      - email-only: lower-cased and matched against the inviter's
        Contacts; if found, link it. Otherwise auto-create a Contact
        in the inviter's personal list (per the locked plan).
    """
    if contact_uuid:
        contact = (
            Contact.objects
            .filter(uuid=contact_uuid, contact_list__owner=inviter)
            .select_related('contact_list')
            .first()
        )
        if contact is None:
            raise ValueError("Contact not found in your address book")
        return contact.email, contact.full_name, contact

    assert email, "validate() should have ensured one of the two is set"
    email_lc = email.strip().lower()

    contact_list = ContactList.get_or_create_for_user(inviter)
    contact = Contact.objects.filter(contact_list=contact_list, email=email_lc).first()
    if contact is None:
        # Auto-add to inviter's contacts. `source='invite'` marks the
        # provenance so an organizer can later filter / clean these up
        # if they don't want one-offs in their address book.
        contact = Contact.objects.create(
            contact_list=contact_list,
            email=email_lc,
            full_name=full_name or '',
            source='invite',
        )
    elif full_name and not contact.full_name:
        # Backfill name from the invite payload if we didn't have one.
        contact.full_name = full_name
        contact.save(update_fields=['full_name', 'updated_at'])
    return contact.email, contact.full_name, contact


def _existing_registration_email_set(target_type: str, target) -> set[str]:
    """Lower-cased emails that already have a CONFIRMED/PENDING registration
    (event) or active enrollment (course). Used to skip re-inviting people
    who already have access."""
    if target_type == LearningInvitation.TargetType.EVENT:
        from registrations.models import Registration
        qs = Registration.objects.filter(
            event=target, deleted_at__isnull=True,
        ).exclude(status=Registration.Status.CANCELLED).values_list('email', flat=True)
    else:
        from learning.models import CourseEnrollment
        # Existing linked-user enrollments + guest invitation rows both
        # count as "already-has-access" for re-invite suppression.
        linked = CourseEnrollment.objects.filter(course=target, user__isnull=False).values_list('user__email', flat=True)
        guest = CourseEnrollment.objects.filter(course=target, user__isnull=True).values_list('invitation_email', flat=True)
        qs = list(linked) + [e for e in guest if e]
    return {e.lower() for e in qs if e}


@transaction.atomic
def create_invitations(
    *,
    inviter: User,
    target_type: str,
    target,
    invitees: Iterable[dict],
    personal_message: str = '',
    comp: bool = False,
) -> InviteBatchResult:
    """Create or refresh invitations for the given target.

    Idempotency:
      - PENDING invite for the same (target, email) → bump send_count and
        last_sent_at, refresh the personal_message and comp flag, and
        re-fire the email. Returns `refreshed`.
      - Already registered/enrolled → skipped with reason `already_registered`.
      - Brand new → created and email queued. Returns `created`.

    The actual email send is delegated to a Celery task to keep this
    function fast even for batches up to 100.
    """
    if target_type not in {LearningInvitation.TargetType.EVENT, LearningInvitation.TargetType.COURSE}:
        raise ValueError(f"Unknown target_type: {target_type}")

    blocked = _existing_registration_email_set(target_type, target)

    created: list[InviteResult] = []
    refreshed: list[InviteResult] = []
    skipped: list[InviteResult] = []
    seen_emails: set[str] = set()

    target_kwargs = (
        {'event': target} if target_type == LearningInvitation.TargetType.EVENT
        else {'course': target}
    )

    for raw in invitees:
        contact_uuid = raw.get('contact_uuid')
        email = raw.get('email')
        full_name = (raw.get('full_name') or '').strip()
        try:
            email_lc, resolved_name, contact = _resolve_invitee(
                inviter=inviter,
                contact_uuid=contact_uuid,
                email=email,
                full_name=full_name,
            )
        except ValueError as exc:
            skipped.append(InviteResult(
                email=email or '<unknown>',
                status='invalid_email',
                reason=str(exc),
            ))
            continue

        # Dedupe within the batch — a paste-many input can repeat the
        # same address; we only want one row per email.
        if email_lc in seen_emails:
            continue
        seen_emails.add(email_lc)

        if email_lc in blocked:
            skipped.append(InviteResult(
                email=email_lc,
                status='already_registered',
                reason='Already has access to this target',
            ))
            continue

        # Look for an existing PENDING invite to refresh (idempotent
        # re-send). Accepted/cancelled/expired rows DON'T block — we
        # create a fresh row.
        existing = LearningInvitation.objects.filter(
            status=LearningInvitation.Status.PENDING,
            email=email_lc,
            **target_kwargs,
        ).first()

        now = timezone.now()
        expires_default = now + timezone.timedelta(seconds=INVITE_TOKEN_MAX_AGE_SECONDS)

        if existing:
            existing.full_name = resolved_name or existing.full_name
            existing.contact = contact
            existing.personal_message = personal_message
            existing.comp = comp
            existing.send_count = existing.send_count + 1
            existing.last_sent_at = now
            existing.expires_at = expires_default  # extend the window on resend
            existing.save(update_fields=[
                'full_name', 'contact', 'personal_message', 'comp',
                'send_count', 'last_sent_at', 'expires_at', 'updated_at',
            ])
            _queue_invitation_email(existing.id)
            refreshed.append(InviteResult(
                email=email_lc,
                invitation_uuid=str(existing.uuid),
                status='refreshed',
            ))
            continue

        invitation = LearningInvitation.objects.create(
            target_type=target_type,
            email=email_lc,
            full_name=resolved_name,
            contact=contact,
            invited_by=inviter,
            personal_message=personal_message,
            comp=comp,
            token=LearningInvitation.generate_token(),
            expires_at=expires_default,
            send_count=1,
            last_sent_at=now,
            **target_kwargs,
        )
        _queue_invitation_email(invitation.id)
        created.append(InviteResult(
            email=email_lc,
            invitation_uuid=str(invitation.uuid),
            status='created',
        ))

    return InviteBatchResult(created=created, refreshed=refreshed, skipped=skipped)


def _queue_invitation_email(invitation_id: int) -> None:
    """Queue the Celery task — wrapped so tests can mock it cleanly."""
    from accounts.tasks import send_invitation_email
    send_invitation_email(invitation_id)


# =============================================================================
# Accept
# =============================================================================


@dataclass
class AcceptResult:
    """Return value from accept_invitation_for_user."""

    redirect_url: str
    target_type: str
    target_uuid: str


@transaction.atomic
def accept_invitation_for_user(invitation: LearningInvitation, user: User) -> AcceptResult:
    """Idempotently accept an invitation for the authenticated user.

    Caller MUST have already verified that user.email matches
    invitation.email — that's a 409-worthy mismatch handled at the view
    layer so we can give the user a "switch account" hint.

    - Event target → upsert a Registration. Comp invites land as
      CONFIRMED + payment_status=NA + was_comped=True. Non-comp invites
      preserve existing semantics: free events go straight to CONFIRMED;
      paid events land as PENDING with payment_status=PENDING and rely
      on the existing Stripe checkout flow when the user navigates to
      the event page.
    - Course target → upsert a CourseEnrollment. If a guest enrollment
      already exists for this email (created earlier by a different
      flow), it gets linked to the user.
    """
    if invitation.target_type == LearningInvitation.TargetType.EVENT:
        registration = _accept_event_invitation(invitation, user)
        target_uuid = str(invitation.event.uuid)
        slug_or_uuid = invitation.event.slug or target_uuid
        redirect_url = f"/events/{slug_or_uuid}/details"
        # Mark the contact's engagement bump so the address book stays useful.
        if invitation.contact_id:
            invitation.contact.record_invite()
        invitation.mark_accepted(user)
        return AcceptResult(redirect_url=redirect_url, target_type='event', target_uuid=target_uuid)

    enrollment = _accept_course_invitation(invitation, user)
    target_uuid = str(invitation.course.uuid)
    redirect_url = f"/learn/{target_uuid}"
    if invitation.contact_id:
        invitation.contact.record_invite()
    invitation.mark_accepted(user)
    return AcceptResult(redirect_url=redirect_url, target_type='course', target_uuid=target_uuid)


def _accept_event_invitation(invitation: LearningInvitation, user: User):
    from registrations.models import Registration
    event = invitation.event

    is_paid = float(event.price or 0) > 0
    comp = invitation.comp and is_paid

    existing = Registration.objects.filter(event=event, email__iexact=invitation.email).first()
    if existing:
        if existing.user_id is None:
            existing.user = user
        if existing.status == Registration.Status.CANCELLED:
            existing.status = Registration.Status.CONFIRMED if (not is_paid or comp) else Registration.Status.PENDING
            existing.cancelled_at = None
        if comp:
            existing.was_comped = True
            existing.comped_by = invitation.invited_by
            existing.payment_status = Registration.PaymentStatus.NA
            existing.status = Registration.Status.CONFIRMED
        existing.source = Registration.Source.INVITE
        existing.save()
        return existing

    return Registration.objects.create(
        event=event,
        user=user,
        email=invitation.email,
        full_name=invitation.full_name or user.full_name or user.email,
        registered_by=invitation.invited_by,
        source=Registration.Source.INVITE,
        status=(
            Registration.Status.CONFIRMED if (not is_paid or comp) else Registration.Status.PENDING
        ),
        payment_status=(
            Registration.PaymentStatus.NA if (not is_paid or comp) else Registration.PaymentStatus.PENDING
        ),
        was_comped=comp,
        comped_by=invitation.invited_by if comp else None,
    )


def _accept_course_invitation(invitation: LearningInvitation, user: User):
    from learning.models import CourseEnrollment
    course = invitation.course

    is_paid = float(getattr(course, 'price', 0) or 0) > 0
    comp = invitation.comp and is_paid

    enrollment = CourseEnrollment.objects.filter(course=course, user=user).first()
    if enrollment:
        if comp:
            enrollment.was_comped = True
            enrollment.comped_by = invitation.invited_by
            enrollment.save(update_fields=['was_comped', 'comped_by', 'updated_at'])
        return enrollment

    guest = CourseEnrollment.objects.filter(
        course=course, user__isnull=True, invitation_email__iexact=invitation.email,
    ).first()
    if guest:
        guest.user = user
        guest.invitation_email = None
        if comp:
            guest.was_comped = True
            guest.comped_by = invitation.invited_by
        guest.save()
        return guest

    return CourseEnrollment.objects.create(
        course=course,
        user=user,
        status=CourseEnrollment.Status.ACTIVE,
        was_comped=comp,
        comped_by=invitation.invited_by if comp else None,
    )
