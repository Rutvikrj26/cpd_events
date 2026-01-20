"""URL configuration for CPD Events backend."""

from django.contrib import admin
from django.urls import include, path

# from drf_yasg import openapi
# from drf_yasg.views import get_schema_view
from billing.webhooks import StripeWebhookView
from registrations import views as registration_views
from common.views import HealthCheckView, ReadinessCheckView

# OpenAPI Schema configuration
# schema_view = get_schema_view(
#     openapi.Info(
#         title="CPD Events API",
#         default_version='v1',
#         description="API for managing events, certificates, and CPD tracking",
#         contact=openapi.Contact(email="rutvikrj26@gmail.com"),
#         license=openapi.License(name="MIT"),
#     ),
#     public=True,
#     permission_classes=[permissions.AllowAny],
# )

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health checks
    path("api/health/", HealthCheckView.as_view(), name="health_check"),
    path("api/ready/", ReadinessCheckView.as_view(), name="readiness_check"),
    # API v1
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("events.urls")),
    path("api/v1/registrations/", include("registrations.urls")),
    path("api/v1/", include("certificates.urls")),
    path("api/v1/", include("contacts.urls")),
    path("api/v1/integrations/", include("integrations.urls")),
    path("api/v1/", include("billing.urls")),
    path("api/v1/", include("learning.urls")),
    path("api/v1/feedback/", include("feedback.urls")),
    path("api/v1/", include("promo_codes.urls")),
    path("api/v1/badges/", include("badges.urls")),
    # Public registration (needs to be at root, not under /registrations/)
    path(
        "api/v1/public/events/<uuid:event_uuid>/register/",
        registration_views.PublicRegistrationView.as_view(),
        name="public_event_register",
    ),
    path(
        "api/v1/public/registrations/<uuid:uuid>/payment-intent/",
        registration_views.RegistrationPaymentIntentView.as_view(),
        name="public_registration_payment_intent",
    ),
    path(
        "api/v1/public/registrations/<uuid:uuid>/confirm-payment/",
        registration_views.ConfirmPaymentView.as_view(),
        name="public_registration_confirm_payment",
    ),
    # Webhooks
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe_webhook"),
    # Internal & Common
    path("api/common/", include("common.urls")),
    # OpenAPI Schema & Docs
    # re_path(r'^api/schema(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    # path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
]

# Serve media files in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
