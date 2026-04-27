"""URL configuration for CPD Events backend."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from billing.webhooks import StripeWebhookView
from registrations import views as registration_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    # OpenAPI 3.0 schema — consumed by frontend's openapi-typescript codegen.
    # Walks the full urlconf; every endpoint in the public API appears here.
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/v1/schema/ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='schema-ui',
    ),
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
        'api/v1/public/registrations/<uuid:uuid>/start-checkout/',
        registration_views.StartCheckoutView.as_view(),
        name='public_registration_start_checkout',
    ),
    path(
        'api/v1/public/registrations/<uuid:uuid>/lobby/',
        registration_views.RegistrationLobbyView.as_view(),
        name='public_registration_lobby',
    ),
    # Internal & Common
    path('api/common/', include('common.urls')),
]

# Serve media files in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
