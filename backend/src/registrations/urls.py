"""
Registrations app URL routing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'registrations'

router = DefaultRouter()
router.register(r'', views.MyRegistrationViewSet, basename='my-registration')

urlpatterns = [
    path('', include(router.urls)),
    # Guest registration linking
    path('users/me/link-registrations/', views.LinkRegistrationsView.as_view(), name='link_registrations'),
    # Public registration
    path('public/events/<uuid:event_uuid>/register/', views.PublicRegistrationView.as_view(), name='public_register'),
    # Start (or resume) a Checkout Session for a pending paid registration.
    path(
        'public/registrations/<uuid:uuid>/start-checkout/',
        views.StartCheckoutView.as_view(),
        name='start_checkout',
    ),
]

# MyRegistrationViewSet is included in accounts URLs (/users/me/registrations/)
