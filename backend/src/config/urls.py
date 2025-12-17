"""URL configuration for CPD Events backend."""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('events.urls')),
    path('api/v1/', include('registrations.urls')),
    path('api/v1/', include('certificates.urls')),
    path('api/v1/', include('contacts.urls')),
    path('api/v1/', include('integrations.urls')),
    path('api/v1/', include('billing.urls')),
    path('api/v1/', include('learning.urls')),
    
    # Webhooks
    path('webhooks/stripe/', include('billing.webhooks')),
    
    # OpenAPI Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
