"""URL configuration for the conferencing app."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from conferencing.views import (
    JoinCourseSessionVideoView,
    JoinVideoGuestView,
    JoinVideoView,
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
    path(
        'events/<uuid:event_uuid>/join-video/',
        JoinVideoView.as_view(),
        name='event-join-video',
    ),
    path(
        'public/events/<uuid:event_uuid>/join-video/',
        JoinVideoGuestView.as_view(),
        name='public-event-join-video',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:session_uuid>/join-video/',
        JoinCourseSessionVideoView.as_view(),
        name='course-session-join-video',
    ),
    # Webhook (no auth — signature verified internally)
    path('webhooks/video/', VideoWebhookView.as_view(), name='video-webhook'),
] + router.urls
