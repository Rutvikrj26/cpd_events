"""
Integrations app URL routing.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'integrations'

# Recordings router (for nested under events)
recording_router = DefaultRouter()
recording_router.register(r'recordings', views.EventRecordingViewSet, basename='event-recording')

# Email logs router
email_router = DefaultRouter()
email_router.register(r'emails', views.EmailLogViewSet, basename='event-email')

# My recordings router
my_recordings_router = DefaultRouter()
my_recordings_router.register(r'recordings', views.MyRecordingsViewSet, basename='my-recordings')

urlpatterns = [
    # Webhooks
    path('webhooks/zoom/', views.ZoomWebhookView.as_view(), name='zoom_webhook'),
    # OAuth
    path('zoom/initiate/', views.ZoomInitiateView.as_view(), name='zoom_initiate'),
    path('zoom/callback/', views.ZoomCallbackView.as_view(), name='zoom_callback'),
    path('zoom/status/', views.ZoomStatusView.as_view(), name='zoom_status'),
    path('zoom/disconnect/', views.ZoomDisconnectView.as_view(), name='zoom_disconnect'),
    # Zoom meetings list
    path('zoom/meetings/', views.ZoomMeetingsListView.as_view(), name='zoom_meetings'),
]

# Note: Recording and email routes are included via events URLs
