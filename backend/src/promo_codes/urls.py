"""
Promo Codes URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PromoCodeViewSet, PublicPromoCodeViewSet

app_name = 'promo_codes'

router = DefaultRouter()
router.register(r'promo-codes', PromoCodeViewSet, basename='promo-code')

# Public validation endpoint (no prefix, will be at /api/v1/public/promo-codes/validate/)
public_router = DefaultRouter()
public_router.register(r'public/promo-codes', PublicPromoCodeViewSet, basename='public-promo-code')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(public_router.urls)),
]
