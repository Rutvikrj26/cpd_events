"""Promo Codes URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PromoCodeViewSet

app_name = 'promo_codes'

router = DefaultRouter()
router.register(r'promo-codes', PromoCodeViewSet, basename='promo-code')

urlpatterns = [path('', include(router.urls))]
