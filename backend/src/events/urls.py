"""
Events app URL routing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from certificates.urls import certificate_router
from feedback.views import EventFeedbackFieldViewSet
from integrations.urls import email_router
from registrations.views import EventRegistrationViewSet

from . import views

app_name = 'events'

# Main event router
router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'speakers', views.SpeakerViewSet, basename='speaker')

# Nested registration router
registration_router = DefaultRouter()
registration_router.register(r'registrations', EventRegistrationViewSet, basename='event-registration')

# Custom fields router
custom_field_router = DefaultRouter()
custom_field_router.register(r'custom-fields', views.EventCustomFieldViewSet, basename='event-custom-field')

# Sessions router (C1: Multi-Session Events API)
session_router = DefaultRouter()
session_router.register(r'sessions', views.EventSessionViewSet, basename='event-session')

# Feedback fields router
feedback_field_router = DefaultRouter()
feedback_field_router.register(r'feedback-fields', EventFeedbackFieldViewSet, basename='event-feedback-field')

urlpatterns = [
    # Main events API
    path('', include(router.urls)),
    # Nested routes under events/{event_uuid}/
    path('events/<uuid:event_uuid>/', include(registration_router.urls)),
    path('events/<uuid:event_uuid>/', include(custom_field_router.urls)),
    path('events/<uuid:event_uuid>/', include(session_router.urls)),
    path('events/<uuid:event_uuid>/', include(feedback_field_router.urls)),
    path('events/<uuid:event_uuid>/', include(certificate_router.urls)),
    path('events/<uuid:event_uuid>/', include(email_router.urls)),
    # Public events
    path('public/events/', views.PublicEventListView.as_view(), name='public_event_list'),
    path('public/events/<str:identifier>/', views.PublicEventDetailView.as_view(), name='public_event_detail'),
    # Speaker self-service: events I'm speaking at
    path('events/my-speaking/', views.MySpeakingEventsView.as_view(), name='my_speaking_events'),
]
