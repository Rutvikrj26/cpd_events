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
    # Main certificate API
    path('', include(router.urls)),
    # Public verification
    path('public/certificates/verify/<str:code>/', views.CertificateVerificationView.as_view(), name='verify'),
]

# User's certificates are in accounts URLs
