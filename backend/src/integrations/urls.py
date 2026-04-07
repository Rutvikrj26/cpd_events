"""
Integrations app URL routing.
"""

from rest_framework.routers import DefaultRouter

from . import views

app_name = 'integrations'

# Email logs router
email_router = DefaultRouter()
email_router.register(r'emails', views.EmailLogViewSet, basename='event-email')

urlpatterns = []

# Note: Email routes are included via events URLs
