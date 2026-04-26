"""
Certificates app URL routing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'certificates'

# Certificate templates router
router = DefaultRouter()
router.register(r'certificate-templates', views.CertificateTemplateViewSet, basename='certificate-template')
router.register(r'certificates', views.MyCertificateViewSet, basename='my-certificate')

# Nested under events
certificate_router = DefaultRouter()
certificate_router.register(r'certificates', views.EventCertificateViewSet, basename='event-certificate')

urlpatterns = [
    # Organization-wide listing + unified issue endpoint (must come before the
    # router so the `organization` / `issue` paths don't collide with the
    # detail lookup of MyCertificateViewSet).
    path(
        'certificates/organization/',
        views.OrganizationCertificateListView.as_view(),
        name='organization-certificates',
    ),
    path(
        'certificates/issue/',
        views.CertificateIssueView.as_view(),
        name='certificate-issue',
    ),
    path(
        'certificates/<uuid:uuid>/revoke/',
        views.CertificateRevokeView.as_view(),
        name='certificate-revoke',
    ),
    # Main certificate API
    path('', include(router.urls)),
    # Public verification
    path('public/certificates/verify/<str:code>/', views.CertificateVerificationView.as_view(), name='verify'),
    path(
        'public/certificates/verify/<str:code>/qr.svg',
        views.CertificateQrCodeView.as_view(),
        name='verify-qr',
    ),
]

# User's certificates are in accounts URLs
