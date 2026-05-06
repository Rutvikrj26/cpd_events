import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from common.utils import generate_unique_slug
from events.models import Event, EventCustomField

logger = logging.getLogger(__name__)


# =============================================================================
# Reminder lifecycle helpers
# =============================================================================
#
# These manage ScheduledEmail rows for event reminders, keyed by the unique
# constraint (event, recipient_email, template_key, send_at) on ScheduledEmail.
# All helpers are idempotent — safe to call from retried registration flows
# and reschedule signals.


def _is_zoom_event(event: Event) -> bool:
    """True iff the event's active VideoRoom is provisioned on Zoom.

    Used to short-circuit reminder + .ics paths — Zoom owns those for
    Zoom-provider events. Cheap query (single row by content_type +
    object_id index, exclude ENDED).
    """
    from django.contrib.contenttypes.models import ContentType
    from conferencing.models import VideoRoom

    try:
        ct = ContentType.objects.get_for_model(Event)
    except Exception:
        return False
    return (
        VideoRoom.objects.filter(content_type=ct, object_id=event.id, provider='zoom')
        .exclude(status=VideoRoom.Status.ENDED)
        .exists()
    )


def build_event_join_url(event: Event, registration=None) -> str:
    """Return the frontend lobby URL for an event/registration.

    Authenticated users → /events/<uuid>/lobby
    Guest registrations (no User) → /r/<registration_uuid>/lobby
    """
    base = (getattr(settings, 'FRONTEND_URL', '') or '').rstrip('/')
    if registration is not None and getattr(registration, 'user_id', None) is None:
        return f"{base}/r/{registration.uuid}/lobby"
    return f"{base}/events/{event.uuid}/lobby"


def _reminder_batch_key(event: Event, registration=None) -> str:
    if registration is not None:
        return f"reminder:{event.id}:{registration.id}"
    return f"reminder:{event.id}"


def _reminder_context(event: Event, registration) -> dict:
    from integrations.calendar import google_calendar_url, outlook_calendar_url

    join = build_event_join_url(event, registration)
    description = (event.short_description or event.description or '')[:500]
    if join:
        description = f"{description}\n\nJoin: {join}".strip()

    return {
        'user_name': registration.full_name or registration.email,
        'event_title': event.title,
        'event_uuid': str(event.uuid),
        'event_date': event.starts_at.strftime('%B %d, %Y at %I:%M %p'),
        'event_timezone': event.timezone,
        'starts_at_iso': event.starts_at.isoformat(),
        'duration_minutes': event.duration_minutes,
        'join_url': join,
        'add_to_google_url': google_calendar_url(
            summary=event.title,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            description=description,
            location=event.location or join,
        ),
        'add_to_outlook_url': outlook_calendar_url(
            summary=event.title,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            description=description,
            location=event.location or join,
        ),
    }


def enqueue_event_reminders(registration) -> int:
    """Idempotently enqueue ScheduledEmail rows for each reminder offset.

    Skips offsets that are already in the past relative to `now`. Skips
    entirely when the event runs on Zoom (Zoom owns reminder cadence
    via per-meeting registration settings). Returns the number of rows
    that ended up PENDING after the operation (created or pre-existing).
    """
    from integrations.models import ScheduledEmail
    from integrations.services import email_service

    event = registration.event
    if event.status not in (Event.Status.PUBLISHED, Event.Status.LIVE):
        logger.debug("enqueue_event_reminders: event %s not in published/live state", event.id)
        return 0

    # Zoom-provider events: Zoom emails registrants reminders directly
    # (configured per-meeting at create time). Suppressing here avoids
    # duplicate "your event is starting soon" emails from accredit + Zoom.
    if _is_zoom_event(event):
        logger.debug(
            "enqueue_event_reminders: event %s is on Zoom; reminders owned by Zoom — skipping",
            event.id,
        )
        return 0

    now = timezone.now()
    offsets = event.effective_reminder_offsets_minutes
    template_key = 'event_reminder'
    subject_template = email_service.SUBJECTS.get(template_key, 'Reminder: {event_title}')
    context = _reminder_context(event, registration)
    try:
        subject = subject_template.format(**context)
    except (KeyError, IndexError):
        subject = subject_template

    rows = 0
    for offset in offsets:
        send_at = event.starts_at - timezone.timedelta(minutes=int(offset))
        if send_at <= now:
            # Past offset — skip rather than send retroactive reminders.
            continue
        ScheduledEmail.objects.update_or_create(
            event=event,
            recipient_email=registration.email,
            template_key=template_key,
            send_at=send_at,
            defaults={
                'recipient_name': registration.full_name,
                'recipient_user': registration.user,
                'subject': subject,
                'context': {**context, 'offset_minutes': int(offset)},
                'registration': registration,
                'batch_key': _reminder_batch_key(event, registration),
                'status': ScheduledEmail.Status.PENDING,
            },
        )
        rows += 1
    logger.info("Enqueued %s reminders for registration %s on event %s", rows, registration.id, event.id)
    return rows


def cancel_event_reminders(*, event=None, registration=None, reason: str = '') -> int:
    """Cancel pending ScheduledEmail reminders for an event or single registration."""
    from integrations.models import ScheduledEmail

    qs = ScheduledEmail.objects.filter(
        template_key='event_reminder', status=ScheduledEmail.Status.PENDING
    )
    if registration is not None:
        qs = qs.filter(registration=registration)
    elif event is not None:
        qs = qs.filter(event=event)
    else:
        return 0

    return qs.update(
        status=ScheduledEmail.Status.CANCELLED,
        error_message=reason or 'cancelled',
    )


def reschedule_event_reminders(event: Event) -> int:
    """Cancel and re-enqueue reminders for every confirmed registration on the event."""
    from registrations.models import Registration

    cancel_event_reminders(event=event, reason='event_rescheduled')

    confirmed = Registration.objects.filter(
        event=event,
        status=Registration.Status.CONFIRMED,
        deleted_at__isnull=True,
    )
    total = 0
    for reg in confirmed.iterator():
        total += enqueue_event_reminders(reg)
    logger.info("Rescheduled reminders for event %s (%s rows enqueued)", event.id, total)
    return total


# =============================================================================
# Calendar (.ics) generation for events
# =============================================================================


def build_event_ics(event: Event, attendee_email: str = '', attendee_name: str = '') -> str:
    """Build an RFC 5545 VCALENDAR string for an event.

    METHOD is CANCEL when the event is cancelled (so calendar clients remove
    the entry), PUBLISH otherwise. SEQUENCE bumps to 1 for cancellations so
    Google/Outlook recognize it as an update.
    """
    from integrations.calendar import build_vevent_lines, ics_calendar

    domain = getattr(settings, 'ICS_UID_DOMAIN', 'accredit.app')
    uid = f"event-{event.uuid}@{domain}"

    cancelled = event.status == Event.Status.CANCELLED
    method = 'CANCEL' if cancelled else 'PUBLISH'

    organizer = event.owner if event.owner_id else None
    organizer_email = getattr(organizer, 'email', '') or ''
    organizer_name = getattr(organizer, 'full_name', '') or ''

    description_parts = []
    if event.short_description:
        description_parts.append(event.short_description)
    elif event.description:
        description_parts.append(event.description[:1000])
    join_url = build_event_join_url(event, registration=None)
    if join_url:
        description_parts.append(f"Join: {join_url}")
    description = '\n\n'.join(description_parts)

    location = event.location or join_url

    vevent = build_vevent_lines(
        uid=uid,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        summary=event.title,
        description=description,
        location=location,
        url=join_url,
        organizer_name=organizer_name,
        organizer_email=organizer_email,
        attendee_name=attendee_name,
        attendee_email=attendee_email,
        cancelled=cancelled,
    )

    return ics_calendar(
        prodid='-//Accredit//Event//EN',
        method=method,
        events=[vevent],
    )


class EventService:
    """Service for managing Events. Handles creation and update orchestration."""

    @staticmethod
    def create_event(user, data: dict[str, Any]) -> Event:
        """Create a new event with default custom + feedback fields."""
        # Pop custom fields to handle separately
        custom_fields_data = data.pop('custom_fields', [])
        speakers_data = data.pop('speakers', None)

        # Generate unique slug if not present
        if 'slug' not in data:
            title = data.get('title', '')
            base_slug = slugify(title)[:40]
            data['slug'] = generate_unique_slug(Event, base_slug)

        with transaction.atomic():
            event = Event.objects.create(owner=user, **data)

            for position, field_data in enumerate(custom_fields_data):
                field_data['position'] = position
                EventCustomField.objects.create(event=event, **field_data)

            # Seed the default feedback form — admins can edit/remove afterwards.
            from feedback.models import FeedbackField

            default_feedback_fields = [
                ('Overall rating', 'rating', True, 0, 1, 5),
                ('Content quality', 'rating', True, 1, 1, 5),
                ('Speaker rating', 'rating', True, 2, 1, 5),
                ('Comments', 'textarea', False, 3, None, None),
            ]
            for label, ftype, required, order, mn, mx in default_feedback_fields:
                FeedbackField.objects.create(
                    event=event,
                    label=label,
                    field_type=ftype,
                    required=required,
                    order=order,
                    min_value=mn,
                    max_value=mx,
                )

            if speakers_data:
                event.speakers.set(speakers_data)

        logger.info("Event created: %s", event.uuid)
        return event


# Singleton instance
event_service = EventService()
