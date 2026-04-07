"""URL configuration for CPD Events backend."""

from django.contrib import admin
from django.urls import include, path

from registrations import views as registration_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # API v1
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('events.urls')),
    path('api/v1/registrations/', include('registrations.urls')),
    path('api/v1/', include('certificates.urls')),
    path('api/v1/', include('contacts.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('learning.urls')),
    path('api/v1/feedback/', include('feedback.urls')),
    path('api/v1/', include('promo_codes.urls')),
    path('api/v1/badges/', include('badges.urls')),
    path('api/v1/', include('conferencing.urls')),
    # Public registration (needs to be at root, not under /registrations/)
    path(
        'api/v1/public/events/<uuid:event_uuid>/register/',
        registration_views.PublicRegistrationView.as_view(),
        name='public_event_register',
    ),
    path(
        'api/v1/public/registrations/<uuid:uuid>/payment-intent/',
        registration_views.RegistrationPaymentIntentView.as_view(),
        name='public_registration_payment_intent',
    ),
    path(
        'api/v1/public/registrations/<uuid:uuid>/confirm-payment/',
        registration_views.ConfirmPaymentView.as_view(),
        name='public_registration_confirm_payment',
    ),
    # Internal & Common
    path('api/common/', include('common.urls')),
]

# Serve media files in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
