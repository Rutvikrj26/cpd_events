"""URL configuration for the conferencing app."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from conferencing.meetings import (
    ActiveCourseSessionMeetingView,
    ActiveEventMeetingView,
    EndMeetingView,
    JoinCourseSessionMeetingView,
    JoinEventMeetingView,
    PublicActiveEventMeetingView,
    PublicJoinEventMeetingView,
    StartCourseSessionMeetingView,
    StartEventMeetingView,
)
from conferencing.views import (
    RecordingTranscriptExportView,
    RecordingTranscriptSearchView,
    RecordingTranscriptView,
    TranscriptFinalizeView,
    TranscriptIngestView,
    TranscriptSegmentEditView,
    TranscriptSegmentHistoryView,
    VideoRecordingViewSet,
    VideoRoomViewSet,
    VideoStatusView,
    VideoWebhookView,
)

router = DefaultRouter()
router.register(r'video/rooms', VideoRoomViewSet, basename='video-rooms')
router.register(r'video/recordings', VideoRecordingViewSet, basename='video-recordings')

urlpatterns = [
    path('video/status/', VideoStatusView.as_view(), name='video-status'),

    # ----------------------------------------------------------------------
    # Meetings — Zoom-model lifecycle (start / join / end / active).
    # Each meeting session is its own VideoRoom; ENDED is terminal; the
    # host explicitly starts and ends each session. See
    # conferencing/meetings.py for the design rationale.
    # ----------------------------------------------------------------------
    path(
        'events/<uuid:event_uuid>/meetings/start/',
        StartEventMeetingView.as_view(),
        name='event-meeting-start',
    ),
    path(
        'events/<uuid:event_uuid>/meetings/join/',
        JoinEventMeetingView.as_view(),
        name='event-meeting-join',
    ),
    path(
        'events/<uuid:event_uuid>/meetings/active/',
        ActiveEventMeetingView.as_view(),
        name='event-meeting-active',
    ),
    path(
        'public/events/<uuid:event_uuid>/meetings/join/',
        PublicJoinEventMeetingView.as_view(),
        name='public-event-meeting-join',
    ),
    path(
        'public/events/<uuid:event_uuid>/meetings/active/',
        PublicActiveEventMeetingView.as_view(),
        name='public-event-meeting-active',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:session_uuid>/meetings/start/',
        StartCourseSessionMeetingView.as_view(),
        name='course-session-meeting-start',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:session_uuid>/meetings/join/',
        JoinCourseSessionMeetingView.as_view(),
        name='course-session-meeting-join',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:session_uuid>/meetings/active/',
        ActiveCourseSessionMeetingView.as_view(),
        name='course-session-meeting-active',
    ),
    path(
        'video/rooms/<uuid:room_uuid>/end/',
        EndMeetingView.as_view(),
        name='video-room-end-meeting',
    ),

    # Webhook (no auth — signature verified internally)
    path('webhooks/video/', VideoWebhookView.as_view(), name='video-webhook'),

    # ----------------------------------------------------------------------
    # Transcripts
    # ----------------------------------------------------------------------
    # Public reads — keyed on the recording the user is already navigating
    # so access control inherits from VideoRecording's existing scope.
    path(
        'video/recordings/<uuid:recording_uuid>/transcript/',
        RecordingTranscriptView.as_view(),
        name='recording-transcript',
    ),
    path(
        'video/recordings/<uuid:recording_uuid>/transcript/search/',
        RecordingTranscriptSearchView.as_view(),
        name='recording-transcript-search',
    ),
    path(
        'video/recordings/<uuid:recording_uuid>/transcript/export/',
        RecordingTranscriptExportView.as_view(),
        name='recording-transcript-export',
    ),

    # Internal — agent-only, HMAC-authenticated. Mounted under /internal/
    # so reverse-proxy rules / WAFs can block external access entirely
    # in production deployments where the agent runs on a private network.
    path(
        'internal/transcripts/<uuid:transcript_uuid>/segments/',
        TranscriptIngestView.as_view(),
        name='transcript-ingest',
    ),
    path(
        'internal/transcripts/<uuid:transcript_uuid>/finalize/',
        TranscriptFinalizeView.as_view(),
        name='transcript-finalize',
    ),

    # Organiser edits — gated to event hosts (see _user_can_edit_transcript).
    # Mounted under /transcripts/ rather than /video/recordings/ because
    # the panel hits this with the segment_uuid it already has from the
    # read endpoint; no need to thread the recording uuid through.
    path(
        'transcripts/<uuid:transcript_uuid>/segments/<uuid:segment_uuid>/',
        TranscriptSegmentEditView.as_view(),
        name='transcript-segment-edit',
    ),
    path(
        'transcripts/<uuid:transcript_uuid>/segments/<uuid:segment_uuid>/history/',
        TranscriptSegmentHistoryView.as_view(),
        name='transcript-segment-history',
    ),
] + router.urls
