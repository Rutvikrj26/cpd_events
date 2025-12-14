"""
Registrations app URL routing.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'registrations'

router = DefaultRouter()
router.register(r'', views.MyRegistrationViewSet, basename='my-registration')

urlpatterns = [
    # Guest registration linking
    path('users/me/link-registrations/', views.LinkRegistrationsView.as_view(), name='link_registrations'),
    
    # Public registration
    path('public/events/<uuid:event_uuid>/register/', views.PublicRegistrationView.as_view(), name='public_register'),
]

# MyRegistrationViewSet is included in accounts URLs (/users/me/registrations/)
