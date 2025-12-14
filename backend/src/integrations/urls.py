"""
Integrations app URL routing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'integrations'

# Recordings router (for nested under events)
recording_router = DefaultRouter()
recording_router.register(r'recordings', views.EventRecordingViewSet, basename='event-recording')

# Email logs router
email_router = DefaultRouter()
email_router.register(r'emails', views.EmailLogViewSet, basename='event-email')

urlpatterns = [
    # Webhooks
    path('webhooks/zoom/', views.ZoomWebhookView.as_view(), name='zoom_webhook'),
]

# Note: Recording and email routes are included via events URLs
