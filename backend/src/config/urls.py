"""URL configuration for CPD Events backend."""

from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from billing.webhooks import StripeWebhookView

# OpenAPI Schema configuration
schema_view = get_schema_view(
    openapi.Info(
        title="CPD Events API",
        default_version='v1',
        description="API for managing events, certificates, and CPD tracking",
        contact=openapi.Contact(email="rutvikrj26@gmail.com"),
        license=openapi.License(name="MIT"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # API v1
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('events.urls')),
    path('api/v1/registrations/', include('registrations.urls')),
    path('api/v1/', include('certificates.urls')),
    path('api/v1/', include('contacts.urls')),
    path('api/v1/', include('integrations.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('learning.urls')),
    # Webhooks
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe_webhook'),
    # Internal & Common
    path('api/common/', include('common.urls')),
    # OpenAPI Schema & Docs
    re_path(r'^api/schema(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
]
