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
    # Payment intent (resume payment)
    path(
        'public/registrations/<uuid:uuid>/payment-intent/', views.RegistrationPaymentIntentView.as_view(), name='payment_intent'
    ),
    # Payment confirmation (sync)
    path('public/registrations/<uuid:uuid>/confirm-payment/', views.ConfirmPaymentView.as_view(), name='confirm_payment'),
]

# MyRegistrationViewSet is included in accounts URLs (/users/me/registrations/)
