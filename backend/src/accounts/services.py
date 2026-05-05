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

from django.db import transaction
from django.utils import timezone

from accounts.models import LearningInvitation, User
from accounts.tokens import (
    INVITE_TOKEN_MAX_AGE_SECONDS,
    INVITE_TOKEN_SALT,
    sign_token,
    verify_token,
)
from contacts.models import Contact, ContactList


def sign_invite_token(invitation: LearningInvitation) -> str:
    """URL-safe signed token. Caller embeds in the accept link."""
    return sign_token(INVITE_TOKEN_SALT, str(invitation.uuid), invitation.token)


def verify_invite_token(uuid_str: str, token: str) -> Optional[LearningInvitation]:
    """Returns the invitation iff the signed token resolves to a row whose
    UUID + secret match. Returns None on any signature/age/match failure
    so callers can answer with a uniform 404 (don't leak which invitations
    exist).
    """
    secret = verify_token(INVITE_TOKEN_SALT, INVITE_TOKEN_MAX_AGE_SECONDS, uuid_str, token)
    if secret is None:
        return None
    invitation = LearningInvitation.objects.filter(uuid=uuid_str).first()
    if invitation is None or invitation.token != secret:
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
      - contact_uuid wins when it resolves. We pull the Contact (must
        belong to inviter) and use its email + full_name.
      - contact_uuid does NOT resolve (stale chip, deleted contact, or
        a contact that never existed for this inviter) BUT email is
        also present: fall through to the email path so the invite
        still ships. The frontend always knows the email of every chip
        it constructs, so requiring contact_uuid resolution is over-
        defensive — the worst case is that we auto-add a fresh Contact
        instead of linking to a stale uuid, which is what the email
        path already does.
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
        if contact is not None:
            return contact.email, contact.full_name, contact
        if not email:
            # No fallback available — surface the uuid we couldn't
            # resolve so the operator can chase it instead of seeing a
            # mysterious "<unknown>" row.
            raise ValueError(
                f"Contact {contact_uuid} not found in your address book"
            )
        # Otherwise, fall through to the email path below.

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


# =============================================================================
# Magic links — self-claim + email-link sign-in
# =============================================================================
#
# These are conceptually adjacent to LearningInvitation but structurally
# distinct (no organizer; no comp seat semantic). They share the signed-
# token primitive (different salt) and the verify-by-email-and-secret
# pattern. See accounts/tokens.py and accounts/models.MagicLink for shape.


from accounts.models import MagicLink  # noqa: E402  (intentional late import to avoid circulars during app init)
from accounts.tokens import (  # noqa: E402
    MAGIC_LINK_CLAIM_MAX_AGE_SECONDS,
    MAGIC_LINK_SALT,
    MAGIC_LINK_SIGN_IN_MAX_AGE_SECONDS,
)


@dataclass
class MagicLinkAcceptResult:
    """Returned from accept_registration_claim / accept_sign_in.

    The view layer maps this to a JWT-issuing response identical in shape
    to EmailVerificationView's success payload.
    """

    user: User
    redirect_url: str
    purpose: str


def sign_magic_link_token(link: MagicLink) -> str:
    """URL-safe signed token. Caller embeds in the email link."""
    return sign_token(MAGIC_LINK_SALT, str(link.uuid), link.token)


def _magic_link_max_age(purpose: str) -> int:
    if purpose == MagicLink.Purpose.REGISTRATION_CLAIM:
        return MAGIC_LINK_CLAIM_MAX_AGE_SECONDS
    return MAGIC_LINK_SIGN_IN_MAX_AGE_SECONDS


def verify_magic_link_token(uuid_str: str, token: str) -> Optional[MagicLink]:
    """Returns the MagicLink iff signature, age, uuid, and stored secret all match.

    The signer's max_age is purpose-aware: we look up the row first to get
    its purpose, then apply the right window. Returning None on any
    failure lets callers answer with a uniform 404.
    """
    link = MagicLink.objects.filter(uuid=uuid_str).first()
    if link is None:
        return None
    secret = verify_token(MAGIC_LINK_SALT, _magic_link_max_age(link.purpose), uuid_str, token)
    if secret is None or link.token != secret:
        return None
    return link


# --- Creation -----------------------------------------------------------------


def create_registration_claim(registration) -> MagicLink:
    """Idempotently create a CLAIM magic link for a registration.

    If a pending CLAIM already exists for this registration, refresh its
    `expires_at` and `last_sent_at` and bump `send_count` rather than
    duplicating. The unique constraint
    ``one_pending_claim_per_registration`` enforces no-dupes at the DB
    level so concurrent webhook retries collapse safely.
    """
    now = timezone.now()
    expires = now + timezone.timedelta(seconds=MAGIC_LINK_CLAIM_MAX_AGE_SECONDS)

    existing = MagicLink.objects.filter(
        registration=registration,
        purpose=MagicLink.Purpose.REGISTRATION_CLAIM,
        status=MagicLink.Status.PENDING,
    ).first()
    if existing:
        existing.expires_at = expires
        existing.last_sent_at = now
        existing.send_count = existing.send_count + 1
        existing.save(update_fields=['expires_at', 'last_sent_at', 'send_count', 'updated_at'])
        return existing

    return MagicLink.objects.create(
        purpose=MagicLink.Purpose.REGISTRATION_CLAIM,
        email=registration.email,
        token=MagicLink.generate_token(),
        expires_at=expires,
        registration=registration,
        last_sent_at=now,
        send_count=1,
    )


def create_sign_in_link(email: str) -> Optional[MagicLink]:
    """Create a SIGN_IN magic link for a known user.

    Returns ``None`` if no User exists for ``email`` (anti-enumeration:
    the caller's response must be the same regardless). The 30-minute
    expiry reflects that a sign-in link is a fresh authentication
    challenge; we don't keep these around.
    """
    email_lc = (email or '').strip().lower()
    if not email_lc:
        return None
    user = User.objects.filter(email__iexact=email_lc).first()
    if user is None:
        return None

    now = timezone.now()
    return MagicLink.objects.create(
        purpose=MagicLink.Purpose.SIGN_IN,
        email=user.email,
        token=MagicLink.generate_token(),
        expires_at=now + timezone.timedelta(seconds=MAGIC_LINK_SIGN_IN_MAX_AGE_SECONDS),
        last_sent_at=now,
        send_count=1,
    )


# --- Acceptance ---------------------------------------------------------------


def _create_or_link_user_for_claim(email: str, password: str, full_name_fallback: str = '') -> User:
    """Find or create a user for a registration claim.

    - User exists: set/replace password (the magic link IS proof of email
      ownership; treating it as a single-use credential is safe and
      matches the user's expectation of "set a password to access my
      registration"). Marks email_verified=True if not already.
    - User missing: create with email_verified=True. Pull the freshest
      name from any matching guest registration to seed the profile.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        # Profile bootstrap from a matching guest registration if any.
        from registrations.models import Registration
        full_name = (
            full_name_fallback
            or (Registration.objects.filter(email__iexact=email, user__isnull=True)
                                    .order_by('-created_at')
                                    .values_list('full_name', flat=True)
                                    .first())
            or email
        )
        user = User.objects.create_user(
            email=email.lower(),
            password=password,
            full_name=full_name,
            email_verified=True,
            email_verified_at=timezone.now(),
        )
        return user

    # Existing user: rotate password + ensure verified flag.
    user.set_password(password)
    fields = ['password', 'updated_at']
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = timezone.now()
        fields += ['email_verified', 'email_verified_at']
    user.save(update_fields=fields)
    return user


@transaction.atomic
def accept_registration_claim(link: MagicLink, password: str) -> MagicLinkAcceptResult:
    """Accept a CLAIM link. Sets password, links registrations, returns result.

    Idempotency: re-entering with an already-accepted link returns the
    existing user + redirect URL (the caller layer guards on status).
    """
    if link.purpose != MagicLink.Purpose.REGISTRATION_CLAIM:
        raise ValueError("accept_registration_claim called for non-claim link")

    from registrations.models import Registration

    user = _create_or_link_user_for_claim(
        email=link.email,
        password=password,
        full_name_fallback=(
            link.registration.full_name if link.registration_id and link.registration else ''
        ),
    )

    # Sweep all guest registrations matching this email into the user.
    Registration.link_registrations_for_user(user)

    # Back-fill any anonymous purchase rows that ride along with the
    # registrations we just linked. Keeps "My Purchases" consistent.
    from billing.models import CoursePurchase
    CoursePurchase.link_for_user(user)

    link.mark_accepted(user)
    redirect_url = _redirect_url_for_claim(link)
    return MagicLinkAcceptResult(
        user=user,
        redirect_url=redirect_url,
        purpose=link.purpose,
    )


@transaction.atomic
def accept_sign_in(link: MagicLink) -> MagicLinkAcceptResult:
    """Accept a SIGN_IN link. Pure auth — no password mutation."""
    if link.purpose != MagicLink.Purpose.SIGN_IN:
        raise ValueError("accept_sign_in called for non-sign-in link")

    user = User.objects.filter(email__iexact=link.email).first()
    if user is None:
        # Defensive: shouldn't happen because create_sign_in_link only
        # issues for existing users, but a delete in the interim could
        # leave a stranded link.
        raise ValueError("No user for sign-in link")

    # Defensive sweep — covers an edge case where a guest registration
    # was created between sign-in-link issuance and click.
    from registrations.models import Registration
    Registration.link_registrations_for_user(user)

    link.mark_accepted(user)
    return MagicLinkAcceptResult(
        user=user,
        redirect_url='/',  # frontend overrides via state passed at issue time
        purpose=link.purpose,
    )


def reissue_claims_for_email(email: str) -> int:
    """Re-issue (or refresh) CLAIM links for every guest registration matching ``email``.

    Used by:
      - the public find-my-registration endpoint (user lost their email)
      - the admin re-issue tool (support flow for typo emails)

    Returns the number of links queued for send. Caller decides what
    response to surface — both call sites return an anti-enumeration
    response that doesn't depend on this count.
    """
    from registrations.models import Registration
    from accounts.tasks import send_magic_link_email

    email_lc = (email or '').strip().lower()
    if not email_lc:
        return 0

    # Only registrations that aren't yet linked to a user have a claim
    # surface. Linked accounts go through /login or sign-in-link instead.
    registrations = Registration.objects.filter(
        email__iexact=email_lc,
        user__isnull=True,
        deleted_at__isnull=True,
    )
    queued = 0
    for reg in registrations:
        link = create_registration_claim(reg)
        send_magic_link_email(link.id)
        queued += 1
    return queued


def _redirect_url_for_claim(link: MagicLink) -> str:
    """Where to send the user after a successful claim accept.

    Best path: the linked registration's event details page.
    Fallback: the registrations dashboard.
    """
    if link.registration_id and link.registration:
        event = getattr(link.registration, 'event', None)
        if event is not None:
            slug_or_uuid = getattr(event, 'slug', None) or str(event.uuid)
            return f"/events/{slug_or_uuid}/details"
    return '/registrations'
