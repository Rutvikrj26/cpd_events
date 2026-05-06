"""Zoom-model meeting endpoints — start / join / end / active.

Replaces the old ``JoinVideoView`` family. Three properties drive the
shape of this module:

  1. **Each meeting session is its own VideoRoom row.** No reopen. The
     host calls ``POST /…/meetings/start/`` to create a fresh row.
  2. **Only the host starts.** Attendees call ``POST /…/meetings/join/``
     which 409s when no room is active. They use ``GET /…/meetings/active/``
     (polled every 10s by the lobby) to know when to enable the join
     button.
  3. **One active room per content object at a time.** Enforced at the
     DB layer by a partial unique index on ``VideoRoom``. The
     ``_start_meeting`` helper also takes ``SELECT FOR UPDATE`` on the
     parent Event/CourseSession so concurrent host clicks serialize
     cleanly — first-click-wins, others rejoin the existing room.

Both Event and CourseSession use this module via thin view classes;
the access-control predicates differ (``is_event_host`` vs
``is_course_session_host``) but the meeting machinery is identical.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings as django_settings
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from conferencing.models import (
    VideoRecording,
    VideoRoom,
    generate_room_name,
)
from conferencing.serializers import JoinVideoResponseSerializer
from conferencing.service import get_video_provider
from conferencing.views import (
    is_course_session_host,
    is_event_host,
    is_platform_admin,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers — provider-agnostic meeting machinery
# ---------------------------------------------------------------------------

# A room counts as "the current meeting" while it's SCHEDULED (provisioned
# but no participants yet) or ACTIVE (room_started has fired). ENDED and
# ERROR are terminal — the next start creates a new row.
_LIVE_STATUSES = (VideoRoom.Status.SCHEDULED, VideoRoom.Status.ACTIVE)


def _get_live_room(content_object) -> Optional[VideoRoom]:
    """Return the single SCHEDULED-or-ACTIVE VideoRoom for a content
    object, or None. Used by start/join/end which only care about
    actionable rooms.
    """
    ct = ContentType.objects.get_for_model(content_object)
    return (
        VideoRoom.objects
        .filter(
            content_type=ct,
            object_id=content_object.id,
            status__in=_LIVE_STATUSES,
        )
        .order_by('-created_at')
        .first()
    )


def _get_latest_room(content_object) -> Optional[VideoRoom]:
    """Return the most recent VideoRoom of ANY status for a content
    object. Used by the active/lobby endpoint, which needs to surface
    `ended` so the lobby can render "Meeting has ended" / "Start a
    new meeting" instead of falling back to "Start meeting" copy
    that suggests no session has happened yet.
    """
    ct = ContentType.objects.get_for_model(content_object)
    return (
        VideoRoom.objects
        .filter(content_type=ct, object_id=content_object.id)
        .order_by('-created_at')
        .first()
    )


def _build_join_response(
    *,
    video_room: VideoRoom,
    user_identity: str,
    user_display_name: str,
    is_host: bool,
    waiting_room_enabled: bool,
    recording_default: bool,
) -> dict:
    """Issue a LiveKit JWT and return the wire shape the frontend expects."""
    waiting = waiting_room_enabled and not is_host
    provider = get_video_provider()
    token = provider.generate_join_token(
        room_name=video_room.room_name,
        participant_identity=user_identity,
        participant_name=user_display_name,
        is_host=is_host,
        waiting=waiting,
    )
    recording_active = VideoRecording.objects.filter(
        video_room=video_room,
        status=VideoRecording.Status.RECORDING,
    ).exists()
    return {
        'token': token,
        # Provider-agnostic. LiveKit returns the WS URL for SDK connect;
        # Zoom returns the meeting's generic join URL (per-registrant
        # personalized URLs are in Registration.zoom_registrant_join_url
        # and surface to the lobby separately).
        'ws_url': provider.client_join_url(video_room.room_name, token=token),
        'room_name': video_room.room_name,
        'room_uuid': str(video_room.uuid),
        'is_host': is_host,
        'waiting': waiting,
        'waiting_room_enabled': waiting_room_enabled,
        'recording_enabled_default': recording_default,
        'recording_active': recording_active,
    }


def _build_provider_metadata(content_object, model_name: str) -> dict:
    """Assemble provider.create_room metadata from the content object.

    Provider-specific fields (alternative_hosts for Zoom, start_time,
    duration) only matter to providers that consume them; LiveKit
    ignores everything except content_type / object_id.
    """
    meta: dict = {'content_type': model_name, 'object_id': content_object.id}

    title = getattr(content_object, 'title', None) or ''
    if title:
        meta['topic'] = title[:200]

    starts_at = getattr(content_object, 'starts_at', None)
    if starts_at is not None:
        meta['start_time'] = starts_at.isoformat()
        tz = getattr(content_object, 'timezone', '') or 'UTC'
        meta['timezone'] = tz

    duration = getattr(content_object, 'duration_minutes', None)
    if duration is not None:
        meta['duration_minutes'] = int(duration)

    settings = getattr(content_object, 'video_settings', None) or {}
    meta['waiting_room'] = bool(settings.get('waiting_room_enabled', True))

    # Alternative hosts: event owner + speaker owners. Speakers without a
    # linked User are skipped (Zoom needs a Licensed-user email under
    # the admin's account; non-Zoom-user speakers can be promoted to
    # co-host at runtime instead).
    emails: list[str] = []
    owner = getattr(content_object, 'owner', None)
    if owner is not None and getattr(owner, 'email', ''):
        emails.append(owner.email)
    speakers_rel = getattr(content_object, 'speakers', None)
    if speakers_rel is not None:
        try:
            speaker_emails = list(
                speakers_rel.filter(owner__isnull=False).values_list('owner__email', flat=True)
            )
            emails.extend(e for e in speaker_emails if e)
        except Exception:
            # speakers M2M may not exist on every content type (CourseSession
            # has 'instructors' instead). Best-effort.
            pass
    if emails:
        # De-dup, preserve order. Zoom expects a comma-separated string.
        seen: set[str] = set()
        deduped = [e for e in emails if not (e in seen or seen.add(e))]
        meta['alternative_hosts'] = ','.join(deduped)

    return meta


def _provision_room(content_object, *, max_participants: int = 0) -> VideoRoom:
    """Create a fresh VideoRoom row + provider-side meeting. DB-first.

    Order matters: insert the row first, then call the provider. If the
    provider call fails after the row is committed, the row is updated
    to ERROR and surfaces as a 502 to the caller. The reverse order
    would orphan a provider-side meeting with no DB record on a DB
    rollback.

    Caller is responsible for the transactional context (the start view
    holds ``SELECT FOR UPDATE`` on the parent for the whole call).
    """
    provider_name = getattr(django_settings, 'VIDEO_PROVIDER', 'livekit')
    ct = ContentType.objects.get_for_model(content_object)
    model_name = ct.model  # e.g. 'event', 'coursesession'
    room_name = generate_room_name(model_name, content_object.uuid)

    settings = (getattr(content_object, 'video_settings', None) or {})
    video_room = VideoRoom.objects.create(
        content_type=ct,
        object_id=content_object.id,
        room_id='',  # populated after provider create
        room_name=room_name,
        provider=provider_name,
        status=VideoRoom.Status.SCHEDULED,
        settings={
            'enabled': True,
            'screen_share': True,
            'recording_enabled': bool(settings.get('recording_enabled', False)),
            'waiting_room_enabled': bool(settings.get('waiting_room_enabled', False)),
            'transcription_enabled': bool(settings.get('transcription_enabled', False)),
        },
        max_participants=max_participants,
    )

    provider = get_video_provider()
    if not provider.is_configured():
        # In dev with a stub provider, skip the real provider call and
        # treat the row as ready. Production deployments always have a
        # real provider; this branch keeps test fixtures working.
        return video_room

    metadata = _build_provider_metadata(content_object, model_name)

    try:
        result = provider.create_room(
            name=room_name,
            metadata=metadata,
            max_participants=max_participants,
        )
    except Exception as e:
        logger.exception(
            "%s create_room failed for %s/%s; marking row ERROR",
            provider_name, model_name, content_object.uuid,
        )
        video_room.mark_error(str(e))
        raise

    update_fields = ['room_id', 'updated_at']
    video_room.room_id = result.room_id
    # Stash Zoom-specific identifiers when the provider returned them.
    rmeta = result.metadata or {}
    if rmeta.get('zoom_meeting_id'):
        video_room.zoom_meeting_id = str(rmeta['zoom_meeting_id'])
        update_fields.append('zoom_meeting_id')
    if rmeta.get('zoom_join_url'):
        video_room.zoom_join_url = rmeta['zoom_join_url']
        update_fields.append('zoom_join_url')
    video_room.save(update_fields=update_fields)
    return video_room


# ----------------------------------------------------------------------
# Event-publish provisioning (Zoom-aware).
#
# For Zoom we want the meeting to exist BEFORE registrations open so the
# registrant API has something to attach attendees to. LiveKit creates
# rooms on host-click; that path remains via _provision_room above. The
# function below is the pre-emptive variant — invoked from the event
# lifecycle signal when status transitions to PUBLISHED.
# ----------------------------------------------------------------------


def provision_meeting_for_event(event) -> VideoRoom | None:
    """Idempotently provision the Zoom meeting for an Event at publish time.

    No-ops when:
      * the configured provider is LiveKit (rooms are on-demand there),
      * the event is not in PUBLISHED/LIVE state,
      * a non-ENDED VideoRoom already exists for the event.

    Returns the VideoRoom row when one is created, else None.
    """
    from events.models import Event

    provider_name = getattr(django_settings, 'VIDEO_PROVIDER', 'livekit')
    if provider_name != 'zoom':
        return None
    if event.status not in (Event.Status.PUBLISHED, Event.Status.LIVE):
        return None

    ct = ContentType.objects.get_for_model(Event)
    existing = VideoRoom.objects.filter(
        content_type=ct,
        object_id=event.id,
    ).exclude(status=VideoRoom.Status.ENDED).first()
    if existing is not None:
        return existing

    try:
        return _provision_room(event, max_participants=event.max_attendees or 0)
    except Exception:
        # _provision_room already marks the row ERROR and logs.
        return None


def _start_meeting(
    *,
    content_object,
    parent_lock_qs,
    user,
    is_host: bool,
) -> tuple[VideoRoom, bool]:
    """Idempotent host-start.

    Returns ``(video_room, created)``. If a SCHEDULED-or-ACTIVE room
    already exists for the content object, returns it untouched
    (``created=False``) — race-safe because the partial unique index
    on (content_type, object_id) WHERE status='active' guarantees at
    most one active row, and the SELECT FOR UPDATE on the parent
    serialises concurrent inserts.

    Required: the caller is in a transaction and has issued
    ``parent_lock_qs.select_for_update().get(...)`` (or equivalent) so
    two simultaneous starts queue rather than racing the unique index.
    """
    if not is_host:
        raise PermissionError('only_host_can_start')

    existing = _get_live_room(content_object)
    if existing is not None:
        logger.info(
            "Start meeting idempotent: existing room=%s status=%s for %s",
            existing.uuid, existing.status, content_object,
        )
        return existing, False

    try:
        video_room = _provision_room(
            content_object,
            max_participants=getattr(content_object, 'max_attendees', 0) or 0,
        )
    except IntegrityError:
        # The partial unique index fired — another request created the
        # active room between our _get_live_room check and the INSERT.
        # Re-read and return whatever's now there.
        existing = _get_live_room(content_object)
        if existing is None:
            raise
        return existing, False

    logger.info(
        "Started meeting: video_room=%s for %s (host_user=%s)",
        video_room.uuid, content_object, user.id,
    )
    return video_room, True


def _end_meeting(video_room: VideoRoom, *, ended_by_user_id: int) -> None:
    """Tear down a live meeting.

    Marks ``settings['ended_by_host']=True`` for analytics, then calls
    LiveKit ``delete_room`` which boots all participants and triggers
    ``room_finished`` — the existing webhook handler stops recordings,
    finalizes the transcript, and transitions the row to ENDED.

    Idempotent: calling on an already-ENDED row is a no-op. Calling
    when LiveKit returns "room not found" is also a no-op (the row
    will be flipped to ENDED by the empty-room timeout if not already).
    """
    if video_room.status == VideoRoom.Status.ENDED:
        return

    # Annotate the row before the destroy so the webhook handler can
    # distinguish "host ended" from "empty timeout" for analytics.
    settings = dict(video_room.settings or {})
    settings['ended_by_host'] = True
    settings['ended_by_user_id'] = ended_by_user_id
    video_room.settings = settings
    video_room.save(update_fields=['settings', 'updated_at'])

    provider = get_video_provider()
    if not provider.is_configured():
        # Dev/test path: no real LiveKit, just mark the row ENDED here.
        video_room.mark_ended()
        return

    try:
        provider.delete_room(video_room.room_name)
    except Exception:
        # delete_room failures are non-fatal — LiveKit's empty-room
        # timeout will still fire room_finished and the row will end.
        # Log loudly and let the webhook do the rest.
        logger.exception(
            "LiveKit delete_room failed for %s; relying on empty-room "
            "timeout to fire room_finished",
            video_room.room_name,
        )


# ---------------------------------------------------------------------------
# Event endpoints
# ---------------------------------------------------------------------------


def _resolve_event_or_404(event_uuid):
    from events.models import Event
    try:
        return Event.objects.get(uuid=event_uuid, deleted_at__isnull=True)
    except Event.DoesNotExist:
        return None


def _event_settings(event) -> tuple[bool, bool]:
    s = event.video_settings or {}
    return (
        bool(s.get('waiting_room_enabled', False)),
        bool(s.get('recording_enabled', False)),
    )


def _event_attendee_can_join(user, event) -> bool:
    from registrations.models import Registration
    return Registration.objects.filter(
        event=event,
        user=user,
        status__in=['confirmed', 'attended'],
        deleted_at__isnull=True,
    ).exists()


class StartEventMeetingView(generics.GenericAPIView):
    """POST /api/v1/events/{event_uuid}/meetings/start/

    Host creates a fresh VideoRoom for the event and gets a host JWT.
    Idempotent: if a meeting is already live, the host gets a token for
    the existing room rather than a 409 — Zoom-style "rejoin" UX.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_uuid):
        event = _resolve_event_or_404(event_uuid)
        if event is None:
            return Response({'error': 'event_not_found'}, status=status.HTTP_404_NOT_FOUND)
        if not is_event_host(request.user, event):
            return Response({'error': 'host_only'}, status=status.HTTP_403_FORBIDDEN)
        if not (event.video_settings or {}).get('enabled', False):
            return Response(
                {'error': 'video_not_enabled', 'detail': 'Enable video on this event before starting a meeting.'},
                status=status.HTTP_409_CONFLICT,
            )

        from events.models import Event
        with transaction.atomic():
            # Lock the parent so two simultaneous host clicks serialize.
            Event.objects.select_for_update().get(pk=event.pk)
            video_room, _created = _start_meeting(
                content_object=event,
                parent_lock_qs=Event.objects,
                user=request.user,
                is_host=True,
            )

        waiting_room_enabled, recording_default = _event_settings(event)

        # NOTE: recording auto-start is NOT triggered here. The
        # `room_started` webhook (fired when the first participant
        # actually connects) is the single source of truth — see
        # `_on_room_started` → `start_recording_if_enabled` in
        # tasks.py. Calling `ensure_recording_started` from here
        # would spawn a LiveKit egress against an empty room, which
        # historically created duplicate egress IDs and orphan
        # recordings. The HTTP API mints a token; the webhook handler
        # runs side-effects.

        if is_platform_admin(request.user) and event.owner_id != request.user.id:
            logger.info(
                "admin_host_override start_meeting event=%s user=%s",
                event.uuid, request.user.id,
            )

        data = _build_join_response(
            video_room=video_room,
            user_identity=str(request.user.uuid),
            user_display_name=request.user.full_name or request.user.email,
            is_host=True,
            waiting_room_enabled=waiting_room_enabled,
            recording_default=recording_default,
        )
        return Response(JoinVideoResponseSerializer(data).data)


class JoinEventMeetingView(generics.GenericAPIView):
    """POST /api/v1/events/{event_uuid}/meetings/join/

    Issues a JWT for the active meeting. Returns 409 ``no_active_meeting``
    when the host hasn't started one — frontend keeps polling
    ``/meetings/active/`` until that flips.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_uuid):
        event = _resolve_event_or_404(event_uuid)
        if event is None:
            return Response({'error': 'event_not_found'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_event_host(request.user, event)
        if not is_host and not _event_attendee_can_join(request.user, event):
            return Response(
                {'error': 'not_registered'},
                status=status.HTTP_403_FORBIDDEN,
            )

        video_room = _get_live_room(event)
        if video_room is None or video_room.status == VideoRoom.Status.SCHEDULED and not is_host:
            # Hosts can join their own SCHEDULED room (the one they just
            # created via /start/); attendees must wait for ACTIVE.
            return Response(
                {'error': 'no_active_meeting', 'detail': 'The host has not started this meeting yet.'},
                status=status.HTTP_409_CONFLICT,
            )

        waiting_room_enabled, recording_default = _event_settings(event)
        data = _build_join_response(
            video_room=video_room,
            user_identity=str(request.user.uuid),
            user_display_name=request.user.full_name or request.user.email,
            is_host=is_host,
            waiting_room_enabled=waiting_room_enabled,
            recording_default=recording_default,
        )
        return Response(JoinVideoResponseSerializer(data).data)


def _build_active_response(video_room: Optional[VideoRoom], *, is_host: bool) -> dict:
    """Wire shape for /meetings/active/.

    Returns the full lifecycle so the lobby can render the right UI
    state without keeping its own client-side history. Four cases:

      - status='active'    — meeting is live; lobby shows "Join now"
      - status='scheduled' — host has clicked Start but no participant
                             has connected yet; lobby shows "Join as
                             host" for the host (so they can rejoin
                             their own pending room) and "Waiting for
                             host" for attendees
      - status='ended'     — most recent room is finalized; lobby
                             shows "Meeting has ended" / "Start a
                             new meeting" depending on role
      - status='none'      — no VideoRoom has ever been created for
                             this content object; lobby shows
                             "Waiting for host" / "Start meeting"

    `is_host` is computed server-side using the same predicate as the
    join endpoint so the lobby doesn't have to duplicate it.
    """
    if video_room is None:
        return {'status': 'none', 'is_host': is_host}
    return {
        'status': video_room.status,
        'room_uuid': str(video_room.uuid),
        'started_at': video_room.started_at.isoformat() if video_room.started_at else None,
        'ended_at': video_room.ended_at.isoformat() if video_room.ended_at else None,
        'is_host': is_host,
    }


class ActiveEventMeetingView(generics.GenericAPIView):
    """GET /api/v1/events/{event_uuid}/meetings/active/

    Cheap polling endpoint used by the lobby every 10s. Returns the
    most recent VideoRoom's lifecycle status (or `none`). Never
    returns a token — the frontend POSTs to ``/join/`` for that.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, event_uuid):
        event = _resolve_event_or_404(event_uuid)
        if event is None:
            return Response({'error': 'event_not_found'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_event_host(request.user, event)
        if not is_host and not _event_attendee_can_join(request.user, event):
            return Response({'error': 'not_registered'}, status=status.HTTP_403_FORBIDDEN)

        return Response(_build_active_response(_get_latest_room(event), is_host=is_host))


# ---------------------------------------------------------------------------
# Public (registration_uuid) attendee endpoints — join + active only.
# Public guests never start meetings.
# ---------------------------------------------------------------------------


def _resolve_registration(event, registration_uuid):
    from registrations.models import Registration
    try:
        registration = Registration.objects.get(
            uuid=registration_uuid,
            event=event,
            deleted_at__isnull=True,
        )
    except Registration.DoesNotExist:
        return None
    if registration.status not in ('confirmed', 'attended'):
        return None
    return registration


class PublicJoinEventMeetingView(generics.GenericAPIView):
    """POST /api/v1/public/events/{event_uuid}/meetings/join/

    Body: ``{"registration_uuid": "..."}``. Returns same shape as the
    authenticated join endpoint, with ``is_host=False`` baked in.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, event_uuid):
        registration_uuid = (
            request.data.get('registration_uuid') if isinstance(request.data, dict) else None
        )
        if not registration_uuid:
            return Response(
                {'error': 'registration_uuid_required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = _resolve_event_or_404(event_uuid)
        if event is None:
            return Response({'error': 'event_not_found'}, status=status.HTTP_404_NOT_FOUND)

        registration = _resolve_registration(event, registration_uuid)
        if registration is None:
            return Response(
                {'error': 'registration_not_found_or_unconfirmed'},
                status=status.HTTP_403_FORBIDDEN,
            )

        video_room = _get_live_room(event)
        if video_room is None or video_room.status != VideoRoom.Status.ACTIVE:
            return Response(
                {'error': 'no_active_meeting'},
                status=status.HTTP_409_CONFLICT,
            )

        waiting_room_enabled, recording_default = _event_settings(event)
        data = _build_join_response(
            video_room=video_room,
            user_identity=f"guest-{registration.uuid}",
            user_display_name=registration.full_name or registration.email,
            is_host=False,
            waiting_room_enabled=waiting_room_enabled,
            recording_default=recording_default,
        )
        return Response(JoinVideoResponseSerializer(data).data)


class PublicActiveEventMeetingView(generics.GenericAPIView):
    """GET /api/v1/public/events/{event_uuid}/meetings/active/?registration_uuid=...

    Polling endpoint for guest attendees. Same payload shape as the
    authenticated variant (`status`, `room_uuid`, `started_at`,
    `ended_at`), plus a 403 when the registration_uuid is missing or
    invalid (so callers can distinguish "no meeting yet" from "you
    don't belong here").
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, event_uuid):
        registration_uuid = request.query_params.get('registration_uuid')
        if not registration_uuid:
            return Response(
                {'error': 'registration_uuid_required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = _resolve_event_or_404(event_uuid)
        if event is None:
            return Response({'error': 'event_not_found'}, status=status.HTTP_404_NOT_FOUND)

        registration = _resolve_registration(event, registration_uuid)
        if registration is None:
            return Response(
                {'error': 'registration_not_found_or_unconfirmed'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(_build_active_response(_get_latest_room(event), is_host=False))


# ---------------------------------------------------------------------------
# CourseSession endpoints — direct mirror of the event endpoints
# ---------------------------------------------------------------------------


def _resolve_course_session_or_404(course_uuid, session_uuid):
    from learning.models import Course, CourseSession
    try:
        course = Course.objects.get(uuid=course_uuid)
    except Course.DoesNotExist:
        return None, None
    try:
        session = CourseSession.objects.get(uuid=session_uuid, course=course)
    except CourseSession.DoesNotExist:
        return course, None
    return course, session


def _session_settings(session) -> tuple[bool, bool]:
    s = getattr(session, 'video_settings', None) or {}
    return (
        bool(s.get('waiting_room_enabled', False)),
        bool(s.get('recording_enabled', False)),
    )


def _session_attendee_can_join(user, course) -> bool:
    from learning.models import CourseEnrollment
    return CourseEnrollment.objects.filter(
        course=course,
        user=user,
        status='active',
    ).exists()


class StartCourseSessionMeetingView(generics.GenericAPIView):
    """POST /api/v1/courses/{course_uuid}/sessions/{session_uuid}/meetings/start/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_uuid, session_uuid):
        course, session = _resolve_course_session_or_404(course_uuid, session_uuid)
        if course is None:
            return Response({'error': 'course_not_found'}, status=status.HTTP_404_NOT_FOUND)
        if session is None:
            return Response({'error': 'session_not_found'}, status=status.HTTP_404_NOT_FOUND)
        if not is_course_session_host(request.user, course):
            return Response({'error': 'host_only'}, status=status.HTTP_403_FORBIDDEN)
        if not (getattr(session, 'video_settings', None) or {}).get('enabled', False):
            return Response(
                {'error': 'video_not_enabled', 'detail': 'Enable video on this session before starting a meeting.'},
                status=status.HTTP_409_CONFLICT,
            )

        from learning.models import CourseSession
        with transaction.atomic():
            CourseSession.objects.select_for_update().get(pk=session.pk)
            video_room, _created = _start_meeting(
                content_object=session,
                parent_lock_qs=CourseSession.objects,
                user=request.user,
                is_host=True,
            )

        waiting_room_enabled, recording_default = _session_settings(session)
        # Recording auto-start happens in the room_started webhook handler,
        # not here. See StartEventMeetingView for the rationale.

        data = _build_join_response(
            video_room=video_room,
            user_identity=str(request.user.uuid),
            user_display_name=request.user.full_name or request.user.email,
            is_host=True,
            waiting_room_enabled=waiting_room_enabled,
            recording_default=recording_default,
        )
        return Response(JoinVideoResponseSerializer(data).data)


class JoinCourseSessionMeetingView(generics.GenericAPIView):
    """POST /api/v1/courses/{course_uuid}/sessions/{session_uuid}/meetings/join/"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_uuid, session_uuid):
        course, session = _resolve_course_session_or_404(course_uuid, session_uuid)
        if course is None:
            return Response({'error': 'course_not_found'}, status=status.HTTP_404_NOT_FOUND)
        if session is None:
            return Response({'error': 'session_not_found'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_course_session_host(request.user, course)
        if not is_host and not _session_attendee_can_join(request.user, course):
            return Response({'error': 'not_enrolled'}, status=status.HTTP_403_FORBIDDEN)

        video_room = _get_live_room(session)
        if video_room is None or (video_room.status == VideoRoom.Status.SCHEDULED and not is_host):
            return Response(
                {'error': 'no_active_meeting'},
                status=status.HTTP_409_CONFLICT,
            )

        waiting_room_enabled, recording_default = _session_settings(session)
        data = _build_join_response(
            video_room=video_room,
            user_identity=str(request.user.uuid),
            user_display_name=request.user.full_name or request.user.email,
            is_host=is_host,
            waiting_room_enabled=waiting_room_enabled,
            recording_default=recording_default,
        )
        return Response(JoinVideoResponseSerializer(data).data)


class ActiveCourseSessionMeetingView(generics.GenericAPIView):
    """GET /api/v1/courses/{course_uuid}/sessions/{session_uuid}/meetings/active/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_uuid, session_uuid):
        course, session = _resolve_course_session_or_404(course_uuid, session_uuid)
        if course is None:
            return Response({'error': 'course_not_found'}, status=status.HTTP_404_NOT_FOUND)
        if session is None:
            return Response({'error': 'session_not_found'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_course_session_host(request.user, course)
        if not is_host and not _session_attendee_can_join(request.user, course):
            return Response({'error': 'not_enrolled'}, status=status.HTTP_403_FORBIDDEN)

        return Response(_build_active_response(_get_latest_room(session), is_host=is_host))


# ---------------------------------------------------------------------------
# End-meeting — host-only. Scoped on room_uuid (not event/session) because
# by the time you're ending you already have the room.
# ---------------------------------------------------------------------------


class EndMeetingView(generics.GenericAPIView):
    """POST /api/v1/video/rooms/{room_uuid}/end/

    Host-only "End meeting for all". Calls LiveKit ``delete_room`` →
    LiveKit boots everyone → ``room_finished`` webhook stops recordings,
    finalises transcript, marks the row ENDED.

    Idempotent: ending an already-ENDED meeting is a 200 no-op.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_uuid):
        try:
            video_room = VideoRoom.objects.select_related('content_type').get(uuid=room_uuid)
        except VideoRoom.DoesNotExist:
            return Response({'error': 'room_not_found'}, status=status.HTTP_404_NOT_FOUND)

        # Only the meeting's host can end it. Resolve via the content
        # object — for events that's `is_event_host`, for course
        # sessions it's `is_course_session_host`. Anything else falls
        # back to "platform admin can override".
        from events.models import Event
        from learning.models import CourseSession

        parent = video_room.content_object
        if isinstance(parent, Event):
            authorized = is_event_host(request.user, parent)
        elif isinstance(parent, CourseSession):
            authorized = is_course_session_host(request.user, parent.course)
        else:
            authorized = is_platform_admin(request.user)

        if not authorized:
            return Response({'error': 'host_only'}, status=status.HTTP_403_FORBIDDEN)

        _end_meeting(video_room, ended_by_user_id=request.user.id)
        return Response({'status': 'ending', 'room_uuid': str(video_room.uuid)})
