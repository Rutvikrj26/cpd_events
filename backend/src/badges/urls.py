from django.urls import path, include
from rest_framework.routers import DefaultRouter
from badges.views import BadgeTemplateViewSet, IssuedBadgeViewSet

router = DefaultRouter()
router.register(r'templates', BadgeTemplateViewSet, basename='badge-templates')
router.register(r'issued', IssuedBadgeViewSet, basename='issued-badges')

urlpatterns = [
    path('', include(router.urls)),
]
